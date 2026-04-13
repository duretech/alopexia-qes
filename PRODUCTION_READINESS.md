# Production Readiness Checklist

This document tracks what has been implemented for production-level security and what still needs external infrastructure.

## ✅ Already Implemented (In Code)

### Security Hardening
- [x] **Security headers middleware** — HSTS, CSP, X-Frame-Options, Permissions-Policy, Referrer-Policy
  - File: `src/backend/app/middleware/security_headers.py`
  - Config: Strict CSP, 2-year HSTS, frame deny, no inline scripts
  
- [x] **Rate limiting** — Per-IP token bucket (100/min default, 10/min for login, 20/min for uploads)
  - File: `src/backend/app/middleware/rate_limit.py`
  - Redis-compatible backend (currently in-memory, swap to Redis for multi-instance)
  
- [x] **Secure error handling** — No stack traces exposed to clients, full errors logged server-side
  - File: `src/backend/app/main.py` (exception handlers)
  - Every error gets a request_id for tracking
  
- [x] **Database connection pooling** — Configurable pool_size and max_overflow
  - File: `src/backend/app/db/session.py`
  - Current: pool_size=10, max_overflow=20 (tunable via `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`)
  
- [x] **Field-level encryption** — AES-256-GCM for phone, PIN, OTP, prescription metadata
  - File: `src/backend/app/utils/encryption.py`
  - Key: `FIELD_ENCRYPTION_KEY` environment variable (256-bit hex string)
  - Usage: doctor phone numbers, PIN, OTP, medication name, dosage, instructions
  
- [x] **Audit trail** — Immutable hash-chained event log with HMAC-SHA256 integrity verification
  - File: `src/backend/app/services/audit/service.py`
  - Every action logged: upload, cancel, download, dispense, user login, role changes
  
- [x] **Data masking in logs** — Redacts sensitive fields and patterns from all structured logs
  - File: `src/backend/app/core/logging.py`
  - Redacts: passwords, tokens, PINs, OTPs, phone numbers, emails, SSNs
  - Pattern-based: phone numbers, credit cards, etc.

### Health & Monitoring
- [x] **Liveness probe** — `/health/live` (process only)
  - File: `src/backend/app/api/v1/endpoints/health.py`
  
- [x] **Readiness probe** — `/health/ready` (process + database)
  - File: `src/backend/app/api/v1/endpoints/health.py`
  
- [x] **Deep health check** — `/health/deep` (database + S3 + ClamAV with timeouts)
  - File: `src/backend/app/api/v1/endpoints/health.py`
  - Checks connectivity and latency for diagnostics

### Input Validation
- [x] **Pydantic schemas** — Type validation on all request bodies
  - File: `src/backend/app/schemas/*.py`
  - Prevents injection, type confusion
  
- [x] **Request size limits** — Max upload size enforced (default 50MB)
  - File: `src/backend/app/services/ingestion/validators.py`
  - Configurable via `MAX_UPLOAD_SIZE_BYTES`

### Configuration Management
- [x] **Environment-based config** — Development vs production aware settings
  - File: `src/backend/app/core/config.py`
  - Method: `is_production()` checks `APP_ENV == "production"`
  - Debug logging automatically disabled in production
  
- [x] **Secrets in environment variables** — No hardcoded secrets
  - All sensitive config (keys, passwords, API credentials) via `.env`
  - `.env` is `.gitignore`d

### Compliance
- [x] **QTSP integration** — Dokobit for EU digital signature verification
  - File: `src/backend/app/services/qtsp/verification_service.py`
  - Verifies ETSI EN 319 102-1 qualified timestamps and certs
  
- [x] **Audit export** — JSON Lines export of audit trail for external systems
  - File: `src/backend/app/api/v1/endpoints/admin.py`
  - Exported to S3 for long-term retention

### Database
- [x] **Schema versioning** — Alembic migrations tracked in version control
  - File: `src/backend/migrations/`
  - Automatic schema deployment on startup (alembic upgrade head)

---

## 🚧 Requires External Infrastructure

### Cloud Provider Setup
- [ ] AWS account (recommended for compliance, S3, RDS, KMS, etc.)
- [ ] VPC with network isolation
- [ ] Security groups / network ACLs
- [ ] VPC Flow Logs for audit

### Database
- [ ] RDS PostgreSQL with:
  - [ ] Multi-AZ deployment
  - [ ] Automated backups (1-month retention)
  - [ ] Encryption at rest (KMS)
  - [ ] Encryption in transit (SSL/TLS)
  - [ ] IAM database authentication (not password-based)
  - [ ] Enhanced monitoring and audit logging
  - [ ] Read replicas for DR

