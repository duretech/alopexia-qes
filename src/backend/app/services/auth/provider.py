"""Authentication provider abstraction — OIDC/SAML/mock.

The platform does NOT store passwords. Authentication is delegated to an
external Identity Provider via OIDC or SAML. The provider abstraction allows:
  - Mock provider for local development and testing
  - OIDC provider for production (Dokobit, Auth0, Azure AD, etc.)
  - SAML provider if required by enterprise customers

The provider's job is to:
  1. Validate an authentication token/assertion
  2. Return the external identity claims (sub, email, name, etc.)
  3. NOT perform authorization — that's the authz layer's job

Implements C-AUTH-01 from the controls catalog.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class IdentityClaims:
    """Claims extracted from the IdP token/assertion.

    These are used to look up or provision the user in our database.
    """
    external_id: str          # OIDC 'sub' or SAML NameID — unique at IdP
    email: str                # Verified email from IdP
    full_name: str = ""       # Display name
    email_verified: bool = False
    mfa_completed: bool = False
    provider: str = ""        # Which IdP issued this (e.g., "oidc", "saml", "mock")
    raw_claims: dict | None = None  # Preserved for audit/debugging


@runtime_checkable
class AuthProvider(Protocol):
    """Protocol for authentication providers."""

    async def validate_token(self, token: str) -> IdentityClaims | None:
        """Validate an authentication token and return identity claims.

        Args:
            token: The bearer token, session cookie value, or SAML assertion.

        Returns:
            IdentityClaims if the token is valid, None if invalid/expired.
        """
        ...

    async def get_login_url(self, redirect_uri: str, state: str) -> str:
        """Get the IdP login URL for initiating authentication.

        Args:
            redirect_uri: Where the IdP should redirect after login.
            state: Anti-CSRF state parameter.

        Returns:
            Full IdP login URL.
        """
        ...


class MockAuthProvider:
    """Mock authentication provider for local development and testing.

    Accepts tokens in the format: mock:<user_type>:<external_id>:<tenant_id>
    e.g., mock:doctor:doc-001:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee

    In production, AUTH_PROVIDER must NOT be "mock".
    """

    async def validate_token(self, token: str) -> IdentityClaims | None:
        """Parse a mock token into identity claims.

        Mock token format: mock:<user_type>:<external_id>:<email>
        """
        if not token or not token.startswith("mock:"):
            return None

        parts = token.split(":")
        if len(parts) < 4:
            return None

        _, user_type, external_id, email = parts[0], parts[1], parts[2], parts[3]

        return IdentityClaims(
            external_id=external_id,
            email=email,
            full_name=f"Mock {user_type.title()} ({external_id})",
            email_verified=True,
            mfa_completed=True,  # Mock always passes MFA
            provider="mock",
            raw_claims={"mock_user_type": user_type, "mock_token": token},
        )

    async def get_login_url(self, redirect_uri: str, state: str) -> str:
        """Mock login URL — not used in mock flow, returns placeholder."""
        return f"/mock-login?redirect_uri={redirect_uri}&state={state}"


def get_auth_provider(provider_name: str) -> AuthProvider:
    """Factory to get the configured auth provider.

    Args:
        provider_name: From settings.auth_provider ("mock", "oidc", "saml").

    Returns:
        An AuthProvider instance.

    Raises:
        ValueError: If provider_name is not recognized.
    """
    if provider_name == "mock":
        return MockAuthProvider()

    # OIDC and SAML providers will be implemented when real IdP integration
    # is needed. The interface is defined — swap MockAuthProvider for the
    # real implementation.
    raise ValueError(
        f"Unknown auth provider '{provider_name}'. "
        f"Available: mock. "
        f"OIDC/SAML providers require implementation — see docs/security.md."
    )
