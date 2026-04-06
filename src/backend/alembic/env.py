"""Alembic migration environment configuration.

Targets the 'alopexiaqes' PostgreSQL schema. All tables and the Alembic
version table itself live in this schema.
"""

import os
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text
from alembic import context

# Add backend app to path so models can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import Base, SCHEMA_NAME
# Import all models so Alembic can detect them
import app.models  # noqa: F401

config = context.config

# Allow DATABASE_URL env var to override alembic.ini
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Alembic needs sync driver — swap asyncpg for psycopg2 if needed
    database_url = database_url.replace("+asyncpg", "+psycopg2")
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL script."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=SCHEMA_NAME,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # Set search_path so the migration sees the correct schema
        connection.execute(text(f"SET search_path TO {SCHEMA_NAME}, public"))
        connection.dialect.default_schema_name = SCHEMA_NAME

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=SCHEMA_NAME,
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