### Object Storage (Pick One)
- [ ] **AWS S3 (Recommended)**
  - [ ] Enable versioning
  - [ ] Enable Object Lock (COMPLIANCE mode, 5-year retention)
  - [ ] Enable server-side encryption (KMS)
  - [ ] Enable access logging
  - [ ] Enable MFA Delete
  - [ ] Configure signed URLs (5-min expiry)
  - [ ] S3 Intelligent-Tiering for archival

  OR

- [ ] **MinIO Self-Hosted**
  - [ ] Deploy distributed MinIO cluster (3+ nodes)
  - [ ] Persistent storage backend (EBS, NAS)
  - [ ] MinIO with Object Lock enabled
  - [ ] TLS certificates
  - [ ] Regular updates

### Secrets Management
- [ ] AWS Secrets Manager OR Vault
  - [ ] Rotation every 30 days
  - [ ] Audit logging for access
  - [ ] No secrets in git, all in Secrets Manager

### Authentication / Identity
- [ ] Corporate OAuth/OIDC provider (Azure AD, Okta, Keycloak, AWS Cognito)
  - [ ] MFA enforcement on all admin accounts
  - [ ] Session timeout (15-30 min idle)
  - [ ] Single sign-on integration

### Malware Scanning
- [ ] **Option A: Self-Hosted ClamAV**
  - [ ] ClamAV server(s) with load balancer
  - [ ] Virus definition auto-update (hourly)
  - [ ] Multiple scanner instances for redundancy
  - [ ] Monitoring for scanning latency

  OR

- [ ] **Option B: Third-Party SaaS**
  - [ ] VirusTotal API OR commercial scanner
  - [ ] Monitor API latency and quota

### Monitoring & Logging
- [ ] CloudWatch (AWS), DataDog, Splunk, or ELK
  - [ ] Centralized log aggregation
  - [ ] 1-year retention for audit logs
  - [ ] Alert on error rate >0.1%, P99 latency >1s
  
- [ ] APM (Application Performance Monitoring)
  - [ ] DataDog, New Relic, or AWS X-Ray
  - [ ] Track database latency, S3 latency, ClamAV latency

