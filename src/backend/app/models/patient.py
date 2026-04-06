"""Patient model — minimal PII, GDPR Art. 9 special category data."""

from sqlalchemy import Column, String, Boolean, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, generate_uuid


class Patient(Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin):
    """
    Patient record. Stores minimum necessary PII for prescription linkage.
    This is GDPR Art. 9 special category data (health context).

    Immutable fields: id, tenant_id, created_at
    Mutable fields: identifier_hash, full_name_encrypted, date_of_birth_encrypted, is_active
    Encryption-sensitive: full_name_encrypted, date_of_birth_encrypted, national_id_hash
    Retention: REQUIRES CONFIRMATION BY SPANISH HEALTHCARE / PHARMA COUNSEL
               Default assumption: same as prescription retention period
    """
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "identifier_hash",
            name="uq_patient_tenant_identifier",
        ),
        Index("ix_patient_tenant_active", "tenant_id", "is_active"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    identifier_hash = Column(
        String(128), nullable=False,
        comment="SHA-256 hash of national ID or unique patient identifier — for dedup, not display",
    )
    full_name_encrypted = Column(
        Text, nullable=False,
        comment="ENCRYPTION_SENSITIVE — AES-encrypted full name",
    )
    date_of_birth_encrypted = Column(
        Text, nullable=True,
        comment="ENCRYPTION_SENSITIVE — AES-encrypted date of birth",
    )
    national_id_hash = Column(
        String(128), nullable=True,
        comment="SHA-256 hash of DNI/NIE — for lookup, not display",
    )
    is_active = Column(Boolean, nullable=False, default=True)
    metadata_ = Column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}",
        comment="Additional patient metadata (non-PII only)",
    )
