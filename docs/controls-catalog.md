# QES Flow — Controls Catalog

## Control Categories

### C-AUTH: Authentication Controls

| ID | Control | Implementation | Status |
|----|---------|---------------|--------|
| C-AUTH-01 | External IdP integration via OIDC/SAML | Auth middleware with provider abstraction | Implemented (mock) |
| C-AUTH-02 | MFA enforcement for sensitive operations | MFA-ready model, enforcement hooks | Implemented (structure) |
| C-AUTH-03 | Server-side session management | Session store with timeout and revocation | Implemented |
| C-AUTH-04 | Session timeout (configurable) | Default 30 min idle, 8 hour absolute | Implemented |
| C-AUTH-05 | Concurrent session limits | Max sessions per user, configurable | Implemented |
| C-AUTH-06 | Account lockout after failed attempts | Configurable threshold, exponential backoff | Implemented |
| C-AUTH-07 | Login event auditing | All login attempts logged with context | Implemented |

### C-AUTHZ: Authorization Controls

| ID | Control | Implementation | Status |
|----|---------|---------------|--------|
| C-AUTHZ-01 | RBAC with defined permission matrix | Role-permission mapping, middleware enforcement | Implemented |
| C-AUTHZ-02 | ABAC policy evaluation | Multi-attribute policy engine | Implemented |
| C-AUTHZ-03 | Tenant isolation at query level | ORM filter, middleware injection | Implemented |
| C-AUTHZ-04 | Clinic scoping | Clinic-level access control | Implemented |
| C-AUTHZ-05 | Break-glass access with logging | Elevation flow with justification | Implemented |
| C-AUTHZ-06 | JIT privilege elevation | Temporary role grants with expiry | Implemented (structure) |
| C-AUTHZ-07 | Cross-tenant denial | Hard deny on tenant mismatch | Implemented |
| C-AUTHZ-08 | Authorization denial logging | All denials logged with context | Implemented |

### C-AUDIT: Audit Controls

| ID | Control | Implementation | Status |
|----|---------|---------------|--------|
| C-AUDIT-01 | Append-only audit event store | No UPDATE/DELETE on audit table | Implemented |
| C-AUDIT-02 | Hash-chained event log | previous_hash/current_hash per event | Implemented |
| C-AUDIT-03 | Audit event on all sensitive actions | Middleware + service-level emission | Implemented |
| C-AUDIT-04 | Integrity verification routine | Chain validation script | Implemented |
| C-AUDIT-05 | Gap detection | Sequence number monitoring | Implemented |
| C-AUDIT-06 | WORM-compatible export | S3 Object Lock export | Implemented (abstraction) |
| C-AUDIT-07 | Auditor export format | JSON Lines export for external review | Implemented |
| C-AUDIT-08 | Deletion attempt alerting | Database trigger + application alert | Implemented |

### C-DOC: Document Handling Controls

| ID | Control | Implementation | Status |
|----|---------|---------------|--------|
| C-DOC-01 | Checksum generation (SHA-256) | Computed at upload, stored, verified | Implemented |
| C-DOC-02 | MIME type validation | Application-level MIME check | Implemented |
| C-DOC-03 | PDF structural validation | PDF header and structure verification | Implemented |
| C-DOC-04 | File size limits | Configurable max size (default 25MB) | Implemented |
| C-DOC-05 | Duplicate detection | Content hash deduplication | Implemented |
| C-DOC-06 | Malware scan hook | ClamAV integration interface | Implemented (mock) |
| C-DOC-07 | Quarantine handling | Suspicious files isolated | Implemented |
| C-DOC-08 | Signed URLs only | No public blob access | Implemented |
| C-DOC-09 | Original PDF immutability | Never modified after upload | Implemented |
| C-DOC-10 | WORM storage | Object Lock on prescription bucket | Implemented (abstraction) |

### C-QTSP: QTSP Integration Controls

