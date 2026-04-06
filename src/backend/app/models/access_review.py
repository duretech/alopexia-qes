"""Access review model for periodic access certification."""

from sqlalchemy import (
    Column, String, Text, ForeignKey, DateTime, Index, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base, TenantScopedMixin, TimestampMixin, generate_uuid


class AccessReview(Base, TenantScopedMixin, TimestampMixin):
    """
    Periodic access review / certification record.
    Tracks who reviewed which user's access and the decision made.

    Immutable fields: id, tenant_id, target_user_id, target_user_type,
                      reviewer_id, review_period_start, review_period_end, created_at
    Mutable fields: decision, decision_at, notes
    Retention: retained for audit trail period
    """
    __tablename__ = "access_reviews"
    __table_args__ = (
        Index("ix_access_review_tenant_period", "tenant_id", "review_period_end"),
        Index("ix_access_review_target", "tenant_id", "target_user_type", "target_user_id"),
        CheckConstraint(
            "decision IN ('approved','revoked','modified','pending')",
            name="ck_access_review_decision",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    target_user_id = Column(UUID(as_uuid=True), nullable=False, comment="Immutable — user being reviewed")
    target_user_type = Column(
        String(50), nullable=False,
        comment="Immutable — doctor, pharmacy_user, admin_user, auditor",
    )
    reviewer_id = Column(UUID(as_uuid=True), nullable=False, comment="Immutable — admin performing review")
    review_period_start = Column(DateTime(timezone=True), nullable=False)
    review_period_end = Column(DateTime(timezone=True), nullable=False)

    # Review outcome
    decision = Column(String(20), nullable=False, default="pending")
    decision_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    access_changes_made = Column(
        JSONB, nullable=True,
        comment="Description of access changes if decision was 'modified' or 'revoked'",
    )
