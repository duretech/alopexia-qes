"""Mock QTSP provider for local development and testing.

Simulates signature verification responses without calling any external
service. The mock can be configured to return different outcomes based
on the document content for testing all verification paths.

Behaviour:
  - Default: returns VERIFIED with a realistic mock certificate
  - If document contains b"INVALID_SIGNATURE": returns FAILED
  - If document contains b"EXPIRED_CERT": returns EXPIRED
  - If document contains b"REVOKED_CERT": returns REVOKED
  - If document contains b"QTSP_ERROR": raises QTSPError
  - If document contains b"QTSP_TIMEOUT": raises QTSPTimeoutError
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from app.core.logging import get_logger
from app.services.qtsp.interface import (
    CertificateInfo,
    EvidenceArtifact,
    QTSPError,
    QTSPTimeoutError,
    TimestampInfo,
    TimestampStatus,
    TrustListStatus,
    VerificationResult,
    VerificationStatus,
)

logger = get_logger(component="mock_qtsp")


class MockQTSPProvider:
    """Mock QTSP provider that simulates signature verification."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def verify_signature(
        self,
        pdf_data: bytes,
        *,
        document_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> VerificationResult:
        request_id = f"mock-{uuid.uuid4().hex[:16]}"

        logger.info(
            "mock_verification_started",
            document_id=document_id,
            request_id=request_id,
            size=len(pdf_data),
        )

        # Simulate error conditions based on content markers
        if b"QTSP_TIMEOUT" in pdf_data:
            raise QTSPTimeoutError("Mock QTSP timeout triggered")
        if b"QTSP_ERROR" in pdf_data:
            raise QTSPError("Mock QTSP error triggered", code="MOCK_ERROR")

        # Determine verification outcome
        now = datetime.now(timezone.utc)

        if b"INVALID_SIGNATURE" in pdf_data:
            return self._build_failed_result(request_id, now, pdf_data)
        elif b"EXPIRED_CERT" in pdf_data:
            return self._build_expired_result(request_id, now, pdf_data)
        elif b"REVOKED_CERT" in pdf_data:
            return self._build_revoked_result(request_id, now, pdf_data)
        else:
            return self._build_verified_result(request_id, now, pdf_data)

    async def health_check(self) -> bool:
        return True

    def _build_verified_result(
        self, request_id: str, now: datetime, pdf_data: bytes,
    ) -> VerificationResult:
        cert = CertificateInfo(
            common_name="Dr. Mock Signer (TEST)",
            serial_number="MOCK-CERT-001",
            organization="Mock Healthcare Provider",
            issuer="Mock Qualified CA (TEST)",
            valid_from=now - timedelta(days=365),
            valid_to=now + timedelta(days=365),
            is_qualified=True,
        )
        timestamp = TimestampInfo(
            status=TimestampStatus.QUALIFIED,
            time=now - timedelta(minutes=5),
            authority="Mock TSA (TEST)",
            is_qualified=True,
        )
        raw = self._build_raw_response(
            request_id, "TOTAL_PASSED", cert, timestamp, now,
        )
        evidence = self._build_evidence_artifacts(request_id, raw, cert, now)

        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            provider="mock",
            request_id=request_id,
            signature_intact=True,
            signature_algorithm="SHA256withRSA",
            certificate=cert,
            timestamp=timestamp,
            trust_list_status=TrustListStatus.TRUSTED,
            trust_list_checked_at=now,
            raw_response=raw,
            raw_response_content_type="application/json",
            evidence_artifacts=evidence,
            normalized_response=json.loads(raw),
        )

    def _build_failed_result(
        self, request_id: str, now: datetime, pdf_data: bytes,
    ) -> VerificationResult:
        cert = CertificateInfo(
            common_name="Unknown Signer (TEST)",
            serial_number="MOCK-CERT-INVALID",
            organization="Unknown",
            issuer="Unknown CA",
            valid_from=now - timedelta(days=30),
            valid_to=now + timedelta(days=30),
            is_qualified=False,
        )
        raw = self._build_raw_response(
            request_id, "TOTAL_FAILED", cert, None, now,
        )
        return VerificationResult(
            status=VerificationStatus.FAILED,
            provider="mock",
            request_id=request_id,
            signature_intact=False,
            signature_algorithm="SHA256withRSA",
            certificate=cert,
            timestamp=TimestampInfo(status=TimestampStatus.MISSING),
            trust_list_status=TrustListStatus.UNTRUSTED,
            trust_list_checked_at=now,
            raw_response=raw,
            raw_response_content_type="application/json",
            error_code="SIGNATURE_INVALID",
            error_message="Document signature verification failed (mock)",
            normalized_response=json.loads(raw),
        )

    def _build_expired_result(
        self, request_id: str, now: datetime, pdf_data: bytes,
    ) -> VerificationResult:
        cert = CertificateInfo(
            common_name="Dr. Expired Signer (TEST)",
            serial_number="MOCK-CERT-EXPIRED",
            organization="Mock Healthcare Provider",
            issuer="Mock Qualified CA (TEST)",
            valid_from=now - timedelta(days=730),
            valid_to=now - timedelta(days=1),
            is_qualified=True,
        )
        raw = self._build_raw_response(
            request_id, "INDETERMINATE", cert, None, now,
        )
        return VerificationResult(
            status=VerificationStatus.EXPIRED,
            provider="mock",
            request_id=request_id,
            signature_intact=True,
            signature_algorithm="SHA256withRSA",
            certificate=cert,
            timestamp=TimestampInfo(status=TimestampStatus.MISSING),
            trust_list_status=TrustListStatus.TRUSTED,
            trust_list_checked_at=now,
            raw_response=raw,
            raw_response_content_type="application/json",
            error_code="CERTIFICATE_EXPIRED",
            error_message="Signing certificate has expired (mock)",
            normalized_response=json.loads(raw),
        )

    def _build_revoked_result(
        self, request_id: str, now: datetime, pdf_data: bytes,
    ) -> VerificationResult:
        cert = CertificateInfo(
            common_name="Dr. Revoked Signer (TEST)",
            serial_number="MOCK-CERT-REVOKED",
            organization="Mock Healthcare Provider",
            issuer="Mock Qualified CA (TEST)",
            valid_from=now - timedelta(days=365),
            valid_to=now + timedelta(days=365),
            is_qualified=True,
        )
        raw = self._build_raw_response(
            request_id, "TOTAL_FAILED", cert, None, now,
        )
        return VerificationResult(
            status=VerificationStatus.REVOKED,
            provider="mock",
            request_id=request_id,
            signature_intact=True,
            signature_algorithm="SHA256withRSA",
            certificate=cert,
            timestamp=TimestampInfo(status=TimestampStatus.MISSING),
            trust_list_status=TrustListStatus.UNTRUSTED,
            trust_list_checked_at=now,
            raw_response=raw,
            raw_response_content_type="application/json",
            error_code="CERTIFICATE_REVOKED",
            error_message="Signing certificate has been revoked (mock)",
            normalized_response=json.loads(raw),
        )

    @staticmethod
    def _build_raw_response(
        request_id: str,
        indication: str,
        cert: CertificateInfo,
        timestamp: TimestampInfo | None,
        now: datetime,
    ) -> bytes:
        """Build a mock raw QTSP response (JSON format)."""
        response = {
            "requestId": request_id,
            "indication": indication,
            "signatureVerification": {
                "signatureIntact": indication == "TOTAL_PASSED",
                "signerInfo": cert.to_dict() if cert else None,
            },
            "timestampVerification": timestamp.to_dict() if timestamp else None,
            "validationTime": now.isoformat(),
            "provider": "mock",
            "version": "1.0",
        }
        return json.dumps(response, indent=2, default=str).encode("utf-8")

    @staticmethod
    def _build_evidence_artifacts(
        request_id: str,
        raw_response: bytes,
        cert: CertificateInfo,
        now: datetime,
    ) -> list[EvidenceArtifact]:
        """Build mock evidence artifacts."""
        # Validation report (simulated XML)
        report_xml = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f"<ValidationReport>\n"
            f"  <RequestId>{request_id}</RequestId>\n"
            f"  <Indication>TOTAL_PASSED</Indication>\n"
            f"  <SignerCN>{cert.common_name}</SignerCN>\n"
            f"  <ValidationTime>{now.isoformat()}</ValidationTime>\n"
            f"</ValidationReport>\n"
        ).encode("utf-8")

        # Certificate chain (simulated PEM)
        cert_chain = (
            f"-----BEGIN CERTIFICATE-----\n"
            f"MOCK-CERTIFICATE-DATA-{request_id}\n"
            f"CN={cert.common_name}\n"
            f"ISSUER={cert.issuer}\n"
            f"-----END CERTIFICATE-----\n"
        ).encode("utf-8")

        return [
            EvidenceArtifact(
                evidence_type="validation_report",
                data=report_xml,
                content_type="application/xml",
                filename_hint=f"validation_report_{request_id}.xml",
            ),
            EvidenceArtifact(
                evidence_type="certificate_chain",
                data=cert_chain,
                content_type="application/x-pem-file",
                filename_hint=f"cert_chain_{request_id}.pem",
            ),
        ]
