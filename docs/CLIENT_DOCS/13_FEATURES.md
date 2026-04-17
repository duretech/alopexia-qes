# Features Guide

## ✨ Core Features

### **1. Digital Prescription Upload**

**What:** Clinics upload prescription PDFs signed with digital signature.

**Why:**
```
Traditional Process:
├─ Paper prescription → Patient takes to pharmacy
├─ Patient loses it → no backup
├─ Pharmacy manually transcribes → errors
└─ No audit trail

QES Flow:
├─ Digital prescription → stored in cloud
├─ Multiple copies → prescriptions, pharmacy, clinic all have access
├─ Automatic verification → no manual transcription errors
├─ Full audit trail → cannot be faked
```

**How:**
1. Clinic opens clinic portal
2. Click "Upload Prescription"
3. Select signed PDF
4. Click "Upload"
5. System verifies signature (automatic)
6. Pharmacy can download and dispense

**Features:**
```
✅ Drag & drop upload
✅ File validation (PDF only, max 50MB)
✅ Malware scanning (ClamAV)
✅ Digital signature verification (Dokobit)
✅ Progress tracking (upload, verify, complete)
✅ Multiple file upload (batch)
✅ Preview before sending
✅ Success confirmation
```

---

### **2. Digital Signature Verification**

**What:** Automatic verification that signature is valid and legal.

**Why:**
```
Problem Without Verification:
├─ How do we know clinic actually signed?
├─ Could be forged
├─ Could be from unauthorized source
├─ No legal proof
└─ Pharmacy might dispense invalid prescription

Solution With Verification:
├─ QTSP (Dokobit) verifies signature
├─ Checks certificate is trusted
├─ Confirms not tampered with
├─ Creates legal proof (qualified timestamp)
├─ Pharmacy can safely dispense
```

**Process:**
```
1. Clinic signs PDF with digital signature
2. Clinic uploads to QES Flow
3. System calls Dokobit (QTSP)
4. Dokobit checks:
   ├─ Signature matches document
   ├─ Certificate from trusted CA
   ├─ Certificate not revoked
   ├─ Timestamp valid
   └─ Issuer authorized
5. Dokobit returns result
6. Status: "Verified" or "Failed"
7. Audit log entry created
```

**Results Stored:**
```
Verification Evidence:
├─ Signature valid: yes/no
├─ Certificate issuer: EstEID2018 (example)
├─ Certificate valid until: 2025-12-31
├─ Qualified timestamp: 2026-04-13T10:30:15Z
├─ TSA (Time Stamp Authority): Lithuanian PTT
└─ Proof retained: 7 years (legal requirement)
```

---

### **3. Encrypted Storage**

**What:** Prescriptions encrypted and stored securely in cloud.

**Why Encryption?**
```
Without Encryption:
├─ Database breach → all prescription data exposed
├─ Hacker can read patient names, medications
├─ GDPR violation → huge fines
├─ Patients trust violated
└─ Non-compliance with healthcare law

With Encryption:
├─ Database breach → encrypted data useless
├─ Hacker sees: garbage (random bytes)
├─ GDPR compliant → data unreadable
├─ Patients' data secure
├─ Healthcare law compliant
```

**Encryption Details:**
```
Prescription Files (PDFs):
├─ Location: Azure Blob Storage
├─ Algorithm: AES-256 (symmetric)
├─ Encryption: Server-side + application-level
├─ Key: In Azure Key Vault (not exposed)
└─ Result: Unreadable without correct key

Patient Data (Database):
├─ Location: PostgreSQL Database
├─ Algorithm: AES-256-GCM (authenticated)
├─ Fields: Patient ID, name, medication, dosage
├─ Key: In Azure Key Vault
└─ Tamper detection: Authentication tag

Key Rotation:
├─ Old keys retained for decryption
├─ New key used for encryption
├─ Every 90 days (automatic)
└─ Zero downtime (transparent)
```

---

### **4. Immutable Audit Trail**

**What:** Complete record of every action, cannot be tampered with.

**Why Audit Trail?**
```
Legal Requirements:
├─ GDPR: Proves data protection compliance
├─ eIDAS: Proves signature verification
├─ Healthcare: Proves audit requirements met
└─ Court: Evidence of what happened

Security:
├─ Detect unauthorized access
├─ Detect tampering attempts
├─ Accountability (who did what)
├─ Non-repudiation (prove user acted)
```

