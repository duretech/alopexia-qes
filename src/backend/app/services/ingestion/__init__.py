"""Prescription ingestion service — upload, validate, store, enqueue.

Implements the ingestion pipeline from docs/architecture.md §4:
  1. Compute SHA-256 checksum
  2. Validate MIME type (application/pdf)
  3. Validate PDF structure
  4. Check file size limits
  5. Check for duplicates (content hash dedup)
  6. Malware scan hook
  7. Store to S3 (encrypted, object-locked)
  8. Create prescription + document records
  9. Enqueue verification job

Controls: C-DOC-01 through C-DOC-10.
"""

from app.services.ingestion.validators import (
    validate_mime_type,
    validate_pdf_structure,
    validate_file_size,
    ValidationError,
)
from app.services.ingestion.scanner import scan_file, ScanResult, ScanVerdict
from app.services.ingestion.dedup import check_duplicate
from app.services.ingestion.service import ingest_prescription

__all__ = [
    "ingest_prescription",
    "validate_mime_type",
    "validate_pdf_structure",
    "validate_file_size",
    "scan_file",
    "ScanResult",
    "ScanVerdict",
    "check_duplicate",
    "ValidationError",
]
