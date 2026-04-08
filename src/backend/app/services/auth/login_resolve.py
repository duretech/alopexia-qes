"""Resolve portal login email to a concrete user row (mock / credentials flow)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import AdminUser, Doctor, PharmacyUser
from app.services.auth.models import Role, UserType


@dataclass(frozen=True)
class ResolvedPortalUser:
    user_id: UUID
    tenant_id: UUID
    user_type: UserType
    email: str
    full_name: str
    role: str  # display / AuthUserResponse


async def resolve_portal_user(
    db: AsyncSession,
    *,
    portal: str,
    email: str,
) -> ResolvedPortalUser | None:
    """Find the first active user matching email for the given portal."""
    normalized = email.strip().lower()

    if portal == "doctor":
        stmt = (
            select(Doctor)
            .where(
                func.lower(Doctor.email) == normalized,
                Doctor.is_deleted.is_(False),
                Doctor.is_active.is_(True),
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return ResolvedPortalUser(
            user_id=row.id,
            tenant_id=row.tenant_id,
            user_type=UserType.DOCTOR,
            email=row.email,
            full_name=row.full_name,
            role=Role.DOCTOR.value,
        )

    if portal == "pharmacy":
        stmt = (
            select(PharmacyUser)
            .where(
                func.lower(PharmacyUser.email) == normalized,
                PharmacyUser.is_deleted.is_(False),
                PharmacyUser.is_active.is_(True),
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return ResolvedPortalUser(
            user_id=row.id,
            tenant_id=row.tenant_id,
            user_type=UserType.PHARMACY_USER,
            email=row.email,
            full_name=row.full_name,
            role=Role.PHARMACY_USER.value,
        )

    if portal == "admin":
        stmt = (
            select(AdminUser)
            .where(
                func.lower(AdminUser.email) == normalized,
                AdminUser.is_deleted.is_(False),
                AdminUser.is_active.is_(True),
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        admin_role = _map_admin_role_display(row.role)
        return ResolvedPortalUser(
            user_id=row.id,
            tenant_id=row.tenant_id,
            user_type=UserType.ADMIN_USER,
            email=row.email,
            full_name=row.full_name,
            role=admin_role,
        )

    return None


def _map_admin_role_display(db_role: str) -> str:
    return db_role if db_role in {
        "clinic_admin", "tenant_admin", "compliance_officer",
        "platform_admin", "support",
    } else "support"
