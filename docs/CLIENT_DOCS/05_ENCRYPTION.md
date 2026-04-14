# Data Encryption Strategy

## 🔐 Encryption Overview

**All prescription-related data is encrypted.** QES Flow uses military-grade encryption standards to protect sensitive data at every stage: at rest, in transit, and during processing.

---

## 📦 What Is Encrypted?

### **Prescription Files**
```
✅ PDF documents (prescription images)
   Location: Azure Blob Storage
   Encryption: AES-256 (Server-side)
   Key Storage: Azure Key Vault
```

### **Patient Information**
```
✅ Patient ID
✅ Patient name
✅ Medical history (if stored)
   Location: PostgreSQL Database
   Encryption: Field-level AES-256-GCM
   Key Storage: Azure Key Vault
```

### **Prescription Metadata**
```
✅ Medication name
✅ Dosage instructions
✅ Prescriber information
✅ Timestamps
   Location: PostgreSQL Database
   Encryption: Field-level AES-256-GCM
   Key Storage: Azure Key Vault
```

### **User Credentials**
```
✅ Phone numbers (encrypted)
✅ PIN (hashed + encrypted)
✅ OTP (encrypted in transit only)
   Location: PostgreSQL Database
   Encryption: AES-256-GCM
   Key Storage: Azure Key Vault
```

### **Audit Logs**
```
✅ User actions
✅ Data access records
✅ System events
✅ Changes made
   Location: PostgreSQL Database
   Encryption: Database-level encryption
   Key Storage: Azure Key Vault
```

---

## 🔒 Encryption Layers

```
┌──────────────────────────────────────┐
│   Data in Plaintext (Doctor)         │
│   (On their computer, not encrypted) │
└──────────────┬───────────────────────┘
               ↓
        TLS 1.2+ Encryption
        (Transport Layer)
        ├─ Encrypts data in transit
        ├─ HTTPS protocol
        └─ Certificate verified
               ↓
    ┌─────────────────────────┐
    │   API Server (FastAPI)  │
    │   Decrypts HTTPS        │
    │   Processes data        │
    └──────────┬──────────────┘
               ↓
    Field-Level Encryption
    (Application Layer)
    ├─ Encrypts sensitive fields
    ├─ AES-256-GCM algorithm
    ├─ Only needed fields encrypted
    └─ Indexes on plaintext keys
               ↓
    ┌─────────────────────────────┐
    │   PostgreSQL Database       │
    │   Storage Encryption (TDE)  │
    │   AES-256 by Azure          │
    └──────────┬──────────────────┘
               ↓
        ┌──────────────────────┐
        │   Encrypted Data     │
        │   At Rest in DB      │
        └──────────────────────┘
               ↓
        ┌──────────────────────┐
        │   Azure Blob Storage │
        │   PDF Files          │
        │   AES-256 encrypted  │
        └──────────────────────┘
```

---

## 🔑 Encryption Algorithms

### **Algorithm 1: AES-256 (Advanced Encryption Standard)**

```
What: Symmetric encryption (same key for encrypt/decrypt)
Standard: NIST approved, used by US government
Strength: 256-bit key = 2^256 possible keys
Time to Crack: ~billion years with current computers
Use Cases:
├─ Prescription PDFs (Azure Blob Storage)
├─ Database fields (sensitive data)
└─ Database backups
```

### **Algorithm 2: AES-256-GCM (Authenticated Encryption)**

```
What: AES-256 + authentication tag
Benefit: Detects tampering (someone can't change encrypted data without detection)
Standard: NIST approved
Use Cases:
├─ Phone numbers
├─ PINs
├─ OTPs
└─ Medication details

How It Works:
1. Encrypt data with AES-256
2. Generate authentication tag (HMAC-like)
3. Tag proves data hasn't been modified
4. Decrypt fails if tag invalid (tampering detected)
```

### **Algorithm 3: HMAC-SHA256 (Authentication)**

```
What: Hash-based Message Authentication Code
Purpose: Verify data hasn't been altered
Use Cases:
├─ Audit log integrity (hash-chaining)
├─ Token signing (JWT)
└─ Message authentication

Why Used:
├─ Proven standard (NIST approved)
├─ Fast computation
├─ Impossible to reverse (one-way)
└─ Small output (256 bits)
```

