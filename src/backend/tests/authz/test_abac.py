"""Tests for ABAC policy evaluator.

Covers tenant isolation (T14), clinic scoping, ownership, MFA requirements,
break-glass override, and deleted resource access.
"""

import uuid

from app.services.auth.models import AuthenticatedUser, UserType, Role
from app.services.authz.abac import (
    evaluate_policy,
    PolicyDecision,
    DenyReason,
    ResourceContext,
)
from app.services.authz.rbac import Permission


_TENANT_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TENANT_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CLINIC_1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
_CLINIC_2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
_USER_1 = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_USER_2 = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


def _doctor(tenant=_TENANT_A, clinic=_CLINIC_1, user_id=_USER_1, **kw):
    return AuthenticatedUser(
        user_id=user_id, tenant_id=tenant, user_type=UserType.DOCTOR,
        role=Role.DOCTOR, clinic_id=clinic, **kw,
    )


def _pharmacy_user(tenant=_TENANT_A, user_id=_USER_2, **kw):
    return AuthenticatedUser(
        user_id=user_id, tenant_id=tenant, user_type=UserType.PHARMACY_USER,
        role=Role.PHARMACY_USER, **kw,
    )


def _platform_admin(tenant=_TENANT_A, user_id=_USER_1, **kw):
    return AuthenticatedUser(
        user_id=user_id, tenant_id=tenant, user_type=UserType.ADMIN_USER,
        role=Role.PLATFORM_ADMIN, **kw,
    )


def _auditor(tenant=_TENANT_A, user_id=_USER_1, **kw):
    return AuthenticatedUser(
        user_id=user_id, tenant_id=tenant, user_type=UserType.AUDITOR,
        role=Role.AUDITOR, **kw,
    )


class TestRBACGate:
    def test_allow_when_role_has_permission(self):
        result = evaluate_policy(
            actor=_doctor(),
            permission=Permission.PRESCRIPTION_UPLOAD,
        )
        assert result.allowed

    def test_deny_when_role_lacks_permission(self):
        result = evaluate_policy(
            actor=_doctor(),
            permission=Permission.USER_MANAGE_TENANT,
        )
        assert not result.allowed
        assert result.reason == DenyReason.NO_PERMISSION


class TestTenantIsolation:
    def test_same_tenant_allowed(self):
        result = evaluate_policy(
            actor=_doctor(tenant=_TENANT_A),
            permission=Permission.PRESCRIPTION_VIEW_OWN,
            resource=ResourceContext(tenant_id=_TENANT_A, owner_id=_USER_1),
        )
        assert result.allowed

    def test_cross_tenant_denied(self):
        """T14: A user in Tenant A MUST NOT access Tenant B resources."""
        result = evaluate_policy(
            actor=_doctor(tenant=_TENANT_A),
            permission=Permission.PRESCRIPTION_VIEW_OWN,
            resource=ResourceContext(tenant_id=_TENANT_B, owner_id=_USER_1),
        )
        assert not result.allowed
        assert result.reason == DenyReason.TENANT_MISMATCH

    def test_platform_admin_cross_tenant_allowed(self):
        """Platform admins can access any tenant."""
        result = evaluate_policy(
            actor=_platform_admin(tenant=_TENANT_A),
            permission=Permission.PRESCRIPTION_VIEW_ALL,
            resource=ResourceContext(tenant_id=_TENANT_B),
        )
        assert result.allowed

    def test_auditor_cross_tenant_allowed(self):
        """Auditors can view data across tenants."""
        result = evaluate_policy(
            actor=_auditor(tenant=_TENANT_A),
            permission=Permission.PRESCRIPTION_VIEW_ALL,
            resource=ResourceContext(tenant_id=_TENANT_B),
        )
        assert result.allowed


class TestClinicScoping:
    def test_same_clinic_allowed(self):
        result = evaluate_policy(
            actor=_doctor(clinic=_CLINIC_1),
            permission=Permission.PRESCRIPTION_VIEW_CLINIC,
            resource=ResourceContext(tenant_id=_TENANT_A, clinic_id=_CLINIC_1),
        )
        # Doctor doesn't have PRESCRIPTION_VIEW_CLINIC — that's for clinic_admin
        assert not result.allowed

    def test_clinic_admin_same_clinic(self):
        admin = AuthenticatedUser(
            user_id=_USER_1, tenant_id=_TENANT_A, user_type=UserType.ADMIN_USER,
            role=Role.CLINIC_ADMIN, clinic_id=_CLINIC_1,
        )
        result = evaluate_policy(
            actor=admin,
            permission=Permission.PRESCRIPTION_VIEW_CLINIC,
            resource=ResourceContext(tenant_id=_TENANT_A, clinic_id=_CLINIC_1),
        )
        assert result.allowed

    def test_clinic_admin_different_clinic_denied(self):
        admin = AuthenticatedUser(
            user_id=_USER_1, tenant_id=_TENANT_A, user_type=UserType.ADMIN_USER,
            role=Role.CLINIC_ADMIN, clinic_id=_CLINIC_1,
        )
        result = evaluate_policy(
            actor=admin,
            permission=Permission.PRESCRIPTION_VIEW_CLINIC,
            resource=ResourceContext(tenant_id=_TENANT_A, clinic_id=_CLINIC_2),
        )
        assert not result.allowed
        assert result.reason == DenyReason.CLINIC_MISMATCH


