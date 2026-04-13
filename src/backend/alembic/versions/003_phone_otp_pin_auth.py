"""Add phone OTP + encrypted PIN auth tables.

Revision ID: 003_phone_auth
Revises: 002_totp
Create Date: 2026-04-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003_phone_auth"
down_revision: Union[str, None] = "002_totp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "alopexiaqes"


def upgrade() -> None:
    op.create_table(
        "phone_auth_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_type", sa.String(50), nullable=False),
        sa.Column("portal", sa.String(20), nullable=False),
        sa.Column("phone_hash", sa.String(64), nullable=False),
        sa.Column("phone_encrypted", sa.Text(), nullable=False),
        sa.Column("pin_encrypted", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "phone_hash", "portal", name="uq_phone_auth_tenant_phone_portal"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_phone_auth_lookup",
        "phone_auth_accounts",
        ["tenant_id", "phone_hash", "portal"],
        schema=SCHEMA,
    )
    op.execute(f"""
        CREATE TRIGGER trg_phone_auth_accounts_updated_at
        BEFORE UPDATE ON {SCHEMA}.phone_auth_accounts
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.set_updated_at();
    """)

    op.create_table(
        "phone_otp_challenges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.phone_auth_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("otp_encrypted", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_phone_otp_account", "phone_otp_challenges", ["tenant_id", "account_id"], schema=SCHEMA)
    op.create_index("ix_phone_otp_expiry", "phone_otp_challenges", ["tenant_id", "expires_at"], schema=SCHEMA)
    op.execute(f"""
        CREATE TRIGGER trg_phone_otp_challenges_updated_at
        BEFORE UPDATE ON {SCHEMA}.phone_otp_challenges
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.set_updated_at();
    """)


def downgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS trg_phone_otp_challenges_updated_at ON {SCHEMA}.phone_otp_challenges")
    op.drop_table("phone_otp_challenges", schema=SCHEMA)

    op.execute(f"DROP TRIGGER IF EXISTS trg_phone_auth_accounts_updated_at ON {SCHEMA}.phone_auth_accounts")
    op.drop_table("phone_auth_accounts", schema=SCHEMA)

