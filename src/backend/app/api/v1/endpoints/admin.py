"""Admin and compliance endpoints — audit export, legal holds, deletion workflow, manual review.

These endpoints serve compliance officers, tenant admins, and auditors.
All require elevated permissions and emit audit events.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.retention import LegalHold, DeletionRequest
from app.models.verification import SignatureVerificationResult
from app.schemas.admin import (
    AuditExportRequest,
    DeletionApprovalRequest,
    DeletionRequestCreate,
    DeletionRequestResponse,
    LegalHoldCreateRequest,
    LegalHoldReleaseRequest,
    LegalHoldResponse,
    ManualReviewDecision,
)
from app.services.auth.models import AuthenticatedUser
from app.services.authz.dependencies import require_permission
from app.services.authz.rbac import Permission

logger = get_logger(component="admin_endpoint")

router = APIRouter()


# ── Audit Export ─────────────────────────────────────────────────────────


@router.post(
    "/audit/export",
    summary="Export audit events as JSON Lines",
    description="Stream audit events for external audit tools. Requires AUDIT_EXPORT permission.",
)
async def export_audit_events(
    body: AuditExportRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.AUDIT_EXPORT)),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export audit events as a streaming JSON Lines response."""
    from app.services.audit.export import export_events

    # Scope to user's tenant unless they're platform-level
    tenant_filter = body.tenant_id if user.is_platform_level else user.tenant_id

    async def _stream():
        async for line in export_events(
            db,
            start_date=body.start_date,
            end_date=body.end_date,
            event_types=body.event_types,
            tenant_id=tenant_filter,
        ):
            yield line + "\n"

    return StreamingResponse(
        _stream(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=audit_export.jsonl"},
    )


# ── Legal Holds ──────────────────────────────────────────────────────────


@router.post(
    "/legal-holds",
    response_model=LegalHoldResponse,
    status_code=201,
    summary="Place a legal hold on a resource",
)
async def create_legal_hold(
    body: LegalHoldCreateRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.RETENTION_MANAGE_LEGAL_HOLD)),
    db: AsyncSession = Depends(get_db),
) -> LegalHoldResponse:
    """Place a legal hold preventing deletion regardless of retention schedule."""
    import uuid
    now = datetime.now(timezone.utc)

    hold = LegalHold(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        target_type=body.target_type,
        target_id=body.target_id,
        reason=body.reason,
        reference_number=body.reference_number,
        placed_by=user.user_id,
        placed_at=now,
        is_active=True,
    )
    db.add(hold)
    await db.flush()

    logger.info(
        "legal_hold_placed",
        hold_id=str(hold.id),
        target_type=body.target_type,
        target_id=str(body.target_id),
        placed_by=str(user.user_id),
    )

    return LegalHoldResponse(
        id=hold.id,
        target_type=hold.target_type,
        target_id=hold.target_id,
        reason=hold.reason,
        reference_number=hold.reference_number,
        placed_by=hold.placed_by,
        placed_at=hold.placed_at,
        is_active=True,
    )


@router.get(
    "/legal-holds",
    response_model=list[LegalHoldResponse],
    summary="List legal holds",
)
async def list_legal_holds(
    user: AuthenticatedUser = Depends(require_permission(Permission.RETENTION_MANAGE_LEGAL_HOLD)),
    db: AsyncSession = Depends(get_db),
    active_only: bool = True,
) -> list[LegalHoldResponse]:
    """List legal holds within the user's tenant."""
    stmt = select(LegalHold).where(LegalHold.tenant_id == user.tenant_id)
    if active_only:
        stmt = stmt.where(LegalHold.is_active.is_(True))
    stmt = stmt.order_by(LegalHold.placed_at.desc())

    result = await db.execute(stmt)
    holds = result.scalars().all()

    return [
        LegalHoldResponse(
            id=h.id, target_type=h.target_type, target_id=h.target_id,
            reason=h.reason, reference_number=h.reference_number,
            placed_by=h.placed_by, placed_at=h.placed_at,
            is_active=h.is_active, released_by=h.released_by,
            released_at=h.released_at,
        )
        for h in holds
    ]


