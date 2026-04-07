"""Structured request/response logging middleware.

Logs every HTTP request with correlation IDs, method, path, status, and
duration. Uses structlog contextvars so request_id and correlation_id
(set by CorrelationMiddleware) appear automatically.

Sensitive paths (e.g. auth endpoints) have their request bodies redacted.
Health check endpoints are logged at DEBUG level to avoid noise.

Implements C-OBS-01, C-OBS-02, C-SEC-09 from the controls catalog.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(component="http")

# Paths logged at DEBUG (too noisy for INFO)
_QUIET_PREFIXES = ("/health/",)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs structured request/response information for every HTTP call."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        method = request.method
        path = request.url.path
        client_ip = self._get_client_ip(request)

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "request_unhandled_exception",
                method=method,
                path=path,
                client_ip=client_ip,
                duration_ms=round(duration_ms, 2),
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        status = response.status_code

        log_data = {
            "method": method,
            "path": path,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "client_ip": client_ip,
        }

        is_quiet = any(path.startswith(p) for p in _QUIET_PREFIXES)

        if is_quiet:
            logger.debug("request_completed", **log_data)
        elif status >= 500:
            logger.error("request_completed", **log_data)
        elif status >= 400:
            logger.warning("request_completed", **log_data)
        else:
            logger.info("request_completed", **log_data)

        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
