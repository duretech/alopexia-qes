#!/usr/bin/env python3
"""Encrypt sensitive columns in pharmacy_users and admin_users.

Encrypts:
  - pharmacy_users.external_idp_id  (adds external_idp_id_hash for lookups)
  - pharmacy_users.pharmacy_name
  - admin_users.external_idp_id     (adds external_idp_id_hash for lookups)

Idempotent: skips rows whose value already looks encrypted (length > 60).
Only touches the alopexiaqes schema.

Run from src/backend/:
    python encrypt_pharmacy_admin_columns.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import asyncpg

from app.core.config import get_settings
from app.utils.encryption import encrypt_field, hash_identifier, decrypt_field

SCHEMA = "alopexiaqes"


def _already_encrypted(value: str) -> bool:
    """AES-256-GCM base64 output is always > 60 chars; short values are plaintext."""
    return len(value) > 60


async def _encrypt_idp_column(conn, table: str, constraint_old: str, constraint_new: str) -> None:
    """Add external_idp_id_hash, encrypt external_idp_id, swap unique constraint."""

    # 1. Add hash column + widen existing column
    await conn.execute(f"""
        ALTER TABLE {SCHEMA}.{table}
        ADD COLUMN IF NOT EXISTS external_idp_id_hash VARCHAR(64)
    """)
    await conn.execute(f"""
        ALTER TABLE {SCHEMA}.{table}
        ALTER COLUMN external_idp_id TYPE VARCHAR(2048)
    """)

    # 2. Encrypt existing rows + populate hash
    rows = await conn.fetch(
        f"SELECT id, external_idp_id FROM {SCHEMA}.{table}"
    )
    enc_count = skip_count = 0
    for row in rows:
        row_id, value = row["id"], row["external_idp_id"]
        if not value:
            continue
        if _already_encrypted(value):
            try:
                plaintext = decrypt_field(value)
                h = hash_identifier(plaintext)
            except Exception:
                skip_count += 1
                continue
            await conn.execute(
                f"UPDATE {SCHEMA}.{table} SET external_idp_id_hash = $1 WHERE id = $2",
                h, row_id,
            )
            skip_count += 1
        else:
            await conn.execute(
                f"""
                UPDATE {SCHEMA}.{table}
                SET external_idp_id      = $1,
                    external_idp_id_hash = $2
                WHERE id = $3
                """,
                encrypt_field(value), hash_identifier(value), row_id,
            )
            enc_count += 1
    print(f"    {table}.external_idp_id — encrypted={enc_count}  already-encrypted={skip_count}")

    # 3. NOT NULL on hash
    await conn.execute(f"""
        ALTER TABLE {SCHEMA}.{table}
        ALTER COLUMN external_idp_id_hash SET NOT NULL
    """)

    # 4. Swap unique constraint from plaintext → hash
    exists = await conn.fetchval(f"""
        SELECT 1 FROM pg_constraint
        WHERE conname = '{constraint_old}'
          AND conrelid = (
              SELECT oid FROM pg_class
              WHERE relname = '{table}'
                AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = $1)
          )
    """, SCHEMA)
    if exists:
        await conn.execute(
            f"ALTER TABLE {SCHEMA}.{table} DROP CONSTRAINT {constraint_old}"
        )
        print(f"    dropped {constraint_old}")

    exists = await conn.fetchval(f"""
        SELECT 1 FROM pg_constraint
        WHERE conname = '{constraint_new}'
          AND conrelid = (
              SELECT oid FROM pg_class
              WHERE relname = '{table}'
                AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = $1)
          )
    """, SCHEMA)
    if not exists:
        await conn.execute(f"""
            ALTER TABLE {SCHEMA}.{table}
            ADD CONSTRAINT {constraint_new}
            UNIQUE (tenant_id, external_idp_id_hash)
        """)
        print(f"    created {constraint_new}")


async def main() -> None:
    settings = get_settings()
    pg_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    print("Connecting…")
    conn = await asyncpg.connect(pg_url)

    try:
        async with conn.transaction():

            # ── pharmacy_users.external_idp_id ───────────────────────────────
            print("\n[1/3] pharmacy_users.external_idp_id")
            await _encrypt_idp_column(
                conn,
                table="pharmacy_users",
                constraint_old="uq_pharma_tenant_idp",
                constraint_new="uq_pharma_tenant_idp_hash",
            )

            # ── pharmacy_users.pharmacy_name ─────────────────────────────────
            print("\n[2/3] pharmacy_users.pharmacy_name")
            await conn.execute(f"""
                ALTER TABLE {SCHEMA}.pharmacy_users
                ALTER COLUMN pharmacy_name TYPE VARCHAR(2048)
            """)
            rows = await conn.fetch(
                f"SELECT id, pharmacy_name FROM {SCHEMA}.pharmacy_users"
            )
            enc_count = skip_count = 0
            for row in rows:
                row_id, value = row["id"], row["pharmacy_name"]
                if not value:
                    continue
                if _already_encrypted(value):
                    skip_count += 1
                else:
                    await conn.execute(
                        f"UPDATE {SCHEMA}.pharmacy_users SET pharmacy_name = $1 WHERE id = $2",
                        encrypt_field(value), row_id,
                    )
                    enc_count += 1
            print(f"    pharmacy_users.pharmacy_name — encrypted={enc_count}  already-encrypted={skip_count}")

            # ── admin_users.external_idp_id ──────────────────────────────────
            print("\n[3/3] admin_users.external_idp_id")
            await _encrypt_idp_column(
                conn,
                table="admin_users",
                constraint_old="uq_admin_tenant_idp",
                constraint_new="uq_admin_tenant_idp_hash",
            )

        print("\nDone — all changes committed.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
