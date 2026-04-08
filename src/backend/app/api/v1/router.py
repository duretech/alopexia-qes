"""Versioned API v1 router — aggregates all v1 endpoint routers.

New endpoint modules should be imported here and included on `api_router`.
All v1 routes are served under the /api/v1 prefix (set in main.py).
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, prescriptions, pharmacy, admin, auth

api_router = APIRouter()

# Health checks are mounted at /health/* (no /api/v1 prefix — they're
# infrastructure endpoints). They're included on the main app directly
# in main.py rather than here.

# Authentication (portal login + MFA)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Prescription endpoints (doctor upload)
api_router.include_router(
    prescriptions.router, prefix="/prescriptions", tags=["prescriptions"],
)

# Pharmacy endpoints (view, download, dispense)
api_router.include_router(
    pharmacy.router, prefix="/pharmacy", tags=["pharmacy"],
)

# Admin/compliance endpoints (audit export, legal holds, deletions, manual review)
api_router.include_router(
    admin.router, prefix="/admin", tags=["admin"],
)