class TestOwnershipScoping:
    def test_owner_can_view_own(self):
        result = evaluate_policy(
            actor=_doctor(user_id=_USER_1),
            permission=Permission.PRESCRIPTION_VIEW_OWN,
            resource=ResourceContext(tenant_id=_TENANT_A, owner_id=_USER_1),
        )
        assert result.allowed

    def test_non_owner_cannot_view_own(self):
        result = evaluate_policy(
            actor=_doctor(user_id=_USER_1),
            permission=Permission.PRESCRIPTION_VIEW_OWN,
            resource=ResourceContext(tenant_id=_TENANT_A, owner_id=_USER_2),
        )
        assert not result.allowed
        assert result.reason == DenyReason.NOT_OWNER


class TestMFARequirement:
    def test_mfa_required_and_not_verified(self):
        result = evaluate_policy(
            actor=_doctor(mfa_verified=False),
            permission=Permission.PRESCRIPTION_UPLOAD,
            require_mfa=True,
        )
        assert not result.allowed
        assert result.reason == DenyReason.MFA_REQUIRED

    def test_mfa_required_and_verified(self):
        result = evaluate_policy(
            actor=_doctor(mfa_verified=True),
            permission=Permission.PRESCRIPTION_UPLOAD,
            require_mfa=True,
        )
        assert result.allowed


class TestBreakGlass:
    def test_break_glass_bypasses_clinic_scoping(self):
        admin = AuthenticatedUser(
            user_id=_USER_1, tenant_id=_TENANT_A, user_type=UserType.ADMIN_USER,
            role=Role.CLINIC_ADMIN, clinic_id=_CLINIC_1,
            is_break_glass=True, break_glass_justification="Emergency patient access",
        )
        result = evaluate_policy(
            actor=admin,
            permission=Permission.PRESCRIPTION_VIEW_CLINIC,
            resource=ResourceContext(tenant_id=_TENANT_A, clinic_id=_CLINIC_2),
        )
        assert result.allowed

    def test_break_glass_does_not_bypass_tenant_isolation(self):
        """Tenant isolation is NEVER bypassed — even under break-glass."""
        admin = AuthenticatedUser(
            user_id=_USER_1, tenant_id=_TENANT_A, user_type=UserType.ADMIN_USER,
            role=Role.CLINIC_ADMIN, clinic_id=_CLINIC_1,
            is_break_glass=True, break_glass_justification="Emergency",
        )
        result = evaluate_policy(
            actor=admin,
            permission=Permission.PRESCRIPTION_VIEW_CLINIC,
            resource=ResourceContext(tenant_id=_TENANT_B, clinic_id=_CLINIC_1),
        )
        assert not result.allowed
        assert result.reason == DenyReason.TENANT_MISMATCH

    def test_break_glass_still_requires_mfa_when_demanded(self):
        admin = AuthenticatedUser(
            user_id=_USER_1, tenant_id=_TENANT_A, user_type=UserType.ADMIN_USER,
            role=Role.PLATFORM_ADMIN, is_break_glass=True,
            break_glass_justification="Emergency", mfa_verified=False,
        )
        result = evaluate_policy(
            actor=admin,
            permission=Permission.PRESCRIPTION_VIEW_ALL,
            resource=ResourceContext(tenant_id=_TENANT_A),
            require_mfa=True,
        )
        assert not result.allowed
        assert result.reason == DenyReason.MFA_REQUIRED


class TestDeletedResources:
    def test_normal_access_to_deleted_resource_denied(self):
        result = evaluate_policy(
            actor=_doctor(),
            permission=Permission.PRESCRIPTION_VIEW_OWN,
            resource=ResourceContext(tenant_id=_TENANT_A, owner_id=_USER_1, is_deleted=True),
        )
        assert not result.allowed
        assert result.reason == DenyReason.RESOURCE_DELETED

    def test_retention_access_to_deleted_resource_allowed(self):
        """Compliance officers can still view deleted resources for retention."""
        co = AuthenticatedUser(
            user_id=_USER_1, tenant_id=_TENANT_A, user_type=UserType.ADMIN_USER,
            role=Role.COMPLIANCE_OFFICER,
        )
        result = evaluate_policy(
            actor=co,
            permission=Permission.RETENTION_VIEW,
            resource=ResourceContext(tenant_id=_TENANT_A, is_deleted=True),
        )
        assert result.allowed
