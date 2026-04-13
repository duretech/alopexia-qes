"""Portal authentication using phone OTP + encrypted PIN."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose.exceptions import JWTError
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.auth import (
    AuthUserResponse,
    AuthenticatedResponse,
    OtpRequiredResponse,
    PhoneLoginRequest,
    PinRequiredResponse,
    VerifyOtpRequest,
    VerifyPinRequest,
    LogoutResponse,
)
from app.services.auth.dependencies import get_current_user
from app.services.auth.models import AuthenticatedUser, UserType
from app.services.auth.pending_jwt import (
    decode_pending_token,
    issue_otp_challenge_token,
    issue_pin_challenge_token,
)
from app.services.auth.session_manager import SessionManager
from app.models.users import AdminUser, Doctor, PharmacyUser
from app.models.phone_auth import PhoneAuthAccount, PhoneOtpChallenge
from app.utils.encryption import encrypt_field, decrypt_field, hash_identifier
@dataclass(frozen=True)
class _ResolvedUser:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    user_type: UserType
    full_name: str
    role: str
    phone_number: str



logger = get_logger(component="auth_endpoint")

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


def _session_manager() -> SessionManager:
    settings = get_settings()
    return SessionManager(
        idle_timeout_minutes=settings.session_idle_timeout_minutes,
        absolute_timeout_minutes=settings.session_absolute_timeout_minutes,
        max_concurrent_sessions=settings.session_max_concurrent,
    )


def _client_ip(request: Request) -> str:
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


async def _touch_last_login(db: AsyncSession, *, user_type: UserType, user_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    if user_type == UserType.DOCTOR:
        await db.execute(update(Doctor).where(Doctor.id == user_id).values(last_login_at=now))
    elif user_type == UserType.PHARMACY_USER:
        await db.execute(update(PharmacyUser).where(PharmacyUser.id == user_id).values(last_login_at=now))
    elif user_type == UserType.ADMIN_USER:
        await db.execute(update(AdminUser).where(AdminUser.id == user_id).values(last_login_at=now))


def _to_user_response(resolved: _ResolvedUser) -> AuthUserResponse:
    return AuthUserResponse(
        id=resolved.user_id,
        phone_number=resolved.phone_number,
        full_name=resolved.full_name,
        role=resolved.role,
        tenant_id=resolved.tenant_id,
    )


async def _finalize_session(
    request: Request,
    db: AsyncSession,
    resolved: _ResolvedUser,
) -> AuthenticatedResponse:
    mgr = _session_manager()
    token, _rec = await mgr.create_session(
        db,
        user_id=resolved.user_id,
        user_type=resolved.user_type.value,
        tenant_id=resolved.tenant_id,
        login_ip=_client_ip(request),
        login_user_agent=_user_agent(request),
        login_method="phone_otp_pin",
        mfa_verified=True,
    )
    await _touch_last_login(db, user_type=resolved.user_type, user_id=resolved.user_id)
    await db.commit()
    logger.info("login_success", user_id=str(resolved.user_id), portal_user_type=resolved.user_type.value)
    return AuthenticatedResponse(
        token=token,
        user=_to_user_response(resolved),
    )


def _normalize_phone(phone: str) -> str:
    cleaned = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


async def _send_sms_otp(phone: str, code: str) -> None:
    settings = get_settings()
    if not settings.sms_gateway_token:
        return
    payload = {
        "sender": settings.sms_sender_name,
        "message": f"Your QES Flow OTP is {code}. It expires in {settings.sms_otp_ttl_seconds // 60} minutes.",
        "recipients": [{"msisdn": phone}],
    }
    headers = {
        "Authorization": f"Bearer {settings.sms_gateway_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(settings.sms_gateway_url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.warning("sms_send_failed", status=resp.status_code, body=resp.text[:300])


async def _load_resolved_user_by_account(db: AsyncSession, account: PhoneAuthAccount) -> _ResolvedUser | None:
    if account.user_type == UserType.DOCTOR.value:
        q = await db.execute(
            select(Doctor).where(
                and_(
                    Doctor.id == account.user_id,
                    Doctor.tenant_id == account.tenant_id,
                    Doctor.is_active.is_(True),
                    Doctor.is_deleted.is_(False),
                )
            )
        )
        row = q.scalar_one_or_none()
        if row is None:
            return None
        return _ResolvedUser(row.id, row.tenant_id, UserType.DOCTOR, row.full_name, "doctor", decrypt_field(account.phone_encrypted))
    if account.user_type == UserType.PHARMACY_USER.value:
        q = await db.execute(
            select(PharmacyUser).where(
                and_(
                    PharmacyUser.id == account.user_id,
                    PharmacyUser.tenant_id == account.tenant_id,
                    PharmacyUser.is_active.is_(True),
                    PharmacyUser.is_deleted.is_(False),
                )
            )
        )
        row = q.scalar_one_or_none()
        if row is None:
            return None
        return _ResolvedUser(row.id, row.tenant_id, UserType.PHARMACY_USER, row.full_name, "pharmacy_user", decrypt_field(account.phone_encrypted))
    if account.user_type == UserType.ADMIN_USER.value:
        q = await db.execute(
            select(AdminUser).where(
                and_(
                    AdminUser.id == account.user_id,
                    AdminUser.tenant_id == account.tenant_id,
                    AdminUser.is_active.is_(True),
                    AdminUser.is_deleted.is_(False),
                )
            )
        )
        row = q.scalar_one_or_none()
        if row is None:
            return None
        return _ResolvedUser(row.id, row.tenant_id, UserType.ADMIN_USER, row.full_name, row.role, decrypt_field(account.phone_encrypted))
    return None


@router.post("/login", response_model=OtpRequiredResponse)
async def login(
    request: Request,
    body: PhoneLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> OtpRequiredResponse:
    """Step 1: phone number -> send OTP -> return challenge token."""
    settings = get_settings()
    phone = _normalize_phone(body.phone_number)
    phone_hash = hash_identifier(phone)
    stmt = (
        select(PhoneAuthAccount)
        .where(
            PhoneAuthAccount.phone_hash == phone_hash,
            PhoneAuthAccount.portal == body.portal,
            PhoneAuthAccount.is_active.is_(True),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=401, detail="Invalid phone number or portal.")

    otp = f"{secrets.randbelow(900000) + 100000}"
    now = datetime.now(timezone.utc)
    challenge = PhoneOtpChallenge(
        id=uuid.uuid4(),
        tenant_id=account.tenant_id,
        account_id=account.id,
        otp_encrypted=encrypt_field(otp),
        expires_at=now + timedelta(seconds=settings.sms_otp_ttl_seconds),
        verified_at=None,
        attempt_count=0,
    )
    db.add(challenge)
    await db.flush()
    await db.commit()

    await _send_sms_otp(phone, otp)

    otp_token = issue_otp_challenge_token(
        challenge_id=str(challenge.id),
        account_id=str(account.id),
        tenant_id=str(account.tenant_id),
        portal=body.portal,
        ttl_seconds=settings.sms_otp_ttl_seconds,
    )
    return OtpRequiredResponse(
        otp_token=otp_token,
        otp_expires_in_seconds=settings.sms_otp_ttl_seconds,
        otp_debug=otp if settings.app_env != "production" else None,
    )


@router.post("/otp/verify", response_model=PinRequiredResponse)
async def verify_otp(
    request: Request,
    body: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
) -> PinRequiredResponse:
    """Step 2: verify OTP and return short-lived pin challenge token."""
    try:
        claims = decode_pending_token(body.otp_token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP token.")

    if claims.get("typ") != "otp_challenge":
        raise HTTPException(status_code=400, detail="Invalid OTP token type.")

    challenge_id = uuid.UUID(claims["cid"])
    account_id = uuid.UUID(claims["aid"])
    tenant_id = uuid.UUID(claims["tid"])
    stmt = (
        select(PhoneOtpChallenge, PhoneAuthAccount)
        .join(PhoneAuthAccount, PhoneAuthAccount.id == PhoneOtpChallenge.account_id)
        .where(
            PhoneOtpChallenge.id == challenge_id,
            PhoneOtpChallenge.account_id == account_id,
            PhoneOtpChallenge.tenant_id == tenant_id,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        raise HTTPException(status_code=400, detail="OTP challenge not found.")
    challenge, account = row
    now = datetime.now(timezone.utc)
    if challenge.verified_at is not None:
        raise HTTPException(status_code=409, detail="OTP already used.")
    if now > challenge.expires_at:
        raise HTTPException(status_code=400, detail="OTP expired.")
    challenge.attempt_count = (challenge.attempt_count or 0) + 1
    if decrypt_field(challenge.otp_encrypted) != body.otp_code:
        await db.commit()
        raise HTTPException(status_code=401, detail="Incorrect OTP.")
    challenge.verified_at = now
    await db.commit()

    pin_token = issue_pin_challenge_token(
        account_id=str(account.id),
        user_id=str(account.user_id),
        tenant_id=str(account.tenant_id),
        user_type=account.user_type,
        ttl_seconds=600,
    )
    return PinRequiredResponse(pin_token=pin_token)


@router.post("/pin/verify", response_model=AuthenticatedResponse)
async def verify_pin(
    request: Request,
    body: VerifyPinRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedResponse:
    """Step 3 (MFA): verify encrypted PIN and create session."""
    try:
        claims = decode_pending_token(body.pin_token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired PIN token.")

    if claims.get("typ") != "pin_challenge":
        raise HTTPException(status_code=400, detail="Invalid PIN token type.")

    account_id = uuid.UUID(claims["aid"])
    tenant_id = uuid.UUID(claims["tid"])
    stmt = (
        select(PhoneAuthAccount)
        .where(
            PhoneAuthAccount.id == account_id,
            PhoneAuthAccount.tenant_id == tenant_id,
            PhoneAuthAccount.is_active.is_(True),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=401, detail="Invalid PIN challenge.")
    if decrypt_field(account.pin_encrypted) != body.pin:
        raise HTTPException(status_code=401, detail="Incorrect PIN.")

    resolved = await _load_resolved_user_by_account(db, account)
    if resolved is None:
        raise HTTPException(status_code=401, detail="User not found for this phone account.")
    return await _finalize_session(request, db, resolved)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    token = None
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    if not token:
        token = request.headers.get("X-Session-Token")
    if not token:
        raise HTTPException(status_code=400, detail="No session token provided.")

    mgr = _session_manager()
    await mgr.end_session(db, token, reason="logout")
    await db.commit()
    return LogoutResponse(ok=True)


@router.get("/me", response_model=AuthUserResponse)
async def me(user: AuthenticatedUser = Depends(get_current_user)) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.user_id,
        phone_number=user.email,
        full_name=user.full_name,
        role=str(user.role),
        tenant_id=user.tenant_id,
    )
