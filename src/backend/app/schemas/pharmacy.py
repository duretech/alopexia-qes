"""Pydantic schemas for pharmacy flow endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class PrescriptionListItem(BaseModel):
    """Summary view of a prescription for pharmacy listing."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    verification_status: str | None = None
    dispensing_status: str | None = None
    doctor_id: UUID
    patient_id: UUID
    upload_checksum: str
    prescribed_date: datetime | None = None
    created_at: datetime | None = None


class PrescriptionDetail(PrescriptionListItem):
    """Detailed prescription view with verification results."""
    clinic_id: UUID
    document_storage_key: str
    external_prescription_id: str | None = None


class DocumentDownloadResponse(BaseModel):
    """Response with a signed URL for downloading the prescription PDF."""
    signed_url: str
    expires_in_seconds: int = 300


class ConfirmDispensingRequest(BaseModel):
    """Request body for confirming dispensing."""
    model_config = ConfigDict(extra="forbid")

    dispensing_status: str = Field(
        ...,
        pattern="^(dispensed|partially_dispensed|cancelled|returned)$",
        description="Dispensing outcome",
    )
    formulation_registration_number: str | None = Field(
        default=None,
        max_length=200,
        description="Formulario Nacional registration number",
    )
    batch_number: str | None = Field(
        default=None, max_length=200,
    )
    quantity_dispensed: str | None = Field(
        default=None, max_length=200,
    )
    notes: str | None = None


class DispensingResponse(BaseModel):
    """Response from dispensing confirmation."""
    model_config = ConfigDict(from_attributes=True)

    dispensing_event_id: UUID
    prescription_id: UUID
    dispensing_status: str
    dispensed_at: datetime
