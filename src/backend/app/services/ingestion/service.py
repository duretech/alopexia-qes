"""Prescription ingestion orchestrator — the core upload pipeline.

Orchestrates the full ingestion flow for a prescription PDF upload:

  1. Validate file size
  2. Validate MIME type (magic bytes, not client header)
  3. Validate PDF structure
  4. Compute SHA-256 checksum
  5. Malware scan
  6. Duplicate detection (content hash)
  7. Idempotency key enforcement (client-provided)
  8. Store PDF to object storage (encrypted, object-locked)
  9. Create Prescription + UploadedDocument records
  10. Emit audit events
  11. (Future) Enqueue verification job

Callers: the /api/v1/prescriptions/upload endpoint.
The function operates within a single DB transaction — if any step fails,
everything rolls back (except the S3 object, which is orphaned and cleaned
up by retention policies).

Implements C-DOC-01 through C-DOC-10.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.document import UploadedDocument
from app.models.prescription import Prescription, PrescriptionMetadata
from app.services.ingestion.validators import (
    validate_file_size,
    validate_mime_type,
    validate_pdf_structure,
    ValidationError,
)
from app.services.ingestion.scanner import scan_file, ScanVerdict
from app.services.ingestion.dedup import check_duplicate

logger = get_logger(component="ingestion")


class IngestionError(Exception):
    """Base exception for ingestion failures."""

    def __init__(self, code: str, message: str, *, detail: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.detail = detail or {}
        super().__init__(f"[{code}] {message}")


class DuplicateDocumentError(IngestionError):
    """Raised when an identical document already exists."""
    pass


class IdempotencyConflictError(IngestionError):
    """Raised when the idempotency key is already used."""
    pass


class QuarantinedError(IngestionError):
    """Raised when the file is quarantined (malware detected)."""
    pass


@dataclass(frozen=True)
class IngestionResult:
    """Successful ingestion result."""
    prescription_id: uuid.UUID
    document_id: uuid.UUID
    storage_key: str
    storage_bucket: str
    checksum_sha256: str
    file_size_bytes: int
    pdf_version: str | None
    estimated_page_count: int | None
    scan_status: str
    is_duplicate_content: bool


async def ingest_prescription(
    db: AsyncSession,
    *,
    file_data: bytes,
    original_filename: str,
    declared_content_type: str | None = None,
    # Identity context (from authenticated user)
    doctor_id: uuid.UUID,
    patient_id: uuid.UUID,
    tenant_id: uuid.UUID,
    clinic_id: uuid.UUID,
    # Client-provided idempotency
    idempotency_key: str,
    # Optional prescription metadata
    prescribed_date: datetime | None = None,
    external_prescription_id: str | None = None,
    medication_name: str | None = None,
    dosage: str | None = None,
    treatment_duration: str | None = None,
    instructions: str | None = None,
    is_compounded: bool = True,
    formulation_details: dict[str, Any] | None = None,
    formulation_registration_number: str | None = None,
    additional_metadata: dict[str, Any] | None = None,
    # Storage backend (injected for testability)
    storage_backend: Any | None = None,
) -> IngestionResult:
    """Execute the full prescription ingestion pipeline.

    This function is the single entry point for all prescription uploads.
    It validates, scans, stores, and records the prescription in one
    atomic transaction.

    Args:
        db: Active async DB session (transaction managed by caller).
        file_data: Raw PDF bytes.
        original_filename: Client-provided filename (hashed, never stored raw).
        declared_content_type: Client Content-Type header (cross-checked).
        doctor_id: Authenticated doctor's UUID.
        patient_id: Target patient's UUID.
        tenant_id: Tenant scope (from session, NOT from request).
        clinic_id: Originating clinic UUID.
        idempotency_key: Client-provided dedup key.
        prescribed_date: Date the prescription was created externally.
        external_prescription_id: Reference ID from external system.
        medication_name: Prescribed medication (encrypted at rest).
        dosage: Dosage instructions (encrypted at rest).
        treatment_duration: Duration string.
        instructions: Additional instructions (encrypted at rest).
        is_compounded: Whether this is formulacion magistral.
        formulation_details: Compounding details (JSON).
        formulation_registration_number: Formulario Nacional reference.
        additional_metadata: Extra metadata fields.
        storage_backend: Optional storage backend override (for testing).

    Returns:
        IngestionResult with all identifiers and validation results.

    Raises:
        ValidationError: File validation failed (size, MIME, structure).
        DuplicateDocumentError: Identical content already uploaded.
        IdempotencyConflictError: Idempotency key already used.
        QuarantinedError: Malware detected, file quarantined.
        IngestionError: Other ingestion failures.
    """
    settings = get_settings()

    # ── Step 1: File size validation ─────────────────────────────────────
    validate_file_size(file_data, max_size_bytes=settings.max_upload_size_bytes)

    # ── Step 2: MIME type validation (magic bytes) ───────────────────────
    validate_mime_type(file_data, declared_content_type=declared_content_type)

    # ── Step 3: PDF structural validation ────────────────────────────────
    pdf_info = validate_pdf_structure(file_data)

    # ── Step 4: Compute SHA-256 checksum ─────────────────────────────────
    checksum = hashlib.sha256(file_data).hexdigest()

    # ── Step 5: Malware scan ─────────────────────────────────────────────
    scan_result = await scan_file(
        file_data,
        filename_hint=original_filename,
        scanner_type=settings.malware_scanner,
        clamav_host=settings.clamav_host,
        clamav_port=settings.clamav_port,
    )

    if scan_result.verdict == ScanVerdict.INFECTED:
        logger.warning(
            "file_quarantined",
            checksum=checksum,
            scanner=scan_result.scanner,
            detail=scan_result.detail,
            tenant_id=str(tenant_id),
        )
        raise QuarantinedError(
            code="QUARANTINED",
            message="File flagged by malware scanner — quarantined",
            detail={"scanner": scan_result.scanner, "detail": scan_result.detail},
        )

    # ── Step 6: Duplicate detection (content hash) ───────────────────────
    dedup_result = await check_duplicate(
        db, tenant_id=tenant_id, checksum_sha256=checksum,
    )

    if dedup_result.is_duplicate:
        raise DuplicateDocumentError(
            code="DUPLICATE_CONTENT",
            message="A document with identical content already exists",
            detail={
                "existing_document_id": str(dedup_result.existing_document_id),
                "existing_prescription_id": str(dedup_result.existing_prescription_id),
            },
        )

    # ── Step 7: Idempotency key enforcement ──────────────────────────────
    existing_rx = await _check_idempotency_key(db, tenant_id, idempotency_key)
    if existing_rx is not None:
        raise IdempotencyConflictError(
            code="IDEMPOTENCY_CONFLICT",
            message="A prescription with this idempotency key already exists",
            detail={"existing_prescription_id": str(existing_rx)},
        )

    # ── Step 8: Store PDF to object storage ──────────────────────────────
    storage = storage_backend
    if storage is None:
        from app.services.storage import get_storage_backend
        storage = get_storage_backend()

    bucket = settings.s3_prescription_bucket
    storage_key = _generate_storage_key(tenant_id, checksum)

    try:
        store_result = await storage.store_object(
            bucket,
            storage_key,
            file_data,
            content_type="application/pdf",
            checksum_sha256=checksum,
            server_side_encryption=True,
            object_lock_days=365 * 5,  # 5-year WORM retention (conservative)
        )
    except Exception as e:
        logger.error(
            "storage_failed",
            error=str(e),
            bucket=bucket,
            key=storage_key,
            tenant_id=str(tenant_id),
        )
        raise IngestionError(
            code="STORAGE_FAILED",
            message="Failed to store document in object storage",
        ) from e

    # ── Step 9: Create DB records ────────────────────────────────────────
    prescription_id = uuid.uuid4()
    document_id = uuid.uuid4()

    # Hash the original filename (we NEVER store the raw filename)
    filename_hash = hashlib.sha256(
        original_filename.encode("utf-8")
    ).hexdigest() if original_filename else None

    prescription = Prescription(
        id=prescription_id,
        tenant_id=tenant_id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        clinic_id=clinic_id,
        status="pending_verification",
        upload_checksum=checksum,
        document_storage_key=storage_key,
        idempotency_key=idempotency_key,
        prescribed_date=prescribed_date,
        external_prescription_id=external_prescription_id,
    )
    db.add(prescription)

    document = UploadedDocument(
        id=document_id,
        tenant_id=tenant_id,
        prescription_id=prescription_id,
        storage_key=storage_key,
        storage_bucket=bucket,
        checksum_sha256=checksum,
        file_size_bytes=len(file_data),
        mime_type="application/pdf",
        original_filename_hash=filename_hash,
        scan_status=scan_result.verdict.value,
        scanned_at=datetime.now(timezone.utc) if scan_result.verdict != ScanVerdict.SKIPPED else None,
        scan_result_detail=scan_result.detail,
        is_quarantined=False,
        pdf_validated=True,
        pdf_page_count=pdf_info.estimated_page_count,
        storage_version_id=store_result.version_id,
        object_lock_until=None,  # Set by S3 Object Lock, not tracked locally for now
    )
    db.add(document)

    # Create metadata record if any metadata was provided
    if any([
        medication_name, dosage, treatment_duration, instructions,
        formulation_details, formulation_registration_number,
    ]):
        meta = PrescriptionMetadata(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            prescription_id=prescription_id,
            medication_name=medication_name,
            dosage=dosage,
            treatment_duration=treatment_duration,
            instructions=instructions,
            is_compounded=is_compounded,
            formulation_details=formulation_details,
            formulation_registration_number=formulation_registration_number,
            additional_metadata=additional_metadata or {},
        )
        db.add(meta)

    await db.flush()

    logger.info(
        "prescription_ingested",
        prescription_id=str(prescription_id),
        document_id=str(document_id),
        checksum=checksum,
        size_bytes=len(file_data),
        pdf_version=pdf_info.version,
        pages=pdf_info.estimated_page_count,
        scan_status=scan_result.verdict.value,
        tenant_id=str(tenant_id),
        doctor_id=str(doctor_id),
    )

    # ── Step 10: (Future) Enqueue verification job ───────────────────────
    # TODO: await enqueue_verification_job(prescription_id, storage_key, checksum)
    # This will be wired when the queue/worker infrastructure is built (Phase C).

    return IngestionResult(
        prescription_id=prescription_id,
        document_id=document_id,
        storage_key=storage_key,
        storage_bucket=bucket,
        checksum_sha256=checksum,
        file_size_bytes=len(file_data),
        pdf_version=pdf_info.version,
        estimated_page_count=pdf_info.estimated_page_count,
        scan_status=scan_result.verdict.value,
        is_duplicate_content=False,
    )


async def _check_idempotency_key(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    idempotency_key: str,
) -> uuid.UUID | None:
    """Check if a prescription with this idempotency key already exists.

    Returns the existing prescription ID if found, None otherwise.
    Scoped to tenant (tenant isolation).
    """
    stmt = (
        select(Prescription.id)
        .where(
            Prescription.tenant_id == tenant_id,
            Prescription.idempotency_key == idempotency_key,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    return row


def _generate_storage_key(tenant_id: uuid.UUID, checksum: str) -> str:
    """Generate a randomized storage key for the prescription PDF.

    Format: {tenant_id}/{random_uuid}/{checksum[:12]}.pdf

    The key is system-generated and never user-controlled (C-DOC-09).
    The checksum prefix is for human readability in S3 listings only.
    """
    random_part = uuid.uuid4().hex
    return f"{tenant_id}/{random_part}/{checksum[:12]}.pdf"
