"""Authentication identity models.

AuthenticatedUser is the canonical representation of a verified user
throughout the request lifecycle. It is created by the auth dependency
and attached to request.state.user.

This is a plain dataclass — no ORM dependency. It can be constructed
from any auth provider (OIDC, SAML, mock) and any user table
(doctors, pharmacy_users, admin_users, auditors).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID


class UserType(StrEnum):
    """Maps to the four user tables in the database."""
    DOCTOR = "doctor"
    PHARMACY_USER = "pharmacy_user"
    ADMIN_USER = "admin_user"
    AUDITOR = "auditor"


class Role(StrEnum):
    """RBAC roles as defined in docs/architecture.md §5.

    Doctors and pharmacy users have a single implicit role matching their
    user type. Admin users have a sub-role stored in admin_users.role.
    Auditors have the auditor role.
    """
    DOCTOR = "doctor"
    PHARMACY_USER = "pharmacy_user"
    CLINIC_ADMIN = "clinic_admin"
    TENANT_ADMIN = "tenant_admin"
    COMPLIANCE_OFFICER = "compliance_officer"
    PLATFORM_ADMIN = "platform_admin"
    AUDITOR = "auditor"
    SUPPORT = "support"


@dataclass(frozen=True)
class AuthenticatedUser:
    """Immutable identity of an authenticated user for the current request.

    Created by the auth dependency after validating the session token.
    Available throughout the request via request.state.user.

    Fields:
        user_id: Primary key from the user's table.
        tenant_id: Tenant scope — ALL queries must filter on this.
        user_type: Which user table this identity comes from.
        role: RBAC role (may differ from user_type for admin sub-roles).
        email: User email (may be encrypted in DB, decrypted here).
        full_name: User's display name.
        clinic_id: Clinic scope (doctors, clinic_admins). None for others.
        session_id: Active session record ID.
        mfa_verified: Whether MFA was completed for this session.
        is_break_glass: Whether break-glass elevation is active.
        break_glass_justification: Mandatory justification if break-glass.
    """
    user_id: UUID
    tenant_id: UUID
    user_type: UserType
    role: Role
    email: str = ""
    full_name: str = ""
    clinic_id: UUID | None = None
    session_id: UUID | None = None
    mfa_verified: bool = False
    is_break_glass: bool = False
    break_glass_justification: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_admin(self) -> bool:
        """Whether this user has any admin-level role."""
        return self.role in (
            Role.CLINIC_ADMIN,
            Role.TENANT_ADMIN,
            Role.COMPLIANCE_OFFICER,
            Role.PLATFORM_ADMIN,
            Role.SUPPORT,
        )

    @property
    def is_platform_level(self) -> bool:
        """Whether this user operates at platform level (cross-tenant)."""
        return self.role in (Role.PLATFORM_ADMIN, Role.AUDITOR)

    def to_audit_kwargs(self) -> dict[str, Any]:
        """Return kwargs for passing actor context to emit_audit_event()."""
        return {
            "actor_id": self.user_id,
            "actor_type": str(self.user_type),
            "actor_role": str(self.role),
            "actor_email": self.email,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
        }
