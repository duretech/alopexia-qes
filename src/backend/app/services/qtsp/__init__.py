"""QTSP integration — signature verification via Qualified Trust Service Providers.

Public API:
    QTSPProvider           — Protocol for QTSP implementations
    VerificationResult     — Normalized verification result
    VerificationStatus     — Verification outcome enum
    verify_prescription()  — Full verification orchestration
    get_qtsp_provider()    — Factory for configured provider
"""

from app.services.qtsp.interface import (
    QTSPProvider,
    QTSPError,
    QTSPConnectionError,
    QTSPTimeoutError,
    QTSPValidationError,
    VerificationResult,
    VerificationStatus,
    CertificateInfo,
    TimestampInfo,
    TimestampStatus,
    TrustListStatus,
    EvidenceArtifact,
)


def __getattr__(name: str):
    """Lazy imports for modules with DB/ORM dependencies."""
    if name == "verify_prescription":
        from app.services.qtsp.verification_service import verify_prescription
        return verify_prescription
    if name == "VerificationOutcome":
        from app.services.qtsp.verification_service import VerificationOutcome
        return VerificationOutcome
    if name == "MockQTSPProvider":
        from app.services.qtsp.mock_provider import MockQTSPProvider
        return MockQTSPProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "QTSPProvider",
    "QTSPError",
    "QTSPConnectionError",
    "QTSPTimeoutError",
    "QTSPValidationError",
    "VerificationResult",
    "VerificationStatus",
    "CertificateInfo",
    "TimestampInfo",
    "TimestampStatus",
    "TrustListStatus",
    "EvidenceArtifact",
    "verify_prescription",
    "VerificationOutcome",
    "MockQTSPProvider",
]
