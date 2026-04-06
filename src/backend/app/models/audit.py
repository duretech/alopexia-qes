"""Immutable audit event model — append-only, hash-chained."""

from sqlalchemy import (
    Column, String, Text, DateTime, BigInteger, Index, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base, generate_uuid


class AuditEvent(Base):
    """
    Append-only, hash-chained audit event. This table has NO UPDATE or DELETE
    capability at the application level. Database role used by the app should
    only have INSERT and SELECT grants.

    ALL FIELDS ARE IMMUTABLE after insert.

    The hash chain works as follows:
    - Each event stores the hash of the previous event (previous_hash)
    - current_hash = SHA-256(sequence_number || event_type || actor_id || tenant_id ||
                             timestamp || object_type || object_id || previous_hash || detail_json)
    - Integrity verification walks the chain and recomputes hashes

    This is NOT a tenant-scoped mixin because audit events span tenants
    and the tenant_id is a data field, not a filter scope (auditors may
    need cross-tenant views).

    Retention: audit events have their own retention schedule, typically
    the longest of any data type in the system.
    REQUIRES CONFIRMATION BY SPANISH HEALTHCARE / PHARMA COUNSEL
    """
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_tenant", "tenant_id"),
        Index("ix_audit_actor", "actor_id"),
        Index("ix_audit_object", "object_type", "object_id"),
        Index("ix_audit_event_type", "event_type"),
        Index("ix_audit_timestamp", "event_timestamp"),
        Index("ix_audit_sequence", "sequence_number", unique=True),
        Index("ix_audit_correlation", "correlation_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    sequence_number = Column(
        BigInteger, nullable=False, unique=True,
        comment="Monotonically increasing sequence — gaps indicate tampering",
    )

    # Hash chain
    previous_hash = Column(
        String(64), nullable=False,
        comment="SHA-256 hex of the previous audit event (genesis event uses '0'*64)",
    )
    current_hash = Column(
        String(64), nullable=False,
        comment="SHA-256 hex of this event's content including previous_hash",
    )

    # Event classification
    event_type = Column(
        String(100), nullable=False,
        comment="Structured event type from AuditEventType enum",
    )
    event_category = Column(
        String(50), nullable=False, default="application",
        comment="Category: authentication, authorization, data_access, data_mutation, "
                "system, admin, security, compliance",
    )
    severity = Column(
        String(20), nullable=False, default="info",
        comment="Severity: info, warning, error, critical",
    )

    # Actor
    actor_id = Column(
        UUID(as_uuid=True), nullable=True,
        comment="User who performed the action (null for system events)",
    )
    actor_type = Column(
        String(50), nullable=True,
        comment="Actor type: doctor, pharmacy_user, admin_user, auditor, system, api_key",
    )
    actor_role = Column(
        String(50), nullable=True,
        comment="Actor's role at time of event",
    )
    actor_email = Column(
        String(320), nullable=True,
        comment="Actor email for display (may be masked in exports)",
    )

    # Tenant context
    tenant_id = Column(
        UUID(as_uuid=True), nullable=True,
        comment="Tenant scope of the event (null for platform-level events)",
    )

    # Target object
    object_type = Column(
        String(100), nullable=True,
        comment="Type of object acted upon: prescription, document, user, etc.",
    )
    object_id = Column(
        UUID(as_uuid=True), nullable=True,
        comment="ID of the object acted upon",
    )

    # Event detail
    action = Column(
        String(100), nullable=False,
        comment="Specific action: create, read, update, delete, login, verify, etc.",
    )
    detail = Column(
        JSONB, nullable=False, default=dict, server_default="{}",
        comment="Structured event detail (before/after state, parameters, etc.)",
    )
    outcome = Column(
        String(20), nullable=False, default="success",
        comment="Outcome: success, failure, denied, error",
    )

    # Request context
    event_timestamp = Column(
        DateTime(timezone=True), nullable=False,
        server_default=text("NOW()"),
        comment="UTC timestamp of the event — server-side only",
    )
    source_ip = Column(String(45), nullable=True, comment="Client IP address")
    user_agent = Column(String(1000), nullable=True, comment="Client user agent")
    request_id = Column(
        String(100), nullable=True,
        comment="Unique request identifier",
    )
    correlation_id = Column(
        String(100), nullable=True,
        comment="Correlation ID linking related events across services",
    )
    session_id = Column(
        UUID(as_uuid=True), nullable=True,
        comment="Session record ID if applicable",
    )

    # Sensitive event classification
    is_sensitive = Column(
        String(10), nullable=False, default="false", server_default=text("'false'"),
        comment="Whether this event involves sensitive data access",
    )
    justification = Column(
        Text, nullable=True,
        comment="Mandatory justification for privileged/break-glass actions",
    )

    # Before/after state for mutations
    state_before = Column(
        JSONB, nullable=True,
        comment="Object state before mutation (for update/delete events)",
    )
    state_after = Column(
        JSONB, nullable=True,
        comment="Object state after mutation (for create/update events)",
    )
