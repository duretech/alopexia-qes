# QES Flow — Reference Architecture

## 1. System Context

```
┌──────────────────────────────────────────────────────────────────────┐
│                        External Systems                              │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Prescription │  │   DocuSign/  │  │    QTSP      │               │
│  │   System     │  │   Signature  │  │  (Dokobit)   │               │
│  │  (External)  │  │   Provider   │  │              │               │
│  └─────────────┘  └──────────────┘  └──────────────┘               │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  Identity    │  │   Malware    │  │  Monitoring  │               │
│  │  Provider    │  │   Scanner    │  │  (External)  │               │
│  │  (OIDC/SAML) │  │  (ClamAV)   │  │              │               │
│  └─────────────┘  └──────────────┘  └──────────────┘               │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     QES Flow Platform                                │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    API Gateway / Load Balancer                │   │
│  │              (Rate limiting, WAF, TLS termination)           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│  ┌────────────┐  ┌───────────┴──────────┐  ┌──────────────────┐    │
│  │  Doctor    │  │    Backend API        │  │  Admin/Compliance│    │
│  │  Portal    │  │    (FastAPI)          │  │  Portal          │    │
│  │  (Next.js) │  │                      │  │  (Next.js)       │    │
│  └────────────┘  │  ┌────────────────┐  │  └──────────────────┘    │
│                  │  │ Auth Middleware │  │                           │
│  ┌────────────┐  │  │ Audit Middleware│  │                          │
│  │  Pharmacy  │  │  │ Tenant Scoping │  │                          │
│  │  Portal    │  │  │ Rate Limiting  │  │                          │
│  │  (Next.js) │  │  └────────────────┘  │                          │
│  └────────────┘  └──────────┬───────────┘                          │
│                              │                                       │
│         ┌────────────────────┼──────────────────────┐               │
│         ▼                    ▼                      ▼               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐      │
│  │  Ingestion   │  │    QTSP      │  │  Immutable Audit     │      │
│  │  Service     │  │  Integration │  │  Service             │      │
│  │              │  │  Service     │  │  (Hash-chained log)  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘      │
│         │                  │                                         │
│         ▼                  ▼                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐      │
│  │  Evidence    │  │  Retention/  │  │  Queue / Workers     │      │
│  │  Processor   │  │  Deletion    │  │  (SQS-compatible)    │      │
│  │              │  │  Service     │  │                      │      │
│  └──────────────┘  └──────────────┘  └──────────────────────┘      │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Data Layer                                 │   │
│  │  ┌──────────┐  ┌────────────────┐  ┌────────────────────┐   │   │
│  │  │PostgreSQL│  │ S3-Compatible  │  │ Audit Event Store  │   │   │
│  │  │          │  │ Object Storage │  │ (Append-only)      │   │   │
│  │  │          │  │ (WORM-capable) │  │                    │   │   │
│  │  └──────────┘  └────────────────┘  └────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

## 2. Trust Boundaries

### Boundary 1: External Network → Platform Edge
- TLS 1.3 termination at load balancer
- WAF rules for common attack patterns
- Rate limiting per IP and per authenticated user
- Geographic IP filtering (optional, Spain/EU focus)

### Boundary 2: Platform Edge → Backend API
- Authentication verification (JWT/session validation)
- Request ID and correlation ID injection
- Tenant context extraction and enforcement
- Input validation at API layer

### Boundary 3: Backend API → Internal Services
- Service-to-service authentication via internal tokens
- All calls logged with correlation IDs
- No direct database access from frontend
- Queue messages authenticated and validated

### Boundary 4: Platform → QTSP (External)
- Mutual TLS or API key authentication
- Request signing for integrity
- Response validation and raw preservation
- Timeout and circuit breaker patterns
- No trust in QTSP response format without validation

### Boundary 5: Platform → Object Storage
- Server-side encryption (SSE-S3 or SSE-KMS)
- No public bucket policies
- Signed URLs with short TTL for downloads
- WORM/Object Lock for immutable documents
- Separate buckets for prescriptions, evidence, audit exports

### Boundary 6: Platform → Database
- Connection via TLS
- Credential rotation support
- Row-level security for tenant isolation
- Audit triggers on sensitive tables

## 3. Service Boundaries

| Service | Responsibility | Scaling |
|---------|---------------|---------|
| Backend API | REST endpoints, auth, routing | Horizontal (stateless) |
| Ingestion Service | PDF validation, storage, job dispatch | Horizontal |
| QTSP Integration | Signature verification orchestration | Horizontal, rate-limited |
| Evidence Processor | Evidence storage and linking | Horizontal |
| Audit Service | Append-only event logging, chain integrity | Vertical preferred (ordering) |
| Retention Service | Retention schedules, deletion workflows | Single instance preferred |
| Queue Workers | Async job processing | Horizontal |

## 4. Data Flow — Prescription Upload to Dispensing

```
Doctor authenticates → [Audit: login_event]
    │
    ▼
