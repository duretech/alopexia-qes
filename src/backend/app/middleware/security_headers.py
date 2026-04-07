"""Security headers middleware.

Applies defensive HTTP headers on every response per OWASP recommendations
and the project security design (docs/security.md, C-SEC-05).

Headers set:
  - Strict-Transport-Security (HSTS) — enforces HTTPS
  - Content-Security-Policy (CSP) — restricts resource loading
  - X-Content-Type-Options — prevents MIME sniffing
  - X-Frame-Options — prevents clickjacking
  - Referrer-Policy — limits referrer leakage
  - Permissions-Policy — disables unused browser features
  - Cache-Control — prevents sensitive data caching
  - X-XSS-Protection — legacy XSS filter hint (deprecated but harmless)
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


# Default headers — conservative for a healthcare/compliance platform.
# CSP is strict: only self-origin, no inline scripts or styles by default.
# Frontends are served from separate origins and make API calls, so the API
# itself should not serve any browser-rendered content.
_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    ),
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma": "no-cache",
    "X-XSS-Protection": "1; mode=block",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every HTTP response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
