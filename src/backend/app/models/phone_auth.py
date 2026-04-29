"""Phone OTP + PIN authentication models (alopexiaqes schema)."""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base, TenantScopedMixin, TimestampMixin, generate_uuid


class PhoneAuthAccount(Base, TenantScopedMixin, TimestampMixin):
    """Per-user phone login credentials with encrypted phone and PIN."""

    __tablename__ = "phone_auth_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "phone_hash", "portal", name="uq_phone_auth_tenant_phone_portal"),
        Index("ix_phone_auth_lookup", "tenant_id", "phone_hash", "portal"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    user_type = Column(String(50), nullable=False, comment="doctor, pharmacy_user, admin_user, auditor")
    portal = Column(String(20), nullable=False, comment="doctor, pharmacy, admin")
    phone_hash = Column(String(64), nullable=False, comment="SHA-256 normalized phone for lookup")
    phone_encrypted = Column(String, nullable=False, comment="AES-GCM encrypted phone number")
    pin_encrypted = Column(String, nullable=True, comment="AES-GCM encrypted user-set PIN; NULL until user completes first-login PIN setup")
    temp_pin_encrypted = Column(String, nullable=True, comment="AES-GCM encrypted temporary PIN set by admin; cleared after user sets own PIN")
    pin_set = Column(Boolean, nullable=False, default=False, server_default=text("FALSE"), comment="True once user has set their own permanent PIN")
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("TRUE"))


class PhoneOtpChallenge(Base, TenantScopedMixin, TimestampMixin):
    """OTP challenge records; OTP value is encrypted at rest."""

    __tablename__ = "phone_otp_challenges"
    __table_args__ = (
        Index("ix_phone_otp_account", "tenant_id", "account_id"),
        Index("ix_phone_otp_expiry", "tenant_id", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("phone_auth_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    otp_encrypted = Column(String, nullable=False, comment="AES-GCM encrypted one-time code")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0, server_default=text("0"))

