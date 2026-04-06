"""Retention, legal hold, and deletion request models."""

from sqlalchemy import (
    Column, String, Boolean, Text, ForeignKey, DateTime, Integer,
    Index, CheckConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base, TenantScopedMixin, TimestampMixin, generate_uuid


class RetentionSchedule(Base, TenantScopedMixin, TimestampMixin):
    """
    Configurable retention schedule per resource type per tenant.
    Default values are ASSUMPTIONS — legal counsel must confirm actual periods.

    Immutable fields: id, tenant_id, created_at
    Mutable fields: retention_days, is_active, notes
    Retention: retained for platform lifetime
    """
    __tablename__ = "retention_schedules"
    __table_args__ = (
        Index("ix_ret_sched_tenant_resource", "tenant_id", "resource_type", unique=True),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    resource_type = Column(
        String(100), nullable=False,
        comment="Resource type: prescription, audit_event, evidence_file, patient, etc.",
    )
    retention_days = Column(
        Integer, nullable=False,
        comment="Retention period in days from creation/completion — "
                "REQUIRES CONFIRMATION BY SPANISH HEALTHCARE / PHARMA COUNSEL",
    )
    retention_basis = Column(
        String(200), nullable=True,
        comment="Legal basis for this retention period (e.g., 'RD 1718/2010 Art. X')",
    )
    is_active = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True, comment="Admin notes on this schedule")
    is_legal_default = Column(
        Boolean, nullable=False, default=False, server_default=text("FALSE"),
        comment="Whether this is a legally mandated minimum (vs organizational choice)",
    )
    approved_by = Column(UUID(as_uuid=True), nullable=True, comment="Admin who approved this schedule")
    approved_at = Column(DateTime(timezone=True), nullable=True)


class LegalHold(Base, TenantScopedMixin, TimestampMixin):
    """
    Legal hold placed on a resource, preventing deletion regardless of retention schedule.

    Immutable fields: id, tenant_id, target_type, target_id, placed_by, placed_at, created_at
    Mutable fields: is_active, released_by, released_at, reason, notes
    Retention: retained indefinitely (legal record)
    """
    __tablename__ = "legal_holds"
    __table_args__ = (
        Index("ix_legal_hold_target", "tenant_id", "target_type", "target_id"),
        Index("ix_legal_hold_active", "tenant_id", "is_active"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    target_type = Column(
        String(100), nullable=False,
        comment="Immutable — type of resource held: prescription, patient, etc.",
    )
    target_id = Column(
        UUID(as_uuid=True), nullable=False,
        comment="Immutable — ID of the held resource",
    )
    reason = Column(
        Text, nullable=False,
        comment="Legal basis or reason for the hold",
    )
    reference_number = Column(
        String(200), nullable=True,
        comment="External legal reference (case number, etc.)",
    )
    placed_by = Column(
        UUID(as_uuid=True), nullable=False,
        comment="Immutable — admin who placed the hold",
    )
    placed_at = Column(
        DateTime(timezone=True), nullable=False,
        comment="Immutable — when the hold was placed",
    )
    is_active = Column(Boolean, nullable=False, default=True)
    released_by = Column(UUID(as_uuid=True), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    release_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)


class DeletionRequest(Base, TenantScopedMixin, TimestampMixin):
    """
    Tracks requests to delete data. Hard deletes require dual approval.
    Soft deletes are recorded but less restrictive.

    Immutable fields: id, tenant_id, target_type, target_id, requested_by,
                      requested_at, deletion_type, created_at
    Mutable fields: status, approved_by_*, executed_at, rejection_reason
    Retention: retained indefinitely (deletion evidence)
    """
    __tablename__ = "deletion_requests"
    __table_args__ = (
        Index("ix_del_req_tenant_status", "tenant_id", "status"),
        Index("ix_del_req_target", "tenant_id", "target_type", "target_id"),
        CheckConstraint(
            "status IN ('pending_first_approval','pending_second_approval',"
            "'approved','rejected','executed','cancelled')",
            name="ck_del_req_status",
        ),
        CheckConstraint(
            "deletion_type IN ('soft','hard','cryptographic_erase')",
            name="ck_del_req_type",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    target_type = Column(String(100), nullable=False, comment="Immutable — resource type to delete")
    target_id = Column(UUID(as_uuid=True), nullable=False, comment="Immutable — resource ID to delete")
    deletion_type = Column(
        String(30), nullable=False,
        comment="Immutable — soft, hard, or cryptographic_erase",
    )
    reason = Column(Text, nullable=False, comment="Justification for deletion")
    legal_basis = Column(
        String(500), nullable=True,
        comment="Legal basis for deletion (e.g., GDPR Art. 17, retention expiry)",
    )

    # Requester
    requested_by = Column(UUID(as_uuid=True), nullable=False, comment="Immutable")
    requested_at = Column(DateTime(timezone=True), nullable=False, comment="Immutable")

    # Approval workflow (dual approval for hard delete)
    status = Column(String(30), nullable=False, default="pending_first_approval")
    first_approver_id = Column(UUID(as_uuid=True), nullable=True)
    first_approved_at = Column(DateTime(timezone=True), nullable=True)
    second_approver_id = Column(
        UUID(as_uuid=True), nullable=True,
        comment="Required for hard delete — must differ from first approver",
    )
    second_approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(UUID(as_uuid=True), nullable=True)

    # Execution
    executed_at = Column(DateTime(timezone=True), nullable=True)
    execution_evidence = Column(
        JSONB, nullable=True,
        comment="Evidence of deletion (checksums destroyed, objects removed, etc.)",
    )
