"""External system reference model."""

from sqlalchemy import Column, String, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base, TenantScopedMixin, TimestampMixin, generate_uuid


class ExternalSystemReference(Base, TenantScopedMixin, TimestampMixin):
    """
    Links internal objects to external system identifiers.
    Used for traceability across system boundaries.

    Immutable fields: id, tenant_id, internal_type, internal_id,
                      external_system, external_id, created_at
    Mutable fields: metadata, is_active
    Retention: same as the referenced internal object
    """
    __tablename__ = "external_system_references"
    __table_args__ = (
        Index(
            "ix_ext_ref_internal",
            "tenant_id", "internal_type", "internal_id",
        ),
        Index(
            "ix_ext_ref_external",
            "tenant_id", "external_system", "external_id",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    internal_type = Column(
        String(100), nullable=False,
        comment="Immutable — type of internal object: prescription, patient, doctor, etc.",
    )
    internal_id = Column(
        UUID(as_uuid=True), nullable=False,
        comment="Immutable — ID of the internal object",
    )
    external_system = Column(
        String(200), nullable=False,
        comment="Immutable — name of external system (e.g., 'docusign', 'clinic_emr')",
    )
    external_id = Column(
        String(500), nullable=False,
        comment="Immutable — identifier in the external system",
    )
    external_url = Column(
        String(2000), nullable=True,
        comment="URL/deep link to the resource in the external system",
    )
    is_active = Column(String(10), nullable=False, default="true")
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
