#!/usr/bin/env python3
"""Make prescriptions.patient_id nullable — aligns DB with the SQLAlchemy model."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import asyncpg
from app.core.config import get_settings

SCHEMA = "alopexiaqes"


async def main() -> None:
    settings = get_settings()
    pg_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    print("Connecting…")
    conn = await asyncpg.connect(pg_url)

    try:
        # Check current nullability
        row = await conn.fetchrow("""
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_schema = $1
              AND table_name   = 'prescriptions'
              AND column_name  = 'patient_id'
        """, SCHEMA)

        if not row:
            print("ERROR: prescriptions.patient_id column not found.")
            return

        if row["is_nullable"] == "YES":
            print("patient_id is already nullable — nothing to do.")
            return

        print("patient_id is NOT NULL — altering to allow nulls…")
        await conn.execute(f"""
            ALTER TABLE {SCHEMA}.prescriptions
            ALTER COLUMN patient_id DROP NOT NULL
        """)
        print("Done — patient_id is now nullable.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
