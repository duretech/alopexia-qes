"""Server-side session record model."""

from sqlalchemy import (
    Column, String, Boolean, DateTime, Index, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base, TenantScopedMixin, TimestampMixin, generate_uuid


class SessionRecord(Base, TenantScopedMixin, TimestampMixin):
    """
    Server-side session tracking. Each authenticated session gets a record.
    Used for session management, concurrent session limits, and audit.

    Immutable fields: id, tenant_id, user_id, user_type, created_at,
                      login_ip, login_user_agent
    Mutable fields: is_active, last_activity_at, ended_at, end_reason
    Encryption-sensitive: none
    Retention: retained for audit trail period
    """
    __tablename__ = "session_records"
    __table_args__ = (
        Index("ix_session_tenant_user", "tenant_id", "user_id"),
        Index("ix_session_active", "tenant_id", "user_id", "is_active"),
        Index("ix_session_token_hash", "token_hash", unique=True),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(UUID(as_uuid=True), nullable=False, comment="Immutable — authenticated user")
    user_type = Column(
        String(50), nullable=False,
        comment="Immutable — doctor, pharmacy_user, admin_user, auditor",
    )
    token_hash = Column(
        String(64), nullable=False, unique=True,
        comment="SHA-256 of session token — for lookup without storing raw token",
    )

    # Session state
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("TRUE"))
    last_activity_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(
        DateTime(timezone=True), nullable=False,
        comment="Absolute session expiry",
    )
    idle_expires_at = Column(
        DateTime(timezone=True), nullable=False,
        comment="Idle timeout expiry — updated on each activity",
    )

    # Login context (immutable)
    login_ip = Column(String(45), nullable=False, comment="Immutable — IP at login time")
    login_user_agent = Column(String(1000), nullable=True, comment="Immutable")
    login_method = Column(
        String(50), nullable=False, default="oidc",
        comment="Immutable — how the user authenticated: oidc, saml, api_key, mock",
    )
    mfa_verified = Column(
        Boolean, nullable=False, default=False, server_default=text("FALSE"),
        comment="Immutable — whether MFA was completed for this session",
    )

    # Session end
    ended_at = Column(DateTime(timezone=True), nullable=True)
    end_reason = Column(
        String(50), nullable=True,
        comment="logout, idle_timeout, absolute_timeout, admin_revocation, "
                "password_change, concurrent_limit, security_event",
    )

    # Device context
    device_fingerprint = Column(
        String(128), nullable=True,
        comment="Optional device fingerprint for anomaly detection",
    )
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
