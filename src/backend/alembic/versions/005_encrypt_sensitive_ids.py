"""Encrypt external_idp_id in doctors and name in clinics.

Revision ID: 005_encrypt_ids
Revises: 004_clinic_portal
Create Date: 2026-04-17

Strategy:
  - Add a *_hash column (SHA-256, deterministic) for unique constraints/lookups.
  - Widen the existing column and overwrite with AES-256-GCM ciphertext.
  - Drop old unique constraints (plaintext) and create new ones on the hash.

This touches ONLY the alopexiaqes schema.
"""

from typing import Sequence, Union
import base64
import hashlib
import os
from pathlib import Path

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "005_encrypt_ids"
down_revision: Union[str, None] = "004_clinic_portal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "alopexiaqes"


# ---------------------------------------------------------------------------
# Helpers — embedded so the migration is self-contained
# ---------------------------------------------------------------------------

def _load_key() -> bytes:
    """Return the raw 32-byte AES key from the environment / .env file."""
    key_b64 = os.getenv("FIELD_ENCRYPTION_KEY")
    if not key_b64:
        # Try loading from project-root .env
        env_path = Path(__file__).resolve().parents[4] / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("FIELD_ENCRYPTION_KEY="):
                    key_b64 = line.split("=", 1)[1].strip()
                    break
    if not key_b64:
        raise RuntimeError(
            "FIELD_ENCRYPTION_KEY not set. Export it before running alembic."
        )
    return base64.b64decode(key_b64)


def _encrypt(plaintext: str, key: bytes) -> str:
    """AES-256-GCM encrypt matching app/utils/encryption.py format."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def _hash(value: str) -> str:
    """SHA-256 matching hash_identifier() in app/utils/encryption.py."""
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

def upgrade() -> None:
    conn = op.get_bind()
    key = _load_key()

    # ── doctors ─────────────────────────────────────────────────────────────
    # 1. Add hash + widen existing column (keep nullable during fill)
    op.add_column(
        "doctors",
        sa.Column("external_idp_id_hash", sa.String(64), nullable=True),
        schema=SCHEMA,
    )
    op.alter_column(
        "doctors", "external_idp_id",
        existing_type=sa.String(500),
        type_=sa.String(2048),
        schema=SCHEMA,
    )

    # 2. Populate hash + encrypt existing rows
    rows = conn.execute(
        text(f'SELECT id, external_idp_id FROM "{SCHEMA}".doctors')
    ).fetchall()

    for row_id, plaintext in rows:
        if plaintext:
            conn.execute(
                text(
                    f'UPDATE "{SCHEMA}".doctors '
                    f'SET external_idp_id = :enc, external_idp_id_hash = :hsh '
                    f'WHERE id = :id'
                ),
                {"enc": _encrypt(plaintext, key), "hsh": _hash(plaintext), "id": row_id},
            )

    # 3. Make hash NOT NULL, drop old unique constraint, create new one on hash
    op.alter_column(
        "doctors", "external_idp_id_hash",
        existing_type=sa.String(64),
        nullable=False,
        schema=SCHEMA,
    )
    op.drop_constraint("uq_doctor_tenant_idp", "doctors", schema=SCHEMA)
    op.create_unique_constraint(
        "uq_doctor_tenant_idp_hash",
        "doctors",
        ["tenant_id", "external_idp_id_hash"],
        schema=SCHEMA,
    )

    # ── clinics ─────────────────────────────────────────────────────────────
    # 1. Add hash + widen existing column (keep nullable during fill)
    op.add_column(
        "clinics",
        sa.Column("name_hash", sa.String(64), nullable=True),
        schema=SCHEMA,
    )
    op.alter_column(
        "clinics", "name",
        existing_type=sa.String(500),
        type_=sa.String(2048),
        schema=SCHEMA,
    )

    # 2. Populate hash + encrypt existing rows
    rows = conn.execute(
        text(f'SELECT id, name FROM "{SCHEMA}".clinics')
    ).fetchall()

    for row_id, plaintext in rows:
        if plaintext:
            conn.execute(
                text(
                    f'UPDATE "{SCHEMA}".clinics '
                    f'SET name = :enc, name_hash = :hsh '
                    f'WHERE id = :id'
                ),
                {"enc": _encrypt(plaintext, key), "hsh": _hash(plaintext), "id": row_id},
            )

    # 3. Make hash NOT NULL, drop old unique constraint, create new one on hash
    op.alter_column(
        "clinics", "name_hash",
        existing_type=sa.String(64),
        nullable=False,
        schema=SCHEMA,
    )
    op.drop_constraint("uq_clinic_tenant_name", "clinics", schema=SCHEMA)
    op.create_unique_constraint(
        "uq_clinic_tenant_name_hash",
        "clinics",
        ["tenant_id", "name_hash"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade not implemented — restore from a pre-migration backup."
    )
