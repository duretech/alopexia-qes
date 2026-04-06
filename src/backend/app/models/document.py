"""Uploaded document model — tracks stored prescription PDFs."""

from sqlalchemy import (
    Column, String, Boolean, ForeignKey, DateTime, BigInteger,
    Index, CheckConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, generate_uuid


class UploadedDocument(Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin):
    """
    A stored document file (prescription PDF). The original signed PDF
    must NEVER be modified after upload.

    Immutable fields: id, tenant_id, prescription_id, storage_key, checksum_sha256,
                      file_size_bytes, mime_type, original_filename_hash, created_at
    Mutable fields: scan_status, quarantine_status, is_deleted, deleted_at
    Encryption-sensitive: none (the file itself is encrypted at rest in S3)
    Retention: same as parent prescription
    """
    __tablename__ = "uploaded_documents"
    __table_args__ = (
        Index("ix_doc_tenant_prescription", "tenant_id", "prescription_id"),
        Index("ix_doc_checksum", "checksum_sha256"),
        CheckConstraint(
            "scan_status IN ('pending','clean','infected','error','skipped')",
            name="ck_doc_scan_status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    prescription_id = Column(
        UUID(as_uuid=True), ForeignKey("prescriptions.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Immutable — parent prescription",
    )
    storage_key = Column(
        String(1000), nullable=False,
        comment="Immutable — S3 object key (randomized, not user-controlled)",
    )
    storage_bucket = Column(
        String(255), nullable=False,
        comment="S3 bucket name",
    )
    checksum_sha256 = Column(
        String(64), nullable=False,
        comment="Immutable — SHA-256 hex digest computed at upload",
    )
    file_size_bytes = Column(
        BigInteger, nullable=False,
        comment="Immutable — file size at upload time",
    )
    mime_type = Column(
        String(100), nullable=False,
        comment="Immutable — validated MIME type (must be application/pdf)",
    )
    original_filename_hash = Column(
        String(64), nullable=True,
        comment="SHA-256 of original filename — we do NOT store original filename",
    )

    # Security scanning
    scan_status = Column(
        String(20), nullable=False, default="pending",
        comment="Malware scan result",
    )
    scanned_at = Column(DateTime(timezone=True), nullable=True)
    scan_result_detail = Column(
        String(500), nullable=True,
        comment="Scanner output detail if infected or error",
    )

    # Quarantine
    is_quarantined = Column(
        Boolean, nullable=False, default=False, server_default=text("FALSE"),
        comment="TRUE if flagged by scan or validation — blocks downstream processing",
    )
    quarantine_reason = Column(String(500), nullable=True)

    # PDF validation
    pdf_validated = Column(
        Boolean, nullable=False, default=False, server_default=text("FALSE"),
        comment="Whether PDF structural validation passed",
    )
    pdf_page_count = Column(BigInteger, nullable=True, comment="Number of pages in PDF")

    # WORM / immutability
    storage_version_id = Column(
        String(500), nullable=True,
        comment="S3 version ID if versioning is enabled",
    )
    object_lock_until = Column(
        DateTime(timezone=True), nullable=True,
        comment="S3 Object Lock retention expiry",
    )

    metadata_ = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")

    # Relationships
    prescription = relationship("Prescription", back_populates="documents")