### **Algorithm 4: bcrypt (Password Hashing)**

```
What: Slow hashing algorithm
Purpose: Securely hash PINs (not encryption, one-way)
Strength: Automatically increases difficulty over time
Use Cases:
├─ PIN hashing (cannot be reversed)
└─ Password verification

Why Not Simple MD5/SHA1:
├─ Too fast (vulnerable to brute force)
├─ No salt by default
└─ Deprecated for security-critical data
```

---

## 🔑 Key Management

### **Where Are Keys Stored?**

```
NOT in Code or Config Files
├─ No hardcoded keys
├─ No keys in git
├─ No keys in environment files
└─ No keys in Docker images

YES in Azure Key Vault
├─ Centralized secret storage
├─ Access control (who can use key)
├─ Audit logging (who accessed key)
├─ Automatic key rotation
├─ Backup and recovery
└─ Encryption at rest (keys encrypted)

Application Access Flow:
┌─ App starts
├─ Authenticates to Azure via Managed Identity
├─ Requests key from Key Vault
├─ Azure approves (RBAC check)
├─ Returns decrypted key
├─ App uses key for encryption/decryption
└─ Key never stored locally, only in memory
```

### **Key Rotation**

```
Schedule: Every 90 days (automatic)

Process:
1. Old key marked for rotation
2. New key generated in Key Vault
3. New encryptions use new key
4. Old key retained for decryption (old data)
5. After retention period, old key deleted

Why Rotate:
├─ Limits damage if key compromised
├─ Industry best practice
├─ Compliance requirement (GDPR, HIPAA)
└─ Reduces key usage (cryptographic best practice)

No Downtime:
├─ Application supports multiple keys
├─ Old data readable with old key
├─ Transition transparent to users
└─ Zero downtime encryption
```

### **Separate Keys per Environment**

```
Development Environment
├─ Development key (test data only)
└─ Never used for production data

Staging Environment
├─ Staging key (test data only)
└─ Similar to production but isolated

Production Environment
├─ Production key (real data)
├─ Different from staging/dev
├─ Higher security restrictions
└─ Separate backup encryption key
```

---

## 🔄 Encryption in Action

### **Scenario 1: Doctor Uploads Prescription**

```
Step 1: Doctor selects PDF on computer
        ↓
Step 2: PDF travels over HTTPS (TLS encrypted)
        ↓
Step 3: API receives PDF (decrypts HTTPS)
        ↓
Step 4: API scans PDF for malware (plaintext)
        ↓
Step 5: API extracts metadata
        ├─ Patient ID → encrypted before storage
        └─ Medication → encrypted before storage
        ↓
Step 6: API encrypts PDF with AES-256
        ├─ Retrieves key from Key Vault
        ├─ Encrypts PDF content
        └─ Stores encrypted blob
        ↓
Step 7: API stores encrypted PDF in Azure
        ├─ Additional AES-256 encryption (server-side)
        ├─ Encrypted file + encrypted metadata
        └─ Only reference stored in DB
        ↓
Result: Doctor can see uploaded prescription
        Pharmacy cannot see PDF content without key
        Only authorized users can decrypt
```

### **Scenario 2: Pharmacy Downloads Prescription**

```
Step 1: Pharmacist requests prescription
        ↓
Step 2: API checks authorization
        ├─ Verify pharmacist assigned to prescription
        ├─ Check permissions (has DOCUMENT_DOWNLOAD)
        └─ Log access request
        ↓
Step 3: API retrieves encrypted PDF from Azure
        ├─ Downloads encrypted blob
        └─ No intermediate decryption needed
        ↓
Step 4: API decrypts PDF
        ├─ Retrieves key from Key Vault
        ├─ Decrypts blob (AES-256)
        └─ Generates temporary URL
        ↓
Step 5: Return temporary download link
        ├─ Link expires in 5 minutes
        ├─ One-time use
        └─ Encrypted in transit (HTTPS)
        ↓
Step 6: Pharmacist downloads PDF
        ├─ Decrypted in browser
        ├─ Displayed as normal PDF
        └─ Cannot be saved/forwarded (enforced by app)
        ↓
Step 7: Audit log created
        ├─ WHO: Pharmacist ID
        ├─ WHAT: Downloaded prescription
        ├─ WHEN: Timestamp
        ├─ WHERE: IP address
        └─ WHY: Patient ID (context)

Result: Prescription visible to authorized user only
        All access logged and immutable
        Data encrypted at rest
```

