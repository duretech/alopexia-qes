"""SQLAlchemy declarative base and common column mixins."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Boolean, text, MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, declared_attr

# All tables live in the 'alopexiaqes' schema.
# This is enforced at the metadata level so every model, migration,
# and query automatically targets the correct schema.
SCHEMA_NAME = "alopexiaqes"


class Base(DeclarativeBase):
    """Base class for all ORM models. Schema set to alopexiaqes."""
    metadata = MetaData(schema=SCHEMA_NAME)


class TenantScopedMixin:
    """Mixin that adds tenant_id column for multi-tenant isolation.
    Every tenant-scoped query MUST filter by tenant_id."""

    @declared_attr
    def tenant_id(cls):
        return Column(
            UUID(as_uuid=True),
            nullable=False,
            index=True,
            comment="Tenant scope — all queries MUST filter on this",
        )


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        comment="Row creation timestamp (UTC, immutable)",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        comment="Last update timestamp (UTC)",
    )


class SoftDeleteMixin:
    """Mixin for soft-delete support. Records are marked deleted, not removed."""

    is_deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("FALSE"),
        index=True,
        comment="Soft delete flag — TRUE means logically deleted",
    )
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of soft deletion (UTC)",
    )
    deleted_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who performed the soft deletion",
    )


def generate_uuid() -> uuid.UUID:
    """Generate a new UUID v4 for primary keys."""
    return uuid.uuid4()
