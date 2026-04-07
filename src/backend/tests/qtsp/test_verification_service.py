"""Tests for the verification orchestration service."""

import hashlib
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.qtsp.interface import (
    CertificateInfo,
    EvidenceArtifact,
    QTSPTimeoutError,
    TimestampInfo,
    TimestampStatus,
    TrustListStatus,
    VerificationResult,
    VerificationStatus,
)
from app.services.qtsp.verification_service import (
    verify_prescription,
    VerificationServiceError,
    _map_verification_to_prescription_status,
)
from app.services.storage.interface import StorageResult


@pytest.fixture
def prescription_id():
    return uuid.uuid4()


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def mock_prescription(prescription_id, tenant_id):
    rx = MagicMock()
    rx.id = prescription_id
    rx.tenant_id = tenant_id
    rx.document_storage_key = f"{tenant_id}/abc123/test.pdf"
    rx.status = "pending_verification"
    return rx


@pytest.fixture
def mock_qtsp_result():
    return VerificationResult(
        status=VerificationStatus.VERIFIED,
        provider="mock",
        request_id="mock-abc123",
        signature_intact=True,
        signature_algorithm="SHA256withRSA",
        certificate=CertificateInfo(
            common_name="Dr. Test",
            serial_number="CERT-001",
            is_qualified=True,
        ),
        timestamp=TimestampInfo(
            status=TimestampStatus.QUALIFIED,
            time=datetime.now(timezone.utc),
        ),
        trust_list_status=TrustListStatus.TRUSTED,
        trust_list_checked_at=datetime.now(timezone.utc),
        raw_response=b'{"test": "response"}',
        raw_response_content_type="application/json",
        evidence_artifacts=[
            EvidenceArtifact(
                evidence_type="validation_report",
                data=b"<report>test</report>",
                content_type="application/xml",
            ),
        ],
        normalized_response={"test": "response"},
    )


@pytest.fixture
def mock_db(mock_prescription):
    db = AsyncMock()

    # First execute: prescription lookup
    rx_result = MagicMock()
    rx_result.scalar_one_or_none.return_value = mock_prescription

    # Second execute: attempt count
    count_result = MagicMock()
    count_result.all.return_value = []

    # Third+ execute: storage, evidence, updates
    generic_result = MagicMock()
    generic_result.scalar_one_or_none.return_value = None

    db.execute.side_effect = [rx_result, count_result] + [generic_result] * 10
    return db


@pytest.fixture
def mock_storage():
    storage = AsyncMock()
    storage.get_object.return_value = b"%PDF-1.4 test content"
    storage.store_object.return_value = StorageResult(
        bucket="qesflow-evidence",
        key="evidence/test",
        version_id="v1",
        checksum_sha256="abc",
        size_bytes=100,
    )
    return storage


@pytest.fixture
def mock_provider(mock_qtsp_result):
    provider = AsyncMock()
    provider.provider_name = "mock"
    provider.verify_signature.return_value = mock_qtsp_result
    return provider


class TestVerifyPrescription:
    async def test_successful_verification(
        self, mock_db, mock_storage, mock_provider,
        prescription_id, tenant_id,
    ):
        outcome = await verify_prescription(
            mock_db,
            prescription_id=prescription_id,
            tenant_id=tenant_id,
            qtsp_provider=mock_provider,
            storage_backend=mock_storage,
        )

        assert outcome.prescription_id == prescription_id
        assert outcome.status == "verified"
        assert outcome.requires_manual_review is False
        assert outcome.attempt_number == 1
        assert outcome.qtsp_request_id == "mock-abc123"
        assert len(outcome.evidence_file_ids) == 1

        # Verify provider was called with PDF data
        mock_provider.verify_signature.assert_called_once()
        # Verify DB records were added
        assert mock_db.add.call_count >= 2  # verification record + evidence files
        assert mock_db.flush.called

    async def test_prescription_not_found(
        self, mock_storage, mock_provider, tenant_id,
    ):
        db = AsyncMock()
        rx_result = MagicMock()
        rx_result.scalar_one_or_none.return_value = None
        db.execute.return_value = rx_result

        with pytest.raises(VerificationServiceError) as exc_info:
            await verify_prescription(
                db,
                prescription_id=uuid.uuid4(),
                tenant_id=tenant_id,
                qtsp_provider=mock_provider,
                storage_backend=mock_storage,
            )
        assert exc_info.value.code == "PRESCRIPTION_NOT_FOUND"

    async def test_pdf_retrieval_failure(
        self, mock_db, mock_provider, prescription_id, tenant_id,
    ):
        storage = AsyncMock()
        storage.get_object.side_effect = Exception("S3 connection failed")

        with pytest.raises(VerificationServiceError) as exc_info:
            await verify_prescription(
                mock_db,
                prescription_id=prescription_id,
                tenant_id=tenant_id,
                qtsp_provider=mock_provider,
                storage_backend=storage,
            )
        assert exc_info.value.code == "PDF_RETRIEVAL_FAILED"
        assert exc_info.value.retryable is True

    async def test_qtsp_timeout_records_error(
        self, mock_db, mock_storage, prescription_id, tenant_id,
    ):
        provider = AsyncMock()
        provider.provider_name = "mock"
        provider.verify_signature.side_effect = QTSPTimeoutError("timeout")

        outcome = await verify_prescription(
            mock_db,
            prescription_id=prescription_id,
            tenant_id=tenant_id,
            qtsp_provider=provider,
            storage_backend=mock_storage,
        )

        # Timeout is retryable — status should be error, not dead
        assert outcome.status == "error"
        assert outcome.error_message is not None


class TestStatusMapping:
    def test_verified_maps_to_verified(self):
        assert _map_verification_to_prescription_status(VerificationStatus.VERIFIED) == "verified"

    def test_failed_maps_to_failed_verification(self):
        assert _map_verification_to_prescription_status(VerificationStatus.FAILED) == "failed_verification"

    def test_error_maps_to_pending(self):
        assert _map_verification_to_prescription_status(VerificationStatus.ERROR) == "pending_verification"

    def test_indeterminate_maps_to_manual_review(self):
        assert _map_verification_to_prescription_status(VerificationStatus.INDETERMINATE) == "manual_review"
