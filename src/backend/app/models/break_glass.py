"""Break-glass emergency access event model."""

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Index, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base, TenantScopedMixin, TimestampMixin, generate_uuid


class BreakGlassEvent(Base, TenantScopedMixin, TimestampMixin):
    """
    Records emergency elevated-access events. Break-glass bypasses normal
    authorization controls and MUST be logged with justification.

    ALL FIELDS ARE IMMUTABLE after insert.
    Every break-glass event triggers a high-severity alert.

    Retention: retained indefinitely
    """
    __tablename__ = "break_glass_events"
    __table_args__ = (
        Index("ix_break_glass_tenant_actor", "tenant_id", "actor_id"),
        Index("ix_break_glass_timestamp", "event_timestamp"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    actor_id = Column(UUID(as_uuid=True), nullable=False, comment="Immutable — who invoked break-glass")
    actor_type = Column(String(50), nullable=False, comment="Immutable — admin_user, platform_admin, etc.")
    actor_role = Column(String(50), nullable=False, comment="Immutable — role at time of event")

    justification = Column(
        Text, nullable=False,
        comment="Immutable — MANDATORY justification for emergency access",
    )
    target_resource_type = Column(String(100), nullable=True, comment="Resource type accessed")
    target_resource_id = Column(UUID(as_uuid=True), nullable=True, comment="Resource ID accessed")
    actions_performed = Column(
        JSONB, nullable=False, default=list, server_default="[]",
        comment="List of actions performed during break-glass session",
    )

    event_timestamp = Column(DateTime(timezone=True), nullable=False)
    source_ip = Column(String(45), nullable=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)

    # Review tracking
    reviewed = Column(
        Boolean, nullable=False, default=False, server_default=text("FALSE"),
        comment="Whether this break-glass event has been reviewed by compliance",
    )
    reviewed_by = Column(UUID(as_uuid=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_outcome = Column(
        String(50), nullable=True,
        comment="justified, unjustified, escalated",
    )
    review_notes = Column(Text, nullable=True)