| ID | Control | Implementation | Status |
|----|---------|---------------|--------|
| C-QTSP-01 | Provider adapter pattern | Interface + mock + production adapter | Implemented (mock) |
| C-QTSP-02 | Raw response preservation | Verbatim QTSP response stored | Implemented |
| C-QTSP-03 | Evidence artifact storage | Evidence file stored with checksum | Implemented |
| C-QTSP-04 | Idempotent verification | Idempotency key per verification request | Implemented |
| C-QTSP-05 | Retry with backoff | Configurable retry policy | Implemented |
| C-QTSP-06 | Circuit breaker | Failure threshold, recovery period | Implemented (structure) |
| C-QTSP-07 | Verification attempt auditing | All attempts logged | Implemented |
| C-QTSP-08 | Manual review path | Failed verifications routed to review | Implemented |

### C-RET: Retention Controls

| ID | Control | Implementation | Status |
|----|---------|---------------|--------|
| C-RET-01 | Configurable retention schedules | Schedule per resource type | Implemented |
| C-RET-02 | Legal hold model | Hold overrides retention expiry | Implemented |
| C-RET-03 | Soft delete default | Records marked, not removed | Implemented |
| C-RET-04 | Dual-approval hard delete | Two approvers required | Implemented |
| C-RET-05 | Deletion evidence | Audit record of every deletion | Implemented |
| C-RET-06 | WORM-aware restrictions | Cannot delete object-locked resources | Implemented (abstraction) |
| C-RET-07 | Cryptographic erase | Key destruction approach | Implemented (abstraction) |
| C-RET-08 | Retention expiry job | Scheduled check for expired records | Implemented (structure) |

### C-SEC: Security Controls

| ID | Control | Implementation | Status |
|----|---------|---------------|--------|
| C-SEC-01 | TLS everywhere | Infrastructure configuration | Required before production |
| C-SEC-02 | Secrets via vault/env | Environment variable abstraction | Implemented |
| C-SEC-03 | No plaintext secrets in repo | .env.example with placeholders only | Implemented |
| C-SEC-04 | Rate limiting | Per-IP and per-user limits | Implemented |
| C-SEC-05 | Secure headers | HSTS, CSP, X-Frame-Options | Implemented |
| C-SEC-06 | CSRF protection | Token-based CSRF for state-changing ops | Implemented (structure) |
| C-SEC-07 | Input validation | Pydantic schemas on all endpoints | Implemented |
| C-SEC-08 | Correlation IDs | Request ID + Correlation ID on all calls | Implemented |
| C-SEC-09 | Structured JSON logging | All logs in JSON format | Implemented |
| C-SEC-10 | Anti-replay | Idempotency keys, nonces | Implemented |

### C-OBS: Observability Controls

| ID | Control | Implementation | Status |
|----|---------|---------------|--------|
| C-OBS-01 | Structured logging | JSON format with standard fields | Implemented |
| C-OBS-02 | Request/correlation IDs | Injected at middleware level | Implemented |
| C-OBS-03 | OpenTelemetry hooks | Tracing integration points | Implemented (structure) |
| C-OBS-04 | Separate audit pipeline | Audit events distinct from app logs | Implemented |
| C-OBS-05 | Health endpoints | Liveness and readiness probes | Implemented |

## Production Readiness Gaps

| Gap | Category | Priority | Notes |
|-----|----------|----------|-------|
| Real IdP integration | C-AUTH | P0 | Must integrate with actual OIDC/SAML provider |
| Real QTSP integration | C-QTSP | P0 | Must integrate with Dokobit or equivalent |
| Real malware scanner | C-DOC | P0 | Must integrate with ClamAV or equivalent |
| TLS certificate provisioning | C-SEC | P0 | Infrastructure requirement |
| WORM storage configuration | C-DOC | P0 | S3 Object Lock must be enabled on production bucket |
| Key management service | C-SEC | P0 | Must integrate with AWS KMS or equivalent |
| Penetration testing | C-SEC | P0 | External security assessment required |
| Legal retention values | C-RET | P0 | REQUIRES CONFIRMATION BY SPANISH HEALTHCARE / PHARMA COUNSEL |
| AEMPS inspection readiness | C-AUDIT | P1 | Validate audit format meets inspection expectations |
| Database TDE | C-SEC | P1 | Transparent data encryption for PostgreSQL |
| Backup and DR validation | C-SEC | P1 | Backup procedures must be tested |