**How Immutability Works:**
```
Hash-Chaining:
├─ Event 1: hash = SHA256(event_1_data)
├─ Event 2: hash = SHA256(event_2_data + event_1_hash)
├─ Event 3: hash = SHA256(event_3_data + event_2_hash)
└─ ...

If someone tries to change Event 2:
├─ Event 2's hash changes
├─ But Event 3 still points to OLD hash
├─ Mismatch detected → tampering proven!
└─ Cannot fix without changing all subsequent events
```

**Events Tracked:**
```
User Actions:
├─ Login, logout
├─ Create user, suspend user
└─ Change permissions

Prescription Actions:
├─ Upload, download
├─ Verify status
├─ Revoke prescription
├─ Dispense prescription

System Actions:
├─ Encryption key rotated
├─ Configuration changed
├─ Backup created/restored
└─ Health checks run
```

---

### **5. Role-Based Access Control (RBAC)**

**What:** Different roles have different permissions.

**Roles:**
```
Doctor:
├─ Upload own prescriptions
├─ View own prescriptions
├─ Revoke own prescriptions
└─ Download verification results

Pharmacist:
├─ View assigned prescriptions
├─ Download prescriptions
├─ Confirm dispensing
└─ View verification evidence

Admin:
├─ Manage users (create, suspend)
├─ View all prescriptions
├─ View audit logs
└─ Configure system settings

Compliance Officer:
├─ View all prescriptions
├─ Export audit logs
├─ Review audit trail integrity
└─ Generate compliance reports
```

**Why RBAC?**
```
Problem Without RBAC:
├─ Doctor can access other doctor's prescriptions
├─ Patient privacy violated
├─ GDPR breach
├─ Data misuse possible

With RBAC:
├─ Each user sees only what they need
├─ Enforcement automatic (database level)
├─ Permissions in audit trail
├─ GDPR compliant
```

---

### **6. Multi-Tenancy (Clinic Isolation)**

**What:** Multiple clinics use same system, data completely isolated.

**How It Works:**
```
Clinic A:
├─ Users: Doctors and pharmacists from Clinic A
├─ Prescriptions: Only Clinic A's prescriptions
├─ Audit logs: Only Clinic A's actions
└─ Configuration: Clinic A's settings

Clinic B:
├─ Users: Doctors and pharmacists from Clinic B
├─ Prescriptions: Only Clinic B's prescriptions
├─ Audit logs: Only Clinic B's actions
└─ Configuration: Clinic B's settings

Data Isolation:
├─ All queries filtered by tenant_id
├─ Database-level enforcement
├─ Cannot query another clinic's data
└─ Even database admin cannot see other clinic data
```

**Why Isolation?**
```
Privacy:
├─ Clinic A cannot see Clinic B's patients
├─ GDPR compliance
├─ Competitive protection (clinics are competitors)

Security:
├─ Compromised Clinic A ≠ Clinic B affected
├─ Blast radius limited
└─ Each clinic can have own backup/recovery

Compliance:
├─ Each clinic responsible for own data
├─ Separate audit trails
└─ Separate compliance reports
```

---

### **7. Prescription Dispensing**

**What:** Pharmacist confirms prescription was dispensed to patient.

**How:**
```
1. Pharmacist downloads prescription
2. Dispenses medication to patient
3. Confirms in system:
   ├─ Quantity: 10 tablets
   ├─ Batch number: LOT123456
   └─ Timestamp: automatically recorded
4. Status changes to "Dispensed"
5. Audit log entry created
```

**What Tracks:**
```
Medical Audit:
├─ When was medication dispensed?
├─ How much was dispensed?
├─ Which batch (for recall tracking)?
├─ Who dispensed it?

For Patient:
├─ Pharmacy record of dispensing
├─ Proof medication received
└─ Needed for insurance claims

For Pharmacy:
├─ Inventory tracking
├─ Controlled substance accounting
├─ Regulatory compliance reporting
```

---

### **8. Data Export (GDPR Right)**

**What:** Users can export all their personal data as JSON.

**Who Can Use:**
```
Patients:
├─ Download all prescriptions
├─ Download all their data
├─ 30-day fulfillment required
└─ Free of charge

Doctors:
├─ Download their prescriptions
├─ Download audit log of their actions
└─ Portable format (can import elsewhere)

Compliance Officer:
├─ Export audit logs for investigation
├─ Export prescriptions for regulatory audit
└─ Format: JSON Lines (standard, portable)
```

**Data Included:**
```
Prescription Data:
├─ All prescriptions
├─ Status (verified, failed, dispensed)
├─ Verification evidence
└─ Audit trail (who accessed)

User Data:
├─ User ID, name, email
├─ Role and permissions
├─ Login history
└─ Actions performed
```

