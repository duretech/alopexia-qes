"""Attribute-Based Access Control (ABAC) policy evaluator.

ABAC supplements RBAC by evaluating contextual attributes beyond the role.
A request must pass BOTH the RBAC permission check AND the ABAC policy
evaluation to be authorized.

Policy dimensions (from docs/architecture.md §6):
  - actor.role, actor.tenant_id, actor.clinic_id
  - resource.tenant_id, resource.clinic_id, resource.owner_id
  - action.type, action.sensitivity
  - context.ip_address, context.mfa_verified, context.break_glass

Policy evaluation is a pure function — no database access. The caller
provides the pre-fetched attributes.

Implements C-AUTHZ-02 from the controls catalog.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.services.auth.models import AuthenticatedUser, Role
from app.services.authz.rbac import Permission, has_permission

logger = get_logger(component="abac")


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class DenyReason(StrEnum):
    """Machine-readable denial reasons for audit logging."""
    NO_PERMISSION = "no_permission"
    TENANT_MISMATCH = "tenant_mismatch"
    CLINIC_MISMATCH = "clinic_mismatch"
    NOT_OWNER = "not_owner"
    MFA_REQUIRED = "mfa_required"
    BREAK_GLASS_REQUIRED = "break_glass_required"
    ACCOUNT_INACTIVE = "account_inactive"
    RESOURCE_DELETED = "resource_deleted"


@dataclass(frozen=True)
class ResourceContext:
    """Attributes of the resource being accessed.

    Populated by the service layer before policy evaluation.
    """
    tenant_id: UUID | None = None
    clinic_id: UUID | None = None
    owner_id: UUID | None = None
    is_deleted: bool = False
    sensitivity: str = "normal"  # normal, sensitive, highly_sensitive


@dataclass(frozen=True)
class PolicyResult:
    """Result of an ABAC policy evaluation."""
    decision: PolicyDecision
    reason: DenyReason | None = None
    detail: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision == PolicyDecision.ALLOW


def evaluate_policy(
    *,
    actor: AuthenticatedUser,
    permission: Permission,
    resource: ResourceContext | None = None,
    require_mfa: bool = False,
) -> PolicyResult:
    """Evaluate the full RBAC + ABAC policy for an action.

    Evaluation order (fail-fast):
      1. RBAC: Does the actor's role have the required permission?
      2. Tenant isolation: Does the actor belong to the resource's tenant?
      3. Clinic scoping: For clinic-scoped actions, does the actor's clinic match?
      4. Ownership: For owner-scoped actions, is the actor the resource owner?
      5. MFA: For sensitive actions, was MFA verified?
      6. Resource state: Is the resource still active (not soft-deleted)?

    Break-glass overrides steps 3-4 but NOT steps 1-2 (tenant isolation
    is never bypassed, even under break-glass).

    Args:
        actor: The authenticated user requesting access.
        permission: The permission being requested.
        resource: Attributes of the resource being accessed (None for non-resource actions).
        require_mfa: Whether this action requires MFA verification.

    Returns:
        PolicyResult with decision and reason.
    """
    # 1. RBAC check
    if not has_permission(actor.role, permission):
        return PolicyResult(
            decision=PolicyDecision.DENY,
            reason=DenyReason.NO_PERMISSION,
            detail=f"Role '{actor.role}' does not have permission '{permission}'",
        )

    # If no resource context, RBAC alone is sufficient
    if resource is None:
        if require_mfa and not actor.mfa_verified:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=DenyReason.MFA_REQUIRED,
                detail="MFA verification required for this action",
            )
        return PolicyResult(decision=PolicyDecision.ALLOW)

    # 2. Tenant isolation — NEVER bypassed, even under break-glass
    if resource.tenant_id is not None and not actor.is_platform_level:
        if actor.tenant_id != resource.tenant_id:
            logger.error(
                "cross_tenant_access_denied",
                actor_id=str(actor.user_id),
                actor_tenant=str(actor.tenant_id),
                resource_tenant=str(resource.tenant_id),
            )
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=DenyReason.TENANT_MISMATCH,
                detail="Cross-tenant access denied",
            )

    # 3. Resource state check — deny access to deleted resources
    #    (unless the actor has explicit deletion-related permissions)
    if resource.is_deleted and permission not in _DELETION_PERMISSIONS:
        return PolicyResult(
            decision=PolicyDecision.DENY,
            reason=DenyReason.RESOURCE_DELETED,
            detail="Resource has been deleted",
        )

    # Break-glass bypasses clinic scoping and ownership checks
    if actor.is_break_glass:
        if require_mfa and not actor.mfa_verified:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=DenyReason.MFA_REQUIRED,
                detail="MFA verification required even under break-glass",
            )
        return PolicyResult(decision=PolicyDecision.ALLOW)

    # 4. Clinic scoping — for clinic-scoped permissions
    if _is_clinic_scoped(permission) and resource.clinic_id is not None:
        if actor.clinic_id is not None and actor.clinic_id != resource.clinic_id:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=DenyReason.CLINIC_MISMATCH,
                detail="Resource belongs to a different clinic",
            )

    # 5. Ownership — for owner-scoped permissions
    if _is_owner_scoped(permission) and resource.owner_id is not None:
        if actor.user_id != resource.owner_id:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=DenyReason.NOT_OWNER,
                detail="Only the resource owner can perform this action",
            )

    # 6. MFA check
    if require_mfa and not actor.mfa_verified:
        return PolicyResult(
            decision=PolicyDecision.DENY,
            reason=DenyReason.MFA_REQUIRED,
            detail="MFA verification required for this action",
        )

    return PolicyResult(decision=PolicyDecision.ALLOW)


# ── Permission classification helpers ─────────────────────────────────────

# Permissions that imply ownership scope (only the owner can act)
_OWNER_SCOPED_PERMISSIONS = frozenset({
    Permission.PRESCRIPTION_VIEW_OWN,
    Permission.PRESCRIPTION_REVOKE_OWN,
})

# Permissions that imply clinic scope
_CLINIC_SCOPED_PERMISSIONS = frozenset({
    Permission.PRESCRIPTION_VIEW_CLINIC,
    Permission.USER_VIEW_CLINIC,
    Permission.USER_MANAGE_CLINIC,
    Permission.AUDIT_VIEW_CLINIC,
})

# Permissions that are related to deletion (allowed on deleted resources)
_DELETION_PERMISSIONS = frozenset({
    Permission.RETENTION_VIEW,
    Permission.RETENTION_MANAGE,
    Permission.RETENTION_REQUEST_DELETION,
    Permission.RETENTION_APPROVE_DELETION,
    Permission.RETENTION_MANAGE_LEGAL_HOLD,
    Permission.AUDIT_VIEW_ALL,
    Permission.AUDIT_VIEW_TENANT,
})


def _is_owner_scoped(permission: Permission) -> bool:
    return permission in _OWNER_SCOPED_PERMISSIONS


def _is_clinic_scoped(permission: Permission) -> bool:
    return permission in _CLINIC_SCOPED_PERMISSIONS
