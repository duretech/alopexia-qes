#!/usr/bin/env python3
"""Insert dev login users into alopexiaqes schema only.

Reads DATABASE_URL from .env at repo root (parent of scripts/).

Usage (from repo root):
  python scripts/seed_dev_users.py

Requires: psycopg2-binary
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

# Repo root = parent of scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def sync_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_URL not set. Add it to .env or export it.", file=sys.stderr)
        sys.exit(1)
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def connect_psycopg2(dsn: str):
    import psycopg2

    parsed = urlparse(dsn)
    if not parsed.hostname:
        print("ERROR: Invalid DATABASE_URL", file=sys.stderr)
        sys.exit(1)
    password = unquote(parsed.password) if parsed.password else None
    dbname = (parsed.path or "/").lstrip("/") or "postgres"
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=password,
        dbname=dbname,
        connect_timeout=30,
    )


SQL = """
BEGIN;

INSERT INTO alopexiaqes.tenants (id, name, display_name, is_active, settings, is_deleted)
VALUES (
  '11111111-1111-1111-1111-111111111111',
  'dev-tenant',
  'Development Tenant',
  TRUE,
  '{}',
  FALSE
) ON CONFLICT (id) DO NOTHING;

INSERT INTO alopexiaqes.clinics (id, tenant_id, name, is_active, is_deleted)
VALUES (
  '22222222-2222-2222-2222-222222222222',
  '11111111-1111-1111-1111-111111111111',
  'Development Clinic',
  TRUE,
  FALSE
) ON CONFLICT (id) DO NOTHING;

INSERT INTO alopexiaqes.patients (
  id, tenant_id, identifier_hash, full_name_encrypted, is_active, is_deleted
) VALUES (
  '66666666-6666-6666-6666-666666666666',
  '11111111-1111-1111-1111-111111111111',
  repeat('a', 64),
  'ZGV2LXBsYWNlaG9sZGVy',
  TRUE,
  FALSE
) ON CONFLICT (id) DO NOTHING;

INSERT INTO alopexiaqes.doctors (
  id, tenant_id, external_idp_id, email, full_name, clinic_id, is_active, is_deleted
) VALUES (
  '33333333-3333-3333-3333-333333333333',
  '11111111-1111-1111-1111-111111111111',
  'mock:doctor:dev-1',
  'doctor@qesflow.local',
  'Dev Doctor',
  '22222222-2222-2222-2222-222222222222',
  TRUE,
  FALSE
) ON CONFLICT (id) DO NOTHING;

INSERT INTO alopexiaqes.pharmacy_users (
  id, tenant_id, external_idp_id, email, full_name, pharmacy_name, is_active, is_deleted
) VALUES (
  '44444444-4444-4444-4444-444444444444',
  '11111111-1111-1111-1111-111111111111',
  'mock:pharmacy:dev-1',
  'pharmacy@qesflow.local',
  'Dev Pharmacist',
  'Dev Pharmacy',
  TRUE,
  FALSE
) ON CONFLICT (id) DO NOTHING;

INSERT INTO alopexiaqes.admin_users (
  id, tenant_id, external_idp_id, email, full_name, role, is_active, is_deleted
) VALUES (
  '55555555-5555-5555-5555-555555555555',
  '11111111-1111-1111-1111-111111111111',
  'mock:admin:dev-1',
  'admin@qesflow.local',
  'Dev Compliance',
  'compliance_officer',
  TRUE,
  FALSE
) ON CONFLICT (id) DO NOTHING;

COMMIT;
"""


def main() -> None:
    load_dotenv(ENV_PATH)
    dsn = sync_database_url()
    conn = connect_psycopg2(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

    print("OK: Seed applied to schema alopexiaqes only.")
    print("  doctor@qesflow.local (doctor portal)")
    print("  pharmacy@qesflow.local (pharmacy portal)")
    print("  admin@qesflow.local (admin portal)")
    print("Use any password with AUTH_PROVIDER=mock.")


if __name__ == "__main__":
    main()
