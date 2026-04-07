"""Tests for audit event type definitions and default mappings."""

from app.services.audit.event_types import (
    AuditEventType,
    AuditCategory,
    AuditSeverity,
    AuditOutcome,
    get_event_defaults,
)


class TestAuditEventType:
    def test_all_values_are_dotted_strings(self):
        """Every event type should follow domain.action naming."""
        for evt in AuditEventType:
            assert "." in evt.value, f"{evt.name} value '{evt.value}' missing dot separator"

    def test_all_values_are_lowercase(self):
        for evt in AuditEventType:
            assert evt.value == evt.value.lower(), f"{evt.name} value not lowercase"

    def test_no_duplicate_values(self):
        values = [evt.value for evt in AuditEventType]
        assert len(values) == len(set(values)), "Duplicate event type values found"

    def test_security_critical_events_exist(self):
        """Events required by the threat model must be defined."""
        required = [
            "auth.login_success", "auth.login_failed",
            "authz.access_denied", "authz.cross_tenant_denied",
            "break_glass.activated",
            "prescription.uploaded",
            "document.accessed", "document.quarantined",
            "verification.completed", "verification.failed",
            "audit.integrity_check_failed", "audit.gap_detected",
        ]
        values = {evt.value for evt in AuditEventType}
        for r in required:
            assert r in values, f"Required event type '{r}' not defined"


class TestGetEventDefaults:
    def test_cross_tenant_denied_is_critical(self):
        cat, sev = get_event_defaults(AuditEventType.AUTHZ_CROSS_TENANT_DENIED)
        assert cat == AuditCategory.SECURITY
        assert sev == AuditSeverity.CRITICAL

    def test_break_glass_is_critical(self):
        cat, sev = get_event_defaults(AuditEventType.BREAK_GLASS_ACTIVATED)
        assert cat == AuditCategory.SECURITY
        assert sev == AuditSeverity.CRITICAL

    def test_audit_integrity_failure_is_critical(self):
        cat, sev = get_event_defaults(AuditEventType.AUDIT_INTEGRITY_CHECK_FAILED)
        assert cat == AuditCategory.SECURITY
        assert sev == AuditSeverity.CRITICAL

    def test_login_success_is_info(self):
        cat, sev = get_event_defaults(AuditEventType.AUTH_LOGIN_SUCCESS)
        assert cat == AuditCategory.AUTHENTICATION
        assert sev == AuditSeverity.INFO

    def test_unknown_event_returns_defaults(self):
        """Unmapped event types get system/info defaults."""
        cat, sev = get_event_defaults(AuditEventType.SYSTEM_STARTUP)
        assert cat == AuditCategory.SYSTEM
        assert sev == AuditSeverity.INFO


class TestAuditOutcome:
    def test_all_outcomes(self):
        assert set(AuditOutcome) == {
            AuditOutcome.SUCCESS,
            AuditOutcome.FAILURE,
            AuditOutcome.DENIED,
            AuditOutcome.ERROR,
        }