Doctor uploads signed PDF → [Audit: upload_initiated]
    │
    ▼
Ingestion Service:
  ├─ Compute SHA-256 checksum
  ├─ Validate MIME type (application/pdf)
  ├─ Validate PDF structure
  ├─ Check for duplicates
  ├─ Malware scan hook
  ├─ Store to S3 (encrypted, object-locked)
  ├─ Create prescription record
  └─ Enqueue verification job → [Audit: upload_completed]
    │
    ▼
QTSP Integration Worker picks up job → [Audit: verification_started]
  ├─ Send PDF to QTSP API
  ├─ Receive verification response
  ├─ Store raw QTSP response
  ├─ Parse certificate details
  ├─ Parse timestamp details
  ├─ Determine verification status
  └─ Store evidence → [Audit: verification_completed | verification_failed]
    │
    ▼
Prescription status updated
  ├─ If VERIFIED: available to pharmacy
  ├─ If FAILED: enters manual review queue
  └─ [Audit: status_changed]
    │
    ▼
Pharmacy user authenticates → [Audit: login_event]
  ├─ Views assigned prescriptions
  ├─ Downloads PDF via signed URL → [Audit: document_accessed]
  ├─ Reviews verification evidence
  └─ Confirms dispensing → [Audit: dispensing_confirmed]
    │
    ▼
Prescription enters retention lifecycle
  ├─ Retention schedule applies
  ├─ Legal hold can override
  └─ Eventual deletion with evidence → [Audit: retention_action]
```

## 5. RBAC Model

| Role | Capabilities |
|------|-------------|
| `doctor` | Upload prescriptions, view own prescriptions, view verification status, revoke own prescriptions |
| `pharmacy_user` | View assigned prescriptions, download PDFs, confirm dispensing, record pharmacy events |
| `clinic_admin` | Manage clinic users, view clinic prescriptions, access clinic audit trail |
| `tenant_admin` | Manage tenant configuration, user management, view tenant-wide audit |
| `compliance_officer` | Read-only audit access, evidence export, retention management, incident management |
| `platform_admin` | System configuration, tenant management, privileged operations (with justification) |
| `auditor` | Read-only access to all audit data, evidence, and compliance reports |
| `support` | Limited read access for troubleshooting, no PHI access without break-glass |

## 6. ABAC Policy Dimensions

| Attribute | Description |
|-----------|-------------|
| `actor.role` | User's assigned role |
| `actor.tenant_id` | User's tenant scope |
| `actor.clinic_id` | User's clinic scope (if applicable) |
| `resource.tenant_id` | Resource's owning tenant |
| `resource.clinic_id` | Resource's owning clinic |
| `resource.owner_id` | Resource's creator/owner |
| `action.type` | The action being performed |
| `action.sensitivity` | Classification of the action |
| `context.ip_address` | Request source IP |
| `context.mfa_verified` | Whether MFA was completed |
| `context.break_glass` | Whether break-glass was invoked |

## 7. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Monorepo vs multi-repo | Monorepo | Simpler dependency management, atomic changes, easier for small team |
| REST vs GraphQL | REST | Simpler to audit, easier to rate-limit per endpoint, better OpenAPI tooling |
| Session vs JWT | Server-side sessions with session tokens | More control over revocation, no JWT size/expiry issues |
| Sync vs async QTSP | Async via queue | QTSP calls can be slow; queue provides retries and isolation |
| Audit storage | PostgreSQL append-only + S3 export | Queryable for operations, exportable for auditors |
| Multi-tenancy | Schema-shared with tenant_id column | Simpler to operate than schema-per-tenant at this scale |
| Encryption at rest | S3 SSE + PostgreSQL TDE/column encryption for PII | Defense in depth |

## 8. Chain of Custody Model

Every prescription document maintains an unbroken chain of custody:

```
1. CREATED    → Doctor uploads, checksum recorded
2. STORED     → Object stored in encrypted S3, storage receipt recorded
3. SUBMITTED  → Sent to QTSP for verification, submission receipt recorded
4. VERIFIED   → QTSP result received, evidence stored, link recorded
5. AVAILABLE  → Made available to pharmacy, access controls recorded
6. ACCESSED   → Pharmacy downloads, access event recorded
7. DISPENSED  → Pharmacy confirms dispensing, confirmation recorded
8. RETAINED   → Under retention policy, schedule recorded
9. HELD       → Legal hold applied (if applicable), hold recorded
10. DELETED   → Authorized deletion with evidence, deletion receipt recorded
```

Each transition is an audit event. No transition can occur without an audit record.
