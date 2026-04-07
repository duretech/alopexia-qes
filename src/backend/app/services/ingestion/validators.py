"""Document validators — MIME type, PDF structure, file size.

These are pure functions with no I/O dependencies, designed for
easy unit testing and reuse.

Implements C-DOC-02 (MIME validation), C-DOC-03 (PDF structure),
C-DOC-04 (file size limits).
"""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(component="ingestion_validators")

# PDF magic bytes: %PDF- (hex 25 50 44 46 2D)
_PDF_MAGIC = b"%PDF-"
# PDF must contain at least one %%EOF marker
_PDF_EOF_MARKER = b"%%EOF"
# Minimum plausible PDF size (header + minimal content + EOF)
_PDF_MIN_SIZE = 67
# Maximum supported PDF version prefix length to check
_PDF_VERSION_PREFIXES = (b"%PDF-1.", b"%PDF-2.")


class ValidationError(Exception):
    """Raised when document validation fails."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def validate_file_size(data: bytes, *, max_size_bytes: int) -> None:
    """Reject files exceeding the configured maximum upload size.

    Args:
        data: Raw file bytes.
        max_size_bytes: Maximum allowed size in bytes.

    Raises:
        ValidationError: If file is too large or empty.
    """
    if len(data) == 0:
        raise ValidationError("EMPTY_FILE", "Uploaded file is empty")
    if len(data) > max_size_bytes:
        size_mb = len(data) / (1024 * 1024)
        max_mb = max_size_bytes / (1024 * 1024)
        raise ValidationError(
            "FILE_TOO_LARGE",
            f"File size ({size_mb:.1f} MB) exceeds maximum ({max_mb:.1f} MB)",
        )


def validate_mime_type(data: bytes, *, declared_content_type: str | None = None) -> None:
    """Validate that the file is a PDF by checking magic bytes.

    We do NOT trust the Content-Type header from the client — we verify
    the actual bytes. The declared content type is only used for an
    additional cross-check.

    Args:
        data: Raw file bytes.
        declared_content_type: The Content-Type header sent by the client (optional).

    Raises:
        ValidationError: If the file is not a valid PDF.
    """
    if len(data) < len(_PDF_MAGIC):
        raise ValidationError(
            "NOT_PDF",
            "File is too small to be a valid PDF",
        )

    if not data[:5] == _PDF_MAGIC:
        raise ValidationError(
            "NOT_PDF",
            "File does not start with PDF magic bytes (%PDF-)",
        )

    # Cross-check declared content type if provided
    if declared_content_type and declared_content_type.lower() not in (
        "application/pdf",
        "application/x-pdf",
    ):
        raise ValidationError(
            "MIME_MISMATCH",
            f"Declared content type '{declared_content_type}' is not application/pdf",
        )


def validate_pdf_structure(data: bytes) -> PdfStructureInfo:
    """Validate basic PDF structural integrity.

    This is NOT a full PDF parser — we check:
      1. Magic bytes present and valid version
      2. File is not suspiciously small
      3. Contains at least one %%EOF marker
      4. Contains cross-reference indicators (xref or startxref)

    For a full deep-parse (e.g., detecting JavaScript, forms, encrypted
    content), a dedicated library like pikepdf would be used. That level
    of validation is deferred to a future enhancement.

    Args:
        data: Raw file bytes.

    Returns:
        PdfStructureInfo with version and page count estimate.

    Raises:
        ValidationError: If the PDF structure is invalid.
    """
    if len(data) < _PDF_MIN_SIZE:
        raise ValidationError(
            "PDF_TOO_SMALL",
            f"PDF is only {len(data)} bytes — minimum plausible size is {_PDF_MIN_SIZE}",
        )

    # Extract version
    version = _extract_pdf_version(data)

    # Check for %%EOF marker
    # Some PDFs have content after %%EOF (incremental updates), so we check
    # the entire file, not just the tail
    if _PDF_EOF_MARKER not in data:
        raise ValidationError(
            "PDF_NO_EOF",
            "PDF file does not contain a %%EOF marker",
        )

    # Check for cross-reference table indicators
    if b"xref" not in data and b"startxref" not in data:
        raise ValidationError(
            "PDF_NO_XREF",
            "PDF file does not contain cross-reference table indicators",
        )

    # Estimate page count by counting /Type /Page occurrences
    # This is a rough heuristic, not authoritative
    page_count = data.count(b"/Type /Page") + data.count(b"/Type/Page")
    # Subtract page tree nodes (/Type /Pages)
    page_tree_count = data.count(b"/Type /Pages") + data.count(b"/Type/Pages")
    page_count = max(page_count - page_tree_count, 0)

    return PdfStructureInfo(version=version, estimated_page_count=page_count or None)


class PdfStructureInfo:
    """Result of PDF structural validation."""

    __slots__ = ("version", "estimated_page_count")

    def __init__(self, *, version: str, estimated_page_count: int | None):
        self.version = version
        self.estimated_page_count = estimated_page_count


def _extract_pdf_version(data: bytes) -> str:
    """Extract the PDF version string from the header."""
    # First line should be %PDF-X.Y
    first_line_end = data.index(b"\n") if b"\n" in data[:20] else min(20, len(data))
    header = data[:first_line_end]
    if header.startswith(b"%PDF-"):
        version_str = header[5:].decode("ascii", errors="replace").strip()
        # Validate version is plausible (1.0-2.0 range)
        return version_str if len(version_str) <= 5 else version_str[:5]
    return "unknown"
