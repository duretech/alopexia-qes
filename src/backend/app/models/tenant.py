"""Tenant and Clinic models — top-level organizational scoping."""

from sqlalchemy import Column, String, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid


class Tenant(Base, TimestampMixin, SoftDeleteMixin):
    """
    Top-level organizational unit. All data is scoped to a tenant.

    Immutable fields: id, created_at
    Mutable fields: name, display_name, is_active, settings, updated_at
    Encryption-sensitive: none (org-level, not PII)
    Retention: retained for platform lifetime
    """
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(
        String(255), nullable=False, unique=True,
        comment="Machine-friendly tenant identifier (slug)",
    )
    display_name = Column(
        String(500), nullable=False,
        comment="Human-readable tenant name",
    )
    is_active = Column(
        Boolean, nullable=False, default=True,
        comment="Whether tenant is active — inactive tenants cannot login",
    )
    settings = Column(
        JSONB, nullable=False, default=dict, server_default="{}",
        comment="Tenant-specific configuration overrides",
    )
    primary_contact_email = Column(
        String(320), nullable=True,
        comment="Primary contact email for the tenant organization",
    )

    # Relationships
    clinics = relationship("Clinic", back_populates="tenant", lazy="selectin")


class Clinic(Base, TimestampMixin, SoftDeleteMixin):
    """
    A clinic within a tenant. Doctors and prescriptions are scoped to clinics.

    Immutable fields: id, tenant_id, created_at
    Mutable fields: name, address, is_active, settings, updated_at
    Encryption-sensitive: none
    Retention: retained for tenant lifetime
    """
    __tablename__ = "clinics"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_clinic_tenant_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False, index=True,
        comment="Owning tenant — immutable after creation",
    )
    name = Column(String(500), nullable=False, comment="Clinic name")
    address = Column(Text, nullable=True, comment="Physical address")
    phone = Column(String(50), nullable=True, comment="Contact phone")
    license_number = Column(
        String(100), nullable=True,
        comment="Official clinic registration / license number",
    )
    is_active = Column(Boolean, nullable=False, default=True)
    settings = Column(JSONB, nullable=False, default=dict, server_default="{}")

    # Relationships
    tenant = relationship("Tenant", back_populates="clinics")
