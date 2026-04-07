"""Duplicate detection — content-hash-based deduplication.

Prevents the same prescription PDF from being uploaded twice within a
tenant by checking the SHA-256 content hash against existing documents.

This is distinct from idempotency-key enforcement (which is client-driven
and prevents accidental double-submits). Content-hash dedup catches the
case where the same PDF is uploaded with different idempotency keys.

Implements C-DOC-05 (duplicate detection).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.document import UploadedDocument

logger = get_logger(component="dedup")


@dataclass(frozen=True)
class DuplicateCheckResult:
    """Result of duplicate content check."""
    is_duplicate: bool
    existing_document_id: UUID | None = None
    existing_prescription_id: UUID | None = None


async def check_duplicate(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    checksum_sha256: str,
) -> DuplicateCheckResult:
    """Check if a document with the same content hash already exists.

    Only checks within the same tenant (tenant isolation). Soft-deleted
    documents are excluded.

    Args:
        db: Active database session.
        tenant_id: Tenant to scope the search.
        checksum_sha256: SHA-256 hex digest of the file content.

    Returns:
        DuplicateCheckResult indicating whether a duplicate was found.
    """
    stmt = (
        select(UploadedDocument.id, UploadedDocument.prescription_id)
        .where(
            UploadedDocument.tenant_id == tenant_id,
            UploadedDocument.checksum_sha256 == checksum_sha256,
            UploadedDocument.is_deleted.is_(False),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()

    if row is not None:
        logger.info(
            "duplicate_document_found",
            tenant_id=str(tenant_id),
            checksum=checksum_sha256,
            existing_document_id=str(row[0]),
            existing_prescription_id=str(row[1]),
        )
        return DuplicateCheckResult(
            is_duplicate=True,
            existing_document_id=row[0],
            existing_prescription_id=row[1],
        )

    return DuplicateCheckResult(is_duplicate=False)
