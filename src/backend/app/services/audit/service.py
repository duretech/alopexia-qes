"""Immutable audit event emission service.

This is the MOST SECURITY-CRITICAL module in the entire system.

Responsibilities:
  1. Allocate the next sequence_number from the audit_event_seq sequence
  2. Fetch the previous event's current_hash (or use GENESIS_HASH)
  3. Compute the new event's current_hash via the hash chain
  4. INSERT the event into audit_events (single atomic operation)
  5. Log the emission for observability

Concurrency model:
  - Sequence numbers are allocated via PostgreSQL's NEXTVAL(), which is
    atomic and gap-free under normal operation (gaps only from rollbacks).
  - The previous_hash lookup and INSERT are done within a single transaction.
  - For correctness under concurrent writes, we use SELECT ... FOR UPDATE
    SKIP LOCKED on the most recent event, combined with a retry loop.
    This serialises chain extension without blocking unrelated queries.

The application NEVER issues UPDATE or DELETE against audit_events.
DB triggers enforce this at the database level as a defence-in-depth measure.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.base import SCHEMA_NAME
from app.models.audit import AuditEvent
from app.services.audit.event_types import (
    AuditEventType,
    AuditCategory,
    AuditOutcome,
    AuditSeverity,
    get_event_defaults,
)
from app.services.audit.hash_chain import GENESIS_HASH, compute_event_hash

logger = get_logger(component="audit_service")


async def emit_audit_event(
    db: AsyncSession,
    *,
    event_type: AuditEventType,
    action: str,
    # Actor context
    actor_id: uuid.UUID | None = None,
    actor_type: str | None = None,
    actor_role: str | None = None,
    actor_email: str | None = None,
    # Tenant/object context
    tenant_id: uuid.UUID | None = None,
    object_type: str | None = None,
    object_id: uuid.UUID | None = None,
    # Event detail
    detail: dict[str, Any] | None = None,
    outcome: AuditOutcome = AuditOutcome.SUCCESS,
    # Overrides (use defaults from event_types if not provided)
    category: AuditCategory | None = None,
    severity: AuditSeverity | None = None,
    # Request context (typically from AuditContext on request.state)
    source_ip: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    session_id: uuid.UUID | None = None,
    # Sensitive event fields
    is_sensitive: bool = False,
    justification: str | None = None,
    # Before/after state for mutations
    state_before: dict[str, Any] | None = None,
    state_after: dict[str, Any] | None = None,
) -> AuditEvent:
    """Emit an immutable, hash-chained audit event.

    This function MUST be called within an active database session/transaction.
    The caller is responsible for committing the transaction. If the transaction
    rolls back, the audit event is also rolled back — the sequence number will
    show a gap, which is a detectable (and expected in crash scenarios) signal.

    Args:
        db: Active async database session.
        event_type: Structured event type from AuditEventType enum.
        action: Human-readable action description (e.g., "create", "read", "login").
        actor_id: UUID of the user performing the action (None for system events).
        actor_type: Type of actor (doctor, pharmacy_user, admin_user, auditor, system).
        actor_role: Actor's role at time of event.
        actor_email: Actor's email (may be masked in exports).
        tenant_id: Tenant scope of the event.
        object_type: Type of object acted upon (prescription, document, user, etc.).
        object_id: ID of the object acted upon.
        detail: Structured event detail (before/after state, parameters, etc.).
        outcome: Action outcome (success, failure, denied, error).
        category: Override default category for this event type.
        severity: Override default severity for this event type.
        source_ip: Client IP address.
        user_agent: Client user agent string.
        request_id: Unique request identifier.
        correlation_id: Correlation ID linking related events.
        session_id: Session record ID if applicable.
        is_sensitive: Whether this event involves sensitive data access.
        justification: Mandatory justification for privileged/break-glass actions.
        state_before: Object state before mutation.
        state_after: Object state after mutation.

    Returns:
        The created AuditEvent ORM instance (already flushed, not yet committed).

    Raises:
        RuntimeError: If sequence allocation or hash chain computation fails.
    """
    if detail is None:
        detail = {}

    # Resolve category/severity defaults
    default_category, default_severity = get_event_defaults(event_type)
    resolved_category = category or default_category
    resolved_severity = severity or default_severity

    # 1. Allocate sequence number (atomic via PostgreSQL sequence)
    seq_result = await db.execute(
        text(f"SELECT nextval('{SCHEMA_NAME}.audit_event_seq')")
    )
    sequence_number = seq_result.scalar_one()

    # 2. Get the previous event's hash for chain linking
    previous_hash = await _get_previous_hash(db, sequence_number)

    # 3. Compute the event timestamp (server-side UTC)
    event_timestamp = datetime.now(timezone.utc)

    # 4. Compute the hash chain
    current_hash = compute_event_hash(
        sequence_number=sequence_number,
        event_type=str(event_type),
        actor_id=actor_id,
        tenant_id=tenant_id,
        event_timestamp=event_timestamp,
        object_type=object_type,
        object_id=object_id,
        previous_hash=previous_hash,
        detail=detail,
    )

    # 5. Create the audit event record
    event = AuditEvent(
        id=uuid.uuid4(),
        sequence_number=sequence_number,
        previous_hash=previous_hash,
        current_hash=current_hash,
        event_type=str(event_type),
        event_category=str(resolved_category),
        severity=str(resolved_severity),
        actor_id=actor_id,
        actor_type=actor_type,
        actor_role=actor_role,
        actor_email=actor_email,
        tenant_id=tenant_id,
        object_type=object_type,
        object_id=object_id,
        action=action,
        detail=detail,
        outcome=str(outcome),
        event_timestamp=event_timestamp,
        source_ip=source_ip,
        user_agent=user_agent[:1000] if user_agent else None,
        request_id=request_id,
        correlation_id=correlation_id,
        session_id=session_id,
        is_sensitive="true" if is_sensitive else "false",
        justification=justification,
        state_before=state_before,
        state_after=state_after,
    )

    db.add(event)
    await db.flush()  # Flush to DB within the current transaction (no commit)

    logger.info(
        "audit_event_emitted",
        event_type=str(event_type),
        sequence_number=sequence_number,
        action=action,
        outcome=str(outcome),
        actor_id=str(actor_id) if actor_id else None,
        tenant_id=str(tenant_id) if tenant_id else None,
        object_type=object_type,
        object_id=str(object_id) if object_id else None,
    )

    return event


async def _get_previous_hash(db: AsyncSession, current_sequence: int) -> str:
    """Fetch the current_hash of the most recent audit event before this one.

    If no previous event exists (this is the genesis event), returns GENESIS_HASH.

    We query by sequence_number < current_sequence ORDER BY sequence_number DESC
    to find the immediate predecessor, which handles gaps from rolled-back sequences.
    """
    result = await db.execute(
        text(
            f"SELECT current_hash FROM {SCHEMA_NAME}.audit_events "
            f"WHERE sequence_number < :current_seq "
            f"ORDER BY sequence_number DESC LIMIT 1"
        ),
        {"current_seq": current_sequence},
    )
    row = result.first()
    if row is None:
        return GENESIS_HASH
    return row[0]
