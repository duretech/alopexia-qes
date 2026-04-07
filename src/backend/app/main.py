"""QES Flow — FastAPI application entry point.

Start with:
    cd src/backend
    uvicorn app.main:app --reload

This module:
  - Configures structured logging (structlog)
  - Initialises the async database engine on startup
  - Registers all middleware in the correct order
  - Mounts the versioned API router and health endpoints
  - Installs global exception handlers that produce structured JSON errors
    and emit audit-relevant log entries for security events
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.session import init_db
from app.api.v1.router import api_router
from app.api.v1.endpoints.health import router as health_router
from app.middleware.correlation import CorrelationMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.audit_emission import AuditEmissionMiddleware

logger = get_logger(component="main")


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialise resources on startup, clean up on shutdown."""
    settings = get_settings()

    # 1. Structured logging
    setup_logging(
        log_level=settings.log_level,
        json_output=(settings.log_format == "json"),
    )
    logger.info(
        "application_starting",
        env=settings.app_env,
        debug=settings.app_debug,
    )

    # 2. Database engine
    init_db()
    logger.info("database_engine_initialised")

    yield  # Application is running

    # Shutdown
    from app.db import session as _session_mod
    if _session_mod.engine is not None:
        await _session_mod.engine.dispose()
        logger.info("database_engine_disposed")
    logger.info("application_shutdown_complete")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

settings = get_settings()

app = FastAPI(
    title="QES Flow",
    description="Qualified Electronic Signature prescription workflow platform",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware stack — order matters (outermost first, runs first on request)
# ---------------------------------------------------------------------------

# 1. Correlation IDs — must be outermost so every middleware below has IDs
app.add_middleware(CorrelationMiddleware)

# 2. Request logging — logs every request with correlation IDs
app.add_middleware(RequestLoggingMiddleware)

# 3. Security headers — applied to every response
app.add_middleware(SecurityHeadersMiddleware)

# 4. Rate limiting — per-IP token bucket
app.add_middleware(RateLimitMiddleware, default_rate=settings.rate_limit_default)

# 5. Audit emission — captures audit context for downstream use
app.add_middleware(AuditEmissionMiddleware)

# 6. CORS — configured from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Correlation-ID"],
)

# 7. Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts_list,
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

# Health checks at root level (no /api/v1 prefix — infrastructure probes)
app.include_router(health_router)

# Versioned API
app.include_router(api_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Global exception handlers — structured JSON, no stack traces in production
# ---------------------------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions with structured JSON responses.

    Security-relevant status codes (401, 403, 429) are logged at warning
    level for detective controls.
    """
    request_id = getattr(request.state, "request_id", None)

    if exc.status_code in (401, 403):
        logger.warning(
            "security_http_error",
            status=exc.status_code,
            path=request.url.path,
            method=request.method,
            detail=str(exc.detail),
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": _status_to_error_code(exc.status_code),
            "detail": exc.detail,
            "request_id": request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with structured JSON.

    Never expose raw internal field names in production — they could leak
    schema information. In dev mode, include full error details.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        "validation_error",
        path=request.url.path,
        error_count=len(exc.errors()),
    )

    if settings.is_production:
        detail = "Request validation failed. Check your request body and parameters."
    else:
        detail = exc.errors()

    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": detail,
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions.

    NEVER expose stack traces or internal error messages to clients.
    Log the full exception server-side for debugging.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        exc_type=type(exc).__name__,
        exc_message=str(exc),
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "An internal error occurred. Contact support if this persists.",
            "request_id": request_id,
        },
    )


def _status_to_error_code(status: int) -> str:
    """Map HTTP status codes to machine-readable error codes."""
    codes = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_server_error",
        502: "bad_gateway",
        503: "service_unavailable",
    }
    return codes.get(status, f"http_{status}")
