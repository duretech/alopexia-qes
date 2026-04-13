"""Prescription endpoints — upload, retrieve, status, cancel.

POST /api/v1/prescriptions/upload — Ingest a signed prescription PDF.
GET  /api/v1/prescriptions         — List own prescriptions (doctor).
GET  /api/v1/prescriptions/{id}    — Get prescription detail with verification.
POST /api/v1/prescriptions/{id}/cancel — Cancel / revoke prescription.
GET  /api/v1/prescriptions/{id}/verification — Verification result detail.

Authentication: X-Session-Token header or session_token cookie.
Authorization: PRESCRIPTION_UPLOAD / PRESCRIPTION_VIEW_OWN permissions.
Tenant scoping: tenant_id from authenticated session, never from request.
"""

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.evidence import EvidenceFile
from app.models.prescription import Prescription
from app.models.verification import SignatureVerificationResult
from app.schemas.pharmacy import PrescriptionListItem
from app.schemas.ingestion import (
    PrescriptionUploadMetadata,
    PrescriptionUploadResponse,
    IngestionErrorResponse,
)
from app.services.auth.models import AuthenticatedUser
from app.services.authz.dependencies import require_permission
from app.services.authz.rbac import Permission
from app.services.ingestion.service import (
    ingest_prescription,
    IngestionError,
    DuplicateDocumentError,
    IdempotencyConflictError,
    QuarantinedError,
)
from app.services.ingestion.validators import ValidationError
from app.services.audit import emit_audit_event
from app.services.audit.event_types import AuditEventType, AuditOutcome

logger = get_logger(component="prescriptions_endpoint")

router = APIRouter()