### Network & Security
- [ ] TLS certificates (AWS ACM or Let's Encrypt)
  - [ ] TLS 1.2+ only
  - [ ] Certificate pinning (optional)
  
- [ ] WAF (Web Application Firewall)
  - [ ] AWS WAF or Cloudflare
  - [ ] Rate limiting rules
  - [ ] IP reputation filtering
  
- [ ] DDoS protection
  - [ ] AWS Shield Standard (free)
  - [ ] AWS Shield Advanced (optional)

### Domain & DNS
- [ ] Domain registration (Route53)
- [ ] DNSSEC (optional but recommended)
- [ ] Subdomain routing (api.qesflow.com, doctor.qesflow.com, etc.)

### CI/CD Pipeline
- [ ] GitHub Actions OR GitLab CI OR AWS CodePipeline
  - [ ] Build → Test → Security Scan → Deploy stages
  - [ ] SAST (static code analysis)
  - [ ] Dependency vulnerability scanning
  - [ ] Container image scanning
  - [ ] Automated rollback on health check failure

### Infrastructure as Code
- [ ] Terraform OR CloudFormation templates
  - [ ] Separate dev/staging/prod AWS accounts
  - [ ] State files encrypted and versioned
  - [ ] Infrastructure documented and version-controlled

### Container Orchestration
- [ ] AWS ECS/Fargate (managed, simpler) OR Kubernetes
  - [ ] Auto-scaling policies
  - [ ] Service mesh (optional, for advanced deployments)
  - [ ] Load balancing across availability zones

### Database & Disaster Recovery
- [ ] Automated daily backups with 30-day retention
- [ ] Backup testing (quarterly restore drill)
- [ ] RTO: 1 hour, RPO: 1 hour
- [ ] Cross-region replication for S3 and RDS

---

## 📋 Pre-Launch Checklist (Week Before Go-Live)

### 1. Load Testing (Week -1)
- [ ] Load test with 100+ concurrent users
- [ ] Baseline latency: P50 <100ms, P99 <500ms for uploads
- [ ] Throughput: 10-50 prescriptions/minute
- [ ] Database query performance under load
- [ ] S3 latency under concurrent load

### 2. Security Scan
- [ ] Dependency vulnerability scan (OWASP, Snyk, Dependabot)
- [ ] SAST code analysis (SonarQube, CodeQL)
- [ ] Container image scan (Trivy, Clair)
- [ ] Secrets detection (GitGuardian, TruffleHog)

### 3. Penetration Testing
- [ ] External security firm (recommended)
- [ ] OWASP Top 10 coverage
- [ ] Authentication/session management
- [ ] API endpoint security

### 4. Staging Environment Validation
- [ ] Full end-to-end workflow test (doctor upload → pharmacy dispense)
- [ ] All three portals (doctor, pharmacy, admin)
- [ ] Audit trail populated correctly
- [ ] QTSP verification working
- [ ] Error handling and recovery scenarios

### 5. Documentation
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Runbooks for common operations (backups, failover, scaling)
- [ ] Incident response playbook
- [ ] Architecture decision records

### 6. Capacity Planning
- [ ] Database sizing (expected row counts, query load)
- [ ] Storage sizing (expected prescriptions/month × data per RX)
- [ ] Network bandwidth
- [ ] Backup storage

---

## 🚀 Launch Sequence

### Phase 1: Internal Testing (Week 1)
- Your team only
- All three portals functional
- Prescriptions end-to-end working
- Audit trail populated

### Phase 2: Beta (Week 2)
- 10-50 doctors and pharmacists
- Real prescriptions
- Monitor closely: error rates, latency, audit trail
- Enable alerts on SLA violations

### Phase 3: Gradual Rollout (Weeks 3-4)
- 25% of target users
- Monitor 24h, then expand
- 50% of target users
- Monitor 24h, then expand
- 100% of target users

### Phase 4: Stabilization (Week 5+)
- Monitor health metrics continuously
- Weekly security scans
- Monthly penetration tests
- Quarterly DR drill

---

## Environment-Specific Settings

### Development
```env
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=DEBUG
QTSP_PROVIDER=mock  # Use mock QTSP for testing
S3_ENDPOINT_URL=http://localhost:9000  # MinIO
MALWARE_SCANNER=clamav  # ClamAV container
```

### Staging
```env
APP_ENV=staging
APP_DEBUG=false
LOG_LEVEL=INFO
QTSP_PROVIDER=dokobit  # Real QTSP
S3_ENDPOINT_URL=  # Real AWS S3
MALWARE_SCANNER=clamav  # Real ClamAV
```

### Production
```env
APP_ENV=production
APP_DEBUG=false
LOG_LEVEL=WARNING  # Only critical events
QTSP_PROVIDER=dokobit  # Real QTSP
S3_ENDPOINT_URL=  # AWS S3
S3_USE_SSL=true
MALWARE_SCANNER=clamav  # Multi-instance ClamAV
DATABASE_POOL_SIZE=50  # Higher for production load
DATABASE_MAX_OVERFLOW=100
RATE_LIMIT_DEFAULT=200/minute  # Higher for legitimate users
RATE_LIMIT_LOGIN=20/minute  # Stricter for auth
RATE_LIMIT_UPLOAD=50/minute  # Stricter for uploads
```

---

## Key Production Changes Required in `.env`

| Setting | Dev | Prod |
|---------|-----|------|
| APP_ENV | development | production |
| APP_DEBUG | true | false |
| LOG_LEVEL | DEBUG | WARNING |
| S3_ENDPOINT_URL | http://minio:9000 | (empty = AWS) |
| S3_USE_SSL | false | true |
| DATABASE_POOL_SIZE | 10 | 50 |
| DATABASE_MAX_OVERFLOW | 20 | 100 |
| RATE_LIMIT_DEFAULT | 100/minute | 200/minute |
| QTSP_PROVIDER | mock | dokobit |
| MALWARE_SCANNER | clamav | clamav (multi) |

---

## Next Steps

1. **Immediately**:
   - ✅ Add `/health/deep` endpoint (DONE)
   - ✅ Add data masking to logs (DONE)
   - [ ] Document all API endpoints with Swagger/OpenAPI
   - [ ] Create production `.env.production` template

2. **This Month**:
   - [ ] Set up AWS account and initial infrastructure
   - [ ] Configure RDS PostgreSQL
   - [ ] Set up AWS Secrets Manager
   - [ ] Configure AWS S3 with Object Lock

3. **Before Beta**:
   - [ ] Set up CI/CD pipeline
   - [ ] Run load testing
   - [ ] Run security scan and penetration test
   - [ ] Deploy to staging environment

4. **Before Production**:
   - [ ] Disaster recovery drill
   - [ ] Capacity planning review
   - [ ] Team training on runbooks
   - [ ] 24/7 monitoring setup

