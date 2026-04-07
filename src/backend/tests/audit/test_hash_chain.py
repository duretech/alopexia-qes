"""Unit tests for the audit hash chain computation.

These tests verify the pure-function hash chain module WITHOUT any
database dependency. They exercise:
  - Deterministic hash output for known inputs
  - GENESIS_HASH usage for the first event
  - Chain linkage (previous_hash → current_hash)
  - Canonical JSON serialisation of detail payloads
  - Handling of None/null fields
  - Tamper detection (changing any field changes the hash)
  - verify_chain_link correctness
"""

import uuid
from datetime import datetime, timezone

from app.services.audit.hash_chain import (
    GENESIS_HASH,
    compute_event_hash,
    verify_chain_link,
    _canonical_json,
    _normalise,
    _normalise_timestamp,
)


# Fixed test values for deterministic assertions
_TEST_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
_TEST_TENANT = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_TEST_TS = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)
_TEST_DETAIL = {"action": "upload", "file_size": 1024}


def _make_hash(**overrides):
    """Helper to compute a hash with default test values, overridable."""
    defaults = {
        "sequence_number": 1,
        "event_type": "prescription.uploaded",
        "actor_id": _TEST_UUID,
        "tenant_id": _TEST_TENANT,
        "event_timestamp": _TEST_TS,
        "object_type": "prescription",
        "object_id": _TEST_UUID,
        "previous_hash": GENESIS_HASH,
        "detail": _TEST_DETAIL,
    }
    defaults.update(overrides)
    return compute_event_hash(**defaults)


class TestGenesisHash:
    def test_genesis_hash_is_64_zeros(self):
        assert GENESIS_HASH == "0" * 64
        assert len(GENESIS_HASH) == 64


class TestComputeEventHash:
    def test_returns_64_char_hex_string(self):
        h = _make_hash()
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic_output(self):
        """Same inputs must always produce the same hash."""
        h1 = _make_hash()
        h2 = _make_hash()
        assert h1 == h2

    def test_different_sequence_number_changes_hash(self):
        h1 = _make_hash(sequence_number=1)
        h2 = _make_hash(sequence_number=2)
        assert h1 != h2

    def test_different_event_type_changes_hash(self):
        h1 = _make_hash(event_type="prescription.uploaded")
        h2 = _make_hash(event_type="prescription.revoked")
        assert h1 != h2

    def test_different_actor_changes_hash(self):
        other_uuid = uuid.UUID("99999999-9999-9999-9999-999999999999")
        h1 = _make_hash(actor_id=_TEST_UUID)
        h2 = _make_hash(actor_id=other_uuid)
        assert h1 != h2

    def test_different_previous_hash_changes_hash(self):
        h1 = _make_hash(previous_hash=GENESIS_HASH)
        h2 = _make_hash(previous_hash="a" * 64)
        assert h1 != h2

    def test_different_detail_changes_hash(self):
        h1 = _make_hash(detail={"key": "value1"})
        h2 = _make_hash(detail={"key": "value2"})
        assert h1 != h2

    def test_none_actor_id(self):
        """System events have no actor — hash should still be deterministic."""
        h = _make_hash(actor_id=None)
        assert len(h) == 64

    def test_none_object_fields(self):
        h = _make_hash(object_type=None, object_id=None)
        assert len(h) == 64

    def test_empty_detail(self):
        h1 = _make_hash(detail=None)
        h2 = _make_hash(detail={})
        # None and {} both produce "{}" canonical JSON — should be equal
        assert h1 == h2

    def test_detail_key_order_irrelevant(self):
        """Canonical JSON sorts keys, so order should not matter."""
        h1 = _make_hash(detail={"b": 2, "a": 1})
        h2 = _make_hash(detail={"a": 1, "b": 2})
        assert h1 == h2


class TestChainLinkage:
    def test_chain_of_two_events(self):
        """Second event's previous_hash should be first event's current_hash."""
        hash_1 = _make_hash(sequence_number=1, previous_hash=GENESIS_HASH)

        hash_2 = _make_hash(
            sequence_number=2,
            previous_hash=hash_1,
            event_type="document.stored",
        )

        # Both should be valid hex strings
        assert len(hash_1) == 64
        assert len(hash_2) == 64
        # They should be different
        assert hash_1 != hash_2

    def test_chain_of_three_events(self):
        h1 = _make_hash(sequence_number=1, previous_hash=GENESIS_HASH)
        h2 = _make_hash(sequence_number=2, previous_hash=h1)
        h3 = _make_hash(sequence_number=3, previous_hash=h2)
        assert len({h1, h2, h3}) == 3  # All different


class TestVerifyChainLink:
    def test_valid_link_returns_true(self):
        stored_hash = _make_hash()
        assert verify_chain_link(
            current_event_hash=stored_hash,
            sequence_number=1,
            event_type="prescription.uploaded",
            actor_id=_TEST_UUID,
            tenant_id=_TEST_TENANT,
            event_timestamp=_TEST_TS,
            object_type="prescription",
            object_id=_TEST_UUID,
            previous_hash=GENESIS_HASH,
            detail=_TEST_DETAIL,
        )

    def test_tampered_hash_returns_false(self):
        assert not verify_chain_link(
            current_event_hash="f" * 64,  # Wrong hash
            sequence_number=1,
            event_type="prescription.uploaded",
            actor_id=_TEST_UUID,
            tenant_id=_TEST_TENANT,
            event_timestamp=_TEST_TS,
            object_type="prescription",
            object_id=_TEST_UUID,
            previous_hash=GENESIS_HASH,
            detail=_TEST_DETAIL,
        )

    def test_tampered_detail_returns_false(self):
        stored_hash = _make_hash(detail={"original": True})
        assert not verify_chain_link(
            current_event_hash=stored_hash,
            sequence_number=1,
            event_type="prescription.uploaded",
            actor_id=_TEST_UUID,
            tenant_id=_TEST_TENANT,
            event_timestamp=_TEST_TS,
            object_type="prescription",
            object_id=_TEST_UUID,
            previous_hash=GENESIS_HASH,
            detail={"original": False},  # Tampered
        )


class TestNormalisationHelpers:
    def test_normalise_none(self):
        assert _normalise(None) == "null"

    def test_normalise_uuid(self):
        assert _normalise(_TEST_UUID) == str(_TEST_UUID)

    def test_normalise_string(self):
        assert _normalise("hello") == "hello"

    def test_normalise_timestamp_datetime(self):
        result = _normalise_timestamp(_TEST_TS)
        assert "2026-04-07" in result

    def test_normalise_timestamp_string(self):
        assert _normalise_timestamp("2026-04-07T12:00:00+00:00") == "2026-04-07T12:00:00+00:00"

    def test_normalise_timestamp_none(self):
        assert _normalise_timestamp(None) == "null"

    def test_canonical_json_sorted_keys(self):
        result = _canonical_json({"z": 1, "a": 2})
        assert result == '{"a":2,"z":1}'

    def test_canonical_json_none(self):
        assert _canonical_json(None) == "{}"

    def test_canonical_json_empty(self):
        assert _canonical_json({}) == "{}"
