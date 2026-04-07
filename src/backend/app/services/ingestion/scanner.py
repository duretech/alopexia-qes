"""Malware scanning interface — ClamAV integration with mock fallback.

The scanner is invoked during ingestion BEFORE the file is stored in the
prescription bucket. If the scan returns INFECTED, the file is quarantined
and never reaches the prescription storage.

The mock scanner always returns CLEAN for testing and local dev. In production,
configure MALWARE_SCANNER=clamav and point to a running ClamAV instance.

Implements C-DOC-06 (malware scan hook), C-DOC-07 (quarantine handling).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.logging import get_logger

logger = get_logger(component="malware_scanner")


class ScanVerdict(StrEnum):
    """Malware scan verdict."""
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ScanResult:
    """Result of a malware scan."""
    verdict: ScanVerdict
    scanner: str
    detail: str | None = None


async def scan_file(
    data: bytes,
    *,
    filename_hint: str = "document.pdf",
    scanner_type: str = "mock",
    clamav_host: str = "localhost",
    clamav_port: int = 3310,
) -> ScanResult:
    """Scan file bytes for malware.

    Args:
        data: Raw file bytes to scan.
        filename_hint: Hint for the scanner (not used as storage key).
        scanner_type: "mock" or "clamav".
        clamav_host: ClamAV daemon host.
        clamav_port: ClamAV daemon port.

    Returns:
        ScanResult with verdict.
    """
    if scanner_type == "mock":
        return _mock_scan(data, filename_hint)
    elif scanner_type == "clamav":
        return await _clamav_scan(data, clamav_host, clamav_port)
    else:
        logger.warning("unknown_scanner_type", scanner_type=scanner_type)
        return ScanResult(
            verdict=ScanVerdict.SKIPPED,
            scanner=scanner_type,
            detail=f"Unknown scanner type: {scanner_type}",
        )


def _mock_scan(data: bytes, filename_hint: str) -> ScanResult:
    """Mock scanner for local development — always returns CLEAN.

    The mock scanner recognizes a special marker in the file content
    for testing quarantine flows: if the data contains
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR" (the EICAR test string),
    it returns INFECTED.
    """
    # EICAR test string detection for testing quarantine paths
    if b"X5O!P%@AP" in data:
        logger.info("mock_scan_infected", filename_hint=filename_hint)
        return ScanResult(
            verdict=ScanVerdict.INFECTED,
            scanner="mock",
            detail="EICAR test signature detected (mock scanner)",
        )

    logger.debug("mock_scan_clean", filename_hint=filename_hint, size=len(data))
    return ScanResult(verdict=ScanVerdict.CLEAN, scanner="mock")


async def _clamav_scan(data: bytes, host: str, port: int) -> ScanResult:
    """Scan via ClamAV daemon using INSTREAM command.

    The ClamAV daemon protocol sends data in chunks:
      1. Send b"zINSTREAM\\0"
      2. Send 4-byte big-endian chunk size + chunk data (repeat)
      3. Send 4 zero bytes to end the stream
      4. Read the response

    This uses asyncio streams for non-blocking I/O.
    """
    import asyncio

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=10.0,
        )
    except (ConnectionError, asyncio.TimeoutError, OSError) as e:
        logger.error("clamav_connection_failed", host=host, port=port, error=str(e))
        return ScanResult(
            verdict=ScanVerdict.ERROR,
            scanner="clamav",
            detail=f"Failed to connect to ClamAV at {host}:{port}: {e}",
        )

    try:
        # Send INSTREAM command
        writer.write(b"zINSTREAM\0")

        # Send data in 8KB chunks
        chunk_size = 8192
        offset = 0
        while offset < len(data):
            chunk = data[offset : offset + chunk_size]
            writer.write(len(chunk).to_bytes(4, "big"))
            writer.write(chunk)
            offset += chunk_size

        # End stream
        writer.write(b"\x00\x00\x00\x00")
        await writer.drain()

        # Read response
        response = await asyncio.wait_for(reader.read(4096), timeout=30.0)
        response_str = response.decode("utf-8", errors="replace").strip()

        writer.close()
        await writer.wait_closed()

        # Parse response: "stream: OK" or "stream: <virus_name> FOUND"
        if response_str.endswith("OK"):
            logger.info("clamav_scan_clean", size=len(data))
            return ScanResult(verdict=ScanVerdict.CLEAN, scanner="clamav")
        elif "FOUND" in response_str:
            logger.warning("clamav_scan_infected", detail=response_str, size=len(data))
            return ScanResult(
                verdict=ScanVerdict.INFECTED,
                scanner="clamav",
                detail=response_str,
            )
        else:
            logger.error("clamav_unexpected_response", response=response_str)
            return ScanResult(
                verdict=ScanVerdict.ERROR,
                scanner="clamav",
                detail=f"Unexpected ClamAV response: {response_str}",
            )

    except asyncio.TimeoutError:
        logger.error("clamav_timeout", host=host, port=port)
        return ScanResult(
            verdict=ScanVerdict.ERROR,
            scanner="clamav",
            detail="ClamAV scan timed out",
        )
    except Exception as e:
        logger.error("clamav_scan_error", error=str(e))
        return ScanResult(
            verdict=ScanVerdict.ERROR,
            scanner="clamav",
            detail=f"ClamAV scan error: {e}",
        )
