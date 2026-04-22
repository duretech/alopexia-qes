"""Admin and compliance endpoints — full feature set.

Audit:
  POST /admin/audit/export               — Export audit events as JSON Lines
  GET  /admin/audit/events               — Query/filter audit events (explorer)

Legal Holds:
  POST /admin/legal-holds                — Place legal hold
  GET  /admin/legal-holds                — List legal holds
  POST /admin/legal-holds/{id}/release   — Release hold

Deletion Requests:
  GET  /admin/deletion-requests          — List deletion requests
  POST /admin/deletion-requests          — Create deletion request
  POST /admin/deletion-requests/{id}/approve — Approve/reject

Manual Review:
  POST /admin/verifications/{id}/review  — Submit manual review
  GET  /admin/verifications/pending-review — List pending reviews

Incidents:
  GET  /admin/incidents                  — List incidents
  POST /admin/incidents                  — Create incident
  GET  /admin/incidents/{id}             — Get incident detail
  PATCH /admin/incidents/{id}            — Update incident status/details

Users:
  GET  /admin/users                      — List users (all types)
  POST /admin/users/{user_type}          — Create user
  PATCH /admin/users/{user_type}/{id}    — Update user (suspend, activate)

Evidence:
  GET  /admin/evidence                   — List evidence files across tenant
  GET  /admin/evidence/{id}/download     — Get signed URL for evidence download

Health:
  GET  /admin/health/stats               — System health stats + dashboard data

Suspicious Events:
  GET  /admin/suspicious-events          — Suspicious / high-severity audit events queue
"""

import uuid as uuid_lib
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.evidence import EvidenceFile
from app.models.incident import Incident
from app.models.prescription import Prescription
from app.models.retention import LegalHold, DeletionRequest
from app.models.users import AdminUser, Doctor, PharmacyUser
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
from app.utils.encryption import decrypt_field

logger = get_logger(component="admin_endpoint")


def _safe_decrypt(value: str) -> str:
    try:
        return decrypt_field(value)
    except Exception:
        return value

router = APIRouter()


# ── Audit Export ─────────────────────────────────────────────────────────


@router.post(
    "/audit/export",
    summary="Export audit events as JSON Lines",
)
async def export_audit_events(
    body: AuditExportRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.AUDIT_EXPORT)),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    from app.services.audit.export import export_events
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


@router.get(
    "/audit/events",
    summary="Audit event explorer — query and filter audit events",
)
async def list_audit_events(
    user: AuthenticatedUser = Depends(require_permission(Permission.AUDIT_VIEW_TENANT)),
    db: AsyncSession = Depends(get_db),
    event_type: str | None = None,
    actor_id: UUID | None = None,
    object_type: str | None = None,
    object_id: UUID | None = None,
    severity: str | None = None,
    outcome: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> dict:
    """Query audit events with filters. Returns paginated results."""
    stmt = select(AuditEvent).where(AuditEvent.tenant_id == user.tenant_id)

    if event_type:
        stmt = stmt.where(AuditEvent.event_type.ilike(f"%{event_type}%"))
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if object_type:
        stmt = stmt.where(AuditEvent.object_type == object_type)
    if object_id:
        stmt = stmt.where(AuditEvent.object_id == object_id)
    if severity:
        stmt = stmt.where(AuditEvent.severity == severity)
    if outcome:
        stmt = stmt.where(AuditEvent.outcome == outcome)
    if start_date:
        stmt = stmt.where(AuditEvent.event_timestamp >= start_date)
    if end_date:
        stmt = stmt.where(AuditEvent.event_timestamp <= end_date)

    # Count query
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = stmt.order_by(AuditEvent.event_timestamp.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    events = result.scalars().all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "events": [
            {
                "id": str(e.id),
                "sequence_number": e.sequence_number,
                "event_type": e.event_type,
                "event_category": e.event_category,
                "severity": e.severity,
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "actor_type": e.actor_type,
                "actor_role": e.actor_role,
                "actor_email": e.actor_email,
                "object_type": e.object_type,
                "object_id": str(e.object_id) if e.object_id else None,
                "action": e.action,
                "outcome": e.outcome,
                "event_timestamp": e.event_timestamp.isoformat() if e.event_timestamp else None,
                "source_ip": e.source_ip,
                "detail": e.detail,
            }
            for e in events
        ],
    }


# ── Legal Holds ──────────────────────────────────────────────────────────


@router.post("/legal-holds", response_model=LegalHoldResponse, status_code=201)
async def create_legal_hold(
    body: LegalHoldCreateRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.RETENTION_MANAGE_LEGAL_HOLD)),
    db: AsyncSession = Depends(get_db),
) -> LegalHoldResponse:
    now = datetime.now(timezone.utc)
    hold = LegalHold(
        id=uuid_lib.uuid4(),
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
    return LegalHoldResponse(
        id=hold.id, target_type=hold.target_type, target_id=hold.target_id,
        reason=hold.reason, reference_number=hold.reference_number,
        placed_by=hold.placed_by, placed_at=hold.placed_at, is_active=True,
    )


@router.get("/legal-holds", response_model=list[LegalHoldResponse])
async def list_legal_holds(
    user: AuthenticatedUser = Depends(require_permission(Permission.RETENTION_MANAGE_LEGAL_HOLD)),
    db: AsyncSession = Depends(get_db),
    active_only: bool = True,
) -> list[LegalHoldResponse]:
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
            is_active=h.is_active, released_by=h.released_by, released_at=h.released_at,
        )
        for h in holds
    ]


