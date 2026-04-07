"""Tests for the mock QTSP provider."""

import pytest

from app.services.qtsp.interface import (
    QTSPError,
    QTSPTimeoutError,
    VerificationStatus,
    TimestampStatus,
    TrustListStatus,
)
from app.services.qtsp.mock_provider import MockQTSPProvider


@pytest.fixture
def provider():
    return MockQTSPProvider()


@pytest.fixture
def valid_pdf():
    return b"%PDF-1.4 valid prescription content for testing"


class TestMockQTSPProvider:
    def test_provider_name(self, provider):
        assert provider.provider_name == "mock"

    async def test_health_check(self, provider):
        assert await provider.health_check() is True

    async def test_verified_result(self, provider, valid_pdf):
        result = await provider.verify_signature(valid_pdf)
        assert result.status == VerificationStatus.VERIFIED
        assert result.provider == "mock"
        assert result.request_id is not None
        assert result.signature_intact is True
        assert result.certificate is not None
        assert result.certificate.is_qualified is True
        assert result.certificate.common_name is not None
        assert result.timestamp is not None
        assert result.timestamp.status == TimestampStatus.QUALIFIED
        assert result.trust_list_status == TrustListStatus.TRUSTED
        assert len(result.raw_response) > 0
        assert len(result.evidence_artifacts) == 2
        assert not result.requires_manual_review

    async def test_failed_signature(self, provider):
        pdf = b"%PDF-1.4 INVALID_SIGNATURE content"
        result = await provider.verify_signature(pdf)
        assert result.status == VerificationStatus.FAILED
        assert result.signature_intact is False
        assert result.error_code == "SIGNATURE_INVALID"
        assert result.requires_manual_review is True

    async def test_expired_certificate(self, provider):
        pdf = b"%PDF-1.4 EXPIRED_CERT content"
        result = await provider.verify_signature(pdf)
        assert result.status == VerificationStatus.EXPIRED
        assert result.certificate is not None
        assert result.certificate.valid_to is not None
        assert result.error_code == "CERTIFICATE_EXPIRED"

    async def test_revoked_certificate(self, provider):
        pdf = b"%PDF-1.4 REVOKED_CERT content"
        result = await provider.verify_signature(pdf)
        assert result.status == VerificationStatus.REVOKED
        assert result.error_code == "CERTIFICATE_REVOKED"

    async def test_timeout_error(self, provider):
        pdf = b"%PDF-1.4 QTSP_TIMEOUT content"
        with pytest.raises(QTSPTimeoutError):
            await provider.verify_signature(pdf)

    async def test_generic_error(self, provider):
        pdf = b"%PDF-1.4 QTSP_ERROR content"
        with pytest.raises(QTSPError):
            await provider.verify_signature(pdf)

    async def test_idempotency_key_accepted(self, provider, valid_pdf):
        result = await provider.verify_signature(
            valid_pdf, idempotency_key="test-key-001",
        )
        assert result.status == VerificationStatus.VERIFIED

    async def test_document_id_accepted(self, provider, valid_pdf):
        result = await provider.verify_signature(
            valid_pdf, document_id="doc-123",
        )
        assert result.status == VerificationStatus.VERIFIED

    async def test_raw_response_is_valid_json(self, provider, valid_pdf):
        import json
        result = await provider.verify_signature(valid_pdf)
        parsed = json.loads(result.raw_response)
        assert "requestId" in parsed
        assert "indication" in parsed

    async def test_evidence_artifacts_have_content(self, provider, valid_pdf):
        result = await provider.verify_signature(valid_pdf)
        for artifact in result.evidence_artifacts:
            assert len(artifact.data) > 0
            assert artifact.evidence_type in ("validation_report", "certificate_chain")
            assert artifact.content_type is not None


class TestVerificationResult:
    async def test_requires_manual_review_for_failed(self, provider):
        result = await provider.verify_signature(b"%PDF-1.4 INVALID_SIGNATURE")
        assert result.requires_manual_review is True

    async def test_no_manual_review_for_verified(self, provider, valid_pdf):
        result = await provider.verify_signature(valid_pdf)
        assert result.requires_manual_review is False
