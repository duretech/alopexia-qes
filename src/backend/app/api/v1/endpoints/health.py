"""Health check endpoints — liveness and readiness probes.

GET /health/live  — Returns 200 if the process is up. No dependencies checked.
GET /health/ready — Returns 200 if all critical dependencies (DB) are reachable.
                    Returns 503 if any dependency is degraded.

These endpoints:
  - Do NOT require authentication (infrastructure probes)
  - Do NOT emit audit events (C-AUDIT-03 exclusion — too noisy)
  - Are excluded from rate limiting (_EXEMPT_PREFIXES in rate_limit.py)
  - Are logged at DEBUG level (logging.py _QUIET_PREFIXES)

Implements C-OBS-05 from the controls catalog.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness():
    """Liveness probe — returns 200 if the process is running."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Readiness probe — verifies database connectivity.

    Returns 200 if all dependencies are healthy, 503 otherwise.
    The response body always includes per-dependency status for diagnostics.
    """
    checks: dict[str, str] = {}
    all_ok = True

    # Database connectivity check
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "degraded"
        all_ok = False

    status_code = 200 if all_ok else 503
    from starlette.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if all_ok else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        },
    )