@router.post("/legal-holds/{hold_id}/release", response_model=LegalHoldResponse)
async def release_legal_hold(
    hold_id: UUID,
    body: LegalHoldReleaseRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.RETENTION_MANAGE_LEGAL_HOLD)),
    db: AsyncSession = Depends(get_db),
) -> LegalHoldResponse:
    stmt = select(LegalHold).where(LegalHold.id == hold_id, LegalHold.tenant_id == user.tenant_id)
    result = await db.execute(stmt)
    hold = result.scalar_one_or_none()
    if hold is None:
        raise HTTPException(status_code=404, detail="Legal hold not found")
    if not hold.is_active:
        raise HTTPException(status_code=409, detail="Legal hold is already released")

    now = datetime.now(timezone.utc)
    await db.execute(
        update(LegalHold).where(LegalHold.id == hold_id).values(
            is_active=False, released_by=user.user_id, released_at=now, release_reason=body.release_reason,
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


@router.get("/deletion-requests", response_model=list[DeletionRequestResponse])
async def list_deletion_requests(
    user: AuthenticatedUser = Depends(require_permission(Permission.RETENTION_APPROVE_DELETION)),
    db: AsyncSession = Depends(get_db),
) -> list[DeletionRequestResponse]:
    stmt = (
        select(DeletionRequest)
        .where(DeletionRequest.tenant_id == user.tenant_id)
        .order_by(DeletionRequest.requested_at.desc())
        .limit(200)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        DeletionRequestResponse(
            id=r.id, target_type=r.target_type, target_id=r.target_id,
            deletion_type=r.deletion_type, reason=r.reason, status=r.status,
            requested_by=r.requested_by, requested_at=r.requested_at,
        )
        for r in rows
    ]


@router.post("/deletion-requests", response_model=DeletionRequestResponse, status_code=201)
async def create_deletion_request(
    body: DeletionRequestCreate,
    user: AuthenticatedUser = Depends(require_permission(Permission.RETENTION_APPROVE_DELETION)),
    db: AsyncSession = Depends(get_db),
) -> DeletionRequestResponse:
    now = datetime.now(timezone.utc)
    hold_stmt = select(LegalHold).where(
        LegalHold.tenant_id == user.tenant_id,
        LegalHold.target_type == body.target_type,
        LegalHold.target_id == body.target_id,
        LegalHold.is_active.is_(True),
    ).limit(1)
    hold_result = await db.execute(hold_stmt)
    if hold_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Cannot delete: resource is under an active legal hold")

    deletion_req = DeletionRequest(
        id=uuid_lib.uuid4(), tenant_id=user.tenant_id,
        target_type=body.target_type, target_id=body.target_id,
        deletion_type=body.deletion_type, reason=body.reason, legal_basis=body.legal_basis,
        requested_by=user.user_id, requested_at=now, status="pending_first_approval",
    )
    db.add(deletion_req)
    await db.flush()
    return DeletionRequestResponse(
        id=deletion_req.id, target_type=deletion_req.target_type, target_id=deletion_req.target_id,
        deletion_type=deletion_req.deletion_type, reason=deletion_req.reason,
        status=deletion_req.status, requested_by=deletion_req.requested_by, requested_at=deletion_req.requested_at,
    )


@router.post("/deletion-requests/{request_id}/approve", response_model=DeletionRequestResponse)
async def approve_deletion_request(
    request_id: UUID,
    body: DeletionApprovalRequest,
    user: AuthenticatedUser = Depends(require_permission(Permission.RETENTION_APPROVE_DELETION)),
    db: AsyncSession = Depends(get_db),
) -> DeletionRequestResponse:
    stmt = select(DeletionRequest).where(
        DeletionRequest.id == request_id, DeletionRequest.tenant_id == user.tenant_id,
    )
    result = await db.execute(stmt)
    del_req = result.scalar_one_or_none()
    if del_req is None:
        raise HTTPException(status_code=404, detail="Deletion request not found")

    now = datetime.now(timezone.utc)
    if body.decision == "reject":
        await db.execute(
            update(DeletionRequest).where(DeletionRequest.id == request_id).values(
                status="rejected", rejection_reason=body.reason, rejected_by=user.user_id,
            )
        )
        await db.flush()
        del_req.status = "rejected"
    elif del_req.status == "pending_first_approval":
        if del_req.requested_by == user.user_id:
            raise HTTPException(status_code=409, detail="Cannot approve your own deletion request")
        new_status = "pending_second_approval" if del_req.deletion_type == "hard" else "approved"
        await db.execute(
            update(DeletionRequest).where(DeletionRequest.id == request_id).values(
                status=new_status, first_approver_id=user.user_id, first_approved_at=now,
            )
        )
        await db.flush()
        del_req.status = new_status
    elif del_req.status == "pending_second_approval":
        if del_req.first_approver_id == user.user_id or del_req.requested_by == user.user_id:
            raise HTTPException(status_code=409, detail="Second approver must differ from requester and first approver")
        await db.execute(
            update(DeletionRequest).where(DeletionRequest.id == request_id).values(
                status="approved", second_approver_id=user.user_id, second_approved_at=now,
            )
        )
        await db.flush()
        del_req.status = "approved"
    else:
        raise HTTPException(status_code=409, detail=f"Cannot approve request in status '{del_req.status}'")

    return DeletionRequestResponse(
        id=del_req.id, target_type=del_req.target_type, target_id=del_req.target_id,
        deletion_type=del_req.deletion_type, reason=del_req.reason, status=del_req.status,
        requested_by=del_req.requested_by, requested_at=del_req.requested_at,
    )


# ── Manual Review ────────────────────────────────────────────────────────


@router.get(
    "/verifications/pending-review",
    summary="List verification results requiring manual review",
)
async def list_pending_reviews(
    user: AuthenticatedUser = Depends(require_permission(Permission.VERIFICATION_MANUAL_REVIEW)),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    stmt = (
        select(SignatureVerificationResult)
        .where(
            SignatureVerificationResult.tenant_id == user.tenant_id,
            SignatureVerificationResult.requires_manual_review.is_(True),
            SignatureVerificationResult.manual_review_completed_at.is_(None),
        )
        .order_by(SignatureVerificationResult.created_at.asc())
    )
    result = await db.execute(stmt)
    vers = result.scalars().all()
    return [
        {
            "id": str(v.id),
            "prescription_id": str(v.prescription_id),
            "verification_status": v.verification_status,
            "qtsp_provider": v.qtsp_provider,
            "verified_at": v.verified_at.isoformat() if v.verified_at else None,
            "error_code": v.error_code,
            "error_message": v.error_message,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in vers
    ]


@router.post("/verifications/{verification_id}/review", summary="Submit manual review decision")
async def submit_manual_review(
    verification_id: UUID,
    body: ManualReviewDecision,
    user: AuthenticatedUser = Depends(require_permission(Permission.VERIFICATION_MANUAL_REVIEW)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(SignatureVerificationResult).where(
        SignatureVerificationResult.id == verification_id,
        SignatureVerificationResult.tenant_id == user.tenant_id,
    )
    result = await db.execute(stmt)
    verification = result.scalar_one_or_none()
    if verification is None:
        raise HTTPException(status_code=404, detail="Verification result not found")
    if not verification.requires_manual_review:
        raise HTTPException(status_code=409, detail="This verification does not require manual review")
    if verification.manual_review_completed_at is not None:
        raise HTTPException(status_code=409, detail="Manual review has already been completed")

    now = datetime.now(timezone.utc)
    await db.execute(
        update(SignatureVerificationResult).where(SignatureVerificationResult.id == verification_id).values(
            manual_review_completed_at=now, manual_review_by=user.user_id,
            manual_review_decision=body.decision, manual_review_notes=body.notes,
        )
    )
    if body.decision == "accept":
        await db.execute(
            update(Prescription).where(Prescription.id == verification.prescription_id).values(
                status="verified", verification_status="verified",
            )
        )
    await db.flush()
    return {
        "verification_id": str(verification_id),
        "decision": body.decision,
        "reviewed_by": str(user.user_id),
        "reviewed_at": now.isoformat(),
    }


# ── Incidents ────────────────────────────────────────────────────────────


@router.get("/incidents", summary="List security/compliance incidents")
async def list_incidents(
    user: AuthenticatedUser = Depends(require_permission(Permission.INCIDENT_VIEW)),
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
    severity: str | None = None,
    limit: int = Query(default=50, le=200),
) -> list[dict]:
    stmt = select(Incident).where(Incident.tenant_id == user.tenant_id)
    if status:
        stmt = stmt.where(Incident.status == status)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    stmt = stmt.order_by(Incident.reported_at.desc()).limit(limit)
    result = await db.execute(stmt)
    incidents = result.scalars().all()
    return [_incident_to_dict(i) for i in incidents]


@router.post("/incidents", status_code=201, summary="Create a security/compliance incident")
async def create_incident(
    body: dict,
    user: AuthenticatedUser = Depends(require_permission(Permission.INCIDENT_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    required = {"title", "description", "severity", "incident_type"}
    missing = required - set(body.keys())
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing fields: {missing}")

    allowed_severities = {"low", "medium", "high", "critical"}
    if body["severity"] not in allowed_severities:
        raise HTTPException(status_code=400, detail=f"Invalid severity. Allowed: {allowed_severities}")

    now = datetime.now(timezone.utc)
    incident = Incident(
        id=uuid_lib.uuid4(),
        tenant_id=user.tenant_id,
        title=body["title"],
        description=body["description"],
        severity=body["severity"],
        incident_type=body["incident_type"],
        status="open",
        reported_by=user.user_id,
        reported_at=now,
        related_object_type=body.get("related_object_type"),
        related_object_id=body.get("related_object_id"),
    )
    db.add(incident)
    await db.flush()
    return _incident_to_dict(incident)


@router.get("/incidents/{incident_id}", summary="Get incident detail")
async def get_incident(
    incident_id: UUID,
    user: AuthenticatedUser = Depends(require_permission(Permission.INCIDENT_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(Incident).where(Incident.id == incident_id, Incident.tenant_id == user.tenant_id)
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _incident_to_dict(incident)


@router.patch("/incidents/{incident_id}", summary="Update incident status or details")
async def update_incident(
    incident_id: UUID,
    body: dict,
    user: AuthenticatedUser = Depends(require_permission(Permission.INCIDENT_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(Incident).where(Incident.id == incident_id, Incident.tenant_id == user.tenant_id)
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    allowed_fields = {
        "status", "severity", "assigned_to", "resolution",
        "root_cause", "corrective_actions", "resolved_at",
    }
    updates: dict = {}
    for field in allowed_fields:
        if field in body:
            updates[field] = body[field]

    if "status" in updates and updates["status"] == "resolved":
        updates["resolved_by"] = user.user_id
        updates["resolved_at"] = datetime.now(timezone.utc)

    if updates:
        await db.execute(update(Incident).where(Incident.id == incident_id).values(**updates))
        await db.flush()
        # Refresh
        result2 = await db.execute(stmt)
        incident = result2.scalar_one_or_none()

    return _incident_to_dict(incident)


def _incident_to_dict(i: Incident) -> dict:
    return {
        "id": str(i.id),
        "title": i.title,
        "description": i.description,
        "severity": i.severity,
        "status": i.status,
        "incident_type": i.incident_type,
        "reported_by": str(i.reported_by),
        "reported_at": i.reported_at.isoformat() if i.reported_at else None,
        "assigned_to": str(i.assigned_to) if i.assigned_to else None,
        "related_object_type": i.related_object_type,
        "related_object_id": str(i.related_object_id) if i.related_object_id else None,
        "resolution": i.resolution,
        "root_cause": i.root_cause,
        "corrective_actions": i.corrective_actions,
        "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
        "resolved_by": str(i.resolved_by) if i.resolved_by else None,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


# ── Users ────────────────────────────────────────────────────────────────


@router.get("/users", summary="List all users in tenant (doctors, pharmacy, admin)")
async def list_users(
    user: AuthenticatedUser = Depends(require_permission(Permission.USER_VIEW_TENANT)),
    db: AsyncSession = Depends(get_db),
    user_type: str | None = Query(default=None, description="Filter by: doctor, pharmacy_user, admin_user"),
    is_active: bool | None = None,
    limit: int = Query(default=50, le=200),
) -> list[dict]:
    results = []

    if user_type is None or user_type == "doctor":
        stmt = select(Doctor).where(Doctor.tenant_id == user.tenant_id, Doctor.is_deleted.is_(False))
        if is_active is not None:
            stmt = stmt.where(Doctor.is_active == is_active)
        stmt = stmt.order_by(Doctor.created_at.desc()).limit(limit)
        r = await db.execute(stmt)
        for d in r.scalars().all():
            results.append({
                "id": str(d.id),
                "user_type": "doctor",
                "email": d.email,
                "full_name": _safe_decrypt(d.full_name),
                "license_number": d.license_number,
                "is_active": d.is_active,
                "mfa_enabled": d.mfa_enabled,
                "last_login_at": d.last_login_at.isoformat() if d.last_login_at else None,
                "locked_until": d.locked_until.isoformat() if d.locked_until else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            })

    if user_type is None or user_type == "pharmacy_user":
        stmt = select(PharmacyUser).where(PharmacyUser.tenant_id == user.tenant_id, PharmacyUser.is_deleted.is_(False))
        if is_active is not None:
            stmt = stmt.where(PharmacyUser.is_active == is_active)
        stmt = stmt.order_by(PharmacyUser.created_at.desc()).limit(limit)
        r = await db.execute(stmt)
        for p in r.scalars().all():
            results.append({
                "id": str(p.id),
                "user_type": "pharmacy_user",
                "email": p.email,
                "full_name": _safe_decrypt(p.full_name),
                "pharmacy_name": _safe_decrypt(p.pharmacy_name),
                "pharmacy_license_number": p.pharmacy_license_number,
                "is_active": p.is_active,
                "mfa_enabled": p.mfa_enabled,
                "last_login_at": p.last_login_at.isoformat() if p.last_login_at else None,
                "locked_until": p.locked_until.isoformat() if p.locked_until else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })

    if user_type is None or user_type == "admin_user":
        stmt = select(AdminUser).where(AdminUser.tenant_id == user.tenant_id, AdminUser.is_deleted.is_(False))
        if is_active is not None:
            stmt = stmt.where(AdminUser.is_active == is_active)
        stmt = stmt.order_by(AdminUser.created_at.desc()).limit(limit)
        r = await db.execute(stmt)
        for a in r.scalars().all():
            results.append({
                "id": str(a.id),
                "user_type": "admin_user",
                "email": a.email,
                "full_name": _safe_decrypt(a.full_name),
                "role": a.role,
                "is_active": a.is_active,
                "mfa_enabled": a.mfa_enabled,
                "last_login_at": a.last_login_at.isoformat() if a.last_login_at else None,
                "locked_until": a.locked_until.isoformat() if a.locked_until else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

    return results


@router.patch(
    "/users/{user_type}/{user_id}",
    summary="Update user — suspend, activate, or update details",
)
async def update_user(
    user_type: str,
    user_id: UUID,
    body: dict,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.USER_SUSPEND)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Suspend or activate a user. Cannot modify own account."""
    if user_id == current_user.user_id:
        raise HTTPException(status_code=409, detail="Cannot modify your own account")

    allowed_types = {"doctor", "pharmacy_user", "admin_user"}
    if user_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid user_type. Allowed: {allowed_types}")

    model_map = {"doctor": Doctor, "pharmacy_user": PharmacyUser, "admin_user": AdminUser}
    Model = model_map[user_type]

    stmt = select(Model).where(Model.id == user_id, Model.tenant_id == current_user.tenant_id)
    result = await db.execute(stmt)
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    updates: dict = {}
    if "is_active" in body:
        updates["is_active"] = bool(body["is_active"])
    if "locked_until" in body:
        updates["locked_until"] = body["locked_until"]

    if updates:
        await db.execute(update(Model).where(Model.id == user_id).values(**updates))
        await db.flush()

    return {"user_id": str(user_id), "user_type": user_type, "updated": updates}


# ── Evidence ─────────────────────────────────────────────────────────────


@router.get("/evidence", summary="List evidence files across tenant")
async def list_evidence(
    user: AuthenticatedUser = Depends(require_permission(Permission.EVIDENCE_VIEW)),
    db: AsyncSession = Depends(get_db),
    prescription_id: UUID | None = None,
    evidence_type: str | None = None,
    limit: int = Query(default=50, le=200),
) -> list[dict]:
    stmt = select(EvidenceFile).where(EvidenceFile.tenant_id == user.tenant_id)
    if prescription_id:
        stmt = stmt.where(EvidenceFile.prescription_id == prescription_id)
    if evidence_type:
        stmt = stmt.where(EvidenceFile.evidence_type == evidence_type)
    stmt = stmt.order_by(EvidenceFile.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    files = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "prescription_id": str(e.prescription_id),
            "verification_result_id": str(e.verification_result_id),
            "evidence_type": e.evidence_type,
            "mime_type": e.mime_type,
            "file_size_bytes": e.file_size_bytes,
            "checksum_sha256": e.checksum_sha256,
            "trust_list_status": e.trust_list_status,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in files
    ]


@router.get("/evidence/{evidence_id}/download", summary="Get signed URL to download an evidence file")
async def download_evidence(
    evidence_id: UUID,
    user: AuthenticatedUser = Depends(require_permission(Permission.EVIDENCE_EXPORT)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    settings = get_settings()
    stmt = select(EvidenceFile).where(
        EvidenceFile.id == evidence_id, EvidenceFile.tenant_id == user.tenant_id,
    )
    result = await db.execute(stmt)
    ev = result.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="Evidence file not found")

    from app.services.storage import get_storage_backend
    storage = get_storage_backend()
    try:
        signed_url = await storage.generate_signed_url(ev.storage_bucket, ev.storage_key, expires_seconds=300)
    except Exception as e:
        logger.error("evidence_signed_url_failed", evidence_id=str(evidence_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate evidence download URL")

    return {
        "evidence_id": str(evidence_id),
        "signed_url": signed_url,
        "expires_in_seconds": 300,
        "evidence_type": ev.evidence_type,
        "mime_type": ev.mime_type,
        "file_size_bytes": ev.file_size_bytes,
    }


@router.get("/evidence/{evidence_id}/view", summary="Stream evidence file bytes for inline viewing")
async def view_evidence(
    evidence_id: UUID,
    user: AuthenticatedUser = Depends(require_permission(Permission.EVIDENCE_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    stmt = select(EvidenceFile).where(
        EvidenceFile.id == evidence_id, EvidenceFile.tenant_id == user.tenant_id,
    )
    result = await db.execute(stmt)
    ev = result.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="Evidence file not found")

    from app.services.storage import get_storage_backend
    storage = get_storage_backend()
    try:
        file_bytes = await storage.get_object(ev.storage_bucket, ev.storage_key)
    except Exception as e:
        logger.error("evidence_view_failed", evidence_id=str(evidence_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve evidence file")

    return Response(
        content=file_bytes,
        media_type=ev.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f"inline; filename=\"evidence-{str(evidence_id)[:8]}.{_mime_ext(ev.mime_type)}\""},
    )


def _mime_ext(mime_type: str | None) -> str:
    exts = {
        "application/pdf": "pdf",
        "application/json": "json",
        "application/xml": "xml",
        "text/xml": "xml",
        "text/plain": "txt",
        "application/octet-stream": "bin",
    }
    return exts.get(mime_type or "", "bin")


# ── System Health ─────────────────────────────────────────────────────────


@router.get("/health/stats", summary="System health stats and dashboard data")
async def get_health_stats(
    user: AuthenticatedUser = Depends(require_permission(Permission.SYSTEM_VIEW_HEALTH)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return system health stats scoped to the user's tenant."""
    # Prescription counts by status
    rx_count_stmt = (
        select(Prescription.status, func.count().label("count"))
        .where(Prescription.tenant_id == user.tenant_id, Prescription.is_deleted.is_(False))
        .group_by(Prescription.status)
    )
    rx_result = await db.execute(rx_count_stmt)
    rx_by_status = {row.status: row.count for row in rx_result}

    # Verification counts by status
    ver_count_stmt = (
        select(SignatureVerificationResult.verification_status, func.count().label("count"))
        .where(SignatureVerificationResult.tenant_id == user.tenant_id)
        .group_by(SignatureVerificationResult.verification_status)
    )
    ver_result = await db.execute(ver_count_stmt)
    ver_by_status = {row.verification_status: row.count for row in ver_result}

    # Pending manual reviews
    pending_reviews_stmt = select(func.count()).select_from(
        select(SignatureVerificationResult).where(
            SignatureVerificationResult.tenant_id == user.tenant_id,
            SignatureVerificationResult.requires_manual_review.is_(True),
            SignatureVerificationResult.manual_review_completed_at.is_(None),
        ).subquery()
    )
    pending_reviews_result = await db.execute(pending_reviews_stmt)
    pending_reviews = pending_reviews_result.scalar() or 0

    # Open incidents
    open_incidents_stmt = select(func.count()).select_from(
        select(Incident).where(
            Incident.tenant_id == user.tenant_id,
            Incident.status.in_(["open", "investigating"]),
        ).subquery()
    )
    open_incidents_result = await db.execute(open_incidents_stmt)
    open_incidents = open_incidents_result.scalar() or 0

    # Active legal holds
    holds_stmt = select(func.count()).select_from(
        select(LegalHold).where(
            LegalHold.tenant_id == user.tenant_id, LegalHold.is_active.is_(True),
        ).subquery()
    )
    holds_result = await db.execute(holds_stmt)
    active_holds = holds_result.scalar() or 0

    # Pending deletion requests
    del_stmt = select(func.count()).select_from(
        select(DeletionRequest).where(
            DeletionRequest.tenant_id == user.tenant_id,
            DeletionRequest.status.in_(["pending_first_approval", "pending_second_approval"]),
        ).subquery()
    )
    del_result = await db.execute(del_stmt)
    pending_deletions = del_result.scalar() or 0

    # Recent audit events (last 24h)
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_audit_stmt = select(func.count()).select_from(
        select(AuditEvent).where(
            AuditEvent.tenant_id == user.tenant_id,
            AuditEvent.event_timestamp >= cutoff,
        ).subquery()
    )
    recent_audit_result = await db.execute(recent_audit_stmt)
    recent_audit_count = recent_audit_result.scalar() or 0

    return {
        "prescriptions": {
            "by_status": rx_by_status,
            "total": sum(rx_by_status.values()),
            "pending_verification": rx_by_status.get("pending_verification", 0),
            "verified": rx_by_status.get("verified", 0),
            "failed": rx_by_status.get("failed_verification", 0),
        },
        "verifications": {
            "by_status": ver_by_status,
            "pending_manual_review": pending_reviews,
        },
        "compliance": {
            "open_incidents": open_incidents,
            "active_legal_holds": active_holds,
            "pending_deletion_requests": pending_deletions,
        },
        "audit": {
            "events_last_24h": recent_audit_count,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Suspicious Events ─────────────────────────────────────────────────────


@router.get("/suspicious-events", summary="Suspicious and high-severity audit events queue")
async def get_suspicious_events(
    user: AuthenticatedUser = Depends(require_permission(Permission.AUDIT_VIEW_TENANT)),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=200),
) -> list[dict]:
    """Return recent high-severity or failure audit events for review."""
    stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == user.tenant_id,
            AuditEvent.severity.in_(["warning", "error", "critical"]),
        )
        .order_by(AuditEvent.event_timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "sequence_number": e.sequence_number,
            "event_type": e.event_type,
            "event_category": e.event_category,
            "severity": e.severity,
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "actor_type": e.actor_type,
            "actor_email": e.actor_email,
            "object_type": e.object_type,
            "object_id": str(e.object_id) if e.object_id else None,
            "action": e.action,
            "outcome": e.outcome,
            "event_timestamp": e.event_timestamp.isoformat() if e.event_timestamp else None,
            "source_ip": e.source_ip,
            "detail": e.detail,
            "is_sensitive": e.is_sensitive,
        }
        for e in events
    ]
