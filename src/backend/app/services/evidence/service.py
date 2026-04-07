"""Evidence retrieval and integrity verification service.

Provides functions for:
  1. Listing evidence files for a prescription/verification
  2. Verifying evidence file integrity (checksum comparison)

Implements C-QTSP-03 (evidence storage) from the controls catalog.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.evidence import EvidenceFile

logger = get_logger(component="evidence_service")


@dataclass(frozen=True)
class EvidenceIntegrityResult:
    """Result of evidence integrity check."""
    evidence_id: UUID
    expected_checksum: str
    actual_checksum: str | None
    is_intact: bool
    error: str | None = None


async def get_evidence_files(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    prescription_id: UUID | None = None,
    verification_result_id: UUID | None = None,
) -> list[EvidenceFile]:
    """Retrieve evidence files, scoped to tenant.

    Filter by prescription_id and/or verification_result_id.
    """
    stmt = select(EvidenceFile).where(EvidenceFile.tenant_id == tenant_id)

    if prescription_id is not None:
        stmt = stmt.where(EvidenceFile.prescription_id == prescription_id)
    if verification_result_id is not None:
        stmt = stmt.where(EvidenceFile.verification_result_id == verification_result_id)

    stmt = stmt.order_by(EvidenceFile.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def verify_evidence_integrity(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    evidence_id: UUID,
    storage_backend=None,
) -> EvidenceIntegrityResult:
    """Verify the integrity of a stored evidence file.

    Downloads the file from storage and compares its SHA-256 hash
    against the stored checksum.
    """
    stmt = select(EvidenceFile).where(
        EvidenceFile.id == evidence_id,
        EvidenceFile.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    evidence = result.scalar_one_or_none()

    if evidence is None:
        return EvidenceIntegrityResult(
            evidence_id=evidence_id,
            expected_checksum="",
            actual_checksum=None,
            is_intact=False,
            error="Evidence file not found",
        )

    storage = storage_backend
    if storage is None:
        from app.services.storage import get_storage_backend
        storage = get_storage_backend()

    try:
        data = await storage.get_object(evidence.storage_bucket, evidence.storage_key)
        actual = hashlib.sha256(data).hexdigest()
    except Exception as e:
        logger.error(
            "evidence_integrity_check_failed",
            evidence_id=str(evidence_id),
            error=str(e),
        )
        return EvidenceIntegrityResult(
            evidence_id=evidence_id,
            expected_checksum=evidence.checksum_sha256,
            actual_checksum=None,
            is_intact=False,
            error=f"Failed to retrieve evidence: {e}",
        )

    is_intact = actual == evidence.checksum_sha256

    if not is_intact:
        logger.critical(
            "evidence_integrity_mismatch",
            evidence_id=str(evidence_id),
            expected=evidence.checksum_sha256,
            actual=actual,
        )

    return EvidenceIntegrityResult(
        evidence_id=evidence_id,
        expected_checksum=evidence.checksum_sha256,
        actual_checksum=actual,
        is_intact=is_intact,
    )