---

## 🛡️ Defense in Depth

### **Layer 1: Network**
```
TLS 1.2+ encryption
├─ Data encrypted in transit
├─ Certificate verified (no MITM)
├─ Perfect forward secrecy (if connection compromised, past traffic safe)
└─ HTTPS only (HTTP redirected)
```

### **Layer 2: Application**
```
Field-Level Encryption
├─ Sensitive fields encrypted before DB insert
├─ Only decrypted when needed
├─ App-level control (not just DB control)
└─ Improves security vs DB-only encryption
```

### **Layer 3: Database**
```
Transparent Data Encryption (TDE)
├─ Entire database encrypted
├─ Encrypts all data, indexes, backups
├─ Transparent (no app changes needed)
└─ Key managed by Azure
```

### **Layer 4: Storage**
```
Azure Storage Service Encryption
├─ Files encrypted in blob storage
├─ Separate from field-level encryption
├─ Server-side encryption (Azure manages)
└─ Transparent to application
```

### **Layer 5: Backups**
```
Encrypted Backups
├─ Database backups encrypted
├─ File backups encrypted
├─ Backup encryption key separate from live key
└─ Disaster recovery key stored securely
```

---

## 🔍 Encryption Verification

### **How to Verify Data Is Encrypted?**

```
1. Check Database
   ├─ Query SELECT * FROM prescriptions
   ├─ Data appears as binary/garbage characters
   ├─ Cannot read without decryption
   └─ Confirms field-level encryption working

2. Check Azure Blob Storage
   ├─ Download encrypted blob directly
   ├─ Open with text editor
   ├─ Data appears as binary/garbage
   └─ Confirms storage encryption working

3. Check Network Traffic
   ├─ Use Wireshark/similar tool
   ├─ Capture traffic to API
   ├─ All data encrypted in HTTPS
   ├─ Cannot read prescription data
   └─ Confirms TLS encryption working

4. Check Backups
   ├─ Try to restore backup
   ├─ Data only readable with correct key
   ├─ Cannot read without Key Vault
   └─ Confirms backup encryption working
```

---

## 📊 Performance Impact

| Operation | Encryption Overhead | Acceptable? |
|-----------|-------------------|-------------|
| Upload prescription | +200ms (QTSP dominates) | ✅ Yes |
| Download prescription | +100ms | ✅ Yes |
| Store in database | +10ms per field | ✅ Yes |
| Search index | None (encrypted at column level) | ✅ Yes |
| Backup | +5% storage space | ✅ Yes |

**Conclusion:** Encryption overhead is minimal and acceptable for healthcare data security.

---

## 🆘 Troubleshooting Encryption

### **Issue: "Decryption failed" error**

```
Causes:
├─ Wrong key being used
├─ Key rotation not completed
├─ Data corrupted
└─ Application bug

Solution:
├─ Check audit log (when was data encrypted?)
├─ Verify correct key version in use
├─ Restore from backup if corrupted
└─ Contact support if persists
```

### **Issue: "Key not found" in Key Vault**

```
Causes:
├─ Key deleted (shouldn't happen)
├─ Permissions not set
├─ Application identity not trusted
└─ Key Vault access disabled

Solution:
├─ Check Key Vault access logs
├─ Verify application Managed Identity
├─ Restore from backup if needed
└─ Contact Azure support
```

---

## ✅ Encryption Checklist

- ✅ All prescription PDFs encrypted (AES-256)
- ✅ All patient data encrypted (AES-256-GCM)
- ✅ All user credentials encrypted
- ✅ All audit logs encrypted
- ✅ Encryption keys in Key Vault
- ✅ Keys rotated every 90 days
- ✅ TLS 1.2+ for all connections
- ✅ Backups encrypted
- ✅ Encryption verified regularly
- ✅ Incident response plan for key compromise

---

## Next Steps

For more details, see:
- [SECURITY.md](./03_SECURITY.md) — Overall security
- [AUDIT_TRAIL.md](./06_AUDIT_TRAIL.md) — Audit logging
- [GDPR_COMPLIANCE.md](./04_GDPR_COMPLIANCE.md) — GDPR requirements

