"""TOTP persistence and user mfa_enabled flag updates."""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mfa_totp import TotpCredential
from app.models.users import AdminUser, Doctor, PharmacyUser
from app.services.auth.login_resolve import ResolvedPortalUser
from app.services.auth.models import UserType
from app.utils.encryption import decrypt_field, encrypt_field


async def has_totp_enrolled(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user_type: UserType,
) -> bool:
    stmt = select(TotpCredential.id).where(
        TotpCredential.tenant_id == tenant_id,
        TotpCredential.user_id == user_id,
        TotpCredential.user_type == user_type.value,
    ).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_totp_secret_plain(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user_type: UserType,
) -> str | None:
    stmt = select(TotpCredential).where(
        TotpCredential.tenant_id == tenant_id,
        TotpCredential.user_id == user_id,
        TotpCredential.user_type == user_type.value,
    ).limit(1)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return decrypt_field(row.secret_encrypted)


async def save_totp_secret(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user_type: UserType,
    secret_base32: str,
) -> None:
    row = TotpCredential(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        user_type=user_type.value,
        secret_encrypted=encrypt_field(secret_base32),
    )
    db.add(row)


async def set_mfa_enabled_flag(
    db: AsyncSession,
    resolved: ResolvedPortalUser,
    enabled: bool,
) -> None:
    if resolved.user_type == UserType.DOCTOR:
        await db.execute(
            update(Doctor)
            .where(Doctor.id == resolved.user_id, Doctor.tenant_id == resolved.tenant_id)
            .values(mfa_enabled=enabled)
        )
    elif resolved.user_type == UserType.PHARMACY_USER:
        await db.execute(
            update(PharmacyUser)
            .where(PharmacyUser.id == resolved.user_id, PharmacyUser.tenant_id == resolved.tenant_id)
            .values(mfa_enabled=enabled)
        )
    elif resolved.user_type == UserType.ADMIN_USER:
        await db.execute(
            update(AdminUser)
            .where(AdminUser.id == resolved.user_id, AdminUser.tenant_id == resolved.tenant_id)
            .values(mfa_enabled=enabled)
        )
