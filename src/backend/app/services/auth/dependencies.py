"""FastAPI authentication dependencies.

These dependencies extract and validate the session token from the request,
look up the user, and produce an AuthenticatedUser instance that downstream
handlers and services use for identity and authorization.

Usage in endpoints:
    @router.get("/prescriptions")
    async def list_prescriptions(
        user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        # user.tenant_id is guaranteed to be the authenticated tenant
        ...

Implements C-AUTH-03 (session validation) and feeds C-AUTHZ-03 (tenant isolation).
"""

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.services.auth.models import AuthenticatedUser, UserType, Role
from app.utils.encryption import decrypt_field
from app.services.auth.provider import get_auth_provider, IdentityClaims
from app.services.auth.session_manager import SessionManager

logger = get_logger(component="auth_dependency")


def _safe_decrypt(value: str) -> str:
    """Decrypt an encrypted field, falling back to plaintext if decryption fails."""
    try:
        return decrypt_field(value)
    except Exception:
        return value


# Session cookie/header name
_SESSION_HEADER = "X-Session-Token"
_SESSION_COOKIE = "session_token"


def _get_session_manager() -> SessionManager:
    """Build a SessionManager with settings from config."""
    settings = get_settings()
    return SessionManager(
        idle_timeout_minutes=settings.session_idle_timeout_minutes,
        absolute_timeout_minutes=settings.session_absolute_timeout_minutes,
        max_concurrent_sessions=settings.session_max_concurrent,
    )


def _extract_token(request: Request) -> str | None:
    """Extract session token from header or cookie.

    Order: X-Session-Token, Authorization Bearer, session cookie.
    """
    token = request.headers.get(_SESSION_HEADER)
    if token:
        return token

    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()

    token = request.cookies.get(_SESSION_COOKIE)
    return token


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    """FastAPI dependency: authenticate the request and return the user.

    Validates the session token, looks up the user in the appropriate
    table, and returns an AuthenticatedUser.

    Raises HTTPException 401 if authentication fails.
    """
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide a session token.",
        )

    session_mgr = _get_session_manager()
    session = await session_mgr.validate_session(db, token)

    if session is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please log in again.",
        )

    # Look up the user from the appropriate table based on session.user_type
    user = await _resolve_user(db, session.user_id, session.user_type, session.tenant_id)

    if user is None:
        logger.error(
            "session_user_not_found",
            session_id=str(session.id),
            user_id=str(session.user_id),
            user_type=session.user_type,
        )
        raise HTTPException(
            status_code=401,
            detail="User account not found.",
        )

    # Attach to request.state for middleware/audit use
    request.state.user = user

    # Update the audit context with actor info if present
    if hasattr(request.state, "audit_context"):
        from app.middleware.audit_emission import AuditContext
        old_ctx = request.state.audit_context
        request.state.audit_context = AuditContext(
            request_id=old_ctx.request_id,
            correlation_id=old_ctx.correlation_id,
            source_ip=old_ctx.source_ip,
            user_agent=old_ctx.user_agent,
            actor_id=str(user.user_id),
            actor_type=str(user.user_type),
            actor_role=str(user.role),
            tenant_id=str(user.tenant_id),
            session_id=str(session.id),
        )

    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser | None:
    """Like get_current_user but returns None instead of 401.

    Useful for endpoints that behave differently for authenticated
    vs unauthenticated requests.
    """
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None


async def _resolve_user(
    db: AsyncSession,
    user_id,
    user_type: str,
    tenant_id,
) -> AuthenticatedUser | None:
    """Look up a user by ID and type, returning an AuthenticatedUser.

    Each user type has its own table and role-derivation logic.
    Tenant isolation: the query filters by both user_id AND tenant_id.
    """
    # Import models lazily to avoid circular imports with ORM
    from app.models.users import Doctor, PharmacyUser, AdminUser, Auditor

    if user_type == UserType.DOCTOR:
        result = await db.execute(
            select(Doctor).where(
                Doctor.id == user_id,
                Doctor.tenant_id == tenant_id,
                Doctor.is_deleted == False,  # noqa: E712
                Doctor.is_active == True,  # noqa: E712
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return AuthenticatedUser(
            user_id=row.id,
            tenant_id=row.tenant_id,
            user_type=UserType.DOCTOR,
            role=Role.DOCTOR,
            email=row.email,
            full_name=_safe_decrypt(row.full_name),
            clinic_id=row.clinic_id,
        )

    elif user_type == UserType.PHARMACY_USER:
        result = await db.execute(
            select(PharmacyUser).where(
                PharmacyUser.id == user_id,
                PharmacyUser.tenant_id == tenant_id,
                PharmacyUser.is_deleted == False,  # noqa: E712
                PharmacyUser.is_active == True,  # noqa: E712
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return AuthenticatedUser(
            user_id=row.id,
            tenant_id=row.tenant_id,
            user_type=UserType.PHARMACY_USER,
            role=Role.PHARMACY_USER,
            email=row.email,
            full_name=_safe_decrypt(row.full_name),
        )

    elif user_type == UserType.ADMIN_USER:
        result = await db.execute(
            select(AdminUser).where(
                AdminUser.id == user_id,
                AdminUser.tenant_id == tenant_id,
                AdminUser.is_deleted == False,  # noqa: E712
                AdminUser.is_active == True,  # noqa: E712
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        # Admin sub-role comes from the admin_users.role column
        admin_role = _map_admin_role(row.role)
        return AuthenticatedUser(
            user_id=row.id,
            tenant_id=row.tenant_id,
            user_type=UserType.ADMIN_USER,
            role=admin_role,
            email=row.email,
            full_name=_safe_decrypt(row.full_name),
        )

    elif user_type == UserType.AUDITOR:
        result = await db.execute(
            select(Auditor).where(
                Auditor.id == user_id,
                Auditor.tenant_id == tenant_id,
                Auditor.is_deleted == False,  # noqa: E712
                Auditor.is_active == True,  # noqa: E712
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return AuthenticatedUser(
            user_id=row.id,
            tenant_id=row.tenant_id,
            user_type=UserType.AUDITOR,
            role=Role.AUDITOR,
            email=row.email,
            full_name=row.full_name,
        )

    logger.warning("unknown_user_type", user_type=user_type)
    return None


def _map_admin_role(db_role: str) -> Role:
    """Map the admin_users.role DB column to the Role enum."""
    mapping = {
        "clinic_admin": Role.CLINIC_ADMIN,
        "tenant_admin": Role.TENANT_ADMIN,
        "compliance_officer": Role.COMPLIANCE_OFFICER,
        "platform_admin": Role.PLATFORM_ADMIN,
        "support": Role.SUPPORT,
    }
    return mapping.get(db_role, Role.SUPPORT)
