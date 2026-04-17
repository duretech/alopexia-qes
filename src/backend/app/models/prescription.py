"""Prescription and PrescriptionMetadata models."""

from sqlalchemy import (
    Column, String, Boolean, Text, ForeignKey, DateTime, Integer,
    UniqueConstraint, Index, CheckConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, generate_uuid


class Prescription(Base, TenantScopedMixin, TimestampMixin, SoftDeleteMixin):
    """
    Core prescription record. Represents a signed prescription that has been
    uploaded into the platform.

    Immutable fields: id, tenant_id, doctor_id, patient_id, upload_checksum,
                      idempotency_key, created_at
    Mutable fields: status, verification_status, assigned_pharmacy_user_id,
                    dispensing_status, updated_at
    Encryption-sensitive: none directly (linked to patient PII via patient_id)
    Retention: REQUIRES CONFIRMATION BY SPANISH HEALTHCARE / PHARMA COUNSEL
               Default assumption: 5 years from dispensing date (conservative)
    """
    __tablename__ = "prescriptions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_rx_tenant_idempotency"),
        Index("ix_rx_tenant_status", "tenant_id", "status"),
        Index("ix_rx_tenant_doctor", "tenant_id", "doctor_id"),
        Index("ix_rx_tenant_patient", "tenant_id", "patient_id"),
        Index("ix_rx_tenant_pharmacy", "tenant_id", "assigned_pharmacy_user_id"),
        CheckConstraint(
            "status IN ('draft','pending_verification','verified','failed_verification',"
            "'manual_review','available','dispensed','cancelled','revoked','expired')",
            name="ck_rx_status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    doctor_id = Column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="RESTRICT"),
        nullable=False, index=True,
        comment="Immutable — doctor who uploaded this prescription",
    )
    patient_id = Column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=True, index=True,
        comment="Patient this prescription is for (nullable for clinic-direct uploads)",
    )
    clinic_id = Column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="RESTRICT"),
        nullable=False, index=True,
        comment="Clinic where this prescription originated",
    )
    assigned_pharmacy_user_id = Column(
        UUID(as_uuid=True), ForeignKey("pharmacy_users.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Pharmacy user assigned to dispense",
    )

    # Status tracking
    status = Column(
        String(50), nullable=False, default="pending_verification",
        comment="Current lifecycle status",
    )
    verification_status = Column(
        String(50), nullable=True,
        comment="QTSP verification result: verified, failed, pending, error",
    )
    dispensing_status = Column(
        String(50), nullable=True,
        comment="Dispensing status: pending, dispensed, partially_dispensed, cancelled",
    )

    # Document reference
    upload_checksum = Column(
        String(128), nullable=False,
        comment="Immutable — SHA-256 of uploaded PDF, computed at ingestion",
    )
    document_storage_key = Column(
        String(1000), nullable=False,
        comment="S3 object key for the stored prescription PDF",
    )
    idempotency_key = Column(
        String(100), nullable=False,
        comment="Immutable — client-provided idempotency key for upload dedup",
    )

    # Prescription metadata from the external system
    prescribed_date = Column(
        DateTime(timezone=True), nullable=True,
        comment="Date the prescription was created in the external system",
    )
    external_prescription_id = Column(
        String(500), nullable=True,
        comment="Reference ID from the external prescription system",
    )

    # Cancellation / revocation
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(UUID(as_uuid=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    # Retention
    retention_expires_at = Column(
        DateTime(timezone=True), nullable=True,
        comment="Computed retention expiry — null means indefinite or not yet calculated",
    )
    is_under_legal_hold = Column(
        Boolean, nullable=False, default=False, server_default=text("FALSE"),
        comment="Legal hold overrides retention expiry",
    )

    # Relationships
    metadata_record = relationship(
        "PrescriptionMetadata", back_populates="prescription",
        uselist=False, lazy="selectin",
    )
    documents = relationship("UploadedDocument", back_populates="prescription", lazy="selectin")
    verification_results = relationship(
        "SignatureVerificationResult", back_populates="prescription", lazy="selectin",
    )
    evidence_files = relationship("EvidenceFile", back_populates="prescription", lazy="selectin")


class PrescriptionMetadata(Base, TenantScopedMixin, TimestampMixin):
    """
    Extended metadata for a prescription, extracted from the document or
    provided by the doctor at upload time.

    Immutable fields: id, tenant_id, prescription_id, created_at
    Mutable fields: medication, dosage, duration, notes, etc.
    Encryption-sensitive: medication, dosage (health data context)
    Retention: same as parent prescription
    """
    __tablename__ = "prescription_metadata"
    __table_args__ = (
        UniqueConstraint("prescription_id", name="uq_rx_meta_prescription"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    prescription_id = Column(
        UUID(as_uuid=True), ForeignKey("prescriptions.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="Immutable — parent prescription",
    )
    medication_name = Column(
        Text, nullable=True,
        comment="ENCRYPTION_SENSITIVE — prescribed medication name",
    )
    dosage = Column(
        Text, nullable=True,
        comment="ENCRYPTION_SENSITIVE — prescribed dosage",
    )
    treatment_duration = Column(
        String(200), nullable=True,
        comment="Treatment duration as specified",
    )
    instructions = Column(
        Text, nullable=True,
        comment="ENCRYPTION_SENSITIVE — additional prescribing instructions",
    )
    is_compounded = Column(
        Boolean, nullable=False, default=True,
        comment="Whether this is a formulacion magistral (compounded medicine)",
    )
    formulation_details = Column(
        JSONB, nullable=True,
        comment="Compounding formulation details if applicable",
    )
    formulation_registration_number = Column(
        String(200), nullable=True,
        comment="Formulario Nacional / registration number for the formulation",
    )
    additional_metadata = Column(
        JSONB, nullable=False, default=dict, server_default="{}",
        comment="Extensible metadata fields",
    )

    # Relationships
    prescription = relationship("Prescription", back_populates="metadata_record")
