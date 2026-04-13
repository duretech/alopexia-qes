"""Pydantic schemas for prescription upload (ingestion) endpoint.

These schemas define the request/response contract for POST /api/v1/prescriptions/upload.
The upload uses multipart/form-data: the PDF as a file part, metadata as JSON form fields.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class PrescriptionUploadMetadata(BaseModel):
    """Metadata sent alongside the PDF upload as a JSON form field.

    Required fields: patient_id, idempotency_key.
    All other fields are optional and can be provided by the doctor
    at upload time or extracted from the PDF later.
    """
    model_config = ConfigDict(extra="forbid")

    patient_id: UUID = Field(
        ...,
        description="UUID of the patient this prescription is for",
    )
    idempotency_key: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Client-provided idempotency key for upload dedup",
    )
    prescribed_date: datetime | None = Field(
        default=None,
        description="Date the prescription was created in the external system",
    )
    external_prescription_id: str | None = Field(
        default=None,
        max_length=500,
        description="Reference ID from the external prescription system",
    )
    medication_name: str | None = Field(
        default=None,
        description="Prescribed medication name (encrypted at rest)",
    )
    dosage: str | None = Field(
        default=None,
        description="Dosage instructions (encrypted at rest)",
    )
    treatment_duration: str | None = Field(
        default=None,
        max_length=200,
        description="Treatment duration as specified",
    )
    instructions: str | None = Field(
        default=None,
        description="Additional prescribing instructions (encrypted at rest)",
    )
    is_compounded: bool = Field(
        default=True,
        description="Whether this is a formulacion magistral",
    )
    formulation_details: dict | None = Field(
        default=None,
        description="Compounding formulation details if applicable",
    )
    formulation_registration_number: str | None = Field(
        default=None,
        max_length=200,
        description="Formulario Nacional / registration number",
    )
    additional_metadata: dict | None = Field(
        default=None,
        description="Extensible metadata fields",
    )


class PrescriptionUploadResponse(BaseModel):
    """Response from a successful prescription upload."""
    model_config = ConfigDict(from_attributes=True)

    prescription_id: UUID
    document_id: UUID
    storage_key: str
    checksum_sha256: str
    file_size_bytes: int
    pdf_version: str | None = None
    estimated_page_count: int | None = None
    scan_status: str
    status: str = "pending_verification"
    verification_status: str | None = None
    verification_id: UUID | None = None


class IngestionErrorResponse(BaseModel):
    """Structured error response for ingestion failures."""
    error_code: str
    message: str
    detail: dict | None = None
