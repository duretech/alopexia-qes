"""Tests for RBAC permission matrix.

Validates that the role-permission mapping from docs/architecture.md §5
is correctly implemented. These are security-critical assertions.
"""

from app.services.auth.models import Role
from app.services.authz.rbac import Permission, has_permission, get_role_permissions


class TestDoctorPermissions:
    def test_can_upload_prescriptions(self):
        assert has_permission(Role.DOCTOR, Permission.PRESCRIPTION_UPLOAD)

    def test_can_view_own_prescriptions(self):
        assert has_permission(Role.DOCTOR, Permission.PRESCRIPTION_VIEW_OWN)

    def test_can_revoke_own(self):
        assert has_permission(Role.DOCTOR, Permission.PRESCRIPTION_REVOKE_OWN)

    def test_cannot_revoke_any(self):
        assert not has_permission(Role.DOCTOR, Permission.PRESCRIPTION_REVOKE_ANY)

    def test_cannot_view_all_prescriptions(self):
        assert not has_permission(Role.DOCTOR, Permission.PRESCRIPTION_VIEW_ALL)

    def test_cannot_download_documents(self):
        """Doctors view metadata but don't download — they uploaded the PDF."""
        assert not has_permission(Role.DOCTOR, Permission.DOCUMENT_DOWNLOAD)

    def test_cannot_manage_users(self):
        assert not has_permission(Role.DOCTOR, Permission.USER_MANAGE_CLINIC)

    def test_cannot_activate_break_glass(self):
        assert not has_permission(Role.DOCTOR, Permission.BREAK_GLASS_ACTIVATE)


class TestPharmacyUserPermissions:
    def test_can_view_assigned_prescriptions(self):
        assert has_permission(Role.PHARMACY_USER, Permission.PRESCRIPTION_VIEW_ASSIGNED)

    def test_can_download_documents(self):
        assert has_permission(Role.PHARMACY_USER, Permission.DOCUMENT_DOWNLOAD)

    def test_can_confirm_dispensing(self):
        assert has_permission(Role.PHARMACY_USER, Permission.PHARMACY_CONFIRM_DISPENSING)

    def test_cannot_upload_prescriptions(self):
        assert not has_permission(Role.PHARMACY_USER, Permission.PRESCRIPTION_UPLOAD)

    def test_cannot_manage_users(self):
        assert not has_permission(Role.PHARMACY_USER, Permission.USER_MANAGE_TENANT)


class TestPlatformAdminPermissions:
    def test_has_break_glass(self):
        assert has_permission(Role.PLATFORM_ADMIN, Permission.BREAK_GLASS_ACTIVATE)

    def test_can_view_all_audit(self):
        assert has_permission(Role.PLATFORM_ADMIN, Permission.AUDIT_VIEW_ALL)

    def test_can_create_tenants(self):
        assert has_permission(Role.PLATFORM_ADMIN, Permission.TENANT_CREATE)

    def test_can_manage_incidents(self):
        assert has_permission(Role.PLATFORM_ADMIN, Permission.INCIDENT_MANAGE)

    def test_can_revoke_any_prescription(self):
        assert has_permission(Role.PLATFORM_ADMIN, Permission.PRESCRIPTION_REVOKE_ANY)


class TestAuditorPermissions:
    def test_can_view_all_prescriptions(self):
        assert has_permission(Role.AUDITOR, Permission.PRESCRIPTION_VIEW_ALL)

    def test_can_export_audit(self):
        assert has_permission(Role.AUDITOR, Permission.AUDIT_EXPORT)

    def test_can_verify_integrity(self):
        assert has_permission(Role.AUDITOR, Permission.AUDIT_VERIFY_INTEGRITY)

    def test_cannot_upload(self):
        assert not has_permission(Role.AUDITOR, Permission.PRESCRIPTION_UPLOAD)

    def test_cannot_manage_users(self):
        assert not has_permission(Role.AUDITOR, Permission.USER_MANAGE_TENANT)

    def test_cannot_activate_break_glass(self):
        """Auditors are read-only — no elevated access."""
        assert not has_permission(Role.AUDITOR, Permission.BREAK_GLASS_ACTIVATE)


class TestSupportPermissions:
    def test_has_break_glass(self):
        assert has_permission(Role.SUPPORT, Permission.BREAK_GLASS_ACTIVATE)

    def test_cannot_download_documents(self):
        """Support has NO PHI access without break-glass."""
        assert not has_permission(Role.SUPPORT, Permission.DOCUMENT_DOWNLOAD)

    def test_can_view_health(self):
        assert has_permission(Role.SUPPORT, Permission.SYSTEM_VIEW_HEALTH)


class TestComplianceOfficerPermissions:
    def test_can_manual_review_verifications(self):
        assert has_permission(Role.COMPLIANCE_OFFICER, Permission.VERIFICATION_MANUAL_REVIEW)

    def test_can_approve_deletions(self):
        assert has_permission(Role.COMPLIANCE_OFFICER, Permission.RETENTION_APPROVE_DELETION)

    def test_can_manage_legal_holds(self):
        assert has_permission(Role.COMPLIANCE_OFFICER, Permission.RETENTION_MANAGE_LEGAL_HOLD)

    def test_cannot_upload_prescriptions(self):
        assert not has_permission(Role.COMPLIANCE_OFFICER, Permission.PRESCRIPTION_UPLOAD)


class TestRolePermissionCompleteness:
    def test_all_roles_have_permissions(self):
        """Every defined role must have at least one permission."""
        for role in Role:
            perms = get_role_permissions(role)
            assert len(perms) > 0, f"Role {role} has no permissions defined"

    def test_no_role_has_all_permissions(self):
        """No single role should have every permission (least privilege)."""
        all_perms = set(Permission)
        for role in Role:
            perms = get_role_permissions(role)
            assert perms != all_perms, f"Role {role} has ALL permissions — violates least privilege"
