"""Retention management service.

Handles:
  1. Retention schedule lookups per resource type
  2. Identifying resources past their retention period
  3. Checking active legal holds before deletion
  4. Executing approved soft and hard deletes
  5. Recording deletion evidence

Implements C-RET-01 through C-RET-06.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.retention import DeletionRequest, LegalHold, RetentionSchedule

logger = get_logger(component="retention_service")


async def get_retention_schedule(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    resource_type: str,
) -> RetentionSchedule | None:
    """Look up the retention schedule for a resource type within a tenant.

    Returns None if no schedule is configured (defaults should be set
    during tenant provisioning).
    """
    stmt = select(RetentionSchedule).where(
        RetentionSchedule.tenant_id == tenant_id,
        RetentionSchedule.resource_type == resource_type,
        RetentionSchedule.is_active.is_(True),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def check_legal_hold(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    target_type: str,
    target_id: uuid.UUID,
) -> bool:
    """Check if a resource is under an active legal hold.

    Returns True if at least one active legal hold exists.
    """
    stmt = select(LegalHold.id).where(
        LegalHold.tenant_id == tenant_id,
        LegalHold.target_type == target_type,
        LegalHold.target_id == target_id,
        LegalHold.is_active.is_(True),
    ).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def apply_retention_schedules(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    resource_type: str,
    batch_size: int = 100,
) -> int:
    """Identify resources past their retention expiry and create soft-delete requests.

    This is called by a scheduled job (cron/worker). It does NOT execute
    deletes — it creates DeletionRequest records that must be approved.

    Returns the number of deletion requests created.
    """
    schedule = await get_retention_schedule(
        db, tenant_id=tenant_id, resource_type=resource_type,
    )
    if schedule is None:
        logger.warning(
            "no_retention_schedule",
            tenant_id=str(tenant_id),
            resource_type=resource_type,
        )
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=schedule.retention_days)

    # For prescriptions, find those past retention with no legal hold
    if resource_type == "prescription":
        from app.models.prescription import Prescription
        stmt = (
            select(Prescription.id)
            .where(
                Prescription.tenant_id == tenant_id,
                Prescription.is_deleted.is_(False),
                Prescription.is_under_legal_hold.is_(False),
                Prescription.created_at < cutoff,
            )
            .limit(batch_size)
        )
        result = await db.execute(stmt)
        expired_ids = [row[0] for row in result.all()]
    else:
        # Generic: not implemented for other resource types yet
        return 0

    now = datetime.now(timezone.utc)
    created = 0
    for target_id in expired_ids:
        # Check for active legal hold
        has_hold = await check_legal_hold(
            db, tenant_id=tenant_id, target_type=resource_type, target_id=target_id,
        )
        if has_hold:
            continue

        # Check for existing pending deletion request
        existing = await db.execute(
            select(DeletionRequest.id).where(
                DeletionRequest.tenant_id == tenant_id,
                DeletionRequest.target_type == resource_type,
                DeletionRequest.target_id == target_id,
                DeletionRequest.status.in_(["pending_first_approval", "pending_second_approval"]),
            ).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            continue

        req = DeletionRequest(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            target_type=resource_type,
            target_id=target_id,
            deletion_type="soft",
            reason=f"Retention period expired ({schedule.retention_days} days)",
            legal_basis=schedule.retention_basis,
            requested_by=uuid.UUID(int=0),  # System-generated
            requested_at=now,
            status="pending_first_approval",
        )
        db.add(req)
        created += 1

    if created:
        await db.flush()
        logger.info(
            "retention_requests_created",
            tenant_id=str(tenant_id),
            resource_type=resource_type,
            count=created,
        )

    return created


async def execute_approved_deletions(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    batch_size: int = 50,
) -> int:
    """Execute approved deletion requests (soft delete).

    Hard deletes and cryptographic erasure require additional implementation
    per resource type and are not yet implemented.

    Returns the number of deletions executed.
    """
    stmt = select(DeletionRequest).where(
        DeletionRequest.tenant_id == tenant_id,
        DeletionRequest.status == "approved",
    ).limit(batch_size)
    result = await db.execute(stmt)
    approved = result.scalars().all()

    now = datetime.now(timezone.utc)
    executed = 0

    for req in approved:
        # Re-check legal hold before executing
        has_hold = await check_legal_hold(
            db, tenant_id=tenant_id, target_type=req.target_type, target_id=req.target_id,
        )
        if has_hold:
            logger.warning(
                "deletion_blocked_legal_hold",
                request_id=str(req.id),
                target=f"{req.target_type}/{req.target_id}",
            )
            continue

        if req.deletion_type == "soft" and req.target_type == "prescription":
            from app.models.prescription import Prescription
            await db.execute(
                update(Prescription)
                .where(Prescription.id == req.target_id, Prescription.tenant_id == tenant_id)
                .values(is_deleted=True, deleted_at=now)
            )
        else:
            # Hard delete / other resource types — not yet implemented
            logger.warning(
                "deletion_type_not_implemented",
                deletion_type=req.deletion_type,
                target_type=req.target_type,
            )
            continue

        # Mark request as executed
        await db.execute(
            update(DeletionRequest)
            .where(DeletionRequest.id == req.id)
            .values(
                status="executed",
                executed_at=now,
                execution_evidence={
                    "type": req.deletion_type,
                    "target": f"{req.target_type}/{req.target_id}",
                    "executed_at": now.isoformat(),
                },
            )
        )
        executed += 1

    if executed:
        await db.flush()
        logger.info(
            "deletions_executed",
            tenant_id=str(tenant_id),
            count=executed,
        )

    return executed
