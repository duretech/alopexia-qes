# QES Flow — Qualified Electronic Signature Prescription Workflow Platform

A production-grade prescription workflow platform for compounded medicine (formulacion magistral) in Spain. This system handles the post-signature lifecycle of prescription documents: ingestion, qualified signature verification via QTSP, immutable audit trails, secure storage, pharmacy dispensing, and compliance reporting.

## System Overview

QES Flow does **not** create prescriptions or signatures. It starts **after** a doctor signs a prescription PDF in an external system. Our platform:

1. Authenticates the doctor and records the access event
2. Ingests the signed prescription PDF with full validation
3. Sends the document to a Qualified Trust Service Provider (QTSP) for signature verification
4. Stores the verification evidence alongside the original document
5. Provides pharmacy access for retrieval, verification, and dispensing confirmation
6. Maintains a complete, immutable, hash-chained audit trail
7. Enforces retention policies and legal hold controls

## Regulatory Context

- **Spanish prescription law**: Real Decreto 1718/2010
- **Compounded medicine**: Formulacion magistral traceability (AEMPS expectations)
- **Electronic signatures**: EU eIDAS Regulation (910/2014)
- **Data protection**: GDPR (Regulation 2016/679) for health data
- **Trust services**: QTSP integration (Dokobit or equivalent)

> Items marked `REQUIRES CONFIRMATION BY SPANISH HEALTHCARE / PHARMA COUNSEL` indicate legal assumptions that need external validation before production.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI (Python 3.11+) |
| Frontend | Next.js 14+ (TypeScript) |
| Database | PostgreSQL 15+ |
| Object Storage | S3-compatible (MinIO for dev) |
| Queue | SQS-compatible (LocalStack for dev) |
| Auth | OIDC/SAML-ready with internal RBAC+ABAC |
| Infrastructure | Docker, Terraform |
| Observability | Structured JSON logging, OpenTelemetry |

## Repository Structure

```
├── docs/                          # Architecture, security, compliance docs
├── src/
│   ├── backend/                   # FastAPI application
│   │   ├── app/
│   │   │   ├── api/v1/endpoints/  # REST API endpoints
│   │   │   ├── core/              # Config, security, dependencies
│   │   │   ├── db/                # Database engine, session, migrations
│   │   │   ├── models/            # SQLAlchemy ORM models
│   │   │   ├── schemas/           # Pydantic request/response schemas
│   │   │   ├── services/          # Business logic services
│   │   │   ├── middleware/        # Security, audit, correlation middleware
│   │   │   ├── workers/           # Background job processors
│   │   │   └── utils/             # Shared utilities
│   │   ├── alembic/               # Database migrations
│   │   └── tests/                 # Test suites
│   ├── frontend/
│   │   ├── doctor-portal/         # Next.js doctor-facing app
│   │   ├── pharmacy-portal/       # Next.js pharmacy-facing app
│   │   └── admin-portal/          # Next.js admin/compliance app
│   └── infra/
│       ├── terraform/             # IaC definitions
│       ├── docker/                # Dockerfiles
│       └── ci/                    # CI/CD pipeline definitions
├── scripts/                       # Developer and ops scripts
└── seeds/                         # Sample seed data
```

## Quick Start

```bash
# Prerequisites: Docker, Docker Compose, Python 3.11+, Node.js 20+

# Start infrastructure (PostgreSQL, MinIO, LocalStack)
docker-compose up -d

# Backend setup
cd src/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.main

# Frontend setup (each portal)
cd src/frontend/doctor-portal
npm install && npm run dev
```

## Security Model

- All actions emit immutable audit events
- Hash-chained audit log with tamper detection
- RBAC + ABAC authorization with tenant isolation
- MFA-ready authentication via external IdP
- Signed URLs only for document access (no public URLs)
- WORM-compatible storage abstraction
- Break-glass access with mandatory logging

## License

Proprietary. All rights reserved.