@router.post(
    "/legal-holds/{hold_id}/release",
    response_model=LegalHoldResponse,
    summary="Release a legal hold",
)
async def release_legal_hold(
    hold_id: UUID,
    body: LegalHoldReleaseRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.RETENTION_MANAGE_LEGAL_HOLD)),
    db: AsyncSession = Depends(get_db),
) -> LegalHoldResponse:
    """Release an active legal hold."""
    stmt = select(LegalHold).where(
        LegalHold.id == hold_id,
        LegalHold.tenant_id == user.tenant_id,
    )
    result = await db.execute(stmt)
    hold = result.scalar_one_or_none()

    if hold is None:
        raise HTTPException(status_code=404, detail="Legal hold not found")
    if not hold.is_active:
        raise HTTPException(status_code=409, detail="Legal hold is already released")

    now = datetime.now(timezone.utc)
    await db.execute(
        update(LegalHold)
        .where(LegalHold.id == hold_id)
        .values(
            is_active=False,
            released_by=user.user_id,
            released_at=now,
            release_reason=body.release_reason,
        )
    )
    await db.flush()

    return LegalHoldResponse(
        id=hold.id, target_type=hold.target_type, target_id=hold.target_id,
        reason=hold.reason, reference_number=hold.reference_number,
        placed_by=hold.placed_by, placed_at=hold.placed_at,
        is_active=False, released_by=user.user_id, released_at=now,
    )


# ── Deletion Requests ────────────────────────────────────────────────────


@router.post(
    "/deletion-requests",
    response_model=DeletionRequestResponse,
    status_code=201,
    summary="Create a deletion request (requires dual approval for hard delete)",
)
async def create_deletion_request(
    body: DeletionRequestCreate,
    user: AuthenticatedUser = Depends(require_permission(Permission.RETENTION_APPROVE_DELETION)),
    db: AsyncSession = Depends(get_db),
) -> DeletionRequestResponse:
    """Initiate a deletion workflow. Hard deletes require two approvers."""
    import uuid
    now = datetime.now(timezone.utc)

    # Check for active legal holds on the target
    hold_stmt = select(LegalHold).where(
        LegalHold.tenant_id == user.tenant_id,
        LegalHold.target_type == body.target_type,
        LegalHold.target_id == body.target_id,
        LegalHold.is_active.is_(True),
    ).limit(1)
    hold_result = await db.execute(hold_stmt)
    if hold_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: resource is under an active legal hold",
        )

    deletion_req = DeletionRequest(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        target_type=body.target_type,
        target_id=body.target_id,
        deletion_type=body.deletion_type,
        reason=body.reason,
        legal_basis=body.legal_basis,
        requested_by=user.user_id,
        requested_at=now,
        status="pending_first_approval",
    )
    db.add(deletion_req)
    await db.flush()

    return DeletionRequestResponse(
        id=deletion_req.id,
        target_type=deletion_req.target_type,
        target_id=deletion_req.target_id,
        deletion_type=deletion_req.deletion_type,
        reason=deletion_req.reason,
        status=deletion_req.status,
        requested_by=deletion_req.requested_by,
        requested_at=deletion_req.requested_at,
    )