---

## 🔄 Advanced Features

### **9. Prescription Revocation**

**What:** Doctor can revoke (cancel) a prescription.

**When Used:**
```
Patient change of mind:
├─ Requested different medication
├─ No longer needs prescription
└─ Changed doctor

Mistake:
├─ Wrong patient (prescribed to wrong person)
├─ Wrong medication
├─ Wrong dosage

Safety:
├─ Potential drug interaction discovered
├─ Contraindication found
└─ Patient allergy identified
```

**Process:**
```
1. Doctor opens prescription
2. Click "Revoke"
3. Select reason (required)
4. Confirm revocation
5. Status changes to "Revoked"
6. Audit log entry created
7. Pharmacy notified
```

**Guarantees:**
```
✅ Only original doctor can revoke
✅ Revocation immutable (cannot undo)
✅ Reason logged (accountability)
✅ Pharmacy notified immediately
✅ Already-dispensed: recorded as dispensed
✅ Not-yet-dispensed: cannot download
```

---

### **10. Malware Scanning**

**What:** Upload PDFs scanned for viruses before storage.

**Why?**
```
Risk:
├─ Attacker uploads infected PDF
├─ When doctor/pharmacist downloads, malware infects
├─ Malware spreads to other users
└─ System compromised

Prevention:
├─ Scan before storing
├─ Block if infected
├─ Quarantine for investigation
└─ Users protected
```

**How:**
```
1. Doctor selects PDF
2. Browser sends to API
3. API scans with ClamAV:
   ├─ Checks against 100M+ virus signatures
   ├─ Measures scan time
   └─ Returns: Clean / Infected / Suspicious
4. If clean: proceed with upload
5. If infected: reject, error to doctor
6. If suspicious: manual review by admin
```

**Results:**
```
Infected File:
├─ Not stored
├─ Error returned to doctor
├─ Quarantine log created
├─ Admin notified
└─ Doctor told to fix/resign

Suspicious File:
├─ Stored separately (quarantine)
├─ Admin review required
├─ Not available to pharmacy
└─ Doctor contacted
```

---

### **11. Prescription Template**

**What:** Downloadable template for unsigned prescriptions.

**Why?**
```
Doctor needs template to:
├─ Know what information to include
├─ Ensure medical form is complete
├─ Get familiar with format
└─ Prepare prescription offline

Then:
├─ Fill in template
├─ Sign with digital signature
├─ Upload to QES Flow
└─ Upload proceeds normally
```

**Available For Download:**
```
Location: https://your-domain.com/templates/prescription-template.pdf

Content:
├─ Patient ID field
├─ Doctor name / license field
├─ Medication name field
├─ Dosage field
├─ Instructions field
├─ Date field
├─ Signature field (for digital signing)
└─ QES Flow branding
```

---

### **12. Batch Upload**

**What:** Upload multiple prescriptions at once.

**How:**
```
1. Click "Add Files"
2. Select multiple PDFs
3. For each file:
   ├─ Enter patient ID
   ├─ Enter medication
   ├─ Enter dosage
   └─ Review in preview
4. Click "Upload All"
5. Files uploaded sequentially
6. Progress shows: 1/5, 2/5, 3/5...
7. Results shown for each file
```

**Benefits:**
```
Time Saving:
├─ Upload 10 prescriptions in 2 minutes
├─ Not one-by-one (would take 10+ minutes)

Efficiency:
├─ Doctor uploads all daily prescriptions together
├─ Batch processing more efficient

Error Recovery:
├─ If file 3 fails, others still proceed
├─ Can retry just the failed ones
```

---

### **13. Idempotency Keys**

**What:** Guarantee prescription uploaded exactly once, never duplicated.

**Why Important?**
```
Problem:
1. Doctor uploads prescription
2. Network connection fails
3. Doctor doesn't see response
4. Doctor clicks upload again
5. Prescription uploaded twice
6. Pharmacy dispenses twice
7. Patient gets double dose 💀

Solution With Idempotency:
1. System generates UUID before upload
2. Includes UUID with prescription
3. Server checks: "Have I seen this UUID?"
4. If yes: return same response (don't re-upload)
5. If no: upload normally
6. Result: exactly-once guarantee
```

**Implementation:**
```
API Call:
POST /api/v1/prescriptions/upload
{
  "file": <PDF>,
  "patient_id": "pat-123",
  "idempotency_key": "upload-a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}

Server Logic:
1. Check if UUID seen before
2. If yes:
   ├─ Database has record
   ├─ Return same prescription_id
   ├─ Return same status
   └─ Don't process again
3. If no:
   ├─ Process normally
   ├─ Save UUID + prescription_id
   └─ Return new result

Benefit:
├─ Network fails 3 times
├─ Doctor clicks upload 3 times
├─ Server processes once
└─ Prescription created once
```

