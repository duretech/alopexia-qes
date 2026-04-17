#!/usr/bin/env python3
"""Seed 4 clinic accounts into the alopexiaqes schema.

Creates:
  - 4 clinic rows
  - 4 doctor rows (one per clinic, each is the clinic's login identity)
  - 4 phone_auth_accounts (portal = 'doctor', user_type = 'doctor')

Run from src/backend/:
    python seed_clinics.py

All inserts are idempotent (ON CONFLICT … DO UPDATE), so re-running is safe.
Only touches the alopexiaqes schema.
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Ensure src/backend is importable
sys.path.insert(0, str(Path(__file__).parent))

import asyncpg

from app.core.config import get_settings
from app.utils.encryption import encrypt_field, hash_identifier

SCHEMA = "alopexiaqes"

CLINICS = [
    {
        "name":  "Alopexia Clinic One",
        "phone": "+458888899999",
        "pin":   "847291",
    },
    {
        "name":  "Alopexia Clinic Two",
        "phone": "+468888899999",
        "pin":   "362815",
    },
    {
        "name":  "Alopexia Clinic Three",
        "phone": "+488888899999",
        "pin":   "591473",
    },
    {
        "name":  "Alopexia Clinic Four",
        "phone": "+498888899999",
        "pin":   "728364",
    },
]


async def main() -> None:
    settings = get_settings()
    pg_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    print("Connecting…")
    conn = await asyncpg.connect(pg_url)

    try:
        # ── Find the active tenant ────────────────────────────────────────
        tenant = await conn.fetchrow(
            f"SELECT id, name FROM {SCHEMA}.tenants"
            f" WHERE is_deleted = FALSE ORDER BY created_at LIMIT 1"
        )
        if not tenant:
            print("ERROR: No tenant found. Create a tenant first.")
            return

        tenant_id = tenant["id"]
        print(f"Tenant : {tenant['name']} ({tenant_id})\n")

        async with conn.transaction():
            for c in CLINICS:
                print(f"--- {c['name']} ---")

                # ── 1. Clinic ─────────────────────────────────────────────
                clinic_name_enc  = encrypt_field(c["name"])
                clinic_name_hash = hash_identifier(c["name"])
                clinic_row = await conn.fetchrow(
                    f"""
                    INSERT INTO {SCHEMA}.clinics (id, tenant_id, name, name_hash, is_active)
                    VALUES ($1, $2, $3, $4, TRUE)
                    ON CONFLICT ON CONSTRAINT uq_clinic_tenant_name_hash
                        DO UPDATE SET is_active = TRUE
                    RETURNING id
                    """,
                    uuid.uuid4(), tenant_id, clinic_name_enc, clinic_name_hash,
                )
                clinic_id = clinic_row["id"]
                print(f"  clinic_id  : {clinic_id}")

                # ── 2. Doctor row (clinic's authenticated identity) ────────
                ext_idp_plaintext = f"clinic-phone-{c['phone']}"
                ext_idp_enc       = encrypt_field(ext_idp_plaintext)
                ext_idp_hash      = hash_identifier(ext_idp_plaintext)
                name_enc          = encrypt_field(c["name"])
                mail_enc          = encrypt_field(f"account{c['phone']}@alopexia.local")

                doctor_row = await conn.fetchrow(
                    f"""
                    INSERT INTO {SCHEMA}.doctors (
                        id, tenant_id, external_idp_id, external_idp_id_hash,
                        email, full_name, clinic_id,
                        is_active, is_deleted, failed_login_count
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, FALSE, 0)
                    ON CONFLICT ON CONSTRAINT uq_doctor_tenant_idp_hash
                        DO UPDATE SET
                            clinic_id           = EXCLUDED.clinic_id,
                            full_name           = EXCLUDED.full_name,
                            is_active           = TRUE
                    RETURNING id
                    """,
                    uuid.uuid4(), tenant_id, ext_idp_enc, ext_idp_hash,
                    mail_enc, name_enc, clinic_id,
                )
                doctor_id = doctor_row["id"]
                print(f"  doctor_id  : {doctor_id}")

                # ── 3. Phone auth account ─────────────────────────────────
                phone_norm = c["phone"].strip().lower()
                phone_hash = hash_identifier(phone_norm)
                phone_enc  = encrypt_field(phone_norm)
                pin_enc    = encrypt_field(c["pin"])

                await conn.execute(
                    f"""
                    INSERT INTO {SCHEMA}.phone_auth_accounts (
                        id, tenant_id, user_id, user_type, portal,
                        phone_hash, phone_encrypted, pin_encrypted, is_active
                    )
                    VALUES ($1, $2, $3, 'doctor', 'doctor', $4, $5, $6, TRUE)
                    ON CONFLICT ON CONSTRAINT uq_phone_auth_tenant_phone_portal
                        DO UPDATE SET
                            user_id         = EXCLUDED.user_id,
                            phone_encrypted = EXCLUDED.phone_encrypted,
                            pin_encrypted   = EXCLUDED.pin_encrypted,
                            is_active       = TRUE
                    """,
                    uuid.uuid4(), tenant_id, doctor_id,
                    phone_hash, phone_enc, pin_enc,
                )
                print(f"  phone      : {c['phone']}")
                print(f"  PIN        : {c['pin']}")
                print()

    finally:
        await conn.close()

    print("-" * 54)
    print(" CREDENTIALS SUMMARY")
    print("-" * 54)
    print(f"  {'Clinic':<22}  {'Phone':<16}  PIN")
    print(f"  {'-'*22}  {'-'*16}  ------")
    for c in CLINICS:
        print(f"  {c['name']:<22}  {c['phone']:<16}  {c['pin']}")
    print("-" * 54)
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(main())