@router.post(
    "/deletion-requests/{request_id}/approve",
    response_model=DeletionRequestResponse,
    summary="Approve or reject a deletion request",
)
async def approve_deletion_request(
    request_id: UUID,
    body: DeletionApprovalRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.RETENTION_APPROVE_DELETION)),
    db: AsyncSession = Depends(get_db),
) -> DeletionRequestResponse:
    """Approve or reject a deletion request (dual approval for hard deletes)."""
    stmt = select(DeletionRequest).where(
        DeletionRequest.id == request_id,
        DeletionRequest.tenant_id == user.tenant_id,
    )
    result = await db.execute(stmt)
    del_req = result.scalar_one_or_none()

    if del_req is None:
        raise HTTPException(status_code=404, detail="Deletion request not found")

    now = datetime.now(timezone.utc)

    if body.decision == "reject":
        await db.execute(
            update(DeletionRequest)
            .where(DeletionRequest.id == request_id)
            .values(
                status="rejected",
                rejection_reason=body.reason,
                rejected_by=user.user_id,
            )
        )
        await db.flush()
        del_req.status = "rejected"
    elif del_req.status == "pending_first_approval":
        # Cannot approve your own request
        if del_req.requested_by == user.user_id:
            raise HTTPException(
                status_code=409,
                detail="Cannot approve your own deletion request",
            )
        await db.execute(
            update(DeletionRequest)
            .where(DeletionRequest.id == request_id)
            .values(
                status="pending_second_approval" if del_req.deletion_type == "hard" else "approved",
                first_approver_id=user.user_id,
                first_approved_at=now,
            )
        )
        await db.flush()
        del_req.status = "pending_second_approval" if del_req.deletion_type == "hard" else "approved"
    elif del_req.status == "pending_second_approval":
        # Second approver must differ from first
        if del_req.first_approver_id == user.user_id:
            raise HTTPException(
                status_code=409,
                detail="Second approver must be different from first approver",
            )
        if del_req.requested_by == user.user_id:
            raise HTTPException(
                status_code=409,
                detail="Cannot approve your own deletion request",
            )
        await db.execute(
            update(DeletionRequest)
            .where(DeletionRequest.id == request_id)
            .values(
                status="approved",
                second_approver_id=user.user_id,
                second_approved_at=now,
            )
        )
        await db.flush()
        del_req.status = "approved"
    else:
        raise HTTPException(
            status_code=409,
            detail=f"Deletion request is in status '{del_req.status}' and cannot be approved",
        )

    return DeletionRequestResponse(
        id=del_req.id,
        target_type=del_req.target_type,
        target_id=del_req.target_id,
        deletion_type=del_req.deletion_type,
        reason=del_req.reason,
        status=del_req.status,
        requested_by=del_req.requested_by,
        requested_at=del_req.requested_at,
    )


# ── Manual Review ────────────────────────────────────────────────────────


@router.post(
    "/verifications/{verification_id}/review",
    summary="Submit a manual review decision for a verification result",
)
async def submit_manual_review(
    verification_id: UUID,
    body: ManualReviewDecision,
    user: AuthenticatedUser = Depends(require_permission(Permission.VERIFICATION_MANUAL_REVIEW)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit a manual review decision for a failed/indeterminate verification."""
    stmt = select(SignatureVerificationResult).where(
        SignatureVerificationResult.id == verification_id,
        SignatureVerificationResult.tenant_id == user.tenant_id,
    )
    result = await db.execute(stmt)
    verification = result.scalar_one_or_none()

    if verification is None:
        raise HTTPException(status_code=404, detail="Verification result not found")

    if not verification.requires_manual_review:
        raise HTTPException(
            status_code=409,
            detail="This verification does not require manual review",
        )

    if verification.manual_review_completed_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Manual review has already been completed",
        )

    now = datetime.now(timezone.utc)
    await db.execute(
        update(SignatureVerificationResult)
        .where(SignatureVerificationResult.id == verification_id)
        .values(
            manual_review_completed_at=now,
            manual_review_by=user.user_id,
            manual_review_decision=body.decision,
            manual_review_notes=body.notes,
        )
    )

    # If accepted, update prescription status to verified/available
    if body.decision == "accept":
        from sqlalchemy import select as sa_select
        from app.models.prescription import Prescription
        await db.execute(
            update(Prescription)
            .where(Prescription.id == verification.prescription_id)
            .values(status="verified", verification_status="verified")
        )

    await db.flush()

    logger.info(
        "manual_review_completed",
        verification_id=str(verification_id),
        decision=body.decision,
        reviewer=str(user.user_id),
    )

    return {
        "verification_id": str(verification_id),
        "decision": body.decision,
        "reviewed_by": str(user.user_id),
        "reviewed_at": now.isoformat(),
    }
