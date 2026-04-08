"""Add totp_credentials for authenticator-app MFA.

Revision ID: 002_totp
Revises: 001_initial
Create Date: 2026-04-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002_totp"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "alopexiaqes"


def upgrade() -> None:
    op.create_table(
        "totp_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "user_type",
            sa.String(50),
            nullable=False,
            comment="doctor, pharmacy_user, admin_user, auditor",
        ),
        sa.Column(
            "secret_encrypted",
            sa.Text(),
            nullable=False,
            comment="AES-GCM ciphertext of base32 TOTP secret",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "user_id", "user_type", name="uq_totp_tenant_user_type"),
        schema=SCHEMA,
    )
    op.create_index("ix_totp_tenant_user", "totp_credentials", ["tenant_id", "user_id"], schema=SCHEMA)
    op.execute(f"""
        CREATE TRIGGER trg_totp_credentials_updated_at
        BEFORE UPDATE ON {SCHEMA}.totp_credentials
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.set_updated_at();
    """)


def downgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS trg_totp_credentials_updated_at ON {SCHEMA}.totp_credentials")
    op.drop_table("totp_credentials", schema=SCHEMA)
