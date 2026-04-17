#!/usr/bin/env python3
"""Rename the 4 seeded clinics. Run from src/backend/: python rename_clinics.py"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncpg
from app.core.config import get_settings
from app.utils.encryption import encrypt_field, hash_identifier

SCHEMA = "alopexiaqes"

# phone -> new clinic name
RENAMES = {
    "+458888899999": "Alopexia Clinic",
    "+468888899999": "EuroCare Medical Clinic",
    "+488888899999": "NovaMed Health Centre",
    "+498888899999": "Vitalis European Clinic",
}

async def main():
    settings = get_settings()
    pg_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(pg_url)
    try:
        async with conn.transaction():
            for phone, new_name in RENAMES.items():
                ext_idp_plaintext = f"clinic-phone-{phone}"
                # Look up by hash — deterministic, works with encrypted column
                ext_idp_hash      = hash_identifier(ext_idp_plaintext)
                new_name_enc      = encrypt_field(new_name)
                new_name_hash     = hash_identifier(new_name)

                # Update clinic name + name_hash (look up via doctor hash)
                await conn.execute(
                    f"""
                    UPDATE {SCHEMA}.clinics c
                    SET name = $1, name_hash = $2
                    FROM {SCHEMA}.doctors d
                    WHERE d.external_idp_id_hash = $3
                      AND d.clinic_id = c.id
                    """,
                    new_name_enc, new_name_hash, ext_idp_hash,
                )

                # Update doctor full_name (encrypted, look up by hash)
                await conn.execute(
                    f"""
                    UPDATE {SCHEMA}.doctors
                    SET full_name = $1
                    WHERE external_idp_id_hash = $2
                    """,
                    encrypt_field(new_name), ext_idp_hash,
                )

                print(f"  {phone}  ->  {new_name}")

    finally:
        await conn.close()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
