# QES Flow — Setup Guide

> This document contains every setup instruction needed to get the platform running.
> It is updated as new components are built. Check the **Last Updated** date below.

**Last Updated**: 2026-04-07  
**Current Build Phase**: Phase B (Backend skeleton complete, audit service next)

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Repository Setup](#2-repository-setup)
3. [Environment Configuration](#3-environment-configuration)
4. [Database Setup](#4-database-setup)
5. [Encryption Key Generation](#5-encryption-key-generation)
6. [Running Migrations](#6-running-migrations)
7. [Verifying the Database](#7-verifying-the-database)
8. [Backend API](#8-backend-api)
9. [Frontend Portals](#9-frontend-portals) *(not yet implemented)*
10. [Object Storage (S3/MinIO)](#10-object-storage-s3minio) *(not yet implemented)*
11. [Queue (SQS/LocalStack)](#11-queue-sqslocalstack) *(not yet implemented)*
12. [Docker Compose (Full Local Stack)](#12-docker-compose-full-local-stack) *(not yet implemented)*
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Prerequisites

| Tool | Minimum Version | Purpose |
|------|----------------|---------|
| Python | 3.11+ | Backend API and migrations |
| pip | latest | Python package management |
| PostgreSQL | 15+ | Primary database (hosted on your VM) |
| Node.js | 20+ | Frontend portals *(later)* |
| Docker | 24+ | Local infrastructure *(later)* |
| Git | 2.40+ | Version control |

### Verify prerequisites

```bash
python3 --version    # Should be 3.11+
pip --version
psql --version       # For connecting to your VM database
node --version       # 20+ (needed later for frontends)
git --version
```

---

## 2. Repository Setup

```bash
# Clone or navigate to the project
cd /path/to/QES\ Flow

# The repository structure is already created. Verify:
ls src/backend/app/models/   # Should list 14 model files
ls src/backend/alembic/versions/   # Should show 001_initial_schema.py
```

---

## 3. Environment Configuration

```bash
# Copy the template
cp .env.example .env

# Edit .env with your actual values:
```

### Critical variables to set NOW (for database migration)

| Variable | What to set | Example |
|----------|------------|---------|
| `DATABASE_URL` | Your VM PostgreSQL connection (async driver) | `postgresql+asyncpg://user:pass@vm-ip:5432/dbname` |
| `DATABASE_SCHEMA` | Must be `alopexiaqes` | `alopexiaqes` |
| `APP_SECRET_KEY` | Random 64-char hex string | *(see generation command below)* |
| `FIELD_ENCRYPTION_KEY` | Base64-encoded 32-byte key | *(see Section 5 below)* |

### Generate APP_SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output into `APP_SECRET_KEY` in your `.env`.

### Variables needed later (can leave defaults for now)

| Variable | When needed | Default OK for now? |
|----------|------------|-------------------|
| `S3_*` | When object storage is built | Yes |
| `SQS_*` | When queue workers are built | Yes |
| `QTSP_*` | When QTSP integration is built | Yes (uses mock) |
| `OIDC_*` | When real IdP is connected | Yes (uses mock auth) |
| `CLAMAV_*` | When malware scanning is wired | Yes (uses mock) |

---

## 4. Database Setup

### 4.1 Your PostgreSQL VM

You have a PostgreSQL database hosted on a VM. You need:

- **A database** (e.g., `qesflow` or your existing database)
- **A user** with privileges to create schemas and extensions
- **Network access** from your development machine to the VM

### 4.2 Verify connectivity

```bash
# Test that you can connect from your machine
psql "postgresql://YOUR_USER:YOUR_PASS@YOUR_VM_HOST:5432/YOUR_DB"

# Once connected, verify your user has the right privileges:
SELECT current_user, current_database();
```

### 4.3 Required database privileges

The migration needs to:
1. Create the `alopexiaqes` schema
2. Enable the `pgcrypto` extension
3. Create tables, indexes, triggers, functions, sequences

If your user lacks these, ask your DBA to run:

```sql
-- Grant schema creation (run as superuser or DB owner)
GRANT CREATE ON DATABASE your_db TO your_user;

-- Enable pgcrypto (requires superuser)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Alternatively, grant your user superuser temporarily for the migration:
-- ALTER USER your_user WITH SUPERUSER;
-- (Revoke after migration: ALTER USER your_user WITH NOSUPERUSER;)
```

### 4.4 If the `alopexiaqes` schema already exists

If you previously created this schema manually, the migration handles it gracefully:
- `CREATE SCHEMA IF NOT EXISTS alopexiaqes` — will not fail if it exists
- Tables will be created inside it
- If you have **existing tables** in this schema that conflict, drop them first:

```sql
-- DANGER: Only run this if the schema has no production data
DROP SCHEMA alopexiaqes CASCADE;
```

---

## 5. Encryption Key Generation

**This is critical.** The `FIELD_ENCRYPTION_KEY` encrypts all patient PII (names, dates of birth, medical data). Losing this key means **permanent loss of access to patient data**.

### Generate the key

```bash
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

This outputs a Base64-encoded 32-byte (256-bit) key. Example output:
```
k7Hx9mN2pQ4wR8vT1bY6cF3eA5dG0jL9sU7iO2xZ4nM=
```

### Store the key

1. Copy the output into `FIELD_ENCRYPTION_KEY` in your `.env` file
2. **Back up the key securely** — store it in a password manager, vault, or secure note
3. **Never commit it** to version control (`.env` is in `.gitignore`)
4. In production, use a secrets manager (HashiCorp Vault, AWS Secrets Manager, etc.)

### What gets encrypted

| Table | Field | Encryption Method |
|-------|-------|------------------|
| `patients` | `full_name_encrypted` | AES-256-GCM (app-level) |
| `patients` | `date_of_birth_encrypted` | AES-256-GCM (app-level) |
| `patients` | `identifier_hash` | SHA-256 one-way hash (for dedup) |
| `patients` | `national_id_hash` | SHA-256 one-way hash (for lookup) |
| `prescription_metadata` | `medication_name` | AES-256-GCM (app-level, when written via service) |
| `prescription_metadata` | `dosage` | AES-256-GCM (app-level, when written via service) |
| `prescription_metadata` | `instructions` | AES-256-GCM (app-level, when written via service) |
| All user tables | `email`, `full_name` | Marked ENCRYPTION_SENSITIVE — encrypted via service layer |

> **Note:** The database columns store ciphertext (Base64-encoded). The actual encryption/decryption happens in the Python application layer (`app/utils/encryption.py`), not in PostgreSQL. This means the DB never sees plaintext PII, and key management stays in the app/vault.

---

## 6. Running Migrations

### 6.1 Install Python dependencies

```bash
cd src/backend
python3 -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

pip install -r requirements.txt
```

### 6.2 Set the database URL for Alembic

Alembic uses the **synchronous** PostgreSQL driver (`psycopg2`), not the async one (`asyncpg`). Set the URL accordingly:

```bash
# Option A: Environment variable (recommended)
export DATABASE_URL="postgresql+psycopg2://YOUR_USER:YOUR_PASS@YOUR_VM_HOST:5432/YOUR_DB"

# Option B: Edit alembic.ini directly (less recommended — don't commit credentials)
# In src/backend/alembic.ini, change the sqlalchemy.url line
```

> **Important:** If your `.env` has `DATABASE_URL` with `+asyncpg`, the Alembic env.py automatically swaps it to `+psycopg2`. So setting the env var from your `.env` value works:
> ```bash
> export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db"  # Also works — auto-converted
> ```

### 6.3 Run the migration

```bash
cd src/backend
alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial, Initial schema — all 24 tables in the 'alopexiaqes' PostgreSQL schema.
```

### 6.4 What the migration creates

Inside the `alopexiaqes` schema:

| # | Table | Purpose |
|---|-------|---------|
| 1 | `tenants` | Top-level organizational unit |
| 2 | `clinics` | Clinics within tenants |
| 3 | `doctors` | Doctor users |
| 4 | `pharmacy_users` | Pharmacy/lab users |
| 5 | `admin_users` | Admin/compliance/support users |
| 6 | `auditors` | Read-only inspector users |
| 7 | `patients` | Patient records (PII encrypted) |
| 8 | `prescriptions` | Core prescription records |
| 9 | `prescription_metadata` | Extended prescription details |
| 10 | `uploaded_documents` | Stored PDF tracking |
| 11 | `signature_verification_results` | QTSP verification results |
| 12 | `evidence_files` | QTSP evidence artifacts |
| 13 | `pharmacy_events` | Pharmacy actions on prescriptions |
| 14 | `dispensing_events` | Dispensing confirmations |
| 15 | `audit_events` | Immutable hash-chained audit log |
| 16 | `legal_holds` | Legal hold on resources |
| 17 | `retention_schedules` | Configurable retention periods |
| 18 | `deletion_requests` | Dual-approval deletion workflow |
| 19 | `incidents` | Security/compliance incidents |
| 20 | `external_system_references` | Cross-system linkage |
| 21 | `access_reviews` | Periodic access certification |
| 22 | `break_glass_events` | Emergency access records |
| 23 | `api_credentials_metadata` | API key tracking |
| 24 | `session_records` | Server-side sessions |

Plus:
- `alembic_version` table (migration tracking, also in `alopexiaqes`)
- `audit_event_seq` sequence
- `set_updated_at()` function + triggers on all mutable tables
- `prevent_audit_modification()` function + triggers on `audit_events`

### 6.5 Preview SQL without executing

If you want to review the SQL before running it:

```bash
cd src/backend
alembic upgrade head --sql > migration_preview.sql
```

Then inspect `migration_preview.sql` and run it manually via `psql` if preferred.

---

## 7. Verifying the Database

After running the migration, verify everything was created correctly:

```bash
psql "postgresql://YOUR_USER:YOUR_PASS@YOUR_VM_HOST:5432/YOUR_DB"
```

```sql
-- 1. Check the schema exists
SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'alopexiaqes';

-- 2. List all tables in the schema
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'alopexiaqes'
ORDER BY table_name;
-- Expected: 25 rows (24 tables + alembic_version)

-- 3. Verify the audit protection triggers exist
SELECT trigger_name, event_manipulation, action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'alopexiaqes'
  AND event_object_table = 'audit_events';
-- Expected: trg_audit_no_update (BEFORE UPDATE) and trg_audit_no_delete (BEFORE DELETE)

-- 4. Verify the audit sequence exists
SELECT sequence_name FROM information_schema.sequences
WHERE sequence_schema = 'alopexiaqes';
-- Expected: audit_event_seq

-- 5. Test that audit_events rejects UPDATE
INSERT INTO alopexiaqes.audit_events (
    id, sequence_number, previous_hash, current_hash,
    event_type, action, event_timestamp
) VALUES (
    gen_random_uuid(), 1, repeat('0', 64), repeat('a', 64),
    'test_event', 'test', NOW()
);
-- Should succeed

UPDATE alopexiaqes.audit_events SET action = 'tampered' WHERE sequence_number = 1;
-- Should FAIL with: "SECURITY VIOLATION: audit_events is append-only..."

DELETE FROM alopexiaqes.audit_events WHERE sequence_number = 1;
-- Should FAIL with the same error

-- 6. Clean up the test row (must be done by a superuser bypassing the trigger)
-- ALTER TABLE alopexiaqes.audit_events DISABLE TRIGGER trg_audit_no_delete;
-- DELETE FROM alopexiaqes.audit_events WHERE sequence_number = 1;
-- ALTER TABLE alopexiaqes.audit_events ENABLE TRIGGER trg_audit_no_delete;

-- 7. Check pgcrypto is available
SELECT gen_random_uuid();
-- Should return a UUID

-- 8. Verify the Alembic version
SELECT * FROM alopexiaqes.alembic_version;
-- Expected: version_num = '001_initial'
```

---

## 8. Backend API

### 8.1 Starting the backend server

```bash
cd src/backend

# Activate your virtual environment (if not already active)
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

# Ensure environment variables are set (via .env or export)
# Required: DATABASE_URL, APP_SECRET_KEY, FIELD_ENCRYPTION_KEY

# Start the development server
uvicorn app.main:app --reload
```

The server starts on `http://localhost:8000` by default.

### 8.2 API documentation (development only)

In non-production environments, interactive API docs are available:

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI (interactive) |
| `http://localhost:8000/redoc` | ReDoc (read-only) |
| `http://localhost:8000/openapi.json` | OpenAPI JSON spec |

> **Note:** These endpoints are disabled in production (`APP_ENV=production`) to prevent information disclosure.

### 8.3 Health check endpoints

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/health/live` | GET | Liveness probe — returns 200 if the process is up | No |
| `/health/ready` | GET | Readiness probe — checks DB connectivity, returns 200 or 503 | No |

Example:
```bash
curl http://localhost:8000/health/live
# {"status": "ok", "timestamp": "2026-04-07T10:00:00+00:00"}

curl http://localhost:8000/health/ready
# {"status": "ok", "timestamp": "...", "checks": {"database": "ok"}}
```

### 8.4 Request tracing

Every response includes tracing headers:

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Unique ID for this request |
| `X-Correlation-ID` | Correlation ID (forwarded from client or auto-generated) |

To forward your own correlation ID, include `X-Correlation-ID` in the request headers.

### 8.5 Running tests

```bash
cd src/backend

# Run all tests
python -m pytest -v

# Run only health endpoint smoke tests
python -m pytest tests/api/test_health.py -v
```

### 8.6 Middleware stack

The backend applies the following middleware (outermost first):

1. **Correlation IDs** — generates request_id, forwards correlation_id
2. **Request logging** — structured JSON logs with method, path, status, duration
3. **Security headers** — HSTS, CSP, X-Frame-Options, etc.
4. **Rate limiting** — per-IP token bucket (configurable via `RATE_LIMIT_DEFAULT`)
5. **Audit emission** — captures audit context for downstream services
6. **CORS** — configured from `APP_CORS_ORIGINS`
7. **Trusted hosts** — configured from `APP_ALLOWED_HOSTS`

### 8.7 Authentication setup

> **Status:** Not yet implemented. Will be added when the auth/authz layer is built. Currently no endpoints require authentication.

---

## 9. Frontend Portals

> **Status:** Not yet implemented. This section will be updated when Next.js portals are built.

Will cover:
- Doctor Portal setup (port 3000)
- Pharmacy Portal setup (port 3001)
- Admin/Compliance Portal setup (port 3002)

---

## 10. Object Storage (S3/MinIO)

> **Status:** Not yet implemented. This section will be updated when the storage abstraction is built.

Will cover:
- MinIO setup for local development
- Bucket creation and WORM configuration
- S3 credentials and endpoint configuration

---

## 11. Queue (SQS/LocalStack)

> **Status:** Not yet implemented. This section will be updated when queue workers are built.

Will cover:
- LocalStack setup for local SQS
- Queue creation
- Worker startup

---

## 12. Docker Compose (Full Local Stack)

> **Status:** Not yet implemented. This section will be updated when docker-compose.yml is created.

Will cover:
- Single command to start all infrastructure
- PostgreSQL, MinIO, LocalStack, ClamAV
- Backend API and frontend portals

---

## 13. Troubleshooting

### Migration fails with "permission denied for schema"
Your DB user needs `CREATE` privilege on the database:
```sql
GRANT CREATE ON DATABASE your_db TO your_user;
```

### Migration fails with "extension pgcrypto not available"
`pgcrypto` must be created by a superuser:
```sql
-- Run as superuser
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

### Migration fails with "relation already exists"
If you're re-running after a partial failure:
```bash
# Check current migration state
alembic current

# If stuck, mark as complete and re-run
alembic stamp head

# Or drop the schema and start fresh (DANGER: destroys all data)
psql -c "DROP SCHEMA alopexiaqes CASCADE;" "postgresql://..."
alembic upgrade head
```

### "FIELD_ENCRYPTION_KEY is required" error
You need to generate and set the encryption key:
```bash
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
# Copy output to FIELD_ENCRYPTION_KEY in .env
```

### psycopg2 installation fails
On macOS:
```bash
brew install postgresql
pip install psycopg2-binary
```

On Linux:
```bash
sudo apt-get install libpq-dev
pip install psycopg2-binary
```

### asyncpg vs psycopg2 confusion
- **Alembic** (migrations) uses `psycopg2` (synchronous) — connection string: `postgresql+psycopg2://...`
- **FastAPI** (runtime) uses `asyncpg` (asynchronous) — connection string: `postgresql+asyncpg://...`
- The `alembic/env.py` automatically converts `+asyncpg` to `+psycopg2` if you set `DATABASE_URL` as an env var
- Your `.env` should use the asyncpg format (for the app), and Alembic will adapt

---

*This document is updated as new components are built. Check PROGRESS.md for overall build status.*
