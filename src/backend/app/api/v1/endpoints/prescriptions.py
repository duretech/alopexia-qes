"""Prescription endpoints — upload, retrieve, status.

POST /api/v1/prescriptions/upload — Ingest a signed prescription PDF.

The upload endpoint accepts multipart/form-data with:
  - file: The PDF file (required)
  - metadata: JSON string with PrescriptionUploadMetadata fields (required)

Authentication: X-Session-Token header or session_token cookie.
Authorization: PRESCRIPTION_UPLOAD permission (Doctor role).
Tenant scoping: tenant_id from authenticated session, never from request.
"""

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
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

logger = get_logger(component="prescriptions_endpoint")

router = APIRouter()


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
    """Upload a signed prescription PDF for ingestion.

    The endpoint reads the full file into memory (bounded by MAX_UPLOAD_SIZE_MB),
    validates the metadata JSON, and delegates to the ingestion service.
    """
    # Parse metadata JSON from form field
    try:
        meta_dict = json.loads(metadata)
        meta = PrescriptionUploadMetadata(**meta_dict)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "INVALID_METADATA", "message": f"Invalid metadata JSON: {e}"},
        )

    # Read file content
    file_data = await file.read()

    try:
        result = await ingest_prescription(
            db,
            file_data=file_data,
            original_filename=file.filename or "unknown.pdf",
            declared_content_type=file.content_type,
            # Identity from session (NEVER from request)
            doctor_id=user.user_id,
            patient_id=meta.patient_id,
            tenant_id=user.tenant_id,
            clinic_id=user.clinic_id,
            # Idempotency
            idempotency_key=meta.idempotency_key,
            # Optional metadata
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
        raise HTTPException(
            status_code=400,
            detail={"error_code": e.code, "message": e.message},
        )
    except DuplicateDocumentError as e:
        raise HTTPException(
            status_code=409,
            detail={"error_code": e.code, "message": e.message, "detail": e.detail},
        )
    except IdempotencyConflictError as e:
        raise HTTPException(
            status_code=409,
            detail={"error_code": e.code, "message": e.message, "detail": e.detail},
        )
    except QuarantinedError as e:
        logger.warning(
            "upload_quarantined",
            actor_id=str(user.user_id),
            tenant_id=str(user.tenant_id),
            detail=e.detail,
        )
        raise HTTPException(
            status_code=422,
            detail={"error_code": e.code, "message": e.message},
        )
    except IngestionError as e:
        logger.error(
            "upload_failed",
            error_code=e.code,
            message=e.message,
            actor_id=str(user.user_id),
            tenant_id=str(user.tenant_id),
        )
        raise HTTPException(
            status_code=500,
            detail={"error_code": "INGESTION_ERROR", "message": "An internal error occurred during ingestion."},
        )

    return PrescriptionUploadResponse(
        prescription_id=result.prescription_id,
        document_id=result.document_id,
        storage_key=result.storage_key,
        checksum_sha256=result.checksum_sha256,
        file_size_bytes=result.file_size_bytes,
        pdf_version=result.pdf_version,
        estimated_page_count=result.estimated_page_count,
        scan_status=result.scan_status,
    )
