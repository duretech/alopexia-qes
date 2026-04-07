"""QTSP provider interface — contract for all QTSP implementations.

A Qualified Trust Service Provider (QTSP) validates electronic signatures
on prescription PDFs per eIDAS Regulation (EU 910/2014). The interface
abstracts the QTSP-specific API so the rest of the system is provider-agnostic.

The verification flow:
  1. Submit a PDF for signature verification
  2. Receive a structured result with certificate, timestamp, and trust details
  3. Store the raw QTSP response verbatim for audit (C-QTSP-02)
  4. Parse and normalize the response into our standard schema

Implements C-QTSP-01 (provider adapter pattern).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable
from uuid import UUID


class VerificationStatus(StrEnum):
    """Outcome of a signature verification."""
    VERIFIED = "verified"
    FAILED = "failed"
    ERROR = "error"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INDETERMINATE = "indeterminate"


class TimestampStatus(StrEnum):
    """Outcome of timestamp verification."""
    VALID = "valid"
    INVALID = "invalid"
    MISSING = "missing"
    QUALIFIED = "qualified"


class TrustListStatus(StrEnum):
    """Trust list lookup result."""
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CertificateInfo:
    """Normalized certificate details from the QTSP response."""
    common_name: str | None = None
    serial_number: str | None = None
    organization: str | None = None
    issuer: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_qualified: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "common_name": self.common_name,
            "serial_number": self.serial_number,
            "organization": self.organization,
            "issuer": self.issuer,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "is_qualified": self.is_qualified,
        }


@dataclass(frozen=True)
class TimestampInfo:
    """Normalized timestamp details from the QTSP response."""
    status: TimestampStatus = TimestampStatus.MISSING
    time: datetime | None = None
    authority: str | None = None
    is_qualified: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": str(self.status),
            "time": self.time.isoformat() if self.time else None,
            "authority": self.authority,
            "is_qualified": self.is_qualified,
        }


@dataclass(frozen=True)
class VerificationResult:
    """Complete result from a QTSP signature verification.

    This is the normalized, provider-agnostic result. The raw response
    is stored separately for audit purposes.
    """
    status: VerificationStatus
    provider: str
    request_id: str | None = None

    # Signature details
    signature_intact: bool | None = None
    signature_algorithm: str | None = None

    # Certificate info
    certificate: CertificateInfo | None = None

    # Timestamp info
    timestamp: TimestampInfo | None = None

    # Trust list
    trust_list_status: TrustListStatus = TrustListStatus.UNKNOWN
    trust_list_checked_at: datetime | None = None

    # Raw response (bytes — stored in evidence bucket)
    raw_response: bytes = b""
    raw_response_content_type: str = "application/json"

    # Error info
    error_code: str | None = None
    error_message: str | None = None

    # Additional evidence artifacts (e.g., validation report XML, cert chain)
    evidence_artifacts: list[EvidenceArtifact] = field(default_factory=list)

    # Full normalized response for DB storage
    normalized_response: dict[str, Any] = field(default_factory=dict)

    @property
    def requires_manual_review(self) -> bool:
        """Whether this result should be routed to manual review."""
        return self.status in (
            VerificationStatus.FAILED,
            VerificationStatus.INDETERMINATE,
            VerificationStatus.ERROR,
        )


@dataclass(frozen=True)
class EvidenceArtifact:
    """An evidence artifact produced by the QTSP verification."""
    evidence_type: str  # validation_report, evidence_record, certificate_chain, timestamp_token
    data: bytes
    content_type: str = "application/octet-stream"
    filename_hint: str = "evidence"


class QTSPError(Exception):
    """Base exception for QTSP operations."""
    def __init__(self, message: str, *, code: str | None = None, retryable: bool = False):
        self.code = code
        self.retryable = retryable
        super().__init__(message)


class QTSPConnectionError(QTSPError):
    """Connection to QTSP failed (retryable)."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=True, **kwargs)


class QTSPTimeoutError(QTSPError):
    """QTSP request timed out (retryable)."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=True, **kwargs)


class QTSPValidationError(QTSPError):
    """QTSP rejected the request (not retryable)."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=False, **kwargs)


@runtime_checkable
class QTSPProvider(Protocol):
    """Protocol for QTSP provider implementations.

    Implementations must be async and handle their own connection
    management, retries, and timeout enforcement.
    """

    @property
    def provider_name(self) -> str:
        """Unique name identifying this QTSP provider."""
        ...

    async def verify_signature(
        self,
        pdf_data: bytes,
        *,
        document_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> VerificationResult:
        """Verify the electronic signature on a PDF document.

        Args:
            pdf_data: Raw PDF bytes.
            document_id: Internal document reference (for correlation).
            idempotency_key: Idempotency key for this verification request.

        Returns:
            VerificationResult with all verification details.

        Raises:
            QTSPConnectionError: Network/connectivity issues (retryable).
            QTSPTimeoutError: Request timed out (retryable).
            QTSPValidationError: Request rejected by QTSP (not retryable).
            QTSPError: Other QTSP errors.
        """
        ...

    async def health_check(self) -> bool:
        """Check if the QTSP provider is reachable.

        Returns True if healthy, False otherwise.
        """
        ...
