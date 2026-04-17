"""Make prescriptions.patient_id nullable for clinic-direct uploads.

Revision ID: 004_clinic_portal
Revises: 003_phone_auth
Create Date: 2026-04-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004_clinic_portal"
down_revision: Union[str, None] = "003_phone_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "alopexiaqes"


def upgrade() -> None:
    op.alter_column(
        "prescriptions",
        "patient_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.alter_column(
        "prescriptions",
        "patient_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
        schema=SCHEMA,
    )
