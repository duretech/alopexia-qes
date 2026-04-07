"""Pydantic schemas for admin and compliance endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ── Audit Export ─────────────────────────────────────────────────────────

class AuditExportRequest(BaseModel):
    """Parameters for audit event export."""
    model_config = ConfigDict(extra="forbid")

    start_date: datetime | None = None
    end_date: datetime | None = None
    event_types: list[str] | None = None
    tenant_id: UUID | None = None


# ── Legal Hold ───────────────────────────────────────────────────────────

class LegalHoldCreateRequest(BaseModel):
    """Request to place a legal hold on a resource."""
    model_config = ConfigDict(extra="forbid")

    target_type: str = Field(..., max_length=100)
    target_id: UUID
    reason: str = Field(..., min_length=1)
    reference_number: str | None = Field(default=None, max_length=200)


class LegalHoldResponse(BaseModel):
    """Response for a legal hold."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_type: str
    target_id: UUID
    reason: str
    reference_number: str | None = None
    placed_by: UUID
    placed_at: datetime
    is_active: bool
    released_by: UUID | None = None
    released_at: datetime | None = None


class LegalHoldReleaseRequest(BaseModel):
    """Request to release a legal hold."""
    model_config = ConfigDict(extra="forbid")

    release_reason: str = Field(..., min_length=1)


# ── Deletion Request ─────────────────────────────────────────────────────

class DeletionRequestCreate(BaseModel):
    """Request to initiate a deletion workflow."""
    model_config = ConfigDict(extra="forbid")

    target_type: str = Field(..., max_length=100)
    target_id: UUID
    deletion_type: str = Field(
        ..., pattern="^(soft|hard|cryptographic_erase)$",
    )
    reason: str = Field(..., min_length=1)
    legal_basis: str | None = Field(default=None, max_length=500)


class DeletionRequestResponse(BaseModel):
    """Response for a deletion request."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_type: str
    target_id: UUID
    deletion_type: str
    reason: str
    status: str
    requested_by: UUID
    requested_at: datetime


class DeletionApprovalRequest(BaseModel):
    """Request to approve a deletion."""
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(..., pattern="^(approve|reject)$")
    reason: str | None = None


# ── Manual Review ────────────────────────────────────────────────────────

class ManualReviewDecision(BaseModel):
    """Decision on a verification that requires manual review."""
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(..., pattern="^(accept|reject|escalate)$")
    notes: str | None = None
