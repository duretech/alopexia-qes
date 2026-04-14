# System Architecture

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       CLIENT LAYER (Browser)                     │
├──────────────┬──────────────────┬──────────────────────────────┤
│  Doctor      │   Pharmacy       │      Admin                   │
│  Portal      │   Portal         │      Portal                  │
│  (Port 3000) │   (Port 3001)    │      (Port 3002)             │
└──────────────┴──────────────────┴──────────────────────────────┘
                           ↓ HTTPS
┌─────────────────────────────────────────────────────────────────┐
│                    API LAYER (FastAPI)                           │
│                        (Port 8000)                               │
│  ┌─ Authentication (Phone OTP + PIN)                            │
│  ├─ Authorization (RBAC with 6 roles)                           │
│  ├─ Prescription Upload/Download                                │
│  ├─ Verification (QTSP)                                         │
│  ├─ Audit Trail (Hash-chained)                                  │
│  └─ Admin Dashboard                                             │
└─────────────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   PostgreSQL     │  │   Azure Blob     │  │  QTSP Provider   │
│   Database       │  │   Storage        │  │  (Dokobit)       │
│                  │  │                  │  │                  │
│ • Users          │  │ • Encrypted      │  │ • Signature      │
│ • Prescriptions  │  │   Prescriptions  │  │   Verification   │
│ • Audit Logs     │  │ • Audit Exports  │  │ • Timestamp      │
│ • Encrypted PHI  │  │                  │  │   Verification   │
└──────────────────┘  └──────────────────┘  └──────────────────┘
         ↓                                           ↓
    ┌──────────────────────────────────────────────────────┐
    │         EXTERNAL INTEGRATIONS                        │
    │  • ClamAV (Malware Scanning)                         │
    │  • Azure Key Vault (Encryption Keys)                 │
    │  • Azure Monitor (Logging & Monitoring)              │
    └──────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Schema (PostgreSQL)

```
USERS TABLE
├── admin_users (id, email, role, tenant_id, ...)
├── doctors (id, email, license_number, tenant_id, ...)
└── pharmacy_users (id, email, pharmacy_name, tenant_id, ...)

PRESCRIPTIONS TABLE
├── id (UUID, primary key)
├── tenant_id (UUID, for multi-tenancy)
├── file_path (S3 URL, encrypted in DB)
├── status (pending_verification, verified, failed)
├── created_by (doctor UUID)
├── created_at (timestamp)
└── is_deleted (soft delete flag)

VERIFICATION RESULTS TABLE
├── id (UUID)
├── prescription_id (FK to prescriptions)
├── verification_status (valid, invalid, error)
├── signature_valid (boolean)
├── certificate_valid (boolean)
├── qualified_timestamp (timestamp from QTSP)
├── evidence_stored (boolean)
└── verified_at (timestamp)

AUDIT EVENTS TABLE (Immutable)
├── id (sequential, immutable)
├── event_type (PRESCRIPTION_UPLOADED, DISPENSED, etc.)
├── actor_id (who performed action)
├── action (what was done)
├── resource_id (prescription UUID)
├── timestamp (when)
├── previous_hash (for hash-chain verification)
├── current_hash (HMAC-SHA256)
└── tenant_id (ForeignKey)

ENCRYPTION KEYS TABLE
├── field_name (e.g., "doctor.phone")
├── encryption_key_id (Azure Key Vault reference)
├── created_at (timestamp)
└── rotated_at (for key rotation)
```

---

## 🔐 Encryption Architecture

### **Database Encryption**
```
At Rest (Azure)
└── PostgreSQL Instance
    └── Transparent Data Encryption (TDE)
        └── AES-256 (Azure managed keys)

In Transit
└── Application ↔ Database
    └── SSL/TLS 1.2+
```

### **Field-Level Encryption**
```
Sensitive Fields
├── Phone Numbers (doctor, pharmacist)
├── PIN (authentication)
├── OTP (one-time password)
├── Prescription metadata
└── Dosage instructions

Encryption Algorithm: AES-256-GCM
Key Storage: Azure Key Vault
Key Rotation: Every 90 days
```

### **File Encryption (Azure Blob Storage)**
```
Prescription PDF
└── Client (Browser)
    └── Encrypted with Azure SDK
        └── Stored as encrypted blob
            └── Server-side encryption (AES-256)
                └── Key in Azure Key Vault
```

---

## 🔄 Data Flow - Prescription Upload

```
1. Doctor Selects PDF
   ↓
2. Browser (Client-Side)
   ├─ Validate file (type, size)
   └─ No encryption here (TLS handles it)
   ↓
3. API Server (FastAPI)
   ├─ Authenticate (JWT token)
   ├─ Authorize (check RBAC permissions)
   ├─ Validate metadata
   └─ Generate idempotency key
   ↓
4. Malware Scanning (ClamAV)
   ├─ Scan PDF for viruses
   ├─ Block if infected
   └─ Continue if clean
   ↓
5. QTSP Verification (Dokobit)
   ├─ Upload PDF to Dokobit
   ├─ Verify digital signature
   ├─ Extract qualified timestamp
   └─ Validate certificate chain
   ↓
6. Encrypt & Store
   ├─ Encrypt PDF (AES-256)
   ├─ Store in Azure Blob Storage
   ├─ Record reference in PostgreSQL
   └─ Encrypt sensitive metadata in DB
   ↓
7. Audit Log
   ├─ Create audit event (immutable)
   ├─ Calculate hash (HMAC-SHA256)
   ├─ Chain to previous event
   └─ Store in PostgreSQL
   ↓
8. Notify Pharmacy
   ├─ Send notification to pharmacy
   ├─ Log notification event
   └─ Mark as "ready for dispensing"
```

