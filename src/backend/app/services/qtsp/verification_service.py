"""Signature verification orchestration service.

Orchestrates the full verification flow for a prescription:
  1. Retrieve the PDF from object storage
  2. Call the QTSP provider to verify the signature
  3. Store the raw QTSP response in the evidence bucket
  4. Store evidence artifacts (validation report, cert chain, etc.)
  5. Create SignatureVerificationResult and EvidenceFile DB records
  6. Update the prescription status
  7. Emit audit events

This service is called by the verification worker (async queue consumer)
or directly in tests. It handles retries at the orchestration level,
delegating per-request retries to the QTSP provider itself.

Implements C-QTSP-01 through C-QTSP-08.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.evidence import EvidenceFile
from app.models.prescription import Prescription
from app.models.verification import SignatureVerificationResult
from app.services.qtsp.interface import (
    QTSPError,
    VerificationResult,
    VerificationStatus,
)

logger = get_logger(component="verification_service")


class VerificationServiceError(Exception):
    """Raised when the verification orchestration fails."""

    def __init__(self, code: str, message: str, *, retryable: bool = False):
        self.code = code
        self.retryable = retryable
        super().__init__(f"[{code}] {message}")


@dataclass(frozen=True)
class VerificationOutcome:
    """Result of the verification orchestration."""
    verification_id: uuid.UUID
    prescription_id: uuid.UUID
    status: str
    requires_manual_review: bool
    attempt_number: int
    evidence_file_ids: list[uuid.UUID]
    qtsp_request_id: str | None = None
    error_message: str | None = None


async def verify_prescription(
    db: AsyncSession,
    *,
    prescription_id: uuid.UUID,
    tenant_id: uuid.UUID,
    # Injected dependencies (for testability)
    qtsp_provider: Any | None = None,
    storage_backend: Any | None = None,
) -> VerificationOutcome:
    """Run the full signature verification pipeline for a prescription.

    Args:
        db: Active async DB session.
        prescription_id: Prescription to verify.
        tenant_id: Tenant scope.
        qtsp_provider: Optional QTSP provider override.
        storage_backend: Optional storage backend override.

    Returns:
        VerificationOutcome with result details.

    Raises:
        VerificationServiceError: If the orchestration fails.
    """
    settings = get_settings()

    # ── Step 1: Load the prescription ────────────────────────────────────
    stmt = select(Prescription).where(
        Prescription.id == prescription_id,
        Prescription.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    prescription = result.scalar_one_or_none()
    if prescription is None:
        raise VerificationServiceError(
            "PRESCRIPTION_NOT_FOUND",
            f"Prescription {prescription_id} not found in tenant {tenant_id}",
        )

    # ── Step 2: Determine attempt number ─────────────────────────────────
    count_stmt = select(SignatureVerificationResult.id).where(
        SignatureVerificationResult.prescription_id == prescription_id,
        SignatureVerificationResult.tenant_id == tenant_id,
    )
    count_result = await db.execute(count_stmt)
    attempt_number = len(count_result.all()) + 1

    # ── Step 3: Retrieve PDF from storage ────────────────────────────────
    storage = storage_backend
    if storage is None:
        from app.services.storage import get_storage_backend
        storage = get_storage_backend()

    try:
        pdf_data = await storage.get_object(
            settings.s3_prescription_bucket,
            prescription.document_storage_key,
        )
    except Exception as e:
        raise VerificationServiceError(
            "PDF_RETRIEVAL_FAILED",
            f"Failed to retrieve PDF from storage: {e}",
            retryable=True,
        ) from e

    # ── Step 4: Call QTSP provider ───────────────────────────────────────
    provider = qtsp_provider
    if provider is None:
        provider = _get_qtsp_provider()

    idempotency_key = f"verify-{prescription_id}-{attempt_number}"
    verification_id = uuid.uuid4()

    try:
        qtsp_result = await provider.verify_signature(
            pdf_data,
            document_id=str(prescription_id),
            idempotency_key=idempotency_key,
        )
    except QTSPError as e:
        # Record the failed attempt
        return await _record_error_result(
            db,
            verification_id=verification_id,
            prescription_id=prescription_id,
            tenant_id=tenant_id,
            attempt_number=attempt_number,
            idempotency_key=idempotency_key,
            provider_name=provider.provider_name,
            error_code=e.code or "QTSP_ERROR",
            error_message=str(e),
            retryable=e.retryable,
        )

    # ── Step 5: Store raw response + evidence in object storage ──────────
    evidence_file_ids: list[uuid.UUID] = []

    # Store raw QTSP response
    if qtsp_result.raw_response:
        raw_checksum = hashlib.sha256(qtsp_result.raw_response).hexdigest()
        raw_key = f"{tenant_id}/verification/{verification_id}/raw_response"
        try:
            await storage.store_object(
                settings.s3_evidence_bucket,
                raw_key,
                qtsp_result.raw_response,
                content_type=qtsp_result.raw_response_content_type,
                checksum_sha256=raw_checksum,
            )
        except Exception as e:
            logger.error(
                "raw_response_storage_failed",
                error=str(e),
                verification_id=str(verification_id),
            )
            # Continue — raw response storage failure should not block verification

    # Store evidence artifacts
    for artifact in qtsp_result.evidence_artifacts:
        evidence_id = uuid.uuid4()
        artifact_checksum = hashlib.sha256(artifact.data).hexdigest()
        artifact_key = (
            f"{tenant_id}/verification/{verification_id}"
            f"/{artifact.evidence_type}_{evidence_id.hex[:8]}"
        )
        try:
            store_result = await storage.store_object(
                settings.s3_evidence_bucket,
                artifact_key,
                artifact.data,
                content_type=artifact.content_type,
                checksum_sha256=artifact_checksum,
            )
        except Exception as e:
            logger.error(
                "evidence_storage_failed",
                error=str(e),
                evidence_type=artifact.evidence_type,
                verification_id=str(verification_id),
            )
            continue

        evidence_file = EvidenceFile(
            id=evidence_id,
            tenant_id=tenant_id,
            prescription_id=prescription_id,
            verification_result_id=verification_id,
            storage_key=artifact_key,
            storage_bucket=settings.s3_evidence_bucket,
            checksum_sha256=artifact_checksum,
            file_size_bytes=len(artifact.data),
            mime_type=artifact.content_type,
            evidence_type=artifact.evidence_type,
            storage_version_id=store_result.version_id,
        )
        db.add(evidence_file)
        evidence_file_ids.append(evidence_id)

    # ── Step 6: Create verification result DB record ─────────────────────
    raw_checksum = hashlib.sha256(qtsp_result.raw_response).hexdigest() if qtsp_result.raw_response else None
    raw_storage_key = f"{tenant_id}/verification/{verification_id}/raw_response" if qtsp_result.raw_response else None

    now = datetime.now(timezone.utc)
    verification_record = SignatureVerificationResult(
        id=verification_id,
        tenant_id=tenant_id,
        prescription_id=prescription_id,
        attempt_number=attempt_number,
        idempotency_key=idempotency_key,
        qtsp_provider=qtsp_result.provider,
        qtsp_request_id=qtsp_result.request_id,
        verification_status=str(qtsp_result.status),
        verified_at=now if qtsp_result.status != VerificationStatus.ERROR else None,
        # Certificate details
        signer_common_name=qtsp_result.certificate.common_name if qtsp_result.certificate else None,
        signer_serial_number=qtsp_result.certificate.serial_number if qtsp_result.certificate else None,
        signer_organization=qtsp_result.certificate.organization if qtsp_result.certificate else None,
        certificate_issuer=qtsp_result.certificate.issuer if qtsp_result.certificate else None,
        certificate_valid_from=qtsp_result.certificate.valid_from if qtsp_result.certificate else None,
        certificate_valid_to=qtsp_result.certificate.valid_to if qtsp_result.certificate else None,
        certificate_is_qualified=qtsp_result.certificate.is_qualified if qtsp_result.certificate else None,
        # Timestamp details
        timestamp_status=str(qtsp_result.timestamp.status) if qtsp_result.timestamp else None,
        timestamp_time=qtsp_result.timestamp.time if qtsp_result.timestamp else None,
        timestamp_authority=qtsp_result.timestamp.authority if qtsp_result.timestamp else None,
        timestamp_is_qualified=qtsp_result.timestamp.is_qualified if qtsp_result.timestamp else None,
        # Trust list
        trust_list_status=str(qtsp_result.trust_list_status),
        trust_list_checked_at=qtsp_result.trust_list_checked_at,
        # Signature
        signature_intact=qtsp_result.signature_intact,
        signature_algorithm=qtsp_result.signature_algorithm,
        # Raw response
        raw_response_storage_key=raw_storage_key,
        raw_response_checksum=raw_checksum,
        # Error info
        error_code=qtsp_result.error_code,
        error_message=qtsp_result.error_message,
        # Manual review
        requires_manual_review=qtsp_result.requires_manual_review,
        # Normalized response
        normalized_response=qtsp_result.normalized_response,
    )
    db.add(verification_record)

    # ── Step 7: Update prescription status ───────────────────────────────
    new_status = _map_verification_to_prescription_status(qtsp_result.status)
    await db.execute(
        update(Prescription)
        .where(Prescription.id == prescription_id)
        .values(
            status=new_status,
            verification_status=str(qtsp_result.status),
        )
    )

    await db.flush()

    logger.info(
        "verification_completed",
        prescription_id=str(prescription_id),
        verification_id=str(verification_id),
        status=str(qtsp_result.status),
        attempt_number=attempt_number,
        evidence_count=len(evidence_file_ids),
        requires_manual_review=qtsp_result.requires_manual_review,
    )

    return VerificationOutcome(
        verification_id=verification_id,
        prescription_id=prescription_id,
        status=str(qtsp_result.status),
        requires_manual_review=qtsp_result.requires_manual_review,
        attempt_number=attempt_number,
        evidence_file_ids=evidence_file_ids,
        qtsp_request_id=qtsp_result.request_id,
    )


async def _record_error_result(
    db: AsyncSession,
    *,
    verification_id: uuid.UUID,
    prescription_id: uuid.UUID,
    tenant_id: uuid.UUID,
    attempt_number: int,
    idempotency_key: str,
    provider_name: str,
    error_code: str,
    error_message: str,
    retryable: bool,
) -> VerificationOutcome:
    """Record a failed verification attempt."""
    record = SignatureVerificationResult(
        id=verification_id,
        tenant_id=tenant_id,
        prescription_id=prescription_id,
        attempt_number=attempt_number,
        idempotency_key=idempotency_key,
        qtsp_provider=provider_name,
        verification_status="error",
        error_code=error_code,
        error_message=error_message,
        requires_manual_review=not retryable,
    )
    db.add(record)

    # Update prescription status if not retryable
    if not retryable:
        await db.execute(
            update(Prescription)
            .where(Prescription.id == prescription_id)
            .values(
                status="failed_verification",
                verification_status="error",
            )
        )

    await db.flush()

    logger.warning(
        "verification_error",
        prescription_id=str(prescription_id),
        verification_id=str(verification_id),
        error_code=error_code,
        error_message=error_message,
        retryable=retryable,
        attempt_number=attempt_number,
    )

    return VerificationOutcome(
        verification_id=verification_id,
        prescription_id=prescription_id,
        status="error",
        requires_manual_review=not retryable,
        attempt_number=attempt_number,
        evidence_file_ids=[],
        error_message=error_message,
    )


def _map_verification_to_prescription_status(status: VerificationStatus) -> str:
    """Map QTSP verification status to prescription lifecycle status."""
    mapping = {
        VerificationStatus.VERIFIED: "verified",
        VerificationStatus.FAILED: "failed_verification",
        VerificationStatus.ERROR: "pending_verification",  # Will be retried
        VerificationStatus.EXPIRED: "failed_verification",
        VerificationStatus.REVOKED: "failed_verification",
        VerificationStatus.INDETERMINATE: "manual_review",
    }
    return mapping.get(status, "pending_verification")


def _get_qtsp_provider():
    """Factory: return the configured QTSP provider."""
    settings = get_settings()
    if settings.qtsp_provider == "mock":
        from app.services.qtsp.mock_provider import MockQTSPProvider
        return MockQTSPProvider()
    if settings.qtsp_provider == "dokobit":
        from app.services.qtsp.dokobit_provider import DokobitQTSPProvider
        return DokobitQTSPProvider()
    raise ValueError(f"Unknown QTSP provider: {settings.qtsp_provider}")
