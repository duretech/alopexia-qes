"""Signature verification result from QTSP integration."""

from sqlalchemy import (
    Column, String, Boolean, Text, ForeignKey, DateTime, Integer,
    Index, CheckConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TenantScopedMixin, TimestampMixin, generate_uuid


class SignatureVerificationResult(Base, TenantScopedMixin, TimestampMixin):
    """
    Result of QTSP signature verification for a prescription PDF.
    One prescription may have multiple verification attempts (retries, re-verifications).

    Immutable fields: ALL — verification results must never be modified
    Encryption-sensitive: none
    Retention: same as parent prescription
    """
    __tablename__ = "signature_verification_results"
    __table_args__ = (
        Index("ix_sigver_tenant_rx", "tenant_id", "prescription_id"),
        Index("ix_sigver_status", "tenant_id", "verification_status"),
        CheckConstraint(
            "verification_status IN ('pending','verified','failed','error','expired','revoked')",
            name="ck_sigver_status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    prescription_id = Column(
        UUID(as_uuid=True), ForeignKey("prescriptions.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Immutable — prescription being verified",
    )
    attempt_number = Column(
        Integer, nullable=False, default=1,
        comment="Immutable — which verification attempt this is (1-based)",
    )
    idempotency_key = Column(
        String(100), nullable=False, unique=True,
        comment="Immutable — idempotency key for this verification request",
    )

    # QTSP provider info
    qtsp_provider = Column(
        String(100), nullable=False,
        comment="Immutable — QTSP provider name (e.g., 'dokobit', 'mock')",
    )
    qtsp_request_id = Column(
        String(500), nullable=True,
        comment="Immutable — request/transaction ID returned by QTSP",
    )

    # Verification outcome
    verification_status = Column(
        String(20), nullable=False, default="pending",
        comment="Immutable once set — verification result",
    )
    verified_at = Column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp when verification completed",
    )

    # Certificate details (normalized from QTSP response)
    signer_common_name = Column(String(500), nullable=True, comment="Certificate CN")
    signer_serial_number = Column(String(200), nullable=True, comment="Certificate serial")
    signer_organization = Column(String(500), nullable=True)
    certificate_issuer = Column(String(500), nullable=True, comment="Issuing CA")
    certificate_valid_from = Column(DateTime(timezone=True), nullable=True)
    certificate_valid_to = Column(DateTime(timezone=True), nullable=True)
    certificate_is_qualified = Column(
        Boolean, nullable=True,
        comment="Whether certificate is a qualified certificate per eIDAS",
    )

    # Timestamp details
    timestamp_status = Column(
        String(50), nullable=True,
        comment="Timestamp verification status: valid, invalid, missing, qualified",
    )
    timestamp_time = Column(
        DateTime(timezone=True), nullable=True,
        comment="Time from the timestamp token",
    )
    timestamp_authority = Column(String(500), nullable=True, comment="TSA identity")
    timestamp_is_qualified = Column(
        Boolean, nullable=True,
        comment="Whether timestamp is a qualified timestamp per eIDAS",
    )

    # Trust list status
    trust_list_status = Column(
        String(50), nullable=True,
        comment="Status against EU trusted list: trusted, untrusted, unknown",
    )
    trust_list_checked_at = Column(DateTime(timezone=True), nullable=True)

    # Signature integrity
    signature_intact = Column(
        Boolean, nullable=True,
        comment="Whether the document has not been modified since signing",
    )
    signature_algorithm = Column(String(100), nullable=True)

    # Raw response preservation — CRITICAL for audit
    raw_response_storage_key = Column(
        String(1000), nullable=True,
        comment="S3 key for the verbatim QTSP response body",
    )
    raw_response_checksum = Column(
        String(64), nullable=True,
        comment="SHA-256 of the raw QTSP response — for integrity verification",
    )

    # Error details
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    # Manual review
    requires_manual_review = Column(
        Boolean, nullable=False, default=False, server_default=text("FALSE"),
        comment="TRUE if verification result needs human review",
    )
    manual_review_completed_at = Column(DateTime(timezone=True), nullable=True)
    manual_review_by = Column(UUID(as_uuid=True), nullable=True)
    manual_review_decision = Column(
        String(50), nullable=True,
        comment="accept, reject, escalate",
    )
    manual_review_notes = Column(Text, nullable=True)

    # Full normalized response
    normalized_response = Column(
        JSONB, nullable=True,
        comment="Normalized/parsed QTSP response in standard schema",
    )

    # Relationships
    prescription = relationship("Prescription", back_populates="verification_results")
