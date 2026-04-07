"""Shared test fixtures for QES Flow backend tests.

Sets required environment variables BEFORE any application code is imported,
so that Pydantic Settings can load without a .env file in CI.
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient


# Set minimal env vars required by Settings — these must exist before
# the FastAPI app is imported (which triggers get_settings()).
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-do-not-use-in-production-0000")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_qesflow")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleTA=")  # 32 bytes b64
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_ALLOWED_HOSTS", "testserver,localhost")
os.environ.setdefault("LOG_FORMAT", "console")

from app.main import app  # noqa: E402 — must come after env setup


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async HTTP client wired to the FastAPI app (no real server needed)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
