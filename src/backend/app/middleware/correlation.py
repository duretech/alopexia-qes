"""Correlation and request ID middleware.

Every inbound request gets:
  - request_id:     A unique UUID for this specific request.
  - correlation_id: Either forwarded from X-Correlation-ID header (if the
                    caller provides one) or a freshly generated UUID.

Both IDs are:
  1. Attached to request.state (available to handlers / services)
  2. Bound into structlog contextvars (appears on every log line automatically)
  3. Returned in response headers (X-Request-ID, X-Correlation-ID)

This is the FIRST middleware in the chain so that all downstream middleware
and handlers have access to these IDs.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

import structlog


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Injects request_id and correlation_id into every request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())

        # Attach to request state for downstream access
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        # Bind to structlog contextvars — every log line from this point
        # will include these fields automatically
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id,
        )

        response = await call_next(request)

        # Return IDs in response headers for client-side tracing
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response
