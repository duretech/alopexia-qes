"""Audit emission middleware — automatic audit event hooks for sensitive endpoints.

This middleware provides the integration point between the HTTP layer and the
immutable audit service (app/services/audit/). It captures request context
(actor, IP, correlation ID, path) and makes it available for audit event
emission by downstream handlers and services.

Downstream code pattern:
    from app.middleware.audit_emission import get_audit_context
    from app.services.audit import emit_audit_event, AuditEventType

    audit_ctx = get_audit_context(request)
    await emit_audit_event(
        db,
        event_type=AuditEventType.PRESCRIPTION_UPLOADED,
        action="create",
        **audit_ctx.as_emit_kwargs(),
    )

Implements C-AUDIT-03 from the controls catalog.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(component="audit_emission")


@dataclass(frozen=True)
class AuditContext:
    """Immutable audit context captured at the middleware level.

    Downstream services use this to build audit events without
    re-extracting request information.
    """
    request_id: str = ""
    correlation_id: str = ""
    source_ip: str = ""
    user_agent: str = ""
    actor_id: str | None = None
    actor_type: str | None = None
    actor_role: str | None = None
    tenant_id: str | None = None
    session_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Serialize for inclusion in audit event detail payloads."""
        return {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "source_ip": self.source_ip,
            "user_agent": self.user_agent,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "actor_role": self.actor_role,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
        }

    def as_emit_kwargs(self) -> dict[str, Any]:
        """Return kwargs suitable for passing to emit_audit_event().

        Usage:
            await emit_audit_event(db, event_type=..., action=..., **ctx.as_emit_kwargs())
        """
        result: dict[str, Any] = {
            "source_ip": self.source_ip or None,
            "user_agent": self.user_agent or None,
            "request_id": self.request_id or None,
            "correlation_id": self.correlation_id or None,
        }
        if self.actor_id:
            result["actor_id"] = UUID(self.actor_id) if isinstance(self.actor_id, str) else self.actor_id
        if self.actor_type:
            result["actor_type"] = self.actor_type
        if self.actor_role:
            result["actor_role"] = self.actor_role
        if self.tenant_id:
            result["tenant_id"] = UUID(self.tenant_id) if isinstance(self.tenant_id, str) else self.tenant_id
        if self.session_id:
            result["session_id"] = UUID(self.session_id) if isinstance(self.session_id, str) else self.session_id
        return result


def get_audit_context(request: Request) -> AuditContext:
    """Extract the AuditContext from a request, with a safe fallback.

    Use this in endpoint handlers and service functions to get the
    audit context without directly accessing request.state.
    """
    return getattr(request.state, "audit_context", AuditContext())


# Paths that do NOT emit automatic audit events (too noisy, no sensitive data)
_NO_AUDIT_PREFIXES = ("/health/", "/docs", "/openapi.json", "/redoc")


class AuditEmissionMiddleware(BaseHTTPMiddleware):
    """Captures audit context and attaches it to request.state.audit_context.

    When the audit service is wired up, this middleware can also emit
    automatic audit events for configured endpoint patterns.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip for non-auditable paths
        path = request.url.path
        if any(path.startswith(p) for p in _NO_AUDIT_PREFIXES):
            return await call_next(request)

        # Build audit context from request state (correlation middleware runs first)
        audit_ctx = AuditContext(
            request_id=getattr(request.state, "request_id", ""),
            correlation_id=getattr(request.state, "correlation_id", ""),
            source_ip=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent", "")[:1000],
            # actor_id, actor_type, actor_role, tenant_id, session_id are
            # populated by the auth middleware (not yet built). They remain
            # None until then.
        )

        # Attach to request.state so handlers and services can access it
        request.state.audit_context = audit_ctx

        response = await call_next(request)
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
