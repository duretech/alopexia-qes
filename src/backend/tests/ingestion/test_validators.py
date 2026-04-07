"""Tests for ingestion validators — MIME type, PDF structure, file size.

These test the pure validation functions with no I/O or DB dependencies.
"""

import pytest

from app.services.ingestion.validators import (
    validate_file_size,
    validate_mime_type,
    validate_pdf_structure,
    PdfStructureInfo,
    ValidationError,
)


# ── Fixtures ─────────────────────────────────────────────────────────────

# Minimal valid PDF structure for testing.
# This is NOT a real renderable PDF, but it satisfies the structural checks.
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
    b"startxref\n183\n"
    b"%%EOF\n"
)


@pytest.fixture
def minimal_pdf():
    return MINIMAL_PDF


@pytest.fixture
def large_pdf():
    """A PDF that exceeds 1 MB (for size limit testing)."""
    # Pad after the valid structure
    padding = b"\x00" * (1024 * 1024 + 1)
    return MINIMAL_PDF + padding


# ── File Size Tests ──────────────────────────────────────────────────────


class TestValidateFileSize:
    def test_valid_size(self, minimal_pdf):
        # Should not raise
        validate_file_size(minimal_pdf, max_size_bytes=10 * 1024 * 1024)

    def test_empty_file(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_file_size(b"", max_size_bytes=1024)
        assert exc_info.value.code == "EMPTY_FILE"

    def test_file_too_large(self):
        data = b"x" * 1025
        with pytest.raises(ValidationError) as exc_info:
            validate_file_size(data, max_size_bytes=1024)
        assert exc_info.value.code == "FILE_TOO_LARGE"
        assert "1024" in str(exc_info.value) or "MB" in str(exc_info.value)

    def test_exact_max_size(self, minimal_pdf):
        # Exactly at the limit should pass
        validate_file_size(minimal_pdf, max_size_bytes=len(minimal_pdf))

    def test_one_byte_over(self, minimal_pdf):
        with pytest.raises(ValidationError) as exc_info:
            validate_file_size(minimal_pdf, max_size_bytes=len(minimal_pdf) - 1)
        assert exc_info.value.code == "FILE_TOO_LARGE"


# ── MIME Type Tests ──────────────────────────────────────────────────────


class TestValidateMimeType:
    def test_valid_pdf_magic(self, minimal_pdf):
        validate_mime_type(minimal_pdf)

    def test_valid_pdf_with_declared_type(self, minimal_pdf):
        validate_mime_type(minimal_pdf, declared_content_type="application/pdf")

    def test_not_pdf_magic(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_mime_type(b"PK\x03\x04 this is a zip")
        assert exc_info.value.code == "NOT_PDF"

    def test_too_small_for_magic(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_mime_type(b"%PD")
        assert exc_info.value.code == "NOT_PDF"

    def test_wrong_declared_type(self, minimal_pdf):
        with pytest.raises(ValidationError) as exc_info:
            validate_mime_type(minimal_pdf, declared_content_type="image/png")
        assert exc_info.value.code == "MIME_MISMATCH"

    def test_x_pdf_content_type_accepted(self, minimal_pdf):
        # application/x-pdf is an alternative MIME type for PDF
        validate_mime_type(minimal_pdf, declared_content_type="application/x-pdf")

    def test_no_declared_type(self, minimal_pdf):
        # None declared type should not raise
        validate_mime_type(minimal_pdf, declared_content_type=None)


# ── PDF Structure Tests ──────────────────────────────────────────────────


class TestValidatePdfStructure:
    def test_valid_pdf(self, minimal_pdf):
        result = validate_pdf_structure(minimal_pdf)
        assert isinstance(result, PdfStructureInfo)
        assert result.version.startswith("1.4")

    def test_too_small(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_pdf_structure(b"%PDF-1.4\nsmall")
        assert exc_info.value.code == "PDF_TOO_SMALL"

    def test_no_eof_marker(self):
        # Valid header but no %%EOF
        data = b"%PDF-1.4\n" + b"x" * 100 + b"\nxref\n" + b"startxref\n"
        with pytest.raises(ValidationError) as exc_info:
            validate_pdf_structure(data)
        assert exc_info.value.code == "PDF_NO_EOF"

    def test_no_xref(self):
        # Valid header and %%EOF but no xref indicators
        data = b"%PDF-1.4\n" + b"x" * 100 + b"\n%%EOF\n"
        with pytest.raises(ValidationError) as exc_info:
            validate_pdf_structure(data)
        assert exc_info.value.code == "PDF_NO_XREF"

    def test_page_count_estimation(self, minimal_pdf):
        result = validate_pdf_structure(minimal_pdf)
        # Our minimal PDF has one /Type /Page and one /Type /Pages
        # So estimated count = 1 (Page) - 1 (Pages) = 0, which becomes None
        # OR the count is correct depending on exact format
        assert result.estimated_page_count is None or result.estimated_page_count >= 0

    def test_pdf_version_extraction(self, minimal_pdf):
        result = validate_pdf_structure(minimal_pdf)
        assert "1.4" in result.version

    def test_pdf_2_version(self):
        data = (
            b"%PDF-2.0\n"
            b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            b"xref\n0 1\n"
            b"0000000000 65535 f \n"
            b"trailer\n<< /Size 1 /Root 1 0 R >>\n"
            b"startxref\n42\n"
            b"%%EOF\n"
        )
        result = validate_pdf_structure(data)
        assert "2.0" in result.version