---

## 🔑 Authentication & Authorization

### **Authentication Workflow**

```
Step 1: Login
└─ User enters phone number
   └─ API sends OTP (SMS via external provider)

Step 2: OTP Verification
└─ User enters OTP
   └─ API verifies OTP
   └─ API generates challenge token

Step 3: PIN Verification (MFA)
└─ User enters PIN
   └─ API verifies encrypted PIN
   └─ Session created with JWT token

Token Details
├─ Type: JWT (JSON Web Token)
├─ Expiry: 8 hours
├─ Refresh: Via refresh token (24h validity)
├─ Claims: user_id, role, tenant_id, permissions
└─ Signing: HS256 with API secret key
```

### **Authorization (RBAC)**

```
Roles in System
├── Doctor (6 permissions)
│   ├─ Upload prescriptions
│   ├─ View own prescriptions
│   ├─ Revoke own prescriptions
│   └─ View verification results
│
├── Pharmacist (8 permissions)
│   ├─ View assigned prescriptions
│   ├─ Download prescriptions
│   ├─ Confirm dispensing
│   └─ View evidence
│
├── Clinic Admin (6 permissions)
│   ├─ View clinic prescriptions
│   ├─ Manage clinic users
│   └─ View clinic audit logs
│
├── Tenant Admin (9 permissions)
│   ├─ View all tenant prescriptions
│   ├─ Manage all users
│   ├─ Configure tenant settings
│   └─ View audit logs
│
├── Compliance Officer (18 permissions)
│   ├─ View all prescriptions
│   ├─ Export evidence
│   ├─ Review audit trail
│   ├─ Manage legal holds
│   └─ System health dashboard
│
└── Platform Admin (30 permissions)
    ├─ Full system access
    ├─ Create tenants
    ├─ Configure system settings
    └─ Break-glass access
```

---

## 📡 API Design

### **RESTful Principles**
- Resources: `/prescriptions`, `/users`, `/audit`
- Methods: GET (read), POST (create), PATCH (update), DELETE (delete)
- Status Codes: 200 (OK), 201 (Created), 400 (Bad Request), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

### **Security Headers**
```
HSTS: max-age=63072000; includeSubDomains; preload
CSP: default-src 'none'; frame-ancestors 'none'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
```

### **Rate Limiting**
- Default: 100 requests/minute per IP
- Login: 10 requests/minute per IP
- Upload: 20 requests/minute per IP

---

## 🏥 Multi-Tenancy Architecture

```
Tenant 1 (Clinic A)
├── Users (doctors, pharmacists)
├── Prescriptions (isolated)
├── Audit Logs (isolated)
└── Configuration

Tenant 2 (Clinic B)
├── Users (doctors, pharmacists)
├── Prescriptions (isolated)
├── Audit Logs (isolated)
└── Configuration

Data Separation
├── All queries filtered by tenant_id
├── No cross-tenant data leakage
├── Separate encryption keys per tenant option
└── Audit trail shows tenant context
```

---

## 🚀 Deployment Architecture (Production)

```
Load Balancer (Azure)
        ↓
    ┌───┴────┐
    ↓        ↓
Container  Container
Instance   Instance
(API)      (API)
    ↓        ↓
    └───┬────┘
        ↓
    Shared Services
    ├── PostgreSQL (Managed)
    ├── Azure Blob Storage
    ├── Azure Key Vault
    └── Azure Monitor
```

---

## 📊 Monitoring & Observability

### **Health Checks**
- `/health/live` — Process health (always responds if running)
- `/health/ready` — Database connectivity
- `/health/deep` — Database + Storage + Malware Scanner

### **Logging**
- Structured JSON logging
- All user actions logged
- Sensitive data automatically masked
- CloudWatch/Azure Monitor integration
- 1-year retention for compliance

### **Metrics**
- Request latency (P50, P99)
- Error rate
- Database query performance
- Storage access patterns
- Authentication attempts

---

## 🔄 Disaster Recovery

```
Backup Strategy
├── Database: Daily snapshots (30-day retention)
├── Files: Azure Geo-Redundant Storage (automatic)
└── Audit Logs: Immutable backups to Glacier

RTO: Recovery Time Objective = 1 hour
RPO: Recovery Point Objective = 1 hour

Failover Process
1. Detect outage (health check failure)
2. Switch to backup database
3. Restore from latest snapshot
4. Verify data integrity
5. Resume operations
```

---

## Next Steps

For details, see:
- [SECURITY.md](./03_SECURITY.md) — Security implementation
- [ENCRYPTION.md](./05_ENCRYPTION.md) — Encryption details
- [DEPLOYMENT.md](./07_DEPLOYMENT.md) — Production setup

