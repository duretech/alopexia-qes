"""Audit chain integrity verification and gap detection.

This module provides two critical detective controls:

1. **Hash chain verification** (C-AUDIT-04): Walks the entire audit event
   chain and recomputes every hash. Any mismatch indicates tampering.

2. **Sequence gap detection** (C-AUDIT-05): Checks for missing sequence
   numbers. Gaps from transaction rollbacks are expected (and documented),
   but unexpected gaps indicate possible event deletion.

Both routines are designed to be run:
  - As a scheduled background job (e.g., every hour)
  - On-demand by a compliance officer
  - By external auditors against exported JSON Lines data

The verification routines are READ-ONLY — they never modify audit_events.
Results are returned as structured data that can be logged, stored, or
exported. When verification detects a problem, the calling code should
emit an audit meta-event (AUDIT_INTEGRITY_CHECK_FAILED or AUDIT_GAP_DETECTED)
and trigger alerting.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.base import SCHEMA_NAME
from app.services.audit.hash_chain import GENESIS_HASH, compute_event_hash

logger = get_logger(component="audit_verification")


@dataclass
class ChainVerificationResult:
    """Result of a full or partial chain integrity verification."""

    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    events_checked: int = 0
    events_valid: int = 0
    events_invalid: int = 0
    first_invalid_sequence: int | None = None
    invalid_events: list[dict] = field(default_factory=list)
    is_intact: bool = True

    @property
    def summary(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "events_checked": self.events_checked,
            "events_valid": self.events_valid,
            "events_invalid": self.events_invalid,
            "first_invalid_sequence": self.first_invalid_sequence,
            "is_intact": self.is_intact,
        }


@dataclass
class GapDetectionResult:
    """Result of sequence gap detection."""

    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    first_sequence: int | None = None
    last_sequence: int | None = None
    expected_count: int = 0
    actual_count: int = 0
    gaps: list[dict] = field(default_factory=list)
    has_gaps: bool = False

    @property
    def summary(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "first_sequence": self.first_sequence,
            "last_sequence": self.last_sequence,
            "expected_count": self.expected_count,
            "actual_count": self.actual_count,
            "gap_count": len(self.gaps),
            "has_gaps": self.has_gaps,
        }


async def verify_chain_integrity(
    db: AsyncSession,
    *,
    batch_size: int = 1000,
    start_sequence: int | None = None,
    end_sequence: int | None = None,
) -> ChainVerificationResult:
    """Verify the hash chain integrity of the audit event log.

    Walks the chain in sequence order, recomputing each event's hash
    and comparing it to the stored current_hash. Also verifies that
    each event's previous_hash matches the preceding event's current_hash.

    Args:
        db: Active async database session (read-only).
        batch_size: Number of events to fetch per query (memory control).
        start_sequence: Start verification from this sequence number (inclusive).
                        Defaults to the first event.
        end_sequence: Stop verification at this sequence number (inclusive).
                      Defaults to the last event.

    Returns:
        ChainVerificationResult with details of any integrity failures.
    """
    result = ChainVerificationResult()
    expected_previous_hash = GENESIS_HASH
    is_first = True

    async for event_row in _iter_events(db, batch_size, start_sequence, end_sequence):
        result.events_checked += 1

        seq = event_row.sequence_number
        stored_hash = event_row.current_hash
        stored_prev = event_row.previous_hash

        # Verify previous_hash linkage (skip for first event if starting mid-chain)
        if is_first and start_sequence is not None:
            # When starting mid-chain, we trust the stored previous_hash
            # as the starting point (caller should verify the start separately)
            expected_previous_hash = stored_prev
            is_first = False
        elif is_first:
            is_first = False
            # First event in the chain: previous_hash should be GENESIS_HASH
            if stored_prev != GENESIS_HASH:
                result.is_intact = False
                result.events_invalid += 1
                if result.first_invalid_sequence is None:
                    result.first_invalid_sequence = seq
                result.invalid_events.append({
                    "sequence_number": seq,
                    "issue": "genesis_previous_hash_mismatch",
                    "expected_previous": GENESIS_HASH,
                    "stored_previous": stored_prev,
                })
                expected_previous_hash = stored_hash
                continue

        # Verify previous_hash matches the chain
        if stored_prev != expected_previous_hash:
            result.is_intact = False
            result.events_invalid += 1
            if result.first_invalid_sequence is None:
                result.first_invalid_sequence = seq
            result.invalid_events.append({
                "sequence_number": seq,
                "issue": "previous_hash_mismatch",
                "expected_previous": expected_previous_hash,
                "stored_previous": stored_prev,
            })

        # Recompute and verify current_hash
        recomputed = compute_event_hash(
            sequence_number=seq,
            event_type=event_row.event_type,
            actor_id=str(event_row.actor_id) if event_row.actor_id else None,
            tenant_id=str(event_row.tenant_id) if event_row.tenant_id else None,
            event_timestamp=event_row.event_timestamp,
            object_type=event_row.object_type,
            object_id=str(event_row.object_id) if event_row.object_id else None,
            previous_hash=stored_prev,
            detail=event_row.detail,
        )

        if recomputed != stored_hash:
            result.is_intact = False
            result.events_invalid += 1
            if result.first_invalid_sequence is None:
                result.first_invalid_sequence = seq
            result.invalid_events.append({
                "sequence_number": seq,
                "issue": "current_hash_mismatch",
                "expected_hash": recomputed,
                "stored_hash": stored_hash,
            })
        else:
            result.events_valid += 1

        expected_previous_hash = stored_hash

    result.completed_at = datetime.now(timezone.utc)

    if result.is_intact:
        logger.info(
            "chain_integrity_verified",
            events_checked=result.events_checked,
        )
    else:
        logger.error(
            "chain_integrity_failure",
            events_checked=result.events_checked,
            events_invalid=result.events_invalid,
            first_invalid_sequence=result.first_invalid_sequence,
        )

    return result


async def detect_gaps(db: AsyncSession) -> GapDetectionResult:
    """Detect gaps in the audit event sequence numbers.

    Gaps from transaction rollbacks are expected — PostgreSQL sequences
    can have gaps when transactions abort. However, unexpected gaps
    (especially large ones or gaps in otherwise contiguous ranges)
    may indicate event deletion or tampering.

    Returns:
        GapDetectionResult with list of detected gap ranges.
    """
    result = GapDetectionResult()

    # Get the range and count
    range_result = await db.execute(
        text(
            f"SELECT MIN(sequence_number), MAX(sequence_number), COUNT(*) "
            f"FROM {SCHEMA_NAME}.audit_events"
        )
    )
    row = range_result.first()
    if row is None or row[0] is None:
        result.completed_at = datetime.now(timezone.utc)
        return result

    result.first_sequence = row[0]
    result.last_sequence = row[1]
    result.actual_count = row[2]
    result.expected_count = result.last_sequence - result.first_sequence + 1

    if result.actual_count == result.expected_count:
        # No gaps
        result.completed_at = datetime.now(timezone.utc)
        logger.info(
            "gap_detection_clean",
            first_sequence=result.first_sequence,
            last_sequence=result.last_sequence,
            count=result.actual_count,
        )
        return result

    # Find specific gap ranges using a window function
    # This query finds sequences where the next sequence_number is not +1
    gap_query = text(f"""
        SELECT
            sequence_number AS gap_after,
            next_seq AS gap_before,
            (next_seq - sequence_number - 1) AS gap_size
        FROM (
            SELECT
                sequence_number,
                LEAD(sequence_number) OVER (ORDER BY sequence_number) AS next_seq
            FROM {SCHEMA_NAME}.audit_events
        ) sub
        WHERE next_seq - sequence_number > 1
        ORDER BY sequence_number
    """)

    gap_rows = await db.execute(gap_query)
    for gap_row in gap_rows:
        result.gaps.append({
            "after_sequence": gap_row.gap_after,
            "before_sequence": gap_row.gap_before,
            "missing_count": gap_row.gap_size,
        })

    result.has_gaps = len(result.gaps) > 0
    result.completed_at = datetime.now(timezone.utc)

    if result.has_gaps:
        logger.warning(
            "sequence_gaps_detected",
            gap_count=len(result.gaps),
            total_missing=result.expected_count - result.actual_count,
            first_sequence=result.first_sequence,
            last_sequence=result.last_sequence,
        )

    return result


async def _iter_events(
    db: AsyncSession,
    batch_size: int,
    start_sequence: int | None,
    end_sequence: int | None,
) -> AsyncGenerator:
    """Iterate over audit events in sequence order, yielding batches.

    Uses keyset pagination for efficient scanning of large tables.
    """
    conditions = []
    params: dict = {}

    if start_sequence is not None:
        conditions.append("sequence_number >= :start_seq")
        params["start_seq"] = start_sequence
    if end_sequence is not None:
        conditions.append("sequence_number <= :end_seq")
        params["end_seq"] = end_sequence

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    last_seq = None
    while True:
        if last_seq is not None:
            seq_condition = "sequence_number > :last_seq"
            params["last_seq"] = last_seq
            if where_clause:
                page_where = where_clause + f" AND {seq_condition}"
            else:
                page_where = f"WHERE {seq_condition}"
        else:
            page_where = where_clause

        query = text(
            f"SELECT id, sequence_number, previous_hash, current_hash, "
            f"event_type, actor_id, tenant_id, event_timestamp, "
            f"object_type, object_id, detail "
            f"FROM {SCHEMA_NAME}.audit_events "
            f"{page_where} "
            f"ORDER BY sequence_number ASC "
            f"LIMIT :batch_size"
        )
        params["batch_size"] = batch_size

        result = await db.execute(query, params)
        rows = result.fetchall()

        if not rows:
            break

        for row in rows:
            last_seq = row.sequence_number
            yield row
