"""Audit event type definitions — the taxonomy for every auditable action.

Every audit event emitted by the system MUST use one of these event types.
Adding a new event type requires updating this enum — this is intentional
to prevent unclassified events from entering the audit trail.

The event types map to the chain of custody model (docs/architecture.md §8),
threat mitigations (docs/threat-model.md), and controls catalog
(docs/controls-catalog.md C-AUDIT-03).
"""

from enum import StrEnum


class AuditEventType(StrEnum):
    """Structured event type identifiers.

    Naming convention: DOMAIN_ACTION (e.g., PRESCRIPTION_UPLOADED).
    All values are lowercase with underscores for JSON compatibility.
    """

    # ── Authentication ────────────────────────────────────────────────────
    AUTH_LOGIN_SUCCESS = "auth.login_success"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_LOGOUT = "auth.logout"
    AUTH_SESSION_CREATED = "auth.session_created"
    AUTH_SESSION_EXPIRED = "auth.session_expired"
    AUTH_SESSION_REVOKED = "auth.session_revoked"
    AUTH_MFA_VERIFIED = "auth.mfa_verified"
    AUTH_MFA_FAILED = "auth.mfa_failed"
    AUTH_ACCOUNT_LOCKED = "auth.account_locked"
    AUTH_ACCOUNT_UNLOCKED = "auth.account_unlocked"

    # ── Authorization ─────────────────────────────────────────────────────
    AUTHZ_ACCESS_GRANTED = "authz.access_granted"
    AUTHZ_ACCESS_DENIED = "authz.access_denied"
    AUTHZ_CROSS_TENANT_DENIED = "authz.cross_tenant_denied"
    AUTHZ_ROLE_CHANGED = "authz.role_changed"
    AUTHZ_PERMISSION_EVALUATED = "authz.permission_evaluated"

    # ── Break-glass ───────────────────────────────────────────────────────
    BREAK_GLASS_ACTIVATED = "break_glass.activated"
    BREAK_GLASS_DEACTIVATED = "break_glass.deactivated"
    BREAK_GLASS_ACTION = "break_glass.action"

    # ── Prescription lifecycle ────────────────────────────────────────────
    PRESCRIPTION_UPLOAD_INITIATED = "prescription.upload_initiated"
    PRESCRIPTION_UPLOADED = "prescription.uploaded"
    PRESCRIPTION_UPLOAD_FAILED = "prescription.upload_failed"
    PRESCRIPTION_DUPLICATE_DETECTED = "prescription.duplicate_detected"
    PRESCRIPTION_STATUS_CHANGED = "prescription.status_changed"
    PRESCRIPTION_REVOKED = "prescription.revoked"

    # ── Document handling ─────────────────────────────────────────────────
    DOCUMENT_STORED = "document.stored"
    DOCUMENT_ACCESSED = "document.accessed"
    DOCUMENT_DOWNLOAD_SIGNED_URL = "document.download_signed_url"
    DOCUMENT_CHECKSUM_VERIFIED = "document.checksum_verified"
    DOCUMENT_CHECKSUM_MISMATCH = "document.checksum_mismatch"
    DOCUMENT_QUARANTINED = "document.quarantined"
    DOCUMENT_SCAN_COMPLETED = "document.scan_completed"

    # ── QTSP verification ─────────────────────────────────────────────────
    VERIFICATION_SUBMITTED = "verification.submitted"
    VERIFICATION_COMPLETED = "verification.completed"
    VERIFICATION_FAILED = "verification.failed"
    VERIFICATION_RETRY = "verification.retry"
    VERIFICATION_MANUAL_REVIEW = "verification.manual_review"
    VERIFICATION_MANUAL_APPROVED = "verification.manual_approved"
    VERIFICATION_MANUAL_REJECTED = "verification.manual_rejected"

    # ── Evidence ──────────────────────────────────────────────────────────
    EVIDENCE_STORED = "evidence.stored"
    EVIDENCE_ACCESSED = "evidence.accessed"
    EVIDENCE_INTEGRITY_VERIFIED = "evidence.integrity_verified"
    EVIDENCE_INTEGRITY_FAILED = "evidence.integrity_failed"

    # ── Pharmacy ──────────────────────────────────────────────────────────
    PHARMACY_PRESCRIPTION_VIEWED = "pharmacy.prescription_viewed"
    PHARMACY_PRESCRIPTION_ACCEPTED = "pharmacy.prescription_accepted"
    PHARMACY_PRESCRIPTION_REJECTED = "pharmacy.prescription_rejected"
    PHARMACY_DISPENSING_CONFIRMED = "pharmacy.dispensing_confirmed"
    PHARMACY_EVENT_RECORDED = "pharmacy.event_recorded"

    # ── Retention / deletion ──────────────────────────────────────────────
    RETENTION_SCHEDULE_APPLIED = "retention.schedule_applied"
    RETENTION_EXPIRED = "retention.expired"
    RETENTION_DELETION_REQUESTED = "retention.deletion_requested"
    RETENTION_DELETION_APPROVED = "retention.deletion_approved"
    RETENTION_DELETION_EXECUTED = "retention.deletion_executed"
    RETENTION_DELETION_DENIED = "retention.deletion_denied"
    RETENTION_LEGAL_HOLD_APPLIED = "retention.legal_hold_applied"
    RETENTION_LEGAL_HOLD_RELEASED = "retention.legal_hold_released"
    RETENTION_CRYPTO_ERASE = "retention.crypto_erase"

    # ── User / tenant management ──────────────────────────────────────────
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DEACTIVATED = "user.deactivated"
    USER_REACTIVATED = "user.reactivated"
    TENANT_CREATED = "tenant.created"
    TENANT_UPDATED = "tenant.updated"
    TENANT_DEACTIVATED = "tenant.deactivated"

    # ── Admin / system ────────────────────────────────────────────────────
    ADMIN_ACTION = "admin.action"
    ADMIN_CONFIG_CHANGED = "admin.config_changed"
    ADMIN_USER_SUSPENDED = "admin.user_suspended"
    ADMIN_FORCE_LOGOUT = "admin.force_logout"

    # ── Audit meta-events (audit about the audit) ─────────────────────────
    AUDIT_EXPORT_STARTED = "audit.export_started"
    AUDIT_EXPORT_COMPLETED = "audit.export_completed"
    AUDIT_INTEGRITY_CHECK_PASSED = "audit.integrity_check_passed"
    AUDIT_INTEGRITY_CHECK_FAILED = "audit.integrity_check_failed"
    AUDIT_GAP_DETECTED = "audit.gap_detected"

    # ── Incident management ───────────────────────────────────────────────
    INCIDENT_CREATED = "incident.created"
    INCIDENT_UPDATED = "incident.updated"
    INCIDENT_RESOLVED = "incident.resolved"

    # ── API / system events ───────────────────────────────────────────────
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    RATE_LIMIT_EXCEEDED = "system.rate_limit_exceeded"


