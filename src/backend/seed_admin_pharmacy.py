#!/usr/bin/env python3
"""Seed 1 admin user and 1 pharmacy user into the alopexiaqes schema.

Creates:
  - 1 admin_users row     (role: tenant_admin)
  - 1 pharmacy_users row
  - 2 phone_auth_accounts (portal = 'admin' / 'pharmacy')

Run from src/backend/:
    python seed_admin_pharmacy.py

All inserts are idempotent (ON CONFLICT … DO UPDATE), so re-running is safe.
Only touches the alopexiaqes schema.
"""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import asyncpg

from app.core.config import get_settings
from app.utils.encryption import encrypt_field, hash_identifier

SCHEMA = "alopexiaqes"

ADMIN = {
    "phone":    "+328888899999",
    "pin":      "483921",
    "name":     "Platform Administrator",
    "role":     "tenant_admin",         # clinic_admin | tenant_admin | compliance_officer | platform_admin | support
}

PHARMACY = {
    "phone":         "+338888899999",
    "pin":           "637485",
    "name":          "Central Pharmacy",
    "pharmacy_name": "Central Pharmacy",
}


async def main() -> None:
    settings = get_settings()
    pg_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    print("Connecting…")
    conn = await asyncpg.connect(pg_url)

    try:
        # ── Find the active tenant ─────────────────────────────────────────
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

            # ── Admin user ─────────────────────────────────────────────────
            print(f"--- Admin: {ADMIN['name']} ---")

            ext_idp_admin      = f"admin-phone-{ADMIN['phone']}"
            ext_idp_admin_enc  = encrypt_field(ext_idp_admin)
            ext_idp_admin_hash = hash_identifier(ext_idp_admin)
            admin_row = await conn.fetchrow(
                f"""
                INSERT INTO {SCHEMA}.admin_users (
                    id, tenant_id, external_idp_id, external_idp_id_hash,
                    email, full_name, role,
                    is_active, failed_login_count
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, 0)
                ON CONFLICT ON CONSTRAINT uq_admin_tenant_idp_hash
                    DO UPDATE SET
                        full_name = EXCLUDED.full_name,
                        role      = EXCLUDED.role,
                        is_active = TRUE
                RETURNING id
                """,
                uuid.uuid4(), tenant_id, ext_idp_admin_enc, ext_idp_admin_hash,
                encrypt_field(f"admin{ADMIN['phone']}@alopexia.local"),
                encrypt_field(ADMIN["name"]),
                ADMIN["role"],
            )
            admin_id = admin_row["id"]
            print(f"  admin_id   : {admin_id}")

            phone_norm = ADMIN["phone"].strip().lower()
            await conn.execute(
                f"""
                INSERT INTO {SCHEMA}.phone_auth_accounts (
                    id, tenant_id, user_id, user_type, portal,
                    phone_hash, phone_encrypted, pin_encrypted, is_active
                )
                VALUES ($1, $2, $3, 'admin_user', 'admin', $4, $5, $6, TRUE)
                ON CONFLICT ON CONSTRAINT uq_phone_auth_tenant_phone_portal
                    DO UPDATE SET
                        user_id         = EXCLUDED.user_id,
                        phone_encrypted = EXCLUDED.phone_encrypted,
                        pin_encrypted   = EXCLUDED.pin_encrypted,
                        is_active       = TRUE
                """,
                uuid.uuid4(), tenant_id, admin_id,
                hash_identifier(phone_norm),
                encrypt_field(phone_norm),
                encrypt_field(ADMIN["pin"]),
            )
            print(f"  phone      : {ADMIN['phone']}")
            print(f"  PIN        : {ADMIN['pin']}")
            print(f"  role       : {ADMIN['role']}")
            print()

            # ── Pharmacy user ──────────────────────────────────────────────
            print(f"--- Pharmacy: {PHARMACY['name']} ---")

            ext_idp_pharmacy      = f"pharmacy-phone-{PHARMACY['phone']}"
            ext_idp_pharmacy_enc  = encrypt_field(ext_idp_pharmacy)
            ext_idp_pharmacy_hash = hash_identifier(ext_idp_pharmacy)
            pharmacy_row = await conn.fetchrow(
                f"""
                INSERT INTO {SCHEMA}.pharmacy_users (
                    id, tenant_id, external_idp_id, external_idp_id_hash,
                    email, full_name, pharmacy_name,
                    is_active, failed_login_count
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, 0)
                ON CONFLICT ON CONSTRAINT uq_pharma_tenant_idp_hash
                    DO UPDATE SET
                        full_name     = EXCLUDED.full_name,
                        pharmacy_name = EXCLUDED.pharmacy_name,
                        is_active     = TRUE
                RETURNING id
                """,
                uuid.uuid4(), tenant_id, ext_idp_pharmacy_enc, ext_idp_pharmacy_hash,
                encrypt_field(f"pharmacy{PHARMACY['phone']}@alopexia.local"),
                encrypt_field(PHARMACY["name"]),
                encrypt_field(PHARMACY["pharmacy_name"]),
            )
            pharmacy_id = pharmacy_row["id"]
            print(f"  pharmacy_id: {pharmacy_id}")

            phone_norm = PHARMACY["phone"].strip().lower()
            await conn.execute(
                f"""
                INSERT INTO {SCHEMA}.phone_auth_accounts (
                    id, tenant_id, user_id, user_type, portal,
                    phone_hash, phone_encrypted, pin_encrypted, is_active
                )
                VALUES ($1, $2, $3, 'pharmacy_user', 'pharmacy', $4, $5, $6, TRUE)
                ON CONFLICT ON CONSTRAINT uq_phone_auth_tenant_phone_portal
                    DO UPDATE SET
                        user_id         = EXCLUDED.user_id,
                        phone_encrypted = EXCLUDED.phone_encrypted,
                        pin_encrypted   = EXCLUDED.pin_encrypted,
                        is_active       = TRUE
                """,
                uuid.uuid4(), tenant_id, pharmacy_id,
                hash_identifier(phone_norm),
                encrypt_field(phone_norm),
                encrypt_field(PHARMACY["pin"]),
            )
            print(f"  phone      : {PHARMACY['phone']}")
            print(f"  PIN        : {PHARMACY['pin']}")
            print()

    finally:
        await conn.close()

    print("-" * 54)
    print(" CREDENTIALS SUMMARY")
    print("-" * 54)
    print(f"  {'Role':<20}  {'Phone':<16}  PIN")
    print(f"  {'-'*20}  {'-'*16}  ------")
    print(f"  {'Admin ('+ADMIN['role']+')':<20}  {ADMIN['phone']:<16}  {ADMIN['pin']}")
    print(f"  {'Pharmacy':<20}  {PHARMACY['phone']:<16}  {PHARMACY['pin']}")
    print("-" * 54)
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(main())
