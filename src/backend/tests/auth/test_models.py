"""Tests for authentication identity models."""

import uuid

from app.services.auth.models import AuthenticatedUser, UserType, Role


_TENANT = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_USER = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CLINIC = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_SESSION = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


class TestAuthenticatedUser:
    def test_immutable(self):
        user = AuthenticatedUser(user_id=_USER, tenant_id=_TENANT,
                                  user_type=UserType.DOCTOR, role=Role.DOCTOR)
        try:
            user.user_id = uuid.uuid4()  # type: ignore
            assert False, "Should raise"
        except AttributeError:
            pass

    def test_is_admin_for_admin_roles(self):
        for role in (Role.CLINIC_ADMIN, Role.TENANT_ADMIN, Role.COMPLIANCE_OFFICER,
                     Role.PLATFORM_ADMIN, Role.SUPPORT):
            user = AuthenticatedUser(user_id=_USER, tenant_id=_TENANT,
                                      user_type=UserType.ADMIN_USER, role=role)
            assert user.is_admin, f"{role} should be admin"

    def test_is_not_admin_for_non_admin_roles(self):
        for role in (Role.DOCTOR, Role.PHARMACY_USER, Role.AUDITOR):
            ut = {Role.DOCTOR: UserType.DOCTOR, Role.PHARMACY_USER: UserType.PHARMACY_USER,
                  Role.AUDITOR: UserType.AUDITOR}[role]
            user = AuthenticatedUser(user_id=_USER, tenant_id=_TENANT,
                                      user_type=ut, role=role)
            assert not user.is_admin, f"{role} should not be admin"

    def test_is_platform_level(self):
        assert AuthenticatedUser(user_id=_USER, tenant_id=_TENANT,
                                  user_type=UserType.ADMIN_USER,
                                  role=Role.PLATFORM_ADMIN).is_platform_level
        assert AuthenticatedUser(user_id=_USER, tenant_id=_TENANT,
                                  user_type=UserType.AUDITOR,
                                  role=Role.AUDITOR).is_platform_level
        assert not AuthenticatedUser(user_id=_USER, tenant_id=_TENANT,
                                      user_type=UserType.DOCTOR,
                                      role=Role.DOCTOR).is_platform_level

    def test_to_audit_kwargs(self):
        user = AuthenticatedUser(
            user_id=_USER, tenant_id=_TENANT,
            user_type=UserType.DOCTOR, role=Role.DOCTOR,
            email="doc@example.com", session_id=_SESSION,
        )
        kwargs = user.to_audit_kwargs()
        assert kwargs["actor_id"] == _USER
        assert kwargs["actor_type"] == "doctor"
        assert kwargs["actor_role"] == "doctor"
        assert kwargs["actor_email"] == "doc@example.com"
        assert kwargs["tenant_id"] == _TENANT
        assert kwargs["session_id"] == _SESSION


class TestUserType:
    def test_all_user_types(self):
        assert set(UserType) == {
            UserType.DOCTOR, UserType.PHARMACY_USER,
            UserType.ADMIN_USER, UserType.AUDITOR,
        }


class TestRole:
    def test_all_roles(self):
        expected = {"doctor", "pharmacy_user", "clinic_admin", "tenant_admin",
                    "compliance_officer", "platform_admin", "auditor", "support"}
        assert {r.value for r in Role} == expected
