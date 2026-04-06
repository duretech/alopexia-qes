"""API credential metadata model — tracks service accounts and API keys."""

from sqlalchemy import (
    Column, String, Boolean, DateTime, Index, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, generate_uuid


class ApiCredentialMetadata(Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin):
    """
    Metadata about API credentials / service accounts. We do NOT store the
    actual secret — only metadata for tracking, auditing, and rotation.

    Immutable fields: id, tenant_id, key_prefix, created_by, created_at
    Mutable fields: name, is_active, last_used_at, expires_at, revoked_at
    Encryption-sensitive: none (actual secrets never stored here)
    Retention: retained for audit trail period after revocation
    """
    __tablename__ = "api_credentials_metadata"
    __table_args__ = (
        Index("ix_api_cred_tenant_active", "tenant_id", "is_active"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False, comment="Human-friendly credential name")
    key_prefix = Column(
        String(10), nullable=False,
        comment="Immutable — first 8 chars of the API key for identification (e.g., 'qes_a1b2')",
    )
    key_hash = Column(
        String(128), nullable=False,
        comment="SHA-256 hash of the full API key — for authentication lookup",
    )
    created_by = Column(UUID(as_uuid=True), nullable=False, comment="Immutable — who created this credential")

    # Scoping
    scopes = Column(
        JSONB, nullable=False, default=list, server_default="[]",
        comment="Allowed API scopes for this credential",
    )
    allowed_ips = Column(
        JSONB, nullable=True,
        comment="IP allowlist (null = no restriction)",
    )

    # Lifecycle
    is_active = Column(Boolean, nullable=False, default=True)
    expires_at = Column(
        DateTime(timezone=True), nullable=True,
        comment="Credential expiry — null means no expiry (not recommended for production)",
    )
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_ip = Column(String(45), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(UUID(as_uuid=True), nullable=True)
    revocation_reason = Column(String(500), nullable=True)

    # Rotation
    rotated_from_id = Column(
        UUID(as_uuid=True), nullable=True,
        comment="Previous credential ID if this was created by rotation",
    )
