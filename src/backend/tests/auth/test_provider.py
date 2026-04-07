"""Tests for authentication providers."""

import pytest

from app.services.auth.provider import (
    MockAuthProvider,
    IdentityClaims,
    get_auth_provider,
)


class TestMockAuthProvider:
    @pytest.fixture
    def provider(self):
        return MockAuthProvider()

    async def test_valid_mock_token(self, provider):
        claims = await provider.validate_token("mock:doctor:doc-001:doc@example.com")
        assert claims is not None
        assert claims.external_id == "doc-001"
        assert claims.email == "doc@example.com"
        assert claims.provider == "mock"
        assert claims.mfa_completed is True

    async def test_invalid_token_returns_none(self, provider):
        assert await provider.validate_token("") is None
        assert await provider.validate_token("invalid") is None
        assert await provider.validate_token("mock:short") is None

    async def test_non_mock_token_returns_none(self, provider):
        assert await provider.validate_token("bearer:some-jwt") is None

    async def test_raw_claims_preserved(self, provider):
        claims = await provider.validate_token("mock:doctor:doc-001:doc@test.com")
        assert claims.raw_claims is not None
        assert "mock_token" in claims.raw_claims

    async def test_login_url(self, provider):
        url = await provider.get_login_url("http://localhost/callback", "state123")
        assert "redirect_uri" in url
        assert "state123" in url


class TestGetAuthProvider:
    def test_mock_provider(self):
        provider = get_auth_provider("mock")
        assert isinstance(provider, MockAuthProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown auth provider"):
            get_auth_provider("nonexistent")


class TestIdentityClaims:
    def test_defaults(self):
        claims = IdentityClaims(external_id="ext-1", email="test@test.com")
        assert claims.email_verified is False
        assert claims.mfa_completed is False
        assert claims.provider == ""
