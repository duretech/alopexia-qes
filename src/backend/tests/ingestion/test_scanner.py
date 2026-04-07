"""Tests for the malware scanner interface."""

import pytest

from app.services.ingestion.scanner import scan_file, ScanResult, ScanVerdict


class TestMockScanner:
    async def test_clean_file(self):
        result = await scan_file(b"%PDF-1.4 clean content", scanner_type="mock")
        assert result.verdict == ScanVerdict.CLEAN
        assert result.scanner == "mock"

    async def test_eicar_detected(self):
        # The mock scanner recognizes the EICAR test string prefix
        data = b"%PDF-1.4 X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR"
        result = await scan_file(data, scanner_type="mock")
        assert result.verdict == ScanVerdict.INFECTED
        assert result.scanner == "mock"
        assert result.detail is not None
        assert "EICAR" in result.detail

    async def test_unknown_scanner_type(self):
        result = await scan_file(b"data", scanner_type="nonexistent")
        assert result.verdict == ScanVerdict.SKIPPED

    async def test_filename_hint_passed(self):
        result = await scan_file(
            b"clean data",
            filename_hint="prescription_001.pdf",
            scanner_type="mock",
        )
        assert result.verdict == ScanVerdict.CLEAN


class TestScanResult:
    def test_frozen(self):
        result = ScanResult(verdict=ScanVerdict.CLEAN, scanner="mock")
        with pytest.raises(AttributeError):
            result.verdict = ScanVerdict.INFECTED  # type: ignore[misc]

    def test_detail_optional(self):
        result = ScanResult(verdict=ScanVerdict.CLEAN, scanner="mock")
        assert result.detail is None


class TestScanVerdict:
    def test_all_values(self):
        assert set(ScanVerdict) == {"clean", "infected", "error", "skipped"}
