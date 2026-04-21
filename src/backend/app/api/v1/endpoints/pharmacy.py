"""Pharmacy endpoints — view prescriptions, download PDF, confirm dispensing, record events.

GET  /api/v1/pharmacy/prescriptions              — List verified prescriptions.
GET  /api/v1/pharmacy/prescriptions/{id}         — Prescription detail + verification status.
GET  /api/v1/pharmacy/prescriptions/{id}/download — Signed URL for PDF download.
POST /api/v1/pharmacy/prescriptions/{id}/dispense — Confirm dispensing.
GET  /api/v1/pharmacy/prescriptions/{id}/events  — List pharmacy events for prescription.
POST /api/v1/pharmacy/prescriptions/{id}/events  — Record a pharmacy event.
GET  /api/v1/pharmacy/prescriptions/{id}/evidence — List evidence files.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.evidence import EvidenceFile
from app.models.pharmacy import DispensingEvent, PharmacyEvent
from app.models.prescription import Prescription
from app.models.verification import SignatureVerificationResult
from app.schemas.pharmacy import (
    ConfirmDispensingRequest,
    DispensingResponse,
    DocumentDownloadResponse,
    PrescriptionDetail,
    PrescriptionListItem,
)
from app.services.auth.models import AuthenticatedUser
from app.services.authz.dependencies import require_permission
from app.services.authz.rbac import Permission
from app.services.audit import emit_audit_event
from app.services.audit.event_types import AuditEventType, AuditOutcome

logger = get_logger(component="pharmacy_endpoint")

router = APIRouter()


@router.get(
    "/prescriptions",
    response_model=list[PrescriptionListItem],
    summary="List prescriptions available to the pharmacy user",
)
async def list_pharmacy_prescriptions(
    request: Request,
    user: AuthenticatedUser = Depends(require_permission(Permission.PRESCRIPTION_VIEW_ASSIGNED)),
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
) -> list[PrescriptionListItem]:
    stmt = (
        select(Prescription)
        .where(
            Prescription.tenant_id == user.tenant_id,
            Prescription.is_deleted.is_(False),
        )
    )
    stmt = stmt.where(
        Prescription.status.in_(["verified", "available", "dispensed", "partially_dispensed"]),
    )
    if status:
        stmt = stmt.where(Prescription.status == status)

    stmt = stmt.order_by(Prescription.created_at.desc()).limit(100)
    result = await db.execute(stmt)
    prescriptions = result.scalars().all()

    return [
        PrescriptionListItem(
            id=rx.id,
            status=rx.status,
            verification_status=rx.verification_status,
            dispensing_status=rx.dispensing_status,
            doctor_id=rx.doctor_id,
            patient_id=rx.patient_id,
            upload_checksum=rx.upload_checksum,
            prescribed_date=rx.prescribed_date,
            created_at=rx.created_at,
        )
        for rx in prescriptions
    ]


@router.get(
    "/prescriptions/{prescription_id}",
    summary="Get prescription details with verification and evidence status",
)
async def get_pharmacy_prescription(
    prescription_id: UUID,
    request: Request,
    user: AuthenticatedUser = Depends(require_permission(Permission.PRESCRIPTION_VIEW_ASSIGNED)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get detailed prescription information including verification status and evidence."""
    stmt = select(Prescription).where(
        Prescription.id == prescription_id,
        Prescription.tenant_id == user.tenant_id,
        Prescription.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    rx = result.scalar_one_or_none()

    if rx is None:
        raise HTTPException(status_code=404, detail="Prescription not found")

    # Record pharmacy view event
    event = PharmacyEvent(
        tenant_id=user.tenant_id,
        prescription_id=prescription_id,
        pharmacy_user_id=user.user_id,
        event_type="viewed",
        event_timestamp=datetime.now(timezone.utc),
        source_ip=request.client.host if request.client else None,
    )
    db.add(event)

    # Latest verification result
    ver_stmt = (
        select(SignatureVerificationResult)
        .where(
            SignatureVerificationResult.prescription_id == prescription_id,
            SignatureVerificationResult.tenant_id == user.tenant_id,
        )
        .order_by(SignatureVerificationResult.created_at.desc())
        .limit(1)
    )
    ver_result = await db.execute(ver_stmt)
    ver = ver_result.scalar_one_or_none()

    # Evidence files count
    ev_stmt = select(EvidenceFile).where(
        EvidenceFile.prescription_id == prescription_id,
        EvidenceFile.tenant_id == user.tenant_id,
    )
    ev_result = await db.execute(ev_stmt)
    evidence = ev_result.scalars().all()

    meta = rx.metadata_record

    await db.flush()

    return {
        "id": str(rx.id),
        "status": rx.status,
        "verification_status": rx.verification_status,
        "dispensing_status": rx.dispensing_status,
        "doctor_id": str(rx.doctor_id),
        "patient_id": str(rx.patient_id) if rx.patient_id else None,
        "clinic_id": str(rx.clinic_id),
        "prescribed_date": rx.prescribed_date.isoformat() if rx.prescribed_date else None,
        "created_at": rx.created_at.isoformat() if rx.created_at else None,
        "external_prescription_id": rx.external_prescription_id,
        "metadata": {
            "medication_name": meta.medication_name if meta else None,
            "dosage": meta.dosage if meta else None,
            "treatment_duration": meta.treatment_duration if meta else None,
            "instructions": meta.instructions if meta else None,
            "is_compounded": meta.is_compounded if meta else False,
            "formulation_registration_number": meta.formulation_registration_number if meta else None,
        } if meta else None,
        "verification": {
            "id": str(ver.id),
            "status": ver.verification_status,
            "qtsp_provider": ver.qtsp_provider,
            "verified_at": ver.verified_at.isoformat() if ver.verified_at else None,
            "signature_intact": ver.signature_intact,
            "certificate": {
                "common_name": ver.signer_common_name,
                "organization": ver.signer_organization,
                "issuer": ver.certificate_issuer,
                "valid_from": ver.certificate_valid_from.isoformat() if ver.certificate_valid_from else None,
                "valid_to": ver.certificate_valid_to.isoformat() if ver.certificate_valid_to else None,
                "is_qualified": ver.certificate_is_qualified,
            },
            "timestamp_status": ver.timestamp_status,
            "timestamp_is_qualified": ver.timestamp_is_qualified,
            "trust_list_status": ver.trust_list_status,
            "requires_manual_review": ver.requires_manual_review,
            "error_code": ver.error_code,
        } if ver else None,
        "evidence_count": len(evidence),
        "evidence": [
            {
                "id": str(e.id),
                "evidence_type": e.evidence_type,
                "mime_type": e.mime_type,
                "file_size_bytes": e.file_size_bytes,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in evidence
        ],
    }


@router.get(
    "/prescriptions/{prescription_id}/download",
    response_model=DocumentDownloadResponse,
    summary="Get signed URL for prescription PDF download",
)
async def download_prescription_pdf(
    prescription_id: UUID,
    request: Request,
    user: AuthenticatedUser = Depends(require_permission(Permission.DOCUMENT_DOWNLOAD)),
    db: AsyncSession = Depends(get_db),
) -> DocumentDownloadResponse:
    settings = get_settings()

    stmt = select(Prescription).where(
        Prescription.id == prescription_id,
        Prescription.tenant_id == user.tenant_id,
        Prescription.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    rx = result.scalar_one_or_none()

    if rx is None:
        raise HTTPException(status_code=404, detail="Prescription not found")

    from app.services.storage import get_storage_backend
    storage = get_storage_backend()

    try:
        signed_url = await storage.generate_signed_url(
            settings.s3_prescription_bucket,
            rx.document_storage_key,
            expires_seconds=300,
        )
    except Exception as e:
        logger.error("signed_url_generation_failed", prescription_id=str(prescription_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate download URL")

    # Record download event
    event = PharmacyEvent(
        tenant_id=user.tenant_id,
        prescription_id=prescription_id,
        pharmacy_user_id=user.user_id,
        event_type="downloaded",
        event_timestamp=datetime.now(timezone.utc),
        source_ip=request.client.host if request.client else None,
    )
    db.add(event)
    await db.flush()

    try:
        await emit_audit_event(
            db,
            event_type=AuditEventType.DOCUMENT_DOWNLOAD_SIGNED_URL,
            action="download",
            actor_id=user.user_id,
            actor_type=str(user.user_type),
            actor_role=str(user.role),
            actor_email=user.email,
            tenant_id=user.tenant_id,
            object_type="prescription",
            object_id=prescription_id,
            outcome=AuditOutcome.SUCCESS,
            source_ip=request.client.host if request.client else None,
        )
    except Exception as audit_err:
        logger.warning("audit_emission_failed", error=str(audit_err))

    return DocumentDownloadResponse(signed_url=signed_url, expires_in_seconds=300)


@router.post(
    "/prescriptions/{prescription_id}/dispense",
    response_model=DispensingResponse,
    status_code=201,
    summary="Confirm dispensing of a prescription",
)
async def confirm_dispensing(
    prescription_id: UUID,
    body: ConfirmDispensingRequest,
    request: Request,
    user: AuthenticatedUser = Depends(require_permission(Permission.PHARMACY_CONFIRM_DISPENSING)),
    db: AsyncSession = Depends(get_db),
) -> DispensingResponse:
    """Confirm dispensing. Records formulation registration number for compounded medicines."""
    stmt = select(Prescription).where(
        Prescription.id == prescription_id,
        Prescription.tenant_id == user.tenant_id,
        Prescription.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    rx = result.scalar_one_or_none()

    if rx is None:
        raise HTTPException(status_code=404, detail="Prescription not found")

    if rx.status not in ("verified", "available"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot dispense prescription in status '{rx.status}'",
        )

    now = datetime.now(timezone.utc)
    import uuid
    dispensing_id = uuid.uuid4()

    dispensing_event = DispensingEvent(
        id=dispensing_id,
        tenant_id=user.tenant_id,
        prescription_id=prescription_id,
        pharmacy_user_id=user.user_id,
        dispensing_status=body.dispensing_status,
        dispensed_at=now,
        formulation_registration_number=body.formulation_registration_number,
        batch_number=body.batch_number,
        quantity_dispensed=body.quantity_dispensed,
        notes=body.notes,
        source_ip=request.client.host if request.client else None,
    )
    db.add(dispensing_event)

    # Record pharmacy event for formulation registration
    if body.formulation_registration_number:
        reg_event = PharmacyEvent(
            tenant_id=user.tenant_id,
            prescription_id=prescription_id,
            pharmacy_user_id=user.user_id,
            event_type="formulation_registered",
            event_detail=f"Reg#: {body.formulation_registration_number}",
            event_timestamp=now,
            source_ip=request.client.host if request.client else None,
        )
        db.add(reg_event)

    await db.execute(
        update(Prescription)
        .where(Prescription.id == prescription_id)
        .values(
            status="dispensed",
            dispensing_status=body.dispensing_status,
        )
    )

    try:
        await emit_audit_event(
            db,
            event_type=AuditEventType.PHARMACY_PRESCRIPTION_ACCEPTED,
            action="dispense",
            actor_id=user.user_id,
            actor_type=str(user.user_type),
            actor_role=str(user.role),
            actor_email=user.email,
            tenant_id=user.tenant_id,
            object_type="prescription",
            object_id=prescription_id,
            outcome=AuditOutcome.SUCCESS,
            detail={
                "dispensing_status": body.dispensing_status,
                "formulation_registration_number": body.formulation_registration_number,
                "batch_number": body.batch_number,
                "quantity_dispensed": body.quantity_dispensed,
            },
            source_ip=request.client.host if request.client else None,
        )
    except Exception as audit_err:
        logger.warning("audit_emission_failed", error=str(audit_err))

    return DispensingResponse(
        dispensing_event_id=dispensing_id,
        prescription_id=prescription_id,
        dispensing_status=body.dispensing_status,
        dispensed_at=now,
    )


@router.get(
    "/prescriptions/{prescription_id}/events",
    summary="List pharmacy events for a prescription",
)
async def list_prescription_events(
    prescription_id: UUID,
    user: AuthenticatedUser = Depends(require_permission(Permission.PHARMACY_VIEW_PRESCRIPTIONS)),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all pharmacy events recorded against a prescription."""
    # Verify access
    rx_stmt = select(Prescription).where(
        Prescription.id == prescription_id,
        Prescription.tenant_id == user.tenant_id,
        Prescription.is_deleted.is_(False),
    )
    rx_result = await db.execute(rx_stmt)
    if rx_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Prescription not found")

    stmt = (
        select(PharmacyEvent)
        .where(
            PharmacyEvent.prescription_id == prescription_id,
            PharmacyEvent.tenant_id == user.tenant_id,
        )
        .order_by(PharmacyEvent.event_timestamp.desc())
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "event_detail": e.event_detail,
            "pharmacy_user_id": str(e.pharmacy_user_id),
            "event_timestamp": e.event_timestamp.isoformat() if e.event_timestamp else None,
        }
        for e in events
    ]


@router.post(
    "/prescriptions/{prescription_id}/events",
    status_code=201,
    summary="Record a pharmacy event against a prescription",
)
async def record_pharmacy_event(
    prescription_id: UUID,
    body: dict,
    request: Request,
    user: AuthenticatedUser = Depends(require_permission(Permission.PHARMACY_RECORD_EVENT)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Record an arbitrary pharmacy event (notes, status update, flag, etc.)."""
    allowed_types = {"viewed", "downloaded", "notes_added", "status_updated",
                     "formulation_registered", "returned", "flagged", "other"}
    event_type = body.get("event_type", "other")
    if event_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid event_type. Allowed: {sorted(allowed_types)}")

    # Verify access
    rx_stmt = select(Prescription).where(
        Prescription.id == prescription_id,
        Prescription.tenant_id == user.tenant_id,
        Prescription.is_deleted.is_(False),
    )
    rx_result = await db.execute(rx_stmt)
    if rx_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Prescription not found")

    import uuid
    now = datetime.now(timezone.utc)
    event = PharmacyEvent(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        prescription_id=prescription_id,
        pharmacy_user_id=user.user_id,
        event_type=event_type,
        event_detail=body.get("detail"),
        event_timestamp=now,
        source_ip=request.client.host if request.client else None,
    )
    db.add(event)
    await db.flush()

    return {
        "id": str(event.id),
        "event_type": event_type,
        "event_timestamp": now.isoformat(),
    }
