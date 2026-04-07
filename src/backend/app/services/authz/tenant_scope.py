"""Tenant isolation enforcement at the ORM query level.

This module provides helpers that inject tenant_id filters into SQLAlchemy
queries. EVERY query against a tenant-scoped table MUST use these helpers
(or the equivalent filter) — there are no exceptions.

The tenant_id is ALWAYS derived from the authenticated user's session,
NEVER from request parameters. This prevents T13 (privilege escalation)
and T14 (multi-tenant data exposure) from the threat model.

Implements C-AUTHZ-03, C-AUTHZ-07 from the controls catalog.
"""

from typing import TypeVar
from uuid import UUID

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.auth.models import AuthenticatedUser

logger = get_logger(component="tenant_scope")

T = TypeVar("T")


def scope_query_to_tenant(
    query: Select,
    model,
    user: AuthenticatedUser,
) -> Select:
    """Add tenant_id filter to a SQLAlchemy select query.

    This is the PRIMARY mechanism for tenant isolation. Every service
    function that queries a tenant-scoped table should call this.

    Args:
        query: A SQLAlchemy Select statement.
        model: The ORM model class (must have a tenant_id column).
        user: The authenticated user whose tenant_id to filter by.

    Returns:
        The query with tenant_id filter applied.

    Example:
        query = select(Prescription)
        query = scope_query_to_tenant(query, Prescription, user)
        result = await db.execute(query)
    """
    return query.where(model.tenant_id == user.tenant_id)


def scope_query_to_tenant_and_clinic(
    query: Select,
    model,
    user: AuthenticatedUser,
) -> Select:
    """Add tenant_id AND clinic_id filters for clinic-scoped queries.

    Used by clinic admins and doctors who should only see their clinic's data.
    Falls back to tenant-only scope if the user has no clinic_id.

    Args:
        query: A SQLAlchemy Select statement.
        model: The ORM model class (must have tenant_id and clinic_id columns).
        user: The authenticated user.

    Returns:
        The query with tenant and clinic filters applied.
    """
    query = query.where(model.tenant_id == user.tenant_id)
    if user.clinic_id is not None and hasattr(model, "clinic_id"):
        query = query.where(model.clinic_id == user.clinic_id)
    return query


def check_tenant_access(
    user: AuthenticatedUser,
    resource_tenant_id: UUID,
) -> bool:
    """Check if a user can access a resource in a given tenant.

    Platform-level users (platform_admin, auditor) can access any tenant.
    All other users can only access resources in their own tenant.

    Returns:
        True if access is allowed, False if denied.
    """
    if user.is_platform_level:
        return True
    return user.tenant_id == resource_tenant_id


def assert_tenant_access(
    user: AuthenticatedUser,
    resource_tenant_id: UUID,
) -> None:
    """Assert tenant access, raising if denied.

    Logs a security error on denial — this represents either a bug
    (query missing tenant filter) or an attack attempt.

    Raises:
        PermissionError: If the user's tenant doesn't match.
    """
    if not check_tenant_access(user, resource_tenant_id):
        logger.error(
            "cross_tenant_access_violation",
            actor_id=str(user.user_id),
            actor_tenant=str(user.tenant_id),
            resource_tenant=str(resource_tenant_id),
        )
        raise PermissionError(
            f"Cross-tenant access denied. "
            f"Actor tenant {user.tenant_id} != resource tenant {resource_tenant_id}"
        )
