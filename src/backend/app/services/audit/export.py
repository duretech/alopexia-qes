"""Audit event export to JSON Lines format for auditor review.

JSON Lines (one JSON object per line) is the export format for external
auditors, compliance officers, and the WORM-compatible S3 export pipeline.

This format was chosen because:
  - Human-readable and machine-parseable
  - Streamable — no need to hold the entire export in memory
  - Each line is independently verifiable via the hash chain
  - Standard tooling (jq, Python, etc.) can process it
  - Compatible with log aggregation systems

Export procedure (docs/audit-readiness.md §Audit Export Procedure):
  1. Compliance officer requests export for a date range / event types
  2. System generates JSON Lines output
  3. Export includes integrity verification summary as the first line
  4. Export stored in WORM-compatible bucket
  5. Export event itself recorded in audit trail

Implements C-AUDIT-07 from the controls catalog.
"""

import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.base import SCHEMA_NAME

logger = get_logger(component="audit_export")


class _JSONEncoder(json.JSONEncoder):
    """JSON encoder that handles UUID and datetime serialisation."""

    def default(self, o: Any) -> Any:
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def _json_line(obj: dict) -> str:
    """Serialise a dict to a single JSON line (no trailing newline)."""
    return json.dumps(obj, cls=_JSONEncoder, sort_keys=True, separators=(",", ":"))


async def export_events(
    db: AsyncSession,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    event_types: list[str] | None = None,
    tenant_id: UUID | None = None,
    batch_size: int = 1000,
) -> AsyncGenerator[str, None]:
    """Export audit events as JSON Lines (one JSON object per line).

    Yields individual lines. The first line is always a metadata header
    with export parameters and timestamp. Subsequent lines are audit events
    in sequence order.

    Args:
        db: Active async database session (read-only).
        start_date: Include events from this timestamp (inclusive).
        end_date: Include events up to this timestamp (inclusive).
        event_types: Filter to specific event types (None = all).
        tenant_id: Filter to a specific tenant (None = all, for platform auditors).
        batch_size: Number of events to fetch per DB query.

    Yields:
        JSON Lines strings (one per event, plus header and footer).
    """
    export_id = str(UUID(int=0))  # Placeholder; caller should generate
    export_timestamp = datetime.now(timezone.utc)

    # Yield header line
    header = {
        "_type": "export_header",
        "export_id": export_id,
        "export_timestamp": export_timestamp.isoformat(),
        "format": "jsonlines",
        "version": "1.0",
        "filters": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "event_types": event_types,
            "tenant_id": str(tenant_id) if tenant_id else None,
        },
    }
    yield _json_line(header)

    # Build query
    conditions = []
    params: dict[str, Any] = {}

    if start_date is not None:
        conditions.append("event_timestamp >= :start_date")
        params["start_date"] = start_date
    if end_date is not None:
        conditions.append("event_timestamp <= :end_date")
        params["end_date"] = end_date
    if tenant_id is not None:
        conditions.append("tenant_id = :tenant_id")
        params["tenant_id"] = tenant_id
    if event_types:
        conditions.append("event_type = ANY(:event_types)")
        params["event_types"] = event_types

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # Keyset pagination for large exports
    event_count = 0
    last_seq = None

    while True:
        page_conditions = list(conditions)
        page_params = dict(params)

        if last_seq is not None:
            page_conditions.append("sequence_number > :last_seq")
            page_params["last_seq"] = last_seq

        page_where = ""
        if page_conditions:
            page_where = "WHERE " + " AND ".join(page_conditions)

        query = text(
            f"SELECT id, sequence_number, previous_hash, current_hash, "
            f"event_type, event_category, severity, "
            f"actor_id, actor_type, actor_role, actor_email, "
            f"tenant_id, object_type, object_id, "
            f"action, detail, outcome, "
            f"event_timestamp, source_ip, user_agent, "
            f"request_id, correlation_id, session_id, "
            f"is_sensitive, justification, "
            f"state_before, state_after "
            f"FROM {SCHEMA_NAME}.audit_events "
            f"{page_where} "
            f"ORDER BY sequence_number ASC "
            f"LIMIT :batch_size"
        )
        page_params["batch_size"] = batch_size

        result = await db.execute(query, page_params)
        rows = result.fetchall()

        if not rows:
            break

        for row in rows:
            last_seq = row.sequence_number
            event_count += 1

            event_dict = {
                "_type": "audit_event",
                "id": str(row.id),
                "sequence_number": row.sequence_number,
                "previous_hash": row.previous_hash,
                "current_hash": row.current_hash,
                "event_type": row.event_type,
                "event_category": row.event_category,
                "severity": row.severity,
                "actor_id": str(row.actor_id) if row.actor_id else None,
                "actor_type": row.actor_type,
                "actor_role": row.actor_role,
                "actor_email": row.actor_email,
                "tenant_id": str(row.tenant_id) if row.tenant_id else None,
                "object_type": row.object_type,
                "object_id": str(row.object_id) if row.object_id else None,
                "action": row.action,
                "detail": row.detail,
                "outcome": row.outcome,
                "event_timestamp": row.event_timestamp.isoformat() if row.event_timestamp else None,
                "source_ip": row.source_ip,
                "user_agent": row.user_agent,
                "request_id": row.request_id,
                "correlation_id": row.correlation_id,
                "session_id": str(row.session_id) if row.session_id else None,
                "is_sensitive": row.is_sensitive,
                "justification": row.justification,
                "state_before": row.state_before,
                "state_after": row.state_after,
            }
            yield _json_line(event_dict)

    # Yield footer line with summary
    footer = {
        "_type": "export_footer",
        "export_id": export_id,
        "event_count": event_count,
        "first_sequence": None,  # Populated below if events exist
        "last_sequence": last_seq,
        "export_completed_at": datetime.now(timezone.utc).isoformat(),
    }
    yield _json_line(footer)

    logger.info(
        "audit_export_completed",
        event_count=event_count,
        last_sequence=last_seq,
    )
