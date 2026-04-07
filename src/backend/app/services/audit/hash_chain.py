"""SHA-256 hash chain computation for audit event integrity.

The hash chain provides cryptographic proof of ordering and tamper detection.
Each audit event's current_hash is computed as:

    SHA-256(
        sequence_number || event_type || actor_id || tenant_id ||
        event_timestamp (ISO 8601) || object_type || object_id ||
        previous_hash || detail_json (canonical)
    )

Where:
    - '||' is string concatenation with '|' delimiter
    - None/null fields are represented as the literal string "null"
    - detail_json is JSON-serialised with sorted keys (canonical form)
    - The genesis event (sequence_number=1) uses '0'*64 as previous_hash

This module is a PURE FUNCTION layer — no database access, no side effects.
It receives data and returns hashes. This makes it independently testable
and verifiable by external auditors using only the exported JSON Lines data.

Security note: The hash chain alone does not prevent a sufficiently privileged
attacker from rewriting the entire chain. Defense in depth comes from:
  1. DB triggers preventing UPDATE/DELETE
  2. WORM export to S3 Object Lock
  3. Sequence gap detection
  4. Periodic external verification
"""

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID

# Genesis hash — used as previous_hash for the very first audit event
GENESIS_HASH = "0" * 64


def compute_event_hash(
    *,
    sequence_number: int,
    event_type: str,
    actor_id: UUID | str | None,
    tenant_id: UUID | str | None,
    event_timestamp: datetime | str,
    object_type: str | None,
    object_id: UUID | str | None,
    previous_hash: str,
    detail: dict[str, Any] | None,
) -> str:
    """Compute the SHA-256 hash for a single audit event.

    All parameters must match exactly what is stored in the audit_events row.
    Any mismatch during verification indicates tampering.

    Returns:
        64-character lowercase hex string (SHA-256 digest).
    """
    parts = [
        str(sequence_number),
        str(event_type),
        _normalise(actor_id),
        _normalise(tenant_id),
        _normalise_timestamp(event_timestamp),
        _normalise(object_type),
        _normalise(object_id),
        previous_hash,
        _canonical_json(detail),
    ]
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_chain_link(
    *,
    current_event_hash: str,
    sequence_number: int,
    event_type: str,
    actor_id: UUID | str | None,
    tenant_id: UUID | str | None,
    event_timestamp: datetime | str,
    object_type: str | None,
    object_id: UUID | str | None,
    previous_hash: str,
    detail: dict[str, Any] | None,
) -> bool:
    """Verify that a single event's stored hash matches its recomputed hash.

    Returns True if the hash is valid, False if tampering is detected.
    """
    expected = compute_event_hash(
        sequence_number=sequence_number,
        event_type=event_type,
        actor_id=actor_id,
        tenant_id=tenant_id,
        event_timestamp=event_timestamp,
        object_type=object_type,
        object_id=object_id,
        previous_hash=previous_hash,
        detail=detail,
    )
    return expected == current_event_hash


def _normalise(value: UUID | str | None) -> str:
    """Convert a value to its canonical string form for hashing."""
    if value is None:
        return "null"
    return str(value)


def _normalise_timestamp(ts: datetime | str) -> str:
    """Convert a timestamp to ISO 8601 string for hashing."""
    if ts is None:
        return "null"
    if isinstance(ts, datetime):
        return ts.isoformat()
    return str(ts)


def _canonical_json(data: dict[str, Any] | None) -> str:
    """Serialise a dict to canonical JSON (sorted keys, no whitespace).

    This ensures that logically identical detail dicts produce identical
    hash inputs regardless of key ordering.
    """
    if data is None:
        return "{}"
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