---

## 🎯 Security Features

### **14. Two-Factor Authentication (MFA)**

**What:** Requires two different credentials to login (phone + PIN).

**Why MFA?**
```
Without MFA (Password Only):
├─ Hacker guesses/steals password
├─ Hacker logs in as you
├─ Hacker downloads prescriptions
├─ Patient privacy violated

With MFA:
├─ Hacker gets password ✅
├─ But doesn't have phone ❌
├─ Cannot login
├─ Account protected
```

**QES Flow MFA:**
```
Factor 1: Phone (Something You Have)
├─ Doctor enters phone number
├─ System sends OTP via SMS
├─ Only person with phone can receive
├─ Proves phone ownership

Factor 2: PIN (Something You Know)
├─ Doctor enters PIN (from signup)
├─ Only doctor knows the PIN
├─ Even if phone stolen, attacker can't login
├─ Proves person identity
```

---

### **15. Rate Limiting**

**What:** Prevents brute force attacks by limiting login attempts.

**How:**
```
Login Endpoint:
├─ Max 10 attempts per minute per IP
├─ After 10: requests blocked for 24 hours
├─ Attacker can't guess passwords (too slow)

Upload Endpoint:
├─ Max 20 uploads per minute per user
├─ Prevents spam/resource abuse

Default Endpoint:
├─ Max 100 requests per minute per IP
├─ Prevents API abuse
```

**Example Attack Prevention:**
```
Without Rate Limiting:
Attacker tries 1000 passwords per second:
├─ Takes ~5 minutes to crack
├─ Successful breach

With Rate Limiting:
Attacker tries 10 passwords per minute:
├─ Takes 100+ minutes to crack
├─ System bans IP long before
└─ Attack prevented
```

---

## 📊 Reporting Features

### **16. Audit Log Export**

**What:** Export audit logs for compliance investigations.

**Used For:**
```
Compliance Audits:
├─ Prove all actions logged
├─ Show access controls working
├─ Demonstrate data protection
└─ Required for annual audit

Investigations:
├─ Find if data was accessed improperly
├─ Show who did what and when
├─ Prove no tampering
└─ Legal evidence

Legal:**
├─ Court cases (prove actions)
├─ Insurance claims
├─ Regulatory inquiries
└─ GDPR requests
```

**Export Process:**
```
1. Admin goes to audit explorer
2. Select date range
3. Select filters (user, event type, etc.)
4. Click "Export"
5. System:
   ├─ Verifies hash chain integrity
   ├─ Formats as JSON Lines
   ├─ Compresses with gzip
   ├─ Encrypts before download
   └─ Creates 24-hour download link
6. Admin downloads file
7. Can import to external auditor
```

---

### **17. Compliance Reports**

**What:** Automated reports for healthcare compliance.

**Reports:**
```
Monthly Activity Report:
├─ Total prescriptions uploaded
├─ Total prescriptions verified
├─ Total prescriptions dispensed
├─ Failed verifications (with reasons)
└─ Data access by role

User Access Report:
├─ Login frequency by user
├─ Failed login attempts (brute force?)
├─ Documents accessed by user
├─ Permission changes
└─ Suspicious activity

Security Report:
├─ Malware detections
├─ Failed verifications
├─ Unauthorized access attempts
├─ Encryption key rotations
└─ Certificate expirations
```

---

## ✅ Feature Checklist

All current features:
- [x] Digital prescription upload
- [x] Digital signature verification
- [x] Encrypted storage (PDFs + database)
- [x] Immutable audit trail (hash-chained)
- [x] Role-based access control
- [x] Multi-tenancy (clinic isolation)
- [x] Prescription dispensing confirmation
- [x] Data export (GDPR right)
- [x] Prescription revocation
- [x] Malware scanning
- [x] Prescription template
- [x] Batch upload
- [x] Idempotency keys
- [x] Two-factor authentication
- [x] Rate limiting
- [x] Audit log export
- [x] Compliance reports

---

## Next Steps

For more details, see:
- [PRESCRIPTION_FLOW.md](./14_PRESCRIPTION_FLOW.md) — Detailed prescription workflow
- [API_GUIDE.md](./10_API_GUIDE.md) — API endpoints for features
- [SECURITY.md](./03_SECURITY.md) — Security implementation
