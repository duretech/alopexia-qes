#!/usr/bin/env python3
"""Encrypt sensitive identifier columns in the alopexiaqes schema.

Encrypts:
  - doctors.external_idp_id  (adds external_idp_id_hash for lookups)
  - clinics.name             (adds name_hash for lookups)

Idempotent: skips rows whose value already looks encrypted (base64 > 60 chars).
Only touches the alopexiaqes schema.

Run from src/backend/:
    python encrypt_columns.py
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
    """Heuristic: AES-256-GCM base64 output is always > 32 chars.
    Plaintext IDP IDs like 'clinic-phone-+458888899999' are <= 32 chars."""
    return len(value) > 60


async def main() -> None:
    settings = get_settings()
    pg_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    print("Connecting…")
    conn = await asyncpg.connect(pg_url)

    try:
        async with conn.transaction():

            # ── Step 1: Add new columns if they don't exist ─────────────────
            print("\n[1/6] Adding hash columns if not already present…")
            await conn.execute(f"""
                ALTER TABLE {SCHEMA}.doctors
                ADD COLUMN IF NOT EXISTS external_idp_id_hash VARCHAR(64)
            """)
            await conn.execute(f"""
                ALTER TABLE {SCHEMA}.clinics
                ADD COLUMN IF NOT EXISTS name_hash VARCHAR(64)
            """)

            # ── Step 2: Widen columns to hold ciphertext ─────────────────────
            print("[2/6] Widening columns to VARCHAR(2048)…")
            await conn.execute(f"""
                ALTER TABLE {SCHEMA}.doctors
                ALTER COLUMN external_idp_id TYPE VARCHAR(2048)
            """)
            await conn.execute(f"""
                ALTER TABLE {SCHEMA}.clinics
                ALTER COLUMN name TYPE VARCHAR(2048)
            """)

            # ── Step 3: Encrypt doctors.external_idp_id ──────────────────────
            print("[3/6] Encrypting doctors.external_idp_id…")
            doctor_rows = await conn.fetch(
                f"SELECT id, external_idp_id FROM {SCHEMA}.doctors"
            )
            enc_count = skip_count = 0
            for row in doctor_rows:
                doc_id, value = row["id"], row["external_idp_id"]
                if not value:
                    continue
                if _already_encrypted(value):
                    # Already encrypted — ensure hash column is filled
                    try:
                        plaintext = decrypt_field(value)
                        h = hash_identifier(plaintext)
                    except Exception:
                        skip_count += 1
                        continue
                    await conn.execute(
                        f"UPDATE {SCHEMA}.doctors SET external_idp_id_hash = $1 WHERE id = $2",
                        h, doc_id,
                    )
                    skip_count += 1
                else:
                    # Plaintext — encrypt and hash
                    await conn.execute(
                        f"""
                        UPDATE {SCHEMA}.doctors
                        SET external_idp_id      = $1,
                            external_idp_id_hash = $2
                        WHERE id = $3
                        """,
                        encrypt_field(value), hash_identifier(value), doc_id,
                    )
                    enc_count += 1
            print(f"    encrypted={enc_count}  already-encrypted={skip_count}")

            # ── Step 4: Encrypt clinics.name ─────────────────────────────────
            print("[4/6] Encrypting clinics.name…")
            clinic_rows = await conn.fetch(
                f"SELECT id, name FROM {SCHEMA}.clinics"
            )
            enc_count = skip_count = 0
            for row in clinic_rows:
                clinic_id, value = row["id"], row["name"]
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
                        f"UPDATE {SCHEMA}.clinics SET name_hash = $1 WHERE id = $2",
                        h, clinic_id,
                    )
                    skip_count += 1
                else:
                    await conn.execute(
                        f"""
                        UPDATE {SCHEMA}.clinics
                        SET name      = $1,
                            name_hash = $2
                        WHERE id = $3
                        """,
                        encrypt_field(value), hash_identifier(value), clinic_id,
                    )
                    enc_count += 1
            print(f"    encrypted={enc_count}  already-encrypted={skip_count}")

            # ── Step 5: Add NOT NULL constraints on hash columns ──────────────
            print("[5/6] Adding NOT NULL constraints on hash columns…")
            await conn.execute(f"""
                ALTER TABLE {SCHEMA}.doctors
                ALTER COLUMN external_idp_id_hash SET NOT NULL
            """)
            await conn.execute(f"""
                ALTER TABLE {SCHEMA}.clinics
                ALTER COLUMN name_hash SET NOT NULL
            """)

            # ── Step 6: Replace unique constraints ───────────────────────────
            print("[6/6] Replacing unique constraints with hash-based ones…")

            # doctors: drop old plaintext constraint, add hash-based one
            exists = await conn.fetchval("""
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_doctor_tenant_idp'
                  AND conrelid = (
                      SELECT oid FROM pg_class
                      WHERE relname = 'doctors'
                        AND relnamespace = (
                            SELECT oid FROM pg_namespace WHERE nspname = $1
                        )
                  )
            """, SCHEMA)
            if exists:
                await conn.execute(
                    f"ALTER TABLE {SCHEMA}.doctors DROP CONSTRAINT uq_doctor_tenant_idp"
                )
                print("    dropped uq_doctor_tenant_idp")

            exists = await conn.fetchval("""
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_doctor_tenant_idp_hash'
                  AND conrelid = (
                      SELECT oid FROM pg_class
                      WHERE relname = 'doctors'
                        AND relnamespace = (
                            SELECT oid FROM pg_namespace WHERE nspname = $1
                        )
                  )
            """, SCHEMA)
            if not exists:
                await conn.execute(f"""
                    ALTER TABLE {SCHEMA}.doctors
                    ADD CONSTRAINT uq_doctor_tenant_idp_hash
                    UNIQUE (tenant_id, external_idp_id_hash)
                """)
                print("    created uq_doctor_tenant_idp_hash")

            # clinics: drop old plaintext constraint, add hash-based one
            exists = await conn.fetchval("""
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_clinic_tenant_name'
                  AND conrelid = (
                      SELECT oid FROM pg_class
                      WHERE relname = 'clinics'
                        AND relnamespace = (
                            SELECT oid FROM pg_namespace WHERE nspname = $1
                        )
                  )
            """, SCHEMA)
            if exists:
                await conn.execute(
                    f"ALTER TABLE {SCHEMA}.clinics DROP CONSTRAINT uq_clinic_tenant_name"
                )
                print("    dropped uq_clinic_tenant_name")

            exists = await conn.fetchval("""
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_clinic_tenant_name_hash'
                  AND conrelid = (
                      SELECT oid FROM pg_class
                      WHERE relname = 'clinics'
                        AND relnamespace = (
                            SELECT oid FROM pg_namespace WHERE nspname = $1
                        )
                  )
            """, SCHEMA)
            if not exists:
                await conn.execute(f"""
                    ALTER TABLE {SCHEMA}.clinics
                    ADD CONSTRAINT uq_clinic_tenant_name_hash
                    UNIQUE (tenant_id, name_hash)
                """)
                print("    created uq_clinic_tenant_name_hash")

        print("\nDone — all changes committed.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
