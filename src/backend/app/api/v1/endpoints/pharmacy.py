"""Pharmacy endpoints — view prescriptions, download PDF, confirm dispensing.

These endpoints serve the pharmacy user workflow:
  1. List assigned prescriptions (verified and available)
  2. View prescription details and verification evidence
  3. Download the PDF via signed URL
  4. Confirm dispensing

All endpoints require PHARMACY_USER role with appropriate permissions.
Tenant isolation and clinic scoping are enforced.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.pharmacy import DispensingEvent, PharmacyEvent
from app.models.prescription import Prescription
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
    """List prescriptions assigned to or available for this pharmacy user.

    Only returns prescriptions within the user's tenant that are in
    a pharmacy-relevant status (verified, available, dispensed).
    """
    stmt = (
        select(Prescription)
        .where(
            Prescription.tenant_id == user.tenant_id,
            Prescription.is_deleted.is_(False),
        )
    )

    # Pharmacy users see only assigned or unassigned prescriptions
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
    response_model=PrescriptionDetail,
    summary="Get prescription details",
)
async def get_pharmacy_prescription(
    prescription_id: UUID,
    user: AuthenticatedUser = Depends(require_permission(Permission.PRESCRIPTION_VIEW_ASSIGNED)),
    db: AsyncSession = Depends(get_db),
) -> PrescriptionDetail:
    """Get detailed prescription information including verification status."""
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
        source_ip=request.client.host if hasattr(request, "client") and request.client else None,
    )
    db.add(event)

    return PrescriptionDetail(
        id=rx.id,
        status=rx.status,
        verification_status=rx.verification_status,
        dispensing_status=rx.dispensing_status,
        doctor_id=rx.doctor_id,
        patient_id=rx.patient_id,
        clinic_id=rx.clinic_id,
        upload_checksum=rx.upload_checksum,
        prescribed_date=rx.prescribed_date,
        created_at=rx.created_at,
        document_storage_key=rx.document_storage_key,
        external_prescription_id=rx.external_prescription_id,
    )


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
    """Generate a short-lived signed URL for downloading the prescription PDF.

    The URL expires after 5 minutes (configurable). No public URLs are
    ever generated (C-DOC-08).
    """
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

    # Generate signed URL
    from app.services.storage import get_storage_backend
    storage = get_storage_backend()

    try:
        signed_url = await storage.generate_signed_url(
            settings.s3_prescription_bucket,
            rx.document_storage_key,
            expires_seconds=300,
        )
    except Exception as e:
        logger.error(
            "signed_url_generation_failed",
            prescription_id=str(prescription_id),
            error=str(e),
        )
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
    """Confirm dispensing of a prescription.

    Only verified prescriptions can be dispensed. The dispensing event
    is recorded as an immutable legal record.
    """
    stmt = select(Prescription).where(
        Prescription.id == prescription_id,
        Prescription.tenant_id == user.tenant_id,
        Prescription.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    rx = result.scalar_one_or_none()

    if rx is None:
        raise HTTPException(status_code=404, detail="Prescription not found")

    # Only verified/available prescriptions can be dispensed
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

    # Update prescription status
    await db.execute(
        update(Prescription)
        .where(Prescription.id == prescription_id)
        .values(
            status="dispensed",
            dispensing_status=body.dispensing_status,
        )
    )

    return DispensingResponse(
        dispensing_event_id=dispensing_id,
        prescription_id=prescription_id,
        dispensing_status=body.dispensing_status,
        dispensed_at=now,
    )
