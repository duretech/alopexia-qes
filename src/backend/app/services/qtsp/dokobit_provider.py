"""Dokobit QTSP provider — real signature verification via Dokobit API.

Implements the QTSPProvider protocol using Dokobit's document validation API
(https://beta.dokobit.com). The flow:

  1. Upload a PDF (base64 + SHA256 digest) → receive a validation token
  2. Poll the report-xml endpoint until validation completes
  3. Parse the ETSI EN 319 102-1 XML report to extract:
       - certificate validity & details
       - signature integrity (hash/crypto check)
       - timestamp status (qualified / valid / missing)
  4. Return a normalized VerificationResult with raw XML as evidence
  5. Call the delete endpoint to clean up server-side resources

Implements C-QTSP-01 (provider adapter), C-QTSP-02 (verbatim evidence storage).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.qtsp.interface import (
    CertificateInfo,
    EvidenceArtifact,
    QTSPConnectionError,
    QTSPError,
    QTSPTimeoutError,
    QTSPValidationError,
    TimestampInfo,
    TimestampStatus,
    TrustListStatus,
    VerificationResult,
    VerificationStatus,
)

logger = get_logger(component="dokobit_qtsp")

# Dokobit validation report XML namespaces
_NS = {
    "vr": "http://uri.etsi.org/19102/v1.2.1#",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "xades": "http://uri.etsi.org/01903/v1.3.2#",
}

# Polling configuration
_POLL_INTERVAL_SECONDS = 2.0
_MAX_POLL_ATTEMPTS = 60  # 2 minutes max


class DokobitQTSPProvider:
    """Dokobit implementation of the QTSPProvider protocol."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        access_token: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
    ):
        settings = get_settings()
        self._base_url = (base_url or settings.qtsp_api_url).rstrip("/")
        self._access_token = access_token or settings.qtsp_api_key
        self._timeout = timeout_seconds or settings.qtsp_timeout_seconds
        self._max_retries = max_retries or settings.qtsp_max_retries

        if not self._base_url:
            raise QTSPError("Dokobit base URL is not configured", code="CONFIG_MISSING")
        if not self._access_token:
            raise QTSPError("Dokobit access token is not configured", code="CONFIG_MISSING")

    @property
    def provider_name(self) -> str:
        return "dokobit"

    async def verify_signature(
        self,
        pdf_data: bytes,
        *,
        document_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> VerificationResult:
        request_id = f"dokobit-{uuid.uuid4().hex[:16]}"

        logger.info(
            "dokobit_verification_started",
            document_id=document_id,
            request_id=request_id,
            size=len(pdf_data),
        )

        token: str | None = None
        try:
            # Step 1: Upload the PDF
            token = await self._upload_document(pdf_data, request_id)

            # Step 2: Poll for the validation report XML
            report_xml = await self._poll_report(token, request_id)

            # Step 3: Fetch diagnostic data XML (additional evidence)
            diagnostic_xml = await self._fetch_diagnostic_data(token, request_id)

            # Step 4: Parse the report
            result = self._parse_validation_report(
                report_xml, diagnostic_xml, request_id,
            )

            logger.info(
                "dokobit_verification_completed",
                document_id=document_id,
                request_id=request_id,
                status=str(result.status),
            )

            return result

        except (QTSPConnectionError, QTSPTimeoutError, QTSPValidationError):
            raise
        except QTSPError:
            raise
        except httpx.TimeoutException as e:
            raise QTSPTimeoutError(
                f"Dokobit request timed out: {e}",
                code="DOKOBIT_TIMEOUT",
            ) from e
        except httpx.ConnectError as e:
            raise QTSPConnectionError(
                f"Failed to connect to Dokobit: {e}",
                code="DOKOBIT_CONNECTION",
            ) from e
        except Exception as e:
            raise QTSPError(
                f"Unexpected error during Dokobit verification: {e}",
                code="DOKOBIT_UNEXPECTED",
            ) from e
        finally:
            # Step 5: Clean up server-side resources
            if token:
                await self._delete_validation(token, request_id)

    async def health_check(self) -> bool:
        """Check connectivity to Dokobit by making a lightweight request."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/api/validation/upload.json",
                    params={"access_token": self._access_token},
                )
                # A GET to the upload endpoint returns an error (method not allowed
                # or missing params) but proves the API is reachable.
                return resp.status_code < 500
        except Exception:
            return False

    # ── Private: API calls ──────────────────────────────────────────────

    async def _upload_document(self, pdf_data: bytes, request_id: str) -> str:
        """Upload a PDF to Dokobit for validation. Returns validation token."""
        file_digest = hashlib.sha256(pdf_data).hexdigest()
        file_content_b64 = base64.b64encode(pdf_data).decode("ascii")

        payload = {
            "file": {
                "name": f"prescription_{request_id}.pdf",
                "digest": file_digest,
                "content": file_content_b64,
            }
        }

        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        f"{self._base_url}/api/validation/upload.json",
                        params={"access_token": self._access_token},
                        json=payload,
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "ok" and data.get("token"):
                        logger.info(
                            "dokobit_upload_success",
                            request_id=request_id,
                            token=data["token"][:8] + "...",
                        )
                        return data["token"]
                    else:
                        raise QTSPValidationError(
                            f"Dokobit upload rejected: {data}",
                            code="DOKOBIT_UPLOAD_REJECTED",
                        )

                if resp.status_code >= 500 and attempt < self._max_retries:
                    logger.warning(
                        "dokobit_upload_retry",
                        request_id=request_id,
                        status=resp.status_code,
                        attempt=attempt,
                    )
                    await asyncio.sleep(2 ** attempt)
                    continue

                raise QTSPError(
                    f"Dokobit upload failed (HTTP {resp.status_code}): {resp.text}",
                    code=f"DOKOBIT_HTTP_{resp.status_code}",
                    retryable=resp.status_code >= 500,
                )

            except httpx.TimeoutException:
                if attempt < self._max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        raise QTSPTimeoutError(
            "Dokobit upload failed after all retries",
            code="DOKOBIT_UPLOAD_EXHAUSTED",
        )

    async def _poll_report(self, token: str, request_id: str) -> bytes:
        """Poll for the validation report XML until ready."""
        url = f"{self._base_url}/api/validation/{token}/download/report-xml"

        for attempt in range(1, _MAX_POLL_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.get(
                        url,
                        params={"access_token": self._access_token},
                    )

                if resp.status_code == 200:
                    body = resp.content
                    # Dokobit returns a text message while still processing
                    if b"Validation is still in progress" in body:
                        logger.debug(
                            "dokobit_poll_in_progress",
                            request_id=request_id,
                            attempt=attempt,
                        )
                        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
                        continue
                    # We have the actual report
                    logger.info(
                        "dokobit_report_ready",
                        request_id=request_id,
                        poll_attempts=attempt,
                        size=len(body),
                    )
                    return body

                if resp.status_code >= 500:
                    await asyncio.sleep(_POLL_INTERVAL_SECONDS)
                    continue

                raise QTSPError(
                    f"Dokobit report download failed (HTTP {resp.status_code}): {resp.text}",
                    code=f"DOKOBIT_HTTP_{resp.status_code}",
                )

            except httpx.TimeoutException:
                if attempt < _MAX_POLL_ATTEMPTS:
                    await asyncio.sleep(_POLL_INTERVAL_SECONDS)
                    continue
                raise

        raise QTSPTimeoutError(
            "Dokobit validation did not complete within polling window",
            code="DOKOBIT_POLL_EXHAUSTED",
        )

    async def _fetch_diagnostic_data(self, token: str, request_id: str) -> bytes | None:
        """Fetch diagnostic data XML (best-effort, non-blocking)."""
        url = f"{self._base_url}/api/validation/{token}/download/diagnostic-data-xml"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    url,
                    params={"access_token": self._access_token},
                )
            if resp.status_code == 200 and b"Validation is still in progress" not in resp.content:
                return resp.content
        except Exception as e:
            logger.warning(
                "dokobit_diagnostic_fetch_failed",
                request_id=request_id,
                error=str(e),
            )
        return None

    async def _delete_validation(self, token: str, request_id: str) -> None:
        """Clean up validation resources on Dokobit (best-effort)."""
        url = f"{self._base_url}/api/validation/{token}/delete.json"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url,
                    params={"access_token": self._access_token},
                )
            logger.debug(
                "dokobit_cleanup",
                request_id=request_id,
                status=resp.status_code,
            )
        except Exception as e:
            logger.warning(
                "dokobit_cleanup_failed",
                request_id=request_id,
                error=str(e),
            )

    # ── Private: XML parsing ────────────────────────────────────────────

    def _parse_validation_report(
        self,
        report_xml: bytes,
        diagnostic_xml: bytes | None,
        request_id: str,
    ) -> VerificationResult:
        """Parse the Dokobit ETSI validation report XML into a VerificationResult."""
        now = datetime.now(timezone.utc)

        try:
            root = ET.fromstring(report_xml)
        except ET.ParseError as e:
            logger.error(
                "dokobit_xml_parse_error",
                request_id=request_id,
                error=str(e),
            )
            return VerificationResult(
                status=VerificationStatus.ERROR,
                provider="dokobit",
                request_id=request_id,
                raw_response=report_xml,
                raw_response_content_type="application/xml",
                error_code="XML_PARSE_ERROR",
                error_message=f"Failed to parse validation report: {e}",
                evidence_artifacts=self._build_evidence(request_id, report_xml, diagnostic_xml),
            )

        # Extract the top-level indication — Dokobit uses several tag names
        # and URN-based values like "urn:cef:dss:mainindication:totalPassed"
        indication = (
            self._find_text(root, ".//vr:MainIndication", _NS)
            or self._find_text(root, ".//MainIndication", {})
            or self._find_text(root, ".//vr:Indication", _NS)
            or self._find_text(root, ".//Indication", {})
        )
        sub_indication = (
            self._find_text(root, ".//vr:SubIndication", _NS)
            or self._find_text(root, ".//SubIndication", {})
        )

        # Map ETSI indication to our status
        status = self._map_indication(indication, sub_indication)

        # Extract signature details
        sig_intact = self._extract_signature_intact(root)
        sig_algo = self._find_text(root, ".//vr:SignatureAlgorithm", _NS)
        if not sig_algo:
            sig_algo = self._find_text(root, ".//SignatureAlgorithm", {})
            if not sig_algo:
                sig_algo = self._find_text(root, ".//DigestAlgorithm", {})

        # Extract certificate info
        certificate = self._extract_certificate(root)

        # Extract timestamp info
        timestamp = self._extract_timestamp(root)

        # Determine trust list status
        trust_status = TrustListStatus.UNKNOWN
        if status == VerificationStatus.VERIFIED:
            trust_status = TrustListStatus.TRUSTED
        elif status == VerificationStatus.FAILED:
            trust_status = TrustListStatus.UNTRUSTED

        # Build normalized response dict
        normalized = {
            "provider": "dokobit",
            "request_id": request_id,
            "indication": indication,
            "sub_indication": sub_indication,
            "status": str(status),
            "signature_intact": sig_intact,
            "signature_algorithm": sig_algo,
            "certificate": certificate.to_dict() if certificate else None,
            "timestamp": timestamp.to_dict() if timestamp else None,
            "trust_list_status": str(trust_status),
            "validation_time": now.isoformat(),
        }

        return VerificationResult(
            status=status,
            provider="dokobit",
            request_id=request_id,
            signature_intact=sig_intact,
            signature_algorithm=sig_algo,
            certificate=certificate,
            timestamp=timestamp,
            trust_list_status=trust_status,
            trust_list_checked_at=now,
            raw_response=report_xml,
            raw_response_content_type="application/xml",
            error_code=sub_indication if status != VerificationStatus.VERIFIED else None,
            error_message=f"Indication: {indication}, SubIndication: {sub_indication}" if status != VerificationStatus.VERIFIED else None,
            evidence_artifacts=self._build_evidence(request_id, report_xml, diagnostic_xml),
            normalized_response=normalized,
        )

    def _extract_signature_intact(self, root: ET.Element) -> bool | None:
        """Check if the cryptographic signature is intact."""
        # Dokobit structure: SignatureValidationReport > SignatureValidationStatus > MainIndication
        for tag_path in [
            ".//vr:SignatureValidationStatus", ".//SignatureValidationStatus",
            ".//vr:SAV", ".//SAV",
            ".//vr:SignatureValue", ".//SignatureValue",
        ]:
            ns = _NS if "vr:" in tag_path else {}
            el = root.find(tag_path, ns)
            if el is not None:
                ind = (
                    self._find_text(el, "vr:MainIndication", _NS)
                    or self._find_text(el, "MainIndication", {})
                    or self._find_text(el, "vr:Indication", _NS)
                    or self._find_text(el, "Indication", {})
                )
                if ind:
                    normalized = ind.rsplit(":", 1)[-1].upper().replace("-", "_")
                    return normalized in ("TOTALPASSED", "TOTAL_PASSED", "PASSED")

        # Fall back to top-level indication
        ind = (
            self._find_text(root, ".//vr:MainIndication", _NS)
            or self._find_text(root, ".//MainIndication", {})
            or self._find_text(root, ".//vr:Indication", _NS)
            or self._find_text(root, ".//Indication", {})
        )
        if ind:
            normalized = ind.rsplit(":", 1)[-1].upper().replace("-", "_")
            return normalized in ("TOTALPASSED", "TOTAL_PASSED", "PASSED")
        return None

    def _extract_certificate(self, root: ET.Element) -> CertificateInfo | None:
        """Extract signer certificate details from the validation report."""
        # Dokobit uses EU TSL namespace for X509SubjectName inside DigitalId
        _TSL_NS = {"ns4": "http://uri.etsi.org/02231/v2#"}

        # Try multiple possible element paths
        cert_paths = [
            ".//vr:Certificate", ".//Certificate",
            ".//vr:SigningCertificate", ".//SigningCertificate",
            ".//vr:CertificateChain/vr:Certificate", ".//CertificateChain/Certificate",
        ]

        for path in cert_paths:
            ns = _NS if "vr:" in path else {}
            cert_el = root.find(path, ns)
            if cert_el is not None:
                return self._parse_certificate_element(cert_el)

        # Try Dokobit's SignatureValidator > DigitalId > X509SubjectName
        for dn_path in [
            ".//{http://uri.etsi.org/02231/v2#}X509SubjectName",
            ".//ns4:X509SubjectName",
            ".//X509SubjectName",
        ]:
            ns = _TSL_NS if "ns4:" in dn_path else {}
            el = root.find(dn_path, ns)
            if el is not None and el.text:
                dn = el.text.strip()
                cn = self._extract_dn_field(dn, "CN")
                org = self._extract_dn_field(dn, "O")
                return CertificateInfo(common_name=cn, organization=org)

        # Try generic SubjectDistinguishedName
        subject_dn = self._find_text(root, ".//vr:SubjectDistinguishedName", _NS)
        if not subject_dn:
            subject_dn = self._find_text(root, ".//SubjectDistinguishedName", {})
        if subject_dn:
            cn = self._extract_dn_field(subject_dn, "CN")
            org = self._extract_dn_field(subject_dn, "O")
            return CertificateInfo(common_name=cn, organization=org)

        return None

    def _parse_certificate_element(self, cert_el: ET.Element) -> CertificateInfo:
        """Parse a Certificate XML element into CertificateInfo."""
        cn = self._find_text(cert_el, "vr:CommonName", _NS)
        if not cn:
            cn = self._find_text(cert_el, "CommonName", {})
        if not cn:
            # Try DN parsing
            dn = self._find_text(cert_el, "vr:SubjectDistinguishedName", _NS)
            if not dn:
                dn = self._find_text(cert_el, "SubjectDistinguishedName", {})
            if dn:
                cn = self._extract_dn_field(dn, "CN")

        serial = self._find_text(cert_el, "vr:SerialNumber", _NS)
        if not serial:
            serial = self._find_text(cert_el, "SerialNumber", {})

        org = self._find_text(cert_el, "vr:Organization", _NS)
        if not org:
            org = self._find_text(cert_el, "Organization", {})
            if not org:
                dn = self._find_text(cert_el, "vr:SubjectDistinguishedName", _NS)
                if not dn:
                    dn = self._find_text(cert_el, "SubjectDistinguishedName", {})
                if dn:
                    org = self._extract_dn_field(dn, "O")

        issuer = self._find_text(cert_el, "vr:Issuer", _NS)
        if not issuer:
            issuer = self._find_text(cert_el, "Issuer", {})
            if not issuer:
                issuer_dn = self._find_text(cert_el, "vr:IssuerDistinguishedName", _NS)
                if not issuer_dn:
                    issuer_dn = self._find_text(cert_el, "IssuerDistinguishedName", {})
                if issuer_dn:
                    issuer = self._extract_dn_field(issuer_dn, "CN") or issuer_dn

        valid_from = self._parse_datetime(
            self._find_text(cert_el, "vr:NotBefore", _NS)
            or self._find_text(cert_el, "NotBefore", {})
        )
        valid_to = self._parse_datetime(
            self._find_text(cert_el, "vr:NotAfter", _NS)
            or self._find_text(cert_el, "NotAfter", {})
        )

        # Check if certificate is qualified
        qualified_text = self._find_text(cert_el, "vr:QualifiedCertificate", _NS)
        if not qualified_text:
            qualified_text = self._find_text(cert_el, "QualifiedCertificate", {})
        is_qualified = None
        if qualified_text is not None:
            is_qualified = qualified_text.lower() in ("true", "yes", "1")

        return CertificateInfo(
            common_name=cn,
            serial_number=serial,
            organization=org,
            issuer=issuer,
            valid_from=valid_from,
            valid_to=valid_to,
            is_qualified=is_qualified,
        )

    def _extract_timestamp(self, root: ET.Element) -> TimestampInfo:
        """Extract timestamp verification details from the report."""
        ts_paths = [
            ".//vr:Timestamp", ".//Timestamp",
            ".//vr:TimestampValidation", ".//TimestampValidation",
        ]

        for path in ts_paths:
            ns = _NS if "vr:" in path else {}
            ts_el = root.find(path, ns)
            if ts_el is not None:
                return self._parse_timestamp_element(ts_el)

        return TimestampInfo(status=TimestampStatus.MISSING)

    def _parse_timestamp_element(self, ts_el: ET.Element) -> TimestampInfo:
        """Parse a Timestamp XML element into TimestampInfo."""
        indication = self._find_text(ts_el, "vr:Indication", _NS)
        if not indication:
            indication = self._find_text(ts_el, "Indication", {})

        ts_time_str = (
            self._find_text(ts_el, "vr:ProductionTime", _NS)
            or self._find_text(ts_el, "ProductionTime", {})
            or self._find_text(ts_el, "vr:SigningTime", _NS)
            or self._find_text(ts_el, "SigningTime", {})
        )
        ts_time = self._parse_datetime(ts_time_str)

        authority = (
            self._find_text(ts_el, "vr:SignedBy", _NS)
            or self._find_text(ts_el, "SignedBy", {})
            or self._find_text(ts_el, "vr:TSAName", _NS)
            or self._find_text(ts_el, "TSAName", {})
        )

        qualified_text = (
            self._find_text(ts_el, "vr:QualifiedTimestamp", _NS)
            or self._find_text(ts_el, "QualifiedTimestamp", {})
        )
        is_qualified = None
        if qualified_text is not None:
            is_qualified = qualified_text.lower() in ("true", "yes", "1")

        if indication:
            upper = indication.upper()
            if upper in ("PASSED", "TOTAL_PASSED"):
                status = TimestampStatus.QUALIFIED if is_qualified else TimestampStatus.VALID
            elif upper in ("FAILED", "TOTAL_FAILED"):
                status = TimestampStatus.INVALID
            else:
                status = TimestampStatus.VALID
        else:
            status = TimestampStatus.MISSING

        return TimestampInfo(
            status=status,
            time=ts_time,
            authority=authority,
            is_qualified=is_qualified,
        )

    # ── Private: Helpers ────────────────────────────────────────────────

    @staticmethod
    def _find_text(element: ET.Element, path: str, ns: dict[str, str]) -> str | None:
        """Find text content of an XML element, or None."""
        el = element.find(path, ns)
        if el is not None and el.text:
            return el.text.strip()
        return None

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Parse an ISO 8601 datetime string."""
        if not value:
            return None
        try:
            # Handle common formats: 2024-01-15T10:30:00Z, 2024-01-15T10:30:00+00:00
            value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _extract_dn_field(dn: str, field: str) -> str | None:
        """Extract a field from a Distinguished Name string (e.g., CN=...)."""
        for part in dn.split(","):
            part = part.strip()
            if part.upper().startswith(f"{field.upper()}="):
                return part.split("=", 1)[1].strip()
        return None

    @staticmethod
    def _map_indication(
        indication: str | None,
        sub_indication: str | None,
    ) -> VerificationStatus:
        """Map ETSI EN 319 102-1 indication/sub-indication to our status.

        Dokobit uses URN-style values such as:
          - urn:cef:dss:mainindication:totalPassed
          - urn:cef:dss:mainindication:totalFailed
          - urn:cef:dss:mainindication:indeterminate
          - urn:cef:dss:mainindication:noSignatureFound
        We normalize by extracting the trailing segment and uppercasing.
        """
        if not indication:
            return VerificationStatus.INDETERMINATE

        # Normalize: extract last segment of URN if present
        normalized = indication.rsplit(":", 1)[-1] if ":" in indication else indication
        upper = normalized.upper().replace("-", "_")

        if upper in ("TOTALPASSED", "TOTAL_PASSED", "PASSED"):
            return VerificationStatus.VERIFIED

        if upper in ("NOSIGNATUREFOUND", "NO_SIGNATURE_FOUND"):
            return VerificationStatus.FAILED

        if upper in ("TOTALFAILED", "TOTAL_FAILED", "FAILED"):
            if sub_indication:
                sub_norm = sub_indication.rsplit(":", 1)[-1].upper().replace("-", "_")
                if "EXPIRED" in sub_norm or "NOT_YET_VALID" in sub_norm:
                    return VerificationStatus.EXPIRED
                if "REVOKED" in sub_norm:
                    return VerificationStatus.REVOKED
            return VerificationStatus.FAILED

        if upper == "INDETERMINATE":
            if sub_indication:
                sub_norm = sub_indication.rsplit(":", 1)[-1].upper().replace("-", "_")
                if "EXPIRED" in sub_norm:
                    return VerificationStatus.EXPIRED
                if "REVOKED" in sub_norm:
                    return VerificationStatus.REVOKED
            return VerificationStatus.INDETERMINATE

        return VerificationStatus.INDETERMINATE

    @staticmethod
    def _build_evidence(
        request_id: str,
        report_xml: bytes,
        diagnostic_xml: bytes | None,
    ) -> list[EvidenceArtifact]:
        """Build evidence artifacts from raw XML responses."""
        artifacts = [
            EvidenceArtifact(
                evidence_type="validation_report",
                data=report_xml,
                content_type="application/xml",
                filename_hint=f"dokobit_validation_report_{request_id}.xml",
            ),
        ]
        if diagnostic_xml:
            artifacts.append(
                EvidenceArtifact(
                    evidence_type="diagnostic_data",
                    data=diagnostic_xml,
                    content_type="application/xml",
                    filename_hint=f"dokobit_diagnostic_data_{request_id}.xml",
                ),
            )
        return artifacts
