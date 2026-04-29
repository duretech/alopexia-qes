"""Add temp_pin_encrypted and pin_set to phone_auth_accounts.

Revision ID: 006_pin_setup_flow
Revises: 005_encrypt_sensitive_ids
Create Date: 2026-04-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_pin_setup_flow"
down_revision: Union[str, None] = "005_encrypt_sensitive_ids"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "alopexiaqes"


def upgrade() -> None:
    # Allow pin_encrypted to be NULL (it will be NULL until user sets their own PIN)
    op.alter_column(
        "phone_auth_accounts",
        "pin_encrypted",
        nullable=True,
        schema=SCHEMA,
    )

    # Temporary PIN set by admin when creating an account; cleared after user sets their own
    op.add_column(
        "phone_auth_accounts",
        sa.Column(
            "temp_pin_encrypted",
            sa.Text(),
            nullable=True,
            comment="AES-GCM encrypted temporary PIN set by admin; cleared after user sets own PIN",
        ),
        schema=SCHEMA,
    )

    # False until the user has completed first-login PIN setup
    op.add_column(
        "phone_auth_accounts",
        sa.Column(
            "pin_set",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
            comment="True once user has set their own permanent PIN via first-login setup",
        ),
        schema=SCHEMA,
    )

    # Existing accounts that already have a pin_encrypted are considered fully set up
    op.execute(
        f"UPDATE {SCHEMA}.phone_auth_accounts SET pin_set = TRUE WHERE pin_encrypted IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("phone_auth_accounts", "pin_set", schema=SCHEMA)
    op.drop_column("phone_auth_accounts", "temp_pin_encrypted", schema=SCHEMA)
    op.alter_column(
        "phone_auth_accounts",
        "pin_encrypted",
        nullable=False,
        schema=SCHEMA,
    )