class AuditCategory(StrEnum):
    """Broad categories for audit event classification."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MUTATION = "data_mutation"
    SYSTEM = "system"
    ADMIN = "admin"
    SECURITY = "security"
    COMPLIANCE = "compliance"


class AuditSeverity(StrEnum):
    """Severity levels for audit events."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditOutcome(StrEnum):
    """Possible outcomes for audited actions."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    ERROR = "error"


# ── Event type → default category/severity mapping ───────────────────────
# This provides sensible defaults; callers can override when emitting.

_EVENT_DEFAULTS: dict[AuditEventType, tuple[AuditCategory, AuditSeverity]] = {
    # Auth events
    AuditEventType.AUTH_LOGIN_SUCCESS: (AuditCategory.AUTHENTICATION, AuditSeverity.INFO),
    AuditEventType.AUTH_LOGIN_FAILED: (AuditCategory.AUTHENTICATION, AuditSeverity.WARNING),
    AuditEventType.AUTH_LOGOUT: (AuditCategory.AUTHENTICATION, AuditSeverity.INFO),
    AuditEventType.AUTH_ACCOUNT_LOCKED: (AuditCategory.SECURITY, AuditSeverity.WARNING),
    AuditEventType.AUTH_SESSION_REVOKED: (AuditCategory.AUTHENTICATION, AuditSeverity.WARNING),

    # Authz events
    AuditEventType.AUTHZ_ACCESS_DENIED: (AuditCategory.AUTHORIZATION, AuditSeverity.WARNING),
    AuditEventType.AUTHZ_CROSS_TENANT_DENIED: (AuditCategory.SECURITY, AuditSeverity.CRITICAL),

    # Break-glass — always high severity
    AuditEventType.BREAK_GLASS_ACTIVATED: (AuditCategory.SECURITY, AuditSeverity.CRITICAL),
    AuditEventType.BREAK_GLASS_ACTION: (AuditCategory.SECURITY, AuditSeverity.CRITICAL),

    # Prescription lifecycle
    AuditEventType.PRESCRIPTION_UPLOADED: (AuditCategory.DATA_MUTATION, AuditSeverity.INFO),
    AuditEventType.PRESCRIPTION_STATUS_CHANGED: (AuditCategory.DATA_MUTATION, AuditSeverity.INFO),
    AuditEventType.PRESCRIPTION_REVOKED: (AuditCategory.DATA_MUTATION, AuditSeverity.WARNING),

    # Document
    AuditEventType.DOCUMENT_ACCESSED: (AuditCategory.DATA_ACCESS, AuditSeverity.INFO),
    AuditEventType.DOCUMENT_CHECKSUM_MISMATCH: (AuditCategory.SECURITY, AuditSeverity.CRITICAL),
    AuditEventType.DOCUMENT_QUARANTINED: (AuditCategory.SECURITY, AuditSeverity.WARNING),

    # Verification
    AuditEventType.VERIFICATION_FAILED: (AuditCategory.COMPLIANCE, AuditSeverity.WARNING),

    # Retention
    AuditEventType.RETENTION_DELETION_EXECUTED: (AuditCategory.DATA_MUTATION, AuditSeverity.WARNING),
    AuditEventType.RETENTION_LEGAL_HOLD_APPLIED: (AuditCategory.COMPLIANCE, AuditSeverity.INFO),

    # Admin
    AuditEventType.ADMIN_ACTION: (AuditCategory.ADMIN, AuditSeverity.WARNING),
    AuditEventType.ADMIN_USER_SUSPENDED: (AuditCategory.ADMIN, AuditSeverity.WARNING),

    # Audit integrity
    AuditEventType.AUDIT_INTEGRITY_CHECK_FAILED: (AuditCategory.SECURITY, AuditSeverity.CRITICAL),
    AuditEventType.AUDIT_GAP_DETECTED: (AuditCategory.SECURITY, AuditSeverity.CRITICAL),

    # System
    AuditEventType.SYSTEM_ERROR: (AuditCategory.SYSTEM, AuditSeverity.ERROR),
    AuditEventType.RATE_LIMIT_EXCEEDED: (AuditCategory.SECURITY, AuditSeverity.WARNING),
}

# Default for any event type not explicitly mapped
_DEFAULT_CATEGORY = AuditCategory.SYSTEM
_DEFAULT_SEVERITY = AuditSeverity.INFO


def get_event_defaults(event_type: AuditEventType) -> tuple[AuditCategory, AuditSeverity]:
    """Return (category, severity) defaults for a given event type."""
    return _EVENT_DEFAULTS.get(event_type, (_DEFAULT_CATEGORY, _DEFAULT_SEVERITY))
