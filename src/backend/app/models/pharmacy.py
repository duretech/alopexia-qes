"""Pharmacy and dispensing event models."""

from sqlalchemy import (
    Column, String, Text, ForeignKey, DateTime, Index, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TenantScopedMixin, TimestampMixin, generate_uuid


class PharmacyEvent(Base, TenantScopedMixin, TimestampMixin):
    """
    Events recorded by pharmacy users against a prescription.
    Examples: prescription viewed, PDF downloaded, notes added.

    Immutable fields: ALL — pharmacy events are audit records
    Encryption-sensitive: none
    Retention: same as parent prescription
    """
    __tablename__ = "pharmacy_events"
    __table_args__ = (
        Index("ix_pharma_evt_tenant_rx", "tenant_id", "prescription_id"),
        Index("ix_pharma_evt_tenant_user", "tenant_id", "pharmacy_user_id"),
        CheckConstraint(
            "event_type IN ('viewed','downloaded','notes_added','status_updated',"
            "'formulation_registered','returned','flagged','other')",
            name="ck_pharma_evt_type",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    prescription_id = Column(
        UUID(as_uuid=True), ForeignKey("prescriptions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    pharmacy_user_id = Column(
        UUID(as_uuid=True), ForeignKey("pharmacy_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type = Column(String(50), nullable=False, comment="Type of pharmacy event")
    event_detail = Column(Text, nullable=True, comment="Additional event context")
    event_timestamp = Column(
        DateTime(timezone=True), nullable=False,
        comment="When the event occurred (server-side UTC)",
    )
    source_ip = Column(String(45), nullable=True, comment="IP address of the request")
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")


class DispensingEvent(Base, TenantScopedMixin, TimestampMixin):
    """
    Records the dispensing of a prescription by a pharmacy.
    Includes compounding formulation registration number where relevant.

    Immutable fields: ALL — dispensing events are legal records
    Encryption-sensitive: none directly (linked to patient via prescription)
    Retention: REQUIRES CONFIRMATION BY SPANISH HEALTHCARE / PHARMA COUNSEL
               Default assumption: 5 years minimum
    """
    __tablename__ = "dispensing_events"
    __table_args__ = (
        Index("ix_disp_evt_tenant_rx", "tenant_id", "prescription_id"),
        CheckConstraint(
            "dispensing_status IN ('dispensed','partially_dispensed','cancelled','returned')",
            name="ck_disp_status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    prescription_id = Column(
        UUID(as_uuid=True), ForeignKey("prescriptions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    pharmacy_user_id = Column(
        UUID(as_uuid=True), ForeignKey("pharmacy_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dispensing_status = Column(
        String(50), nullable=False,
        comment="Dispensing outcome",
    )
    dispensed_at = Column(
        DateTime(timezone=True), nullable=False,
        comment="Timestamp of dispensing confirmation (server-side UTC)",
    )

    # Compounded medicine traceability
    formulation_registration_number = Column(
        String(200), nullable=True,
        comment="Formulario Nacional registration number for compounded medicine",
    )
    batch_number = Column(String(200), nullable=True, comment="Pharmacy batch/lot number")
    quantity_dispensed = Column(String(200), nullable=True, comment="Quantity dispensed (free text)")

    notes = Column(Text, nullable=True, comment="Pharmacist notes")
    source_ip = Column(String(45), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
