"""Authentication service — identity verification and session management.

Public API:
    AuthenticatedUser   — Identity of the currently authenticated user
    UserType            — Enum of user table types
    get_auth_provider() — Get the configured auth provider
    SessionManager      — Server-side session lifecycle
"""

from app.services.auth.models import AuthenticatedUser, UserType

__all__ = [
    "AuthenticatedUser",
    "UserType",
]
