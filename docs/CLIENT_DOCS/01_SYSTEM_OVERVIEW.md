# System Overview - QES Flow

## 🎯 What is QES Flow?

QES Flow is a **Qualified Electronic Signature Flow management system** that enables clinics to securely upload digitally signed prescriptions, which are then verified and processed through a pharmacy network. The system ensures compliance with EU digital signature regulations (eIDAS) while maintaining GDPR-compliant data handling.

## 🔄 How It Works - End-to-End Flow

### **Step 1: Clinic Uploads Prescription**
```
Clinic Portal → Select PDF → Upload
```
- Clinic selects a digitally signed PDF prescription
- System validates file (size, format, malware scan)
- Idempotency key prevents duplicate uploads
- All uploads are tracked to the clinic that submitted them

### **Step 2: System Processing**
```
File Upload → Malware Scan → QTSP Verification → Storage → Notification
```

**a) Malware Scanning (ClamAV)**
- PDF is scanned for malware
- Ensures security of documents
- Blocks infected files automatically

**b) QTSP Verification (Dokobit)**
- Digital signature is extracted
- Certificate chain is validated
- Qualified timestamp is verified
- System ensures the prescription is authentic and unmodified

**c) Encrypted Storage**
- File is stored in Azure Blob Storage
- All data encrypted end-to-end
- Tenant isolation ensures data separation

**d) Pharmacy Notification**
- Pharmacy is automatically notified
- Prescription appears in pharmacy portal
- Ready for dispensing

### **Step 3: Pharmacy Processes**
```
Pharmacy Portal → View Prescription → Confirm Dispensing → Audit Record
```
- Pharmacy user views verified prescription
- Downloads signed document as evidence
- Confirms dispensing
- All actions recorded in immutable audit log

### **Step 4: Admin Oversight**
```
Admin Portal → View Stats → Monitor Verifications → Export Audit Trail
```
- Admin sees system health and prescription counts
- Reviews verification results
- Exports audit trail for compliance
- Monitors security and performance

---

## 🏗️ System Components

### **Three-Portal Architecture**

| Portal | Users | Purpose |
|--------|-------|---------|
| **Clinic Portal** | Clinics | Upload digitally signed prescriptions for their clinic |
| **Pharmacy Portal** | Pharmacists | View and dispense prescriptions |
| **Admin Portal** | Administrators | Monitor system, audit logs, compliance |

### **Backend Services**

| Service | Purpose |
|---------|---------|
| **API Server** | Handles all requests, business logic, authentication |
| **Database (PostgreSQL)** | Stores users, prescriptions, audit logs |
| **Azure Blob Storage** | Stores encrypted prescription files |
| **QTSP Provider (Dokobit)** | Verifies digital signatures |
| **ClamAV** | Scans files for malware |

---

## 🔐 Data Encryption

**Everything related to prescriptions is encrypted:**

- ✅ **Prescription PDFs** — Stored encrypted in Azure Blob Storage
- ✅ **Clinic/Pharmacist Data** — Phone numbers, PINs, OTPs encrypted
- ✅ **Sensitive Fields** — Automatically masked in logs
- ✅ **Audit Trail** — Hash-chained with HMAC verification

---

## 📊 Key Features & Why They Matter

### **1. Idempotency Key**
**What it is:** A unique identifier generated for each upload attempt.

**Why it matters:**
- Prevents duplicate prescriptions if network fails and user retries
- Ensures "exactly-once" processing semantics
- Clinic can safely retry upload without creating duplicates

### **2. QTSP Verification (Dokobit)**
**What it is:** Verification of digital signatures by a Qualified Trust Service Provider.

**Why it matters:**
- Ensures prescription authenticity (doctor really signed it)
- Verifies qualified timestamp (proof of when it was signed)
- Meets EU eIDAS regulation requirements
- Provides legal proof of signature validity
- Prevents fraud and tampering

### **3. Malware Scanning (ClamAV)**
**What it is:** Automatic virus scanning before storage.

**Why it matters:**
- Protects system from infected PDFs
- Ensures file integrity
- Prevents malware distribution to pharmacy
- Required for secure document handling

### **4. Immutable Audit Trail**
**What it is:** Hash-chained log of every action with HMAC verification.

**Why it matters:**
- Proves compliance for regulatory audits
- Detects tampering (logs cannot be altered without breaking chain)
- Provides accountability (who did what, when)
- Required by GDPR Article 32 (audit logs)
- Legal evidence of system activity

### **5. Tenant Isolation**
**What it is:** Data separation between different organizations.

**Why it matters:**
- Each clinic's data is completely separate
- Prevents data leakage between clinics
- Meets multi-tenancy security requirements
- GDPR requirement (data controllers must be separate)

### **6. Field-Level Encryption**
**What it is:** Sensitive fields encrypted at rest in database.

**Why it matters:**
- Phone numbers encrypted (not readable in DB)
- PINs/OTPs never stored in plaintext
- Even database admin cannot read patient data
- Additional layer beyond database encryption

---

## 🌍 Infrastructure (Production)

**Cloud Provider:** Microsoft Azure

**Components:**
- **Azure Container Instances** — Runs Docker containers (API, portals)
- **Azure Database for PostgreSQL** — Managed database with encryption
- **Azure Blob Storage** — Encrypted file storage
- **Azure Key Vault** — Manages encryption keys
- **Azure Monitor** — Health monitoring and logging

**Why Azure:**
- Enterprise-grade security
- GDPR-compliant data centers (EU regions)
- Automatic backups and disaster recovery
- Compliance certifications (ISO 27001, SOC 2)

---

## 🔄 Workflow Comparison

### **Before QES Flow**
```
Manual Process:
Clinic → Print → Sign → Scan → Email → Pharmacy
Problems: Slow, prone to errors, no audit trail, signature not verified
```

### **With QES Flow**
```
Digital Process:
Clinic → Digital Signature → Upload → QTSP Verification → Pharmacy
Benefits: Fast, secure, verified, audited, compliant
```

---

## 📈 System Statistics

- **Prescription Processing:** < 5 seconds (including QTSP verification)
- **Storage Security:** AES-256 encryption, Azure managed keys
- **Audit Trail:** Immutable, hash-chained, HMAC verified
- **Availability:** 99.9% uptime SLA (Azure)
- **Data Retention:** Configurable, with legal hold support

---

## ⚡ Key Benefits

✅ **Regulatory Compliance** — EU eIDAS, GDPR ready  
✅ **Security** — End-to-end encryption, signature verification  
✅ **Efficiency** — Automated processing, no manual steps  
✅ **Auditability** — Complete audit trail for compliance  
✅ **Reliability** — Cloud infrastructure, automatic backups  
✅ **Scalability** — Handles growing prescription volume  

---

## Next Steps

For more details, see:
- [ARCHITECTURE.md](./02_ARCHITECTURE.md) — Technical architecture
- [PRESCRIPTION_FLOW.md](./14_PRESCRIPTION_FLOW.md) — Detailed prescription workflow
- [SECURITY.md](./03_SECURITY.md) — Security measures
- [ENCRYPTION.md](./05_ENCRYPTION.md) — Encryption strategy

