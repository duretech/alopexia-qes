"""FastAPI authorization dependencies.

These dependencies compose with the auth dependency to enforce permission
and role requirements on endpoints. They also emit audit events for
authorization denials (C-AUTHZ-08).

Usage:
    @router.post("/prescriptions/upload")
    async def upload_prescription(
        user: AuthenticatedUser = Depends(require_permission(Permission.PRESCRIPTION_UPLOAD)),
    ):
        ...

    @router.get("/admin/users")
    async def list_users(
        user: AuthenticatedUser = Depends(require_role(Role.TENANT_ADMIN, Role.PLATFORM_ADMIN)),
    ):
        ...
"""

from typing import Callable

from fastapi import Depends, HTTPException, Request

from app.core.logging import get_logger
from app.services.auth.dependencies import get_current_user
from app.services.auth.models import AuthenticatedUser, Role
from app.services.authz.rbac import Permission, has_permission

logger = get_logger(component="authz_dependency")


def require_permission(*permissions: Permission) -> Callable:
    """FastAPI dependency factory: require the user to have ALL listed permissions.

    Returns an AuthenticatedUser if authorized, raises 403 otherwise.

    Usage:
        user = Depends(require_permission(Permission.PRESCRIPTION_UPLOAD))
    """
    async def _dependency(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        missing = [p for p in permissions if not has_permission(user.role, p)]
        if missing:
            logger.warning(
                "authorization_denied",
                actor_id=str(user.user_id),
                role=str(user.role),
                missing_permissions=[str(p) for p in missing],
                path=request.url.path,
                method=request.method,
            )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action.",
            )
        return user

    return _dependency


def require_role(*roles: Role) -> Callable:
    """FastAPI dependency factory: require the user to have one of the listed roles.

    Returns an AuthenticatedUser if authorized, raises 403 otherwise.

    Usage:
        user = Depends(require_role(Role.TENANT_ADMIN, Role.PLATFORM_ADMIN))
    """
    async def _dependency(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if user.role not in roles:
            logger.warning(
                "role_denied",
                actor_id=str(user.user_id),
                role=str(user.role),
                required_roles=[str(r) for r in roles],
                path=request.url.path,
                method=request.method,
            )
            raise HTTPException(
                status_code=403,
                detail="You do not have the required role for this action.",
            )
        return user

    return _dependency


def require_mfa() -> Callable:
    """FastAPI dependency factory: require MFA verification for this session.

    Used for sensitive operations that demand higher assurance.
    """
    async def _dependency(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not user.mfa_verified:
            logger.warning(
                "mfa_required_denied",
                actor_id=str(user.user_id),
                path=request.url.path,
            )
            raise HTTPException(
                status_code=403,
                detail="Multi-factor authentication is required for this action.",
            )
        return user

    return _dependency
