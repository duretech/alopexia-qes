"""TOTP (authenticator app) credentials per user."""

from sqlalchemy import Column, String, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base, TenantScopedMixin, TimestampMixin, generate_uuid


class TotpCredential(Base, TenantScopedMixin, TimestampMixin):
    """Stores encrypted TOTP shared secret for MFA verification."""

    __tablename__ = "totp_credentials"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "user_type", name="uq_totp_tenant_user_type"),
        Index("ix_totp_tenant_user", "tenant_id", "user_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    user_type = Column(
        String(50),
        nullable=False,
        comment="doctor, pharmacy_user, admin_user, auditor",
    )
    secret_encrypted = Column(Text, nullable=False, comment="AES-GCM ciphertext of base32 TOTP secret")
