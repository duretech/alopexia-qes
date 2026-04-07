"""Server-side session management.

Sessions are stored in the session_records PostgreSQL table, NOT in JWTs.
This design choice (docs/architecture.md §7) gives us:
  - Immediate revocation (no waiting for token expiry)
  - Concurrent session limits
  - Server-side idle/absolute timeout enforcement
  - Session binding to IP/user-agent for anomaly detection

Session tokens are 32-byte cryptographically random values. Only their
SHA-256 hash is stored in the database — the raw token never touches
persistent storage.

Implements C-AUTH-03, C-AUTH-04, C-AUTH-05 from the controls catalog.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.base import SCHEMA_NAME
from app.models.session import SessionRecord
from app.services.auth.models import AuthenticatedUser, UserType, Role

logger = get_logger(component="session_manager")

# Token length in bytes (256 bits of entropy)
_TOKEN_BYTES = 32


def _generate_session_token() -> str:
    """Generate a cryptographically random session token."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def _hash_token(token: str) -> str:
    """SHA-256 hash of the session token for storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SessionManager:
    """Manages server-side session lifecycle."""

    def __init__(
        self,
        *,
        idle_timeout_minutes: int = 30,
        absolute_timeout_minutes: int = 480,
        max_concurrent_sessions: int = 3,
    ):
        self.idle_timeout = timedelta(minutes=idle_timeout_minutes)
        self.absolute_timeout = timedelta(minutes=absolute_timeout_minutes)
        self.max_concurrent = max_concurrent_sessions

    async def create_session(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        user_type: str,
        tenant_id: UUID,
        login_ip: str,
        login_user_agent: str | None = None,
        login_method: str = "oidc",
        mfa_verified: bool = False,
    ) -> tuple[str, SessionRecord]:
        """Create a new session and return (raw_token, session_record).

        Enforces concurrent session limits by deactivating oldest sessions
        if the limit is exceeded.

        Args:
            db: Active database session.
            user_id: The authenticated user's ID.
            user_type: User type string (doctor, pharmacy_user, etc.).
            tenant_id: User's tenant ID.
            login_ip: Client IP at login time.
            login_user_agent: Client user-agent at login time.
            login_method: How the user authenticated (oidc, saml, mock).
            mfa_verified: Whether MFA was completed.

        Returns:
            Tuple of (raw_session_token, SessionRecord).
            The raw token is returned ONCE — it must be sent to the client
            and never stored server-side.
        """
        now = datetime.now(timezone.utc)

        # Enforce concurrent session limit
        await self._enforce_concurrent_limit(db, user_id, tenant_id)

        # Generate token
        raw_token = _generate_session_token()
        token_hash = _hash_token(raw_token)

        session = SessionRecord(
            user_id=user_id,
            user_type=user_type,
            tenant_id=tenant_id,
            token_hash=token_hash,
            is_active=True,
            last_activity_at=now,
            expires_at=now + self.absolute_timeout,
            idle_expires_at=now + self.idle_timeout,
            login_ip=login_ip,
            login_user_agent=login_user_agent[:1000] if login_user_agent else None,
            login_method=login_method,
            mfa_verified=mfa_verified,
        )
        db.add(session)
        await db.flush()

        logger.info(
            "session_created",
            user_id=str(user_id),
            user_type=user_type,
            session_id=str(session.id),
            login_method=login_method,
            mfa_verified=mfa_verified,
        )

        return raw_token, session

    async def validate_session(
        self,
        db: AsyncSession,
        token: str,
    ) -> SessionRecord | None:
        """Validate a session token and return the session record.

        Checks:
          1. Token hash exists in session_records
          2. Session is active (not ended)
          3. Absolute timeout not exceeded
          4. Idle timeout not exceeded

        If valid, updates last_activity_at and idle_expires_at.

        Returns:
            SessionRecord if valid, None if invalid/expired.
        """
        token_hash = _hash_token(token)
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(SessionRecord).where(
                SessionRecord.token_hash == token_hash,
                SessionRecord.is_active == True,  # noqa: E712
            )
        )
        session = result.scalar_one_or_none()

        if session is None:
            return None

        # Check absolute timeout
        if now >= session.expires_at:
            await self._end_session(db, session, "absolute_timeout")
            return None

        # Check idle timeout
        if now >= session.idle_expires_at:
            await self._end_session(db, session, "idle_timeout")
            return None

        # Valid — update activity timestamp
        session.last_activity_at = now
        session.idle_expires_at = now + self.idle_timeout
        await db.flush()

        return session

    async def end_session(
        self,
        db: AsyncSession,
        token: str,
        reason: str = "logout",
    ) -> bool:
        """End a session by token (logout).

        Returns True if a session was ended, False if token not found.
        """
        token_hash = _hash_token(token)

        result = await db.execute(
            select(SessionRecord).where(
                SessionRecord.token_hash == token_hash,
                SessionRecord.is_active == True,  # noqa: E712
            )
        )
        session = result.scalar_one_or_none()

        if session is None:
            return False

        await self._end_session(db, session, reason)
        return True

    async def revoke_all_sessions(
        self,
        db: AsyncSession,
        user_id: UUID,
        tenant_id: UUID,
        reason: str = "admin_revocation",
    ) -> int:
        """Revoke all active sessions for a user. Returns count revoked."""
        now = datetime.now(timezone.utc)

        result = await db.execute(
            update(SessionRecord)
            .where(
                SessionRecord.user_id == user_id,
                SessionRecord.tenant_id == tenant_id,
                SessionRecord.is_active == True,  # noqa: E712
            )
            .values(
                is_active=False,
                ended_at=now,
                end_reason=reason,
            )
        )
        count = result.rowcount

        if count > 0:
            logger.warning(
                "sessions_revoked",
                user_id=str(user_id),
                count=count,
                reason=reason,
            )

        return count

    async def _enforce_concurrent_limit(
        self, db: AsyncSession, user_id: UUID, tenant_id: UUID
    ) -> None:
        """End oldest sessions if concurrent limit would be exceeded."""
        result = await db.execute(
            select(SessionRecord)
            .where(
                SessionRecord.user_id == user_id,
                SessionRecord.tenant_id == tenant_id,
                SessionRecord.is_active == True,  # noqa: E712
            )
            .order_by(SessionRecord.created_at.asc())
        )
        active_sessions = list(result.scalars().all())

        # Need room for the new session
        excess = len(active_sessions) - (self.max_concurrent - 1)
        if excess > 0:
            for session in active_sessions[:excess]:
                await self._end_session(db, session, "concurrent_limit")
            logger.info(
                "concurrent_sessions_limited",
                user_id=str(user_id),
                ended_count=excess,
            )

    async def _end_session(
        self, db: AsyncSession, session: SessionRecord, reason: str
    ) -> None:
        """Mark a session as ended."""
        now = datetime.now(timezone.utc)
        session.is_active = False
        session.ended_at = now
        session.end_reason = reason
        await db.flush()

        logger.info(
            "session_ended",
            session_id=str(session.id),
            user_id=str(session.user_id),
            reason=reason,
        )
