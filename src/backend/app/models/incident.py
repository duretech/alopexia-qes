"""Incident record model for tracking security and compliance incidents."""

from sqlalchemy import (
    Column, String, Text, DateTime, Index, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base, TenantScopedMixin, TimestampMixin, generate_uuid


class Incident(Base, TenantScopedMixin, TimestampMixin):
    """
    Security or compliance incident record.

    Immutable fields: id, tenant_id, reported_by, reported_at, created_at
    Mutable fields: status, severity, assigned_to, resolution, etc.
    Encryption-sensitive: none (incidents should not contain raw PII)
    Retention: retained indefinitely
    """
    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incident_tenant_status", "tenant_id", "status"),
        Index("ix_incident_tenant_severity", "tenant_id", "severity"),
        CheckConstraint(
            "status IN ('open','investigating','mitigated','resolved','closed')",
            name="ck_incident_status",
        ),
        CheckConstraint(
            "severity IN ('low','medium','high','critical')",
            name="ck_incident_severity",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="open")
    incident_type = Column(
        String(100), nullable=False,
        comment="Type: unauthorized_access, data_breach, audit_integrity, "
                "verification_failure, system_compromise, policy_violation, other",
    )

    # Reporting
    reported_by = Column(UUID(as_uuid=True), nullable=False, comment="Immutable")
    reported_at = Column(DateTime(timezone=True), nullable=False, comment="Immutable")

    # Assignment
    assigned_to = Column(UUID(as_uuid=True), nullable=True)

    # Related objects
    related_object_type = Column(String(100), nullable=True)
    related_object_id = Column(UUID(as_uuid=True), nullable=True)
    related_audit_event_ids = Column(
        JSONB, nullable=True,
        comment="List of related audit event IDs",
    )

    # Resolution
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), nullable=True)
    root_cause = Column(Text, nullable=True)
    corrective_actions = Column(Text, nullable=True)

    # Timeline
    timeline = Column(
        JSONB, nullable=True,
        comment="Chronological incident timeline entries",
    )

    metadata_ = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
