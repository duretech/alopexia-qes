"""Short-lived signed JWTs for MFA challenge and enrollment (HS256 + APP_SECRET_KEY)."""

from __future__ import annotations

import time
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings


def _secret() -> str:
    return get_settings().app_secret_key


def issue_mfa_enrollment_token(
    *,
    user_id: str,
    tenant_id: str,
    user_type: str,
    email: str,
    totp_secret: str,
    ttl_seconds: int = 600,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "typ": "mfa_enroll",
        "sub": user_id,
        "tid": tenant_id,
        "ut": user_type,
        "em": email,
        "sec": totp_secret,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def issue_mfa_challenge_token(
    *,
    user_id: str,
    tenant_id: str,
    user_type: str,
    ttl_seconds: int = 600,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "typ": "mfa_challenge",
        "sub": user_id,
        "tid": tenant_id,
        "ut": user_type,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_pending_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _secret(), algorithms=["HS256"])


def is_jwt_error(exc: Exception) -> bool:
    return isinstance(exc, JWTError)
