# QES Flow — Build Progress Tracker

## Overall Status: PHASE B — In Progress (DB ready to migrate, backend skeleton next)

---

## Phase A: Architecture & Foundation — COMPLETE

### Completed
- [x] Git repository initialized (main branch)
- [x] Full directory structure created
- [x] `.gitignore`
- [x] `.env.example` — all environment variables with placeholders (includes DATABASE_SCHEMA=alopexiaqes)
- [x] `README.md` — project overview, tech stack, quick start
- [x] `docs/architecture.md` — reference architecture, trust boundaries, data flow, RBAC/ABAC model, chain of custody
- [x] `docs/threat-model.md` — 17 threats modeled (T01-T17) with mitigations, detective controls, recovery
- [x] `docs/controls-catalog.md` — full controls catalog (C-AUTH, C-AUTHZ, C-AUDIT, C-DOC, C-QTSP, C-RET, C-SEC, C-OBS)
- [x] `docs/security.md` — security design (auth, authz, encryption, input validation, rate limiting, headers, secrets)
- [x] `docs/audit-readiness.md` — inspector verification guide, export procedure, regulatory assumptions
- [x] `docs/setup-guide.md` — complete setup instructions (DB, encryption, migrations, troubleshooting)

---

## Phase B: Schema, Backend, Auth, Audit, Storage, Ingestion — IN PROGRESS

### Completed
- [x] `src/backend/requirements.txt` — all Python dependencies
- [x] `src/backend/app/__init__.py`
- [x] `src/backend/app/core/__init__.py`
- [x] `src/backend/app/core/config.py` — Pydantic settings (includes DATABASE_SCHEMA)
- [x] `src/backend/app/db/__init__.py`
- [x] `src/backend/app/db/base.py` — SQLAlchemy Base with `schema=alopexiaqes` in MetaData
- [x] `src/backend/app/db/session.py` — async engine with `search_path=alopexiaqes,public`
- [x] `src/backend/alembic.ini` — Alembic configuration (supports DATABASE_URL env override)
- [x] `src/backend/alembic/env.py` — Alembic env with schema support, version_table_schema, include_schemas
- [x] `src/backend/alembic/script.py.mako` — migration template
- [x] Database models — ALL 24 tables (SQLAlchemy ORM):
  - [x] `app/models/tenant.py` — Tenant, Clinic
  - [x] `app/models/users.py` — Doctor, PharmacyUser, AdminUser, Auditor
  - [x] `app/models/patient.py` — Patient (encrypted PII fields)
  - [x] `app/models/prescription.py` — Prescription, PrescriptionMetadata
  - [x] `app/models/document.py` — UploadedDocument
  - [x] `app/models/verification.py` — SignatureVerificationResult
  - [x] `app/models/evidence.py` — EvidenceFile
  - [x] `app/models/pharmacy.py` — PharmacyEvent, DispensingEvent
  - [x] `app/models/audit.py` — AuditEvent (append-only, hash-chained)
  - [x] `app/models/retention.py` — LegalHold, RetentionSchedule, DeletionRequest
  - [x] `app/models/incident.py` — Incident
  - [x] `app/models/reference.py` — ExternalSystemReference
  - [x] `app/models/access_review.py` — AccessReview
  - [x] `app/models/break_glass.py` — BreakGlassEvent
  - [x] `app/models/api_credential.py` — ApiCredentialMetadata
  - [x] `app/models/session.py` — SessionRecord
- [x] `app/models/__init__.py` — imports all models for Alembic discovery
- [x] `alembic/versions/001_initial_schema.py` — migration targeting `alopexiaqes` schema with:
  - Creates `alopexiaqes` schema
  - Enables `pgcrypto` extension
  - All 24 tables with `schema=SCHEMA` parameter
  - All FKs reference `alopexiaqes.table_name`
  - `gen_random_uuid()` server-side UUID generation
  - `set_updated_at()` trigger on all mutable tables
  - `prevent_audit_modification()` trigger blocks UPDATE/DELETE on audit_events
  - `audit_event_seq` sequence for hash-chain ordering
  - All indexes and constraints schema-qualified
- [x] `app/utils/encryption.py` — AES-256-GCM field encryption for PII:
  - FieldEncryptor class with encrypt/decrypt
  - hash_identifier() for one-way SHA-256 (patient ID dedup)
  - Key from FIELD_ENCRYPTION_KEY env var (base64-encoded 32 bytes)
  - Ciphertext format: base64(nonce || ciphertext || tag)

### Not Started
- [ ] Backend FastAPI skeleton (`main.py`, middleware, routers)
- [ ] Auth/authz layer (RBAC + ABAC policy engine)
- [ ] Immutable audit service (hash chain, event emission, verification)
- [ ] Object storage abstraction (S3 client, signed URLs, WORM)
- [ ] Prescription ingestion service (upload, validate, checksum, enqueue)

---

## Phase C: QTSP, Evidence, Pharmacy, Admin, Retention — NOT STARTED

- [ ] QTSP integration abstraction + mock provider
- [ ] Evidence processor
- [ ] Pharmacy flow endpoints
- [ ] Admin/compliance flow endpoints
- [ ] Retention/deletion service
- [ ] Queue/worker infrastructure

---

## Phase D: Tests, Docs, Infra, CI/CD — NOT STARTED

- [ ] Test suites (unit, integration, API, authz, audit, security)
- [ ] Infrastructure-as-code (Terraform)
- [ ] Docker + docker-compose for local dev
- [ ] CI/CD skeleton
- [ ] Frontend portals (doctor, pharmacy, admin — Next.js)
- [ ] Remaining delivery artifacts (OpenAPI spec, ERD, runbooks, incident playbook)

---

## Key Design Decisions Made
1. Monorepo structure
2. REST API (not GraphQL) — easier to audit
3. Server-side sessions (not JWT) — better revocation
4. Async QTSP via queue — resilience
5. PostgreSQL append-only + S3 export for audit
6. Schema-shared multi-tenancy with tenant_id column
7. All tables in `alopexiaqes` PostgreSQL schema (not public)
8. Application-level AES-256-GCM encryption for PII (key in env/vault, DB sees ciphertext only)
9. DB-level triggers for audit immutability and auto-updated_at
10. pgcrypto extension for gen_random_uuid()

## How to Run Migration
```bash
cd src/backend
# Set your VM connection string (sync driver for Alembic):
export DATABASE_URL="postgresql+psycopg2://user:pass@your-vm:5432/your_db"
pip install -r requirements.txt
alembic upgrade head
```

## Resume Instructions
- Read this file to understand current state
- Check which phase/task is next based on status above
- Continue from the first "Not Started" item in the current phase
- Update this file as tasks complete
