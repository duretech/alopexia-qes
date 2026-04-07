"""Authorization service — RBAC + ABAC policy enforcement.

Public API:
    Permission          — Enum of all granular permissions
    has_permission()    — Check if a role has a permission (RBAC)
    evaluate_policy()   — Full ABAC policy evaluation
    check_tenant_access() — Tenant isolation check
    require_permission  — FastAPI dependency for permission-gated endpoints
    require_role        — FastAPI dependency for role-gated endpoints
"""

from app.services.authz.rbac import Permission, has_permission, get_role_permissions

__all__ = [
    "Permission",
    "has_permission",
    "get_role_permissions",
]
