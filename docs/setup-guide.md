# QES Flow — Setup Guide

> This document contains every setup instruction needed to get the platform running.
> It is updated as new components are built. Check the **Last Updated** date below.

**Last Updated**: 2026-04-07  
**Current Build Phase**: Phase D — COMPLETE (Docker, CI/CD, Frontend Portals)

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
9. [Frontend Portals](#9-frontend-portals)
10. [Object Storage (S3/MinIO)](#10-object-storage-s3minio)
11. [Queue Workers](#11-queue-workers)
12. [Docker Compose (Full Local Stack)](#12-docker-compose-full-local-stack)
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

### 8.7 Authentication & Authorization

The backend implements server-side session authentication with full RBAC + ABAC:

**Authentication flow:**
1. Client authenticates via `/api/v1/auth/login` (mock provider) or OIDC callback
2. Server creates a session record with a 32-byte random token
3. Token SHA-256 hash is stored in `session_records` — raw token returned to client
4. Client sends `Authorization: Bearer <token>` on subsequent requests
5. Sessions expire after configurable TTL (default 8 hours)

**Roles (8):** `DOCTOR`, `PHARMACIST`, `LAB_TECHNICIAN`, `CLINIC_ADMIN`, `TENANT_ADMIN`, `COMPLIANCE_OFFICER`, `AUDITOR`, `SUPPORT`

**Permission checks:** Every protected endpoint declares required permissions via dependency injection. The authorization engine performs a 6-step fail-fast evaluation:
1. Session validity
2. Tenant isolation (always enforced)
3. Role-level permission check (37 permissions)
4. Clinic-scope check (unless break-glass)
5. ABAC attribute conditions
6. Audit emission

**Break-glass access:** Bypasses clinic scoping but **never** bypasses tenant isolation. Creates `break_glass_events` records for compliance review.

**Mock auth (development):** When `AUTH_PROVIDER=mock`, the login endpoint accepts any email/password and creates a session. Set `AUTH_PROVIDER=oidc` for production.

```bash
# Example: login and use the token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"doctor@example.com","password":"any"}' | jq -r '.token')

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/prescriptions/upload
```

---

## 9. Frontend Portals

Three role-specific Next.js 15 (React 19, TypeScript) portals are available. Each proxies API requests to the backend.

### 9.1 Prerequisites

```bash
node --version   # Must be 20+
npm --version
```

### 9.2 Doctor Portal (port 3000)

Upload prescriptions and track their lifecycle status.

```bash
cd src/frontend/doctor-portal
npm install
npm run dev
# Open http://localhost:3000
```

**Pages:**
- `/` — Upload prescription PDF (file + patient ID + idempotency key)
- `/prescriptions` — List prescriptions with status badges

### 9.3 Pharmacy Portal (port 3001)

View verified prescriptions, download PDFs, and confirm dispensing.

```bash
cd src/frontend/pharmacy-portal
npm install
npm run dev
# Open http://localhost:3001
```

**Pages:**
- `/` — List prescriptions (filtered to pharmacy-relevant statuses), download PDF, confirm dispensing

### 9.4 Admin/Compliance Portal (port 3002)

Audit export, legal holds management, deletion request review.

```bash
cd src/frontend/admin-portal
npm install
npm run dev
# Open http://localhost:3002
```

**Pages:**
- `/` — Dashboard with API health status and quick-action cards
- `/audit` — Export audit trail as JSON Lines (with date range filter)
- `/legal-holds` — Create, list, and release legal holds
- `/deletions` — Review and approve deletion requests (dual-approval workflow)

### 9.5 API proxy configuration

Each portal includes a `next.config.ts` that rewrites `/api/**` requests to `http://localhost:8000/api/**`. If your backend runs on a different host/port, edit the `rewrites()` section in the corresponding `next.config.ts`.

### 9.6 Running all portals simultaneously

```bash
# Terminal 1 — Doctor Portal
cd src/frontend/doctor-portal && npm run dev

# Terminal 2 — Pharmacy Portal
cd src/frontend/pharmacy-portal && npm run dev

# Terminal 3 — Admin Portal
cd src/frontend/admin-portal && npm run dev
```

Or use Docker Compose (see Section 12) which starts all services together.

---

## 10. Object Storage (S3/MinIO)

Prescription PDFs and QTSP evidence artifacts are stored in S3-compatible object storage with WORM (Write Once Read Many) Object Lock for immutability.

### 10.1 Local development with MinIO

Docker Compose (Section 12) automatically starts MinIO and creates the required bucket. For standalone setup:

```bash
# Start MinIO
docker run -d --name minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# Create bucket with Object Lock enabled
docker run --rm --network host minio/mc sh -c "
  mc alias set local http://localhost:9000 minioadmin minioadmin &&
  mc mb --with-lock local/qesflow-documents
"
```

MinIO console is available at `http://localhost:9001`.

### 10.2 Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `S3_ENDPOINT_URL` | MinIO/S3 endpoint | `http://localhost:9000` |
| `S3_ACCESS_KEY_ID` | Access key | `minioadmin` |
| `S3_SECRET_ACCESS_KEY` | Secret key | `minioadmin` |
| `S3_BUCKET_NAME` | Bucket name | `qesflow-documents` |
| `S3_REGION` | AWS region (for real S3) | `eu-south-2` |

### 10.3 Storage backends

The storage layer is pluggable via `STORAGE_BACKEND`:

| Value | Description | Use case |
|-------|-------------|----------|
| `s3` | S3-compatible (MinIO/AWS) | Production + Docker dev |
| `local` | Local filesystem | Bare-metal dev without Docker |

**S3 backend features:**
- Server-side encryption (AES-256)
- Object Lock COMPLIANCE mode with 5-year retention
- Signed URLs with short TTL for secure downloads
- Content-type and checksum metadata

**Local backend features:**
- Stores files in `STORAGE_LOCAL_ROOT` (default: `./storage`)
- `.meta` sidecar JSON files for metadata
- Path traversal prevention
- No WORM enforcement (development only)

### 10.4 Production (AWS S3)

For production, create an S3 bucket with:
- Object Lock enabled (must be set at bucket creation)
- Default retention: COMPLIANCE mode, 5 years (1825 days)
- Server-side encryption: AES-256 or KMS
- Versioning: enabled (required by Object Lock)
- Block public access: all enabled

Set the `S3_*` environment variables to point to your AWS endpoint and credentials.

---

## 11. Queue Workers

The verification pipeline uses an async in-memory job queue to process prescription signature verification after ingestion.

### 11.1 How it works

1. When a prescription is ingested via `POST /api/v1/prescriptions/upload`, a verification job is enqueued
2. A background worker loop picks up jobs and calls the QTSP verification service
3. The worker retries failed jobs (up to configurable max attempts)
4. Results are stored in `signature_verification_results` and `evidence_files`

### 11.2 Worker startup

The worker runs as part of the FastAPI application's lifespan. When the server starts, the worker loop starts automatically in the background. No separate process is needed.

The worker loop:
- Polls the queue every 2 seconds when idle
- Processes one job at a time
- Acknowledges successful jobs, nacks failures for retry
- Shuts down gracefully on SIGTERM/SIGINT

### 11.3 QTSP provider configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `QTSP_PROVIDER` | Provider to use: `mock` or `dokobit` | `mock` |
| `QTSP_DOKOBIT_API_KEY` | Dokobit API key | *(none)* |
| `QTSP_DOKOBIT_ENDPOINT` | Dokobit API endpoint | *(none)* |
| `QTSP_TIMEOUT_SECONDS` | Request timeout | `30` |
| `QTSP_MAX_RETRIES` | Max verification attempts per prescription | `3` |

**Mock provider (development):** Simulates all verification outcomes based on PDF content markers:
- Default: `VERIFIED`
- PDF containing `INVALID_SIGNATURE`: `FAILED`
- PDF containing `EXPIRED_CERT`: `EXPIRED`
- PDF containing `REVOKED_CERT`: `REVOKED`
- PDF containing `QTSP_TIMEOUT`: raises timeout error
- PDF containing `QTSP_ERROR`: raises connection error

### 11.4 Future: External queue

The queue interface (`JobQueue` protocol) is designed to be swappable. A future SQS/Redis implementation can replace the in-memory queue for multi-instance deployments without changing the worker logic.

---

## 12. Docker Compose (Full Local Stack)

A single `docker-compose.yml` starts the entire platform: PostgreSQL, MinIO, and the backend API.

### 12.1 Prerequisites

```bash
docker --version          # 24+
docker compose version    # 2.20+ (compose v2)
```

### 12.2 Quick start

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env — set at minimum: FIELD_ENCRYPTION_KEY, APP_SECRET_KEY

# Start all services
docker compose up -d

# Watch logs
docker compose logs -f api
```

### 12.3 Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `db` | `postgres:16-alpine` | 5432 | PostgreSQL with `alopexiaqes` schema |
| `minio` | `minio/minio` | 9000, 9001 | S3-compatible object storage |
| `createbuckets` | `minio/mc` | — | Init container: creates bucket with Object Lock |
| `api` | Built from `src/backend/Dockerfile` | 8000 | FastAPI backend |

### 12.4 Volumes

| Volume | Purpose |
|--------|---------|
| `pgdata` | PostgreSQL data persistence |
| `miniodata` | MinIO object storage persistence |

### 12.5 Health checks

All services include health checks:

```bash
# Check service health
docker compose ps

# API health
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

### 12.6 Running migrations

Migrations are **not** run automatically by Docker Compose. After the database is up:

```bash
# Option A: Run from host (requires Python + psycopg2)
cd src/backend
alembic upgrade head

# Option B: Run inside the API container
docker compose exec api alembic upgrade head
```

### 12.7 Rebuilding after code changes

```bash
# Rebuild the API image
docker compose up -d --build api

# Or rebuild everything
docker compose up -d --build
```

### 12.8 Stopping and cleanup

```bash
# Stop all services (preserves data)
docker compose down

# Stop and remove volumes (DESTROYS ALL DATA)
docker compose down -v
```

### 12.9 Backend Dockerfile

The backend uses a multi-stage build for minimal image size:

1. **Builder stage:** `python:3.13-slim` with gcc and libpq-dev, installs pip dependencies
2. **Runtime stage:** `python:3.13-slim` with only libpq5, copies installed packages from builder
3. Runs as non-root user `appuser`
4. Built-in `HEALTHCHECK` via curl to `/health/live`
5. Starts with: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

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

### MinIO "bucket does not exist" errors
If using Docker Compose, the `createbuckets` init container creates the bucket automatically. If it failed:
```bash
# Recreate the init container
docker compose up createbuckets

# Or create manually
docker run --rm --network host minio/mc sh -c "
  mc alias set local http://localhost:9000 minioadmin minioadmin &&
  mc mb --with-lock local/qesflow-documents
"
```

### Docker Compose: API can't connect to database
The API waits for the database health check, but migrations must still be run manually:
```bash
docker compose exec api alembic upgrade head
```

If the database is not yet accepting connections, wait for the health check:
```bash
docker compose ps  # Check db health status
```

### Frontend portal: API proxy not working
Each portal's `next.config.ts` proxies `/api/**` to `http://localhost:8000`. Ensure:
1. The backend is running on port 8000
2. No firewall blocking localhost connections
3. If the backend is on a different host, edit `next.config.ts` `rewrites()` destination

### QTSP verification stuck in "pending" state
Check the worker is running (it starts automatically with the API):
```bash
# Look for worker log lines
docker compose logs api | grep "worker"
```
If using mock provider, verify `QTSP_PROVIDER=mock` is set.

---

*This document is updated as new components are built. Check PROGRESS.md for overall build status.*
