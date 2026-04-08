"""Portal authentication: mock/credentials login, TOTP MFA, session lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose.exceptions import JWTError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.auth import (
    AuthUserResponse,
    LoginAuthenticated,
    LoginMfaEnrollment,
    LoginMfaRequired,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    MfaCompleteEnrollmentRequest,
    MfaVerifyRequest,
)
from app.services.auth.dependencies import get_current_user
from app.services.auth.login_resolve import resolve_portal_user
from app.services.auth.mfa_flow import (
    get_totp_secret_plain,
    has_totp_enrolled,
    save_totp_secret,
    set_mfa_enabled_flag,
)
from app.services.auth.models import AuthenticatedUser, UserType
from app.services.auth.pending_jwt import (
    decode_pending_token,
    issue_mfa_challenge_token,
    issue_mfa_enrollment_token,
)
from app.services.auth.session_manager import SessionManager
from app.models.users import AdminUser, Doctor, PharmacyUser

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


async def _touch_last_login(db: AsyncSession, *, user_type: UserType, user_id) -> None:
    now = datetime.now(timezone.utc)
    if user_type == UserType.DOCTOR:
        await db.execute(update(Doctor).where(Doctor.id == user_id).values(last_login_at=now))
    elif user_type == UserType.PHARMACY_USER:
        await db.execute(update(PharmacyUser).where(PharmacyUser.id == user_id).values(last_login_at=now))
    elif user_type == UserType.ADMIN_USER:
        await db.execute(update(AdminUser).where(AdminUser.id == user_id).values(last_login_at=now))


def _to_user_response(resolved) -> AuthUserResponse:
    return AuthUserResponse(
        id=resolved.user_id,
        email=resolved.email,
        full_name=resolved.full_name,
        role=resolved.role,
        tenant_id=resolved.tenant_id,
    )


async def _finalize_session(
    request: Request,
    db: AsyncSession,
    resolved,
) -> LoginAuthenticated:
    mgr = _session_manager()
    token, _rec = await mgr.create_session(
        db,
        user_id=resolved.user_id,
        user_type=resolved.user_type.value,
        tenant_id=resolved.tenant_id,
        login_ip=_client_ip(request),
        login_user_agent=_user_agent(request),
        login_method="mock_mfa",
        mfa_verified=True,
    )
    await _touch_last_login(db, user_type=resolved.user_type, user_id=resolved.user_id)
    await db.commit()
    logger.info("login_success", user_id=str(resolved.user_id), portal_user_type=resolved.user_type.value)
    return LoginAuthenticated(
        token=token,
        user=_to_user_response(resolved),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Password step (mock provider accepts any password). Always continues to MFA."""
    settings = get_settings()
    if settings.auth_provider != "mock":
        raise HTTPException(
            status_code=501,
            detail="Password login is only available with AUTH_PROVIDER=mock. Use your IdP for production.",
        )

    resolved = await resolve_portal_user(db, portal=body.portal, email=body.email)
    if resolved is None:
        raise HTTPException(status_code=401, detail="Invalid email or portal.")

    enrolled = await has_totp_enrolled(
        db,
        tenant_id=resolved.tenant_id,
        user_id=resolved.user_id,
        user_type=resolved.user_type,
    )

    if not enrolled:
        secret = pyotp.random_base32()
        enroll_jwt = issue_mfa_enrollment_token(
            user_id=str(resolved.user_id),
            tenant_id=str(resolved.tenant_id),
            user_type=resolved.user_type.value,
            email=resolved.email,
            totp_secret=secret,
        )
        totp = pyotp.TOTP(secret)
        issuer = f"QES Flow ({body.portal})"
        otpauth_uri = totp.provisioning_uri(name=resolved.email, issuer_name=issuer)
        return LoginMfaEnrollment(
            enrollment_token=enroll_jwt,
            otpauth_uri=otpauth_uri,
        )

    challenge = issue_mfa_challenge_token(
        user_id=str(resolved.user_id),
        tenant_id=str(resolved.tenant_id),
        user_type=resolved.user_type.value,
    )
    return LoginMfaRequired(mfa_token=challenge)


