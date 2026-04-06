"""User models — Doctor, PharmacyUser, AdminUser, Auditor.

All user types share common fields but are separate tables because they have
different authorization semantics, lifecycle, and audit requirements.
"""

from sqlalchemy import (
    Column, String, Boolean, Text, ForeignKey, DateTime,
    Integer, UniqueConstraint, Index, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, generate_uuid


class Doctor(Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin):
    """
    A doctor who uploads signed prescriptions.

    Immutable fields: id, tenant_id, external_idp_id, created_at
    Mutable fields: email, full_name, license_number, clinic_id, is_active, etc.
    Encryption-sensitive: email, full_name (PII)
    Retention: retained for legal prescription retention period + buffer
    """
    __tablename__ = "doctors"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_idp_id", name="uq_doctor_tenant_idp"),
        UniqueConstraint("tenant_id", "email", name="uq_doctor_tenant_email"),
        Index("ix_doctor_tenant_clinic", "tenant_id", "clinic_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    external_idp_id = Column(
        String(500), nullable=False,
        comment="Immutable — identity from external IdP (OIDC sub claim)",
    )
    email = Column(
        String(320), nullable=False,
        comment="ENCRYPTION_SENSITIVE — doctor email",
    )
    full_name = Column(
        String(500), nullable=False,
        comment="ENCRYPTION_SENSITIVE — doctor full name",
    )
    license_number = Column(
        String(100), nullable=True,
        comment="Medical license / colegiado number",
    )
    clinic_id = Column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="RESTRICT"),
        nullable=True, index=True,
        comment="Primary clinic assignment",
    )
    is_active = Column(Boolean, nullable=False, default=True)
    mfa_enabled = Column(
        Boolean, nullable=False, default=False,
        comment="Whether MFA is enabled at IdP (synced)",
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    locked_until = Column(
        DateTime(timezone=True), nullable=True,
        comment="Account locked until this time due to failed attempts",
    )
    metadata_ = Column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}",
        comment="Additional doctor metadata",
    )


class PharmacyUser(Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin):
    """
    A pharmacy / lab user who accesses prescriptions for dispensing.

    Immutable fields: id, tenant_id, external_idp_id, created_at
    Mutable fields: email, full_name, pharmacy_name, is_active, etc.
    Encryption-sensitive: email, full_name (PII)
    Retention: retained for legal prescription retention period + buffer
    """
    __tablename__ = "pharmacy_users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_idp_id", name="uq_pharma_tenant_idp"),
        UniqueConstraint("tenant_id", "email", name="uq_pharma_tenant_email"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    external_idp_id = Column(
        String(500), nullable=False,
        comment="Immutable — identity from external IdP",
    )
    email = Column(
        String(320), nullable=False,
        comment="ENCRYPTION_SENSITIVE — pharmacy user email",
    )
    full_name = Column(
        String(500), nullable=False,
        comment="ENCRYPTION_SENSITIVE — pharmacy user full name",
    )
    pharmacy_name = Column(
        String(500), nullable=False,
        comment="Pharmacy / lab name",
    )
    pharmacy_license_number = Column(
        String(100), nullable=True,
        comment="Pharmacy official license number",
    )
    is_active = Column(Boolean, nullable=False, default=True)
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    locked_until = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")


class AdminUser(Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin):
    """
    Internal admin / operations / compliance / support user.

    Immutable fields: id, tenant_id, external_idp_id, created_at
    Mutable fields: email, full_name, role, is_active
    Encryption-sensitive: email, full_name
    Retention: retained for audit trail period
    """
    __tablename__ = "admin_users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_idp_id", name="uq_admin_tenant_idp"),
        UniqueConstraint("tenant_id", "email", name="uq_admin_tenant_email"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    external_idp_id = Column(
        String(500), nullable=False,
        comment="Immutable — identity from external IdP",
    )
    email = Column(
        String(320), nullable=False,
        comment="ENCRYPTION_SENSITIVE",
    )
    full_name = Column(
        String(500), nullable=False,
        comment="ENCRYPTION_SENSITIVE",
    )
    role = Column(
        String(50), nullable=False,
        comment="Admin sub-role: clinic_admin, tenant_admin, compliance_officer, platform_admin, support",
    )
    is_active = Column(Boolean, nullable=False, default=True)
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    locked_until = Column(DateTime(timezone=True), nullable=True)
    requires_justification = Column(
        Boolean, nullable=False, default=True,
        comment="Whether privileged actions require justification text",
    )
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")


class Auditor(Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin):
    """
    Read-only auditor / inspector user. Cannot modify any data.

    Immutable fields: id, tenant_id, external_idp_id, created_at
    Mutable fields: email, full_name, is_active, scope
    Encryption-sensitive: email, full_name
    Retention: retained for audit trail period
    """
    __tablename__ = "auditors"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_idp_id", name="uq_auditor_tenant_idp"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    external_idp_id = Column(
        String(500), nullable=False,
        comment="Immutable — identity from external IdP",
    )
    email = Column(
        String(320), nullable=False,
        comment="ENCRYPTION_SENSITIVE",
    )
    full_name = Column(
        String(500), nullable=False,
        comment="ENCRYPTION_SENSITIVE",
    )
    organization = Column(
        String(500), nullable=True,
        comment="Auditing organization name (e.g., AEMPS, external auditor firm)",
    )
    scope = Column(
        String(100), nullable=False, default="read_only",
        comment="Audit scope: read_only, compliance_full, inspection",
    )
    is_active = Column(Boolean, nullable=False, default=True)
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    access_expires_at = Column(
        DateTime(timezone=True), nullable=True,
        comment="Auditor access expiry — must be re-authorized after this date",
    )
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
