"""Tests for the prescription ingestion service orchestrator.

These tests exercise the full ingestion pipeline using mock storage
and an in-memory SQLite-compatible approach where possible. The tests
that require real DB interactions (dedup, idempotency) use mocked
DB sessions.

Since the service depends on ORM models and DB queries, these tests
mock the database layer and storage backend to test the orchestration
logic in isolation.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingestion.service import (
    ingest_prescription,
    IngestionError,
    DuplicateDocumentError,
    IdempotencyConflictError,
    QuarantinedError,
    _generate_storage_key,
)
from app.services.ingestion.validators import ValidationError
from app.services.storage.interface import StorageResult


# ── Fixtures ─────────────────────────────────────────────────────────────

# Minimal valid PDF for testing (same as in test_validators.py)
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
    b"startxref\n183\n"
    b"%%EOF\n"
)


@pytest.fixture
def valid_pdf():
    return MINIMAL_PDF


@pytest.fixture
def mock_storage():
    """Mock storage backend that records calls."""
    storage = AsyncMock()
    checksum = hashlib.sha256(MINIMAL_PDF).hexdigest()
    storage.store_object.return_value = StorageResult(
        bucket="qesflow-prescriptions",
        key=f"test-key/{checksum[:12]}.pdf",
        version_id="v1",
        checksum_sha256=checksum,
        size_bytes=len(MINIMAL_PDF),
        server_side_encryption="AES256",
    )
    return storage


@pytest.fixture
def mock_db():
    """Mock async DB session."""
    db = AsyncMock()
    # Default: no duplicates, no existing idempotency key
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    return db


@pytest.fixture
def base_kwargs(mock_db, mock_storage, valid_pdf):
    """Base keyword arguments for ingest_prescription()."""
    return {
        "file_data": valid_pdf,
        "original_filename": "prescription_001.pdf",
        "declared_content_type": "application/pdf",
        "doctor_id": uuid.uuid4(),
        "patient_id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "clinic_id": uuid.uuid4(),
        "idempotency_key": "upload-001",
        "storage_backend": mock_storage,
    }


# ── Storage Key Generation ───────────────────────────────────────────────


class TestStorageKeyGeneration:
    def test_key_format(self):
        tenant_id = uuid.uuid4()
        checksum = "a" * 64
        key = _generate_storage_key(tenant_id, checksum)
        assert str(tenant_id) in key
        assert key.endswith(".pdf")
        assert checksum[:12] in key

    def test_keys_are_unique(self):
        tenant_id = uuid.uuid4()
        checksum = "a" * 64
        key1 = _generate_storage_key(tenant_id, checksum)
        key2 = _generate_storage_key(tenant_id, checksum)
        assert key1 != key2  # Random UUID component ensures uniqueness


# ── Validation Stage Tests ───────────────────────────────────────────────


class TestIngestionValidation:
    async def test_rejects_empty_file(self, mock_db, mock_storage):
        with pytest.raises(ValidationError) as exc_info:
            await ingest_prescription(
                mock_db,
                file_data=b"",
                original_filename="empty.pdf",
                doctor_id=uuid.uuid4(),
                patient_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                clinic_id=uuid.uuid4(),
                idempotency_key="key-empty",
                storage_backend=mock_storage,
            )
        assert exc_info.value.code == "EMPTY_FILE"
        # Storage should NOT be called for invalid files
        mock_storage.store_object.assert_not_called()

    async def test_rejects_non_pdf(self, mock_db, mock_storage):
        with pytest.raises(ValidationError) as exc_info:
            await ingest_prescription(
                mock_db,
                file_data=b"PK\x03\x04 this is a zip file, not a PDF" + b"x" * 100,
                original_filename="fake.pdf",
                doctor_id=uuid.uuid4(),
                patient_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                clinic_id=uuid.uuid4(),
                idempotency_key="key-zip",
                storage_backend=mock_storage,
            )
        assert exc_info.value.code == "NOT_PDF"

    async def test_rejects_oversized_file(self, mock_db, mock_storage, valid_pdf):
        with patch("app.services.ingestion.service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.max_upload_size_bytes = 10  # Tiny limit
            settings.malware_scanner = "mock"
            settings.clamav_host = "localhost"
            settings.clamav_port = 3310
            mock_settings.return_value = settings

            with pytest.raises(ValidationError) as exc_info:
                await ingest_prescription(
                    mock_db,
                    file_data=valid_pdf,
                    original_filename="big.pdf",
                    doctor_id=uuid.uuid4(),
                    patient_id=uuid.uuid4(),
                    tenant_id=uuid.uuid4(),
                    clinic_id=uuid.uuid4(),
                    idempotency_key="key-big",
                    storage_backend=mock_storage,
                )
            assert exc_info.value.code == "FILE_TOO_LARGE"


# ── Malware Scan Tests ───────────────────────────────────────────────────


class TestIngestionMalwareScan:
    async def test_infected_file_raises_quarantined(self, mock_db, mock_storage):
        eicar_pdf = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR\n"
            b"xref\n0 4\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
            b"startxref\n220\n"
            b"%%EOF\n"
        )
        with pytest.raises(QuarantinedError) as exc_info:
            await ingest_prescription(
                mock_db,
                file_data=eicar_pdf,
                original_filename="malware.pdf",
                doctor_id=uuid.uuid4(),
                patient_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                clinic_id=uuid.uuid4(),
                idempotency_key="key-eicar",
                storage_backend=mock_storage,
            )
        assert exc_info.value.code == "QUARANTINED"
        # Storage should NOT be called for infected files
        mock_storage.store_object.assert_not_called()


# ── Duplicate & Idempotency Tests ────────────────────────────────────────


class TestIngestionDedup:
    async def test_duplicate_content_raises(self, mock_db, mock_storage, base_kwargs):
        # First execute call returns a duplicate hit (dedup query)
        dup_result = MagicMock()
        dup_result.first.return_value = (uuid.uuid4(), uuid.uuid4())

        mock_db.execute.return_value = dup_result

        with pytest.raises(DuplicateDocumentError) as exc_info:
            await ingest_prescription(mock_db, **base_kwargs)
        assert exc_info.value.code == "DUPLICATE_CONTENT"

    async def test_idempotency_conflict_raises(self, mock_db, mock_storage, base_kwargs):
        # First call (dedup) returns no match, second call (idempotency) returns a match
        no_dup = MagicMock()
        no_dup.first.return_value = None

        existing_rx = MagicMock()
        existing_rx.scalar_one_or_none.return_value = uuid.uuid4()

        mock_db.execute.side_effect = [no_dup, existing_rx]

        with pytest.raises(IdempotencyConflictError) as exc_info:
            await ingest_prescription(mock_db, **base_kwargs)
        assert exc_info.value.code == "IDEMPOTENCY_CONFLICT"


# ── Happy Path Tests ─────────────────────────────────────────────────────


class TestIngestionHappyPath:
    async def test_successful_ingestion(self, mock_db, mock_storage, base_kwargs):
        # Both dedup and idempotency checks return "no conflict"
        no_match = MagicMock()
        no_match.first.return_value = None
        no_match.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = no_match

        result = await ingest_prescription(mock_db, **base_kwargs)

        assert result.prescription_id is not None
        assert result.document_id is not None
        assert result.checksum_sha256 == hashlib.sha256(MINIMAL_PDF).hexdigest()
        assert result.file_size_bytes == len(MINIMAL_PDF)
        assert result.storage_bucket == "qesflow-prescriptions"
        assert result.scan_status == "clean"
        assert result.is_duplicate_content is False

        # Verify storage was called
        mock_storage.store_object.assert_called_once()
        call_kwargs = mock_storage.store_object.call_args
        assert call_kwargs[0][2] == MINIMAL_PDF  # data argument
        assert call_kwargs[1]["content_type"] == "application/pdf"
        assert call_kwargs[1]["server_side_encryption"] is True

        # Verify DB records were added (3 adds: prescription, document)
        assert mock_db.add.call_count >= 2
        assert mock_db.flush.called

    async def test_ingestion_with_metadata(self, mock_db, mock_storage, base_kwargs):
        no_match = MagicMock()
        no_match.first.return_value = None
        no_match.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = no_match

        base_kwargs["medication_name"] = "Ibuprofeno 600mg"
        base_kwargs["dosage"] = "1 cada 8 horas"
        base_kwargs["is_compounded"] = True

        result = await ingest_prescription(mock_db, **base_kwargs)
        assert result.prescription_id is not None

        # Should have 3 db.add() calls: prescription, document, metadata
        assert mock_db.add.call_count == 3

    async def test_storage_failure_raises_ingestion_error(self, mock_db, mock_storage, base_kwargs):
        no_match = MagicMock()
        no_match.first.return_value = None
        no_match.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = no_match

        mock_storage.store_object.side_effect = Exception("S3 connection refused")

        with pytest.raises(IngestionError) as exc_info:
            await ingest_prescription(mock_db, **base_kwargs)
        assert exc_info.value.code == "STORAGE_FAILED"
