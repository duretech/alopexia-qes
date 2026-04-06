"""Database engine and session management."""

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import get_settings
from app.db.base import SCHEMA_NAME


def create_engine():
    settings = get_settings()
    eng = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        echo=settings.app_debug,
        # Set search_path so unqualified table names resolve to our schema
        connect_args={"server_settings": {"search_path": f"{SCHEMA_NAME},public"}},
    )
    return eng


engine = None
AsyncSessionLocal = None


def init_db():
    global engine, AsyncSessionLocal
    engine = create_engine()
    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a database session."""
    if AsyncSessionLocal is None:
        init_db()
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