@router.get(
    "",
    response_model=list[PrescriptionListItem],
    summary="List prescriptions uploaded by the current doctor",
)
async def list_my_prescriptions(
    user: AuthenticatedUser = Depends(require_permission(Permission.PRESCRIPTION_VIEW_OWN)),
    db: AsyncSession = Depends(get_db),
) -> list[PrescriptionListItem]:
    stmt = (
        select(Prescription)
        .where(
            Prescription.tenant_id == user.tenant_id,
            Prescription.doctor_id == user.user_id,
            Prescription.is_deleted.is_(False),
        )
        .order_by(Prescription.created_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
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
        for rx in rows
    ]


@router.get(
    "/{prescription_id}",
    summary="Get prescription detail with verification result",
)
async def get_prescription_detail(
    prescription_id: UUID,
    user: AuthenticatedUser = Depends(require_permission(Permission.PRESCRIPTION_VIEW_OWN)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return full prescription detail including latest verification result and evidence."""
    stmt = select(Prescription).where(
        Prescription.tenant_id == user.tenant_id,
        Prescription.doctor_id == user.user_id,
        Prescription.id == prescription_id,
        Prescription.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    rx = result.scalar_one_or_none()
    if rx is None:
        raise HTTPException(status_code=404, detail="Prescription not found")

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

    # Evidence files
    ev_stmt = select(EvidenceFile).where(
        EvidenceFile.prescription_id == prescription_id,
        EvidenceFile.tenant_id == user.tenant_id,
    )
    ev_result = await db.execute(ev_stmt)
    evidence = ev_result.scalars().all()

    # Metadata
    meta = rx.metadata_record

    return {
        "id": str(rx.id),
        "status": rx.status,
        "verification_status": rx.verification_status,
        "dispensing_status": rx.dispensing_status,
        "doctor_id": str(rx.doctor_id),
        "patient_id": str(rx.patient_id),
        "clinic_id": str(rx.clinic_id),
        "upload_checksum": rx.upload_checksum,
        "prescribed_date": rx.prescribed_date.isoformat() if rx.prescribed_date else None,
        "created_at": rx.created_at.isoformat() if rx.created_at else None,
        "external_prescription_id": rx.external_prescription_id,
        "cancelled_at": rx.cancelled_at.isoformat() if rx.cancelled_at else None,
        "cancellation_reason": rx.cancellation_reason,
        "is_under_legal_hold": rx.is_under_legal_hold,
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
            "qtsp_request_id": ver.qtsp_request_id,
            "verified_at": ver.verified_at.isoformat() if ver.verified_at else None,
            "signature_intact": ver.signature_intact,
            "signature_algorithm": ver.signature_algorithm,
            "certificate": {
                "common_name": ver.signer_common_name,
                "serial_number": ver.signer_serial_number,
                "organization": ver.signer_organization,
                "issuer": ver.certificate_issuer,
                "valid_from": ver.certificate_valid_from.isoformat() if ver.certificate_valid_from else None,
                "valid_to": ver.certificate_valid_to.isoformat() if ver.certificate_valid_to else None,
                "is_qualified": ver.certificate_is_qualified,
            },
            "timestamp": {
                "status": ver.timestamp_status,
                "time": ver.timestamp_time.isoformat() if ver.timestamp_time else None,
                "authority": ver.timestamp_authority,
                "is_qualified": ver.timestamp_is_qualified,
            },
            "trust_list_status": ver.trust_list_status,
            "requires_manual_review": ver.requires_manual_review,
            "manual_review_decision": ver.manual_review_decision,
            "error_code": ver.error_code,
            "error_message": ver.error_message,
        } if ver else None,
        "evidence": [
            {
                "id": str(e.id),
                "evidence_type": e.evidence_type,
                "mime_type": e.mime_type,
                "file_size_bytes": e.file_size_bytes,
                "checksum_sha256": e.checksum_sha256,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in evidence
        ],
    }


@router.post(
    "/{prescription_id}/cancel",
    summary="Cancel or revoke a prescription",
)
async def cancel_prescription(
    prescription_id: UUID,
    body: dict,
    user: AuthenticatedUser = Depends(require_permission(Permission.PRESCRIPTION_REVOKE_OWN)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel or revoke a prescription uploaded by the current doctor.

    Only prescriptions in 'draft', 'pending_verification', or 'verified' status
    can be cancelled. Dispensed prescriptions cannot be cancelled.
    """
    stmt = select(Prescription).where(
        Prescription.tenant_id == user.tenant_id,
        Prescription.doctor_id == user.user_id,
        Prescription.id == prescription_id,
        Prescription.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    rx = result.scalar_one_or_none()

    if rx is None:
        raise HTTPException(status_code=404, detail="Prescription not found")

    if rx.status in ("dispensed", "cancelled", "revoked"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel prescription in status '{rx.status}'",
        )

    if rx.is_under_legal_hold:
        raise HTTPException(
            status_code=409,
            detail="Cannot cancel prescription under legal hold",
        )

    reason = body.get("reason", "")
    if not reason:
        raise HTTPException(status_code=400, detail="Cancellation reason is required")

    now = datetime.now(timezone.utc)
    new_status = "revoked" if rx.status == "verified" else "cancelled"

    await db.execute(
        update(Prescription)
        .where(Prescription.id == prescription_id)
        .values(
            status=new_status,
            cancelled_at=now,
            cancelled_by=user.user_id,
            cancellation_reason=reason,
        )
    )
    await db.flush()

    logger.info(
        "prescription_cancelled",
        prescription_id=str(prescription_id),
        new_status=new_status,
        actor_id=str(user.user_id),
    )

    try:
        await emit_audit_event(
            db,
            event_type=AuditEventType.PRESCRIPTION_REVOKED,
            action=new_status,
            actor_id=user.user_id,
            actor_type=str(user.user_type),
            actor_role=str(user.role),
            actor_email=user.email,
            tenant_id=user.tenant_id,
            object_type="prescription",
            object_id=prescription_id,
            outcome=AuditOutcome.SUCCESS,
            detail={"reason": reason, "previous_status": rx.status, "new_status": new_status},
        )
    except Exception as audit_err:
        logger.warning("audit_emission_failed", error=str(audit_err))

    return {
        "prescription_id": str(prescription_id),
        "status": new_status,
        "cancelled_at": now.isoformat(),
        "reason": reason,
    }


@router.get(
    "/{prescription_id}/verification",
    summary="Get all verification results for a prescription",
)
async def get_verification_results(
    prescription_id: UUID,
    user: AuthenticatedUser = Depends(require_permission(Permission.PRESCRIPTION_VIEW_OWN)),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return all QTSP verification attempts for a prescription."""
    # Verify ownership
    rx_stmt = select(Prescription).where(
        Prescription.tenant_id == user.tenant_id,
        Prescription.doctor_id == user.user_id,
        Prescription.id == prescription_id,
        Prescription.is_deleted.is_(False),
    )
    rx_result = await db.execute(rx_stmt)
    if rx_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Prescription not found")

    stmt = (
        select(SignatureVerificationResult)
        .where(
            SignatureVerificationResult.prescription_id == prescription_id,
            SignatureVerificationResult.tenant_id == user.tenant_id,
        )
        .order_by(SignatureVerificationResult.created_at.desc())
    )
    result = await db.execute(stmt)
    vers = result.scalars().all()

    return [
        {
            "id": str(v.id),
            "attempt_number": v.attempt_number,
            "status": v.verification_status,
            "qtsp_provider": v.qtsp_provider,
            "verified_at": v.verified_at.isoformat() if v.verified_at else None,
            "signature_intact": v.signature_intact,
            "certificate_common_name": v.signer_common_name,
            "certificate_is_qualified": v.certificate_is_qualified,
            "timestamp_status": v.timestamp_status,
            "timestamp_is_qualified": v.timestamp_is_qualified,
            "trust_list_status": v.trust_list_status,
            "requires_manual_review": v.requires_manual_review,
            "error_code": v.error_code,
            "error_message": v.error_message,
        }
        for v in vers
    ]


@router.get(
    "/audit/own",
    summary="Get current doctor's own audit trail",
)
async def get_own_audit_trail(
    user: AuthenticatedUser = Depends(require_permission(Permission.PRESCRIPTION_VIEW_OWN)),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
) -> list[dict]:
    """Return the audit trail of the current doctor's own actions."""
    stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == user.tenant_id,
            AuditEvent.actor_id == user.user_id,
        )
        .order_by(AuditEvent.event_timestamp.desc())
        .limit(min(limit, 200))
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
            "action": e.action,
            "outcome": e.outcome,
            "object_type": e.object_type,
            "object_id": str(e.object_id) if e.object_id else None,
            "event_timestamp": e.event_timestamp.isoformat() if e.event_timestamp else None,
            "detail": e.detail,
        }
        for e in events
    ]


@router.post(
    "/upload",
    response_model=PrescriptionUploadResponse,
    status_code=201,
    responses={
        400: {"model": IngestionErrorResponse, "description": "Validation error"},
        409: {"model": IngestionErrorResponse, "description": "Duplicate or idempotency conflict"},
        422: {"model": IngestionErrorResponse, "description": "Malware detected / quarantined"},
    },
    summary="Upload a signed prescription PDF",
    description="Ingest a signed prescription PDF into the system. "
                "The file is validated, scanned, stored, and a verification job is enqueued.",
)
async def upload_prescription(
    request: Request,
    file: UploadFile = File(..., description="The signed prescription PDF"),
    metadata: str = Form(..., description="JSON string with upload metadata"),
    user: AuthenticatedUser = Depends(require_permission(Permission.PRESCRIPTION_UPLOAD)),
    db: AsyncSession = Depends(get_db),
) -> PrescriptionUploadResponse:
    """Upload a signed prescription PDF for ingestion."""
    try:
        meta_dict = json.loads(metadata)
        meta = PrescriptionUploadMetadata(**meta_dict)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "INVALID_METADATA", "message": f"Invalid metadata JSON: {e}"},
        )

    file_data = await file.read()

    try:
        result = await ingest_prescription(
            db,
            file_data=file_data,
            original_filename=file.filename or "unknown.pdf",
            declared_content_type=file.content_type,
            doctor_id=user.user_id,
            patient_id=meta.patient_id,
            tenant_id=user.tenant_id,
            clinic_id=user.clinic_id,
            idempotency_key=meta.idempotency_key,
            prescribed_date=meta.prescribed_date,
            external_prescription_id=meta.external_prescription_id,
            medication_name=meta.medication_name,
            dosage=meta.dosage,
            treatment_duration=meta.treatment_duration,
            instructions=meta.instructions,
            is_compounded=meta.is_compounded,
            formulation_details=meta.formulation_details,
            formulation_registration_number=meta.formulation_registration_number,
            additional_metadata=meta.additional_metadata,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail={"error_code": e.code, "message": e.message})
    except DuplicateDocumentError as e:
        raise HTTPException(status_code=409, detail={"error_code": e.code, "message": e.message, "detail": e.detail})
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=409, detail={"error_code": e.code, "message": e.message, "detail": e.detail})
    except QuarantinedError as e:
        logger.warning("upload_quarantined", actor_id=str(user.user_id), tenant_id=str(user.tenant_id), detail=e.detail)
        raise HTTPException(status_code=422, detail={"error_code": e.code, "message": e.message})
    except IngestionError as e:
        logger.error("upload_failed", error_code=e.code, message=e.message, actor_id=str(user.user_id))
        raise HTTPException(status_code=500, detail={"error_code": "INGESTION_ERROR", "message": "An internal error occurred during ingestion."})

    # Emit audit event for the upload
    try:
        await emit_audit_event(
            db,
            event_type=AuditEventType.PRESCRIPTION_UPLOADED,
            action="upload",
            actor_id=user.user_id,
            actor_type=str(user.user_type),
            actor_role=str(user.role),
            actor_email=user.email,
            tenant_id=user.tenant_id,
            object_type="prescription",
            object_id=result.prescription_id,
            outcome=AuditOutcome.SUCCESS,
            detail={
                "document_id": str(result.document_id),
                "checksum_sha256": result.checksum_sha256,
                "file_size_bytes": result.file_size_bytes,
                "scan_status": result.scan_status,
                "verification_status": result.verification_status,
            },
            request_id=request.state.request_id if hasattr(request.state, "request_id") else None,
            correlation_id=request.state.correlation_id if hasattr(request.state, "correlation_id") else None,
            source_ip=request.client.host if request.client else None,
        )
    except Exception as audit_err:
        logger.warning("audit_emission_failed", error=str(audit_err), prescription_id=str(result.prescription_id))

    return PrescriptionUploadResponse(
        prescription_id=result.prescription_id,
        document_id=result.document_id,
        storage_key=result.storage_key,
        checksum_sha256=result.checksum_sha256,
        file_size_bytes=result.file_size_bytes,
        pdf_version=result.pdf_version,
        estimated_page_count=result.estimated_page_count,
        scan_status=result.scan_status,
        status=result.prescription_status,
        verification_status=result.verification_status,
        verification_id=result.verification_id,
    )