@router.post("/mfa/verify", response_model=LoginAuthenticated)
async def mfa_verify(
    request: Request,
    body: MfaVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginAuthenticated:
    settings = get_settings()
    if settings.auth_provider != "mock":
        raise HTTPException(status_code=501, detail="MFA verify is only wired for mock login in this build.")

    try:
        claims = decode_pending_token(body.mfa_token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired MFA token.")

    if claims.get("typ") != "mfa_challenge":
        raise HTTPException(status_code=400, detail="Invalid MFA token type.")

    from uuid import UUID

    user_id = UUID(claims["sub"])
    tenant_id = UUID(claims["tid"])
    user_type = UserType(claims["ut"])

    resolved = await resolve_portal_user(
        db,
        portal=_portal_hint_for_user_type(user_type),
        email=(await _email_for_user(db, user_id, user_type, tenant_id)),
    )
    if resolved is None:
        raise HTTPException(status_code=401, detail="User not found.")

    secret = await get_totp_secret_plain(
        db, tenant_id=tenant_id, user_id=user_id, user_type=user_type
    )
    if not secret:
        raise HTTPException(status_code=400, detail="MFA not enrolled for this user.")

    totp = pyotp.TOTP(secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid authenticator code.")

    return await _finalize_session(request, db, resolved)


@router.post("/mfa/complete-enrollment", response_model=LoginAuthenticated)
async def mfa_complete_enrollment(
    request: Request,
    body: MfaCompleteEnrollmentRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginAuthenticated:
    settings = get_settings()
    if settings.auth_provider != "mock":
        raise HTTPException(status_code=501, detail="MFA enrollment is only wired for mock login.")

    try:
        claims = decode_pending_token(body.enrollment_token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired enrollment token.")

    if claims.get("typ") != "mfa_enroll":
        raise HTTPException(status_code=400, detail="Invalid enrollment token type.")

    from uuid import UUID

    user_id = UUID(claims["sub"])
    tenant_id = UUID(claims["tid"])
    user_type = UserType(claims["ut"])
    email = claims["em"]
    secret = claims["sec"]

    totp = pyotp.TOTP(secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code. Check the time on your device.")

    resolved = await resolve_portal_user(
        db, portal=_portal_hint_for_user_type(user_type), email=email
    )
    if resolved is None or resolved.user_id != user_id:
        raise HTTPException(status_code=400, detail="Enrollment user mismatch.")

    if await has_totp_enrolled(db, tenant_id=tenant_id, user_id=user_id, user_type=user_type):
        raise HTTPException(status_code=409, detail="MFA already enrolled.")

    await save_totp_secret(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        user_type=user_type,
        secret_base32=secret,
    )
    await set_mfa_enabled_flag(db, resolved, True)

    return await _finalize_session(request, db, resolved)


def _portal_hint_for_user_type(user_type: UserType) -> str:
    if user_type == UserType.DOCTOR:
        return "doctor"
    if user_type == UserType.PHARMACY_USER:
        return "pharmacy"
    return "admin"


async def _email_for_user(db: AsyncSession, user_id, user_type: UserType, tenant_id) -> str:
    if user_type == UserType.DOCTOR:
        r = await db.execute(select(Doctor.email).where(Doctor.id == user_id, Doctor.tenant_id == tenant_id))
    elif user_type == UserType.PHARMACY_USER:
        r = await db.execute(
            select(PharmacyUser.email).where(
                PharmacyUser.id == user_id, PharmacyUser.tenant_id == tenant_id
            )
        )
    elif user_type == UserType.ADMIN_USER:
        r = await db.execute(
            select(AdminUser.email).where(AdminUser.id == user_id, AdminUser.tenant_id == tenant_id)
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported user type for MFA.")
    row = r.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return row


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
        email=user.email,
        full_name=user.full_name,
        role=str(user.role),
        tenant_id=user.tenant_id,
    )
