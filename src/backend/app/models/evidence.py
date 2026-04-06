"""Evidence file model — stores QTSP evidence artifacts."""

from sqlalchemy import (
    Column, String, ForeignKey, DateTime, BigInteger, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TenantScopedMixin, TimestampMixin, generate_uuid


class EvidenceFile(Base, TenantScopedMixin, TimestampMixin):
    """
    Evidence artifact returned by QTSP verification.
    May include validation reports, evidence records, or certificate chain data.

    Immutable fields: ALL — evidence records must never be modified
    Encryption-sensitive: none
    Retention: same as parent prescription (evidence must outlive the prescription)
    """
    __tablename__ = "evidence_files"
    __table_args__ = (
        Index("ix_evidence_tenant_rx", "tenant_id", "prescription_id"),
        Index("ix_evidence_tenant_verification", "tenant_id", "verification_result_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    prescription_id = Column(
        UUID(as_uuid=True), ForeignKey("prescriptions.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Immutable — parent prescription",
    )
    verification_result_id = Column(
        UUID(as_uuid=True),
        ForeignKey("signature_verification_results.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Immutable — verification result that produced this evidence",
    )

    # Storage
    storage_key = Column(
        String(1000), nullable=False,
        comment="Immutable — S3 object key in evidence bucket",
    )
    storage_bucket = Column(
        String(255), nullable=False,
        comment="S3 bucket name",
    )
    checksum_sha256 = Column(
        String(64), nullable=False,
        comment="Immutable — SHA-256 of the evidence file",
    )
    file_size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(
        String(100), nullable=False,
        comment="Evidence file MIME type (e.g., application/xml, application/pdf, application/json)",
    )
    evidence_type = Column(
        String(100), nullable=False,
        comment="Type of evidence: validation_report, evidence_record, certificate_chain, timestamp_token",
    )

    # WORM
    storage_version_id = Column(String(500), nullable=True)
    object_lock_until = Column(DateTime(timezone=True), nullable=True)

    # Certificate chain details (normalized)
    certificate_chain_data = Column(
        JSONB, nullable=True,
        comment="Normalized certificate chain information",
    )

    # Trust list fields
    trust_list_provider = Column(String(500), nullable=True)
    trust_list_status = Column(String(50), nullable=True)
    trust_list_checked_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamp details (from evidence)
    timestamp_details = Column(
        JSONB, nullable=True,
        comment="Normalized timestamp information from evidence",
    )

    metadata_ = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")

    # Relationships
    prescription = relationship("Prescription", back_populates="evidence_files")
    verification_result = relationship("SignatureVerificationResult")
