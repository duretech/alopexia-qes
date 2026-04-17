"""Role-Based Access Control (RBAC) permission matrix.

Defines the complete mapping from roles to permissions. Every endpoint
in the system requires one or more permissions. The RBAC layer is the
first gate — if the role doesn't have the permission, access is denied
before ABAC evaluation.

Roles are defined in docs/architecture.md §5. Permissions are granular
actions on specific resource types.

Implements C-AUTHZ-01 from the controls catalog.
"""

from enum import StrEnum

from app.services.auth.models import Role


class Permission(StrEnum):
    """Granular permissions — one per action type per resource.

    Naming convention: RESOURCE_ACTION (e.g., PRESCRIPTION_UPLOAD).
    """

    # ── Prescription ──────────────────────────────────────────────────────
    PRESCRIPTION_UPLOAD = "prescription:upload"
    PRESCRIPTION_VIEW_OWN = "prescription:view_own"
    PRESCRIPTION_VIEW_CLINIC = "prescription:view_clinic"
    PRESCRIPTION_VIEW_ASSIGNED = "prescription:view_assigned"
    PRESCRIPTION_VIEW_ALL = "prescription:view_all"
    PRESCRIPTION_REVOKE_OWN = "prescription:revoke_own"
    PRESCRIPTION_REVOKE_ANY = "prescription:revoke_any"

    # ── Document ──────────────────────────────────────────────────────────
    DOCUMENT_DOWNLOAD = "document:download"
    DOCUMENT_VIEW_METADATA = "document:view_metadata"

    # ── Verification ──────────────────────────────────────────────────────
    VERIFICATION_VIEW = "verification:view"
    VERIFICATION_MANUAL_REVIEW = "verification:manual_review"

    # ── Pharmacy ──────────────────────────────────────────────────────────
    PHARMACY_VIEW_PRESCRIPTIONS = "pharmacy:view_prescriptions"
    PHARMACY_CONFIRM_DISPENSING = "pharmacy:confirm_dispensing"
    PHARMACY_RECORD_EVENT = "pharmacy:record_event"

    # ── Evidence ──────────────────────────────────────────────────────────
    EVIDENCE_VIEW = "evidence:view"
    EVIDENCE_EXPORT = "evidence:export"

    # ── User management ───────────────────────────────────────────────────
    USER_VIEW_CLINIC = "user:view_clinic"
    USER_MANAGE_CLINIC = "user:manage_clinic"
    USER_VIEW_TENANT = "user:view_tenant"
    USER_MANAGE_TENANT = "user:manage_tenant"
    USER_SUSPEND = "user:suspend"

    # ── Tenant management ─────────────────────────────────────────────────
    TENANT_VIEW_CONFIG = "tenant:view_config"
    TENANT_MANAGE_CONFIG = "tenant:manage_config"
    TENANT_CREATE = "tenant:create"

    # ── Audit ─────────────────────────────────────────────────────────────
    AUDIT_VIEW_CLINIC = "audit:view_clinic"
    AUDIT_VIEW_TENANT = "audit:view_tenant"
    AUDIT_VIEW_ALL = "audit:view_all"
    AUDIT_EXPORT = "audit:export"
    AUDIT_VERIFY_INTEGRITY = "audit:verify_integrity"

    # ── Retention ─────────────────────────────────────────────────────────
    RETENTION_VIEW = "retention:view"
    RETENTION_MANAGE = "retention:manage"
    RETENTION_REQUEST_DELETION = "retention:request_deletion"
    RETENTION_APPROVE_DELETION = "retention:approve_deletion"
    RETENTION_MANAGE_LEGAL_HOLD = "retention:manage_legal_hold"

    # ── Incident ──────────────────────────────────────────────────────────
    INCIDENT_VIEW = "incident:view"
    INCIDENT_MANAGE = "incident:manage"

    # ── System / admin ────────────────────────────────────────────────────
    SYSTEM_VIEW_HEALTH = "system:view_health"
    SYSTEM_MANAGE_CONFIG = "system:manage_config"
    BREAK_GLASS_ACTIVATE = "break_glass:activate"


# ── Role → Permission matrix ─────────────────────────────────────────────
# This is the authoritative RBAC mapping. Changes here affect the entire
# system's access model. Review changes with the security architect.

_ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.DOCTOR: frozenset({
        Permission.PRESCRIPTION_UPLOAD,
        Permission.PRESCRIPTION_VIEW_OWN,
        Permission.PRESCRIPTION_REVOKE_OWN,
        Permission.DOCUMENT_VIEW_METADATA,
        Permission.VERIFICATION_VIEW,
    }),

    Role.PHARMACY_USER: frozenset({
        Permission.PRESCRIPTION_VIEW_ASSIGNED,
        Permission.DOCUMENT_DOWNLOAD,
        Permission.DOCUMENT_VIEW_METADATA,
        Permission.VERIFICATION_VIEW,
        Permission.EVIDENCE_VIEW,
        Permission.PHARMACY_VIEW_PRESCRIPTIONS,
        Permission.PHARMACY_CONFIRM_DISPENSING,
        Permission.PHARMACY_RECORD_EVENT,
    }),

    Role.CLINIC_ADMIN: frozenset({
        Permission.PRESCRIPTION_VIEW_CLINIC,
        Permission.DOCUMENT_VIEW_METADATA,
        Permission.VERIFICATION_VIEW,
        Permission.USER_VIEW_CLINIC,
        Permission.USER_MANAGE_CLINIC,
        Permission.AUDIT_VIEW_CLINIC,
    }),

    Role.TENANT_ADMIN: frozenset({
        Permission.PRESCRIPTION_VIEW_ALL,
        Permission.DOCUMENT_VIEW_METADATA,
        Permission.DOCUMENT_DOWNLOAD,
        Permission.VERIFICATION_VIEW,
        Permission.VERIFICATION_MANUAL_REVIEW,
        Permission.EVIDENCE_VIEW,
        Permission.EVIDENCE_EXPORT,
        Permission.USER_VIEW_TENANT,
        Permission.USER_MANAGE_TENANT,
        Permission.USER_SUSPEND,
        Permission.TENANT_VIEW_CONFIG,
        Permission.TENANT_MANAGE_CONFIG,
        Permission.AUDIT_VIEW_TENANT,
        Permission.AUDIT_EXPORT,
        Permission.AUDIT_VERIFY_INTEGRITY,
        Permission.RETENTION_VIEW,
        Permission.RETENTION_MANAGE,
        Permission.RETENTION_REQUEST_DELETION,
        Permission.RETENTION_APPROVE_DELETION,
        Permission.RETENTION_MANAGE_LEGAL_HOLD,
        Permission.INCIDENT_VIEW,
        Permission.INCIDENT_MANAGE,
        Permission.SYSTEM_VIEW_HEALTH,
    }),

    Role.COMPLIANCE_OFFICER: frozenset({
        Permission.PRESCRIPTION_VIEW_ALL,
        Permission.DOCUMENT_VIEW_METADATA,
        Permission.DOCUMENT_DOWNLOAD,
        Permission.VERIFICATION_VIEW,
        Permission.VERIFICATION_MANUAL_REVIEW,
        Permission.EVIDENCE_VIEW,
        Permission.EVIDENCE_EXPORT,
        Permission.USER_VIEW_TENANT,
        Permission.USER_SUSPEND,
        Permission.AUDIT_VIEW_TENANT,
        Permission.AUDIT_EXPORT,
        Permission.AUDIT_VERIFY_INTEGRITY,
        Permission.RETENTION_VIEW,
        Permission.RETENTION_MANAGE,
        Permission.RETENTION_APPROVE_DELETION,
        Permission.RETENTION_MANAGE_LEGAL_HOLD,
        Permission.INCIDENT_VIEW,
        Permission.INCIDENT_MANAGE,
        Permission.SYSTEM_VIEW_HEALTH,
    }),

    Role.PLATFORM_ADMIN: frozenset({
        Permission.PRESCRIPTION_VIEW_ALL,
        Permission.PRESCRIPTION_REVOKE_ANY,
        Permission.DOCUMENT_VIEW_METADATA,
        Permission.DOCUMENT_DOWNLOAD,
        Permission.VERIFICATION_VIEW,
        Permission.VERIFICATION_MANUAL_REVIEW,
        Permission.USER_VIEW_TENANT,
        Permission.USER_MANAGE_TENANT,
        Permission.USER_SUSPEND,
        Permission.TENANT_VIEW_CONFIG,
        Permission.TENANT_MANAGE_CONFIG,
        Permission.TENANT_CREATE,
        Permission.AUDIT_VIEW_ALL,
        Permission.AUDIT_EXPORT,
        Permission.AUDIT_VERIFY_INTEGRITY,
        Permission.RETENTION_VIEW,
        Permission.RETENTION_MANAGE,
        Permission.RETENTION_REQUEST_DELETION,
        Permission.RETENTION_APPROVE_DELETION,
        Permission.RETENTION_MANAGE_LEGAL_HOLD,
        Permission.INCIDENT_VIEW,
        Permission.INCIDENT_MANAGE,
        Permission.SYSTEM_VIEW_HEALTH,
        Permission.SYSTEM_MANAGE_CONFIG,
        Permission.BREAK_GLASS_ACTIVATE,
    }),

    Role.AUDITOR: frozenset({
        Permission.PRESCRIPTION_VIEW_ALL,
        Permission.DOCUMENT_VIEW_METADATA,
        Permission.DOCUMENT_DOWNLOAD,
        Permission.VERIFICATION_VIEW,
        Permission.EVIDENCE_VIEW,
        Permission.EVIDENCE_EXPORT,
        Permission.AUDIT_VIEW_ALL,
        Permission.AUDIT_EXPORT,
        Permission.AUDIT_VERIFY_INTEGRITY,
        Permission.RETENTION_VIEW,
        Permission.INCIDENT_VIEW,
    }),

    Role.SUPPORT: frozenset({
        Permission.PRESCRIPTION_VIEW_ALL,
        Permission.DOCUMENT_VIEW_METADATA,
        Permission.VERIFICATION_VIEW,
        Permission.USER_VIEW_TENANT,
        Permission.SYSTEM_VIEW_HEALTH,
        # NOTE: Support has no PHI access (no DOCUMENT_DOWNLOAD) without break-glass
        Permission.BREAK_GLASS_ACTIVATE,
    }),
}


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission.

    This is a pure lookup — no database access. Returns False for
    unknown roles.
    """
    perms = _ROLE_PERMISSIONS.get(role, frozenset())
    return permission in perms


def get_role_permissions(role: Role) -> frozenset[Permission]:
    """Get all permissions for a role. Returns empty set for unknown roles."""
    return _ROLE_PERMISSIONS.get(role, frozenset())
