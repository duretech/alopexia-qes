# GDPR Compliance Framework

## 📋 GDPR Overview

The General Data Protection Regulation (GDPR) is EU law that regulates data protection and privacy. QES Flow is fully GDPR-compliant with built-in controls for data protection and privacy.

---

## 🔐 Data Protection Principles

| Principle | Implementation |
|-----------|-----------------|
| **Lawfulness** | Data processing has legal basis (healthcare regulations) |
| **Fairness** | Users informed via privacy policy |
| **Transparency** | Clear communication about data use |
| **Purpose Limitation** | Data used only for prescriptions/healthcare |
| **Data Minimization** | Collect only necessary data |
| **Accuracy** | Mechanisms to keep data current |
| **Storage Limitation** | Data deleted per retention policy |
| **Integrity & Confidentiality** | Encryption, access controls, audit logs |
| **Accountability** | Audit trail, documentation |

---

## 👥 GDPR Rights Implementation

### **Right 1: Right to be Informed**
```
What: Users must know how their data is used
Implementation:
├─ Privacy Policy (shown on login)
├─ Consent forms (explicit opt-in)
├─ Transparent communication
└─ Data usage documentation
```

### **Right 2: Right of Access**
```
What: Users can request and download their personal data
Implementation:
├─ Data export endpoint (/api/v1/data-export)
├─ Available within 30 days
├─ Machine-readable format (JSON)
├─ Includes all personal data + audit trail
└─ Audit log entry created (exported by whom, when)
```

### **Right 3: Right to Rectification**
```
What: Users can correct inaccurate data
Implementation:
├─ Profile update endpoints
├─ User can modify: phone number
├─ Pharmacists can update: pharmacy details
├─ Changes logged in audit trail
└─ Version control (old data retained for audit)
```

### **Right 4: Right to Erasure (Right to be Forgotten)**
```
What: Users can request data deletion (with exceptions)
Implementation:
├─ Deletion request endpoint (/api/v1/deletion-request)
├─ Soft delete (marked deleted, not removed)
├─ Exceptions:
│   ├─ Audit logs (legal obligation)
│   ├─ Prescriptions (healthcare record retention)
│   ├─ Evidence (qualified signature proof)
│   └─ 7-year retention for compliance
├─ Data unavailable after deletion request
└─ Audit log shows deletion request + justification
```

### **Right 5: Right to Restrict Processing**
```
What: Users can temporarily stop data processing
Implementation:
├─ Restrict endpoint (/api/v1/restrict-processing)
├─ Account marked as restricted
├─ No new data processing (uploads blocked)
├─ Existing data retained (legal hold)
├─ Can be lifted by user request
└─ Audit log tracks all restrictions
```

### **Right 6: Right to Data Portability**
```
What: Users get data in portable, machine-readable format
Implementation:
├─ Export format: JSON (standard, portable)
├─ Includes: prescriptions, metadata, audit trail
├─ Transfer to other systems: can be imported elsewhere
├─ No fees charged
├─ Within 30 days of request
└─ Audit log created for export
```

### **Right 7: Right to Object**
```
What: Users can object to data processing
Implementation:
├─ Object endpoint (/api/v1/object-processing)
├─ Processing stops after objection (except legal obligation)
├─ Audit trail for objection
└─ Manual review required (flagged for admin)
```

### **Right 8: Rights Related to Automated Decision Making**
```
What: No purely automated decisions affecting users
Implementation:
├─ Verification is automated but:
│   ├─ Based on objective signatures (not profiling)
│   ├─ User can manually request review
│   ├─ Manual override available for errors
│   └─ Human review on denial
└─ No profiling or scoring decisions
```

---

## 📊 Data Processing Activities

### **Activity 1: Prescription Upload**
```
Personal Data: Clinic ID, signature details
Purpose: Prescription verification and processing
Legal Basis: Healthcare regulation, contractual obligation
Retention: 7 years (per healthcare law)
Rights: Access, Rectification, Erasure (with restrictions), Portability
```

### **Activity 2: Audit Logging**
```
Personal Data: User IDs, actions, timestamps, IP addresses
Purpose: Compliance, security, dispute resolution
Legal Basis: Legal obligation (healthcare audit requirement)
Retention: 1-7 years (depending on context)
Rights: Access, NO erasure (legal hold)
```

### **Activity 3: Authentication (Phone OTP)**
```
Personal Data: Phone number, login timestamp
Purpose: Identity verification, security
Legal Basis: Contractual obligation, security
Retention: Until account deletion (then 7 years for audit)
Rights: Access, Rectification, Erasure (after deletion period)
```

### **Activity 4: Email Communication**
```
Personal Data: Email address, communication content
Purpose: Notifications, support, compliance
Legal Basis: Contractual obligation, legal obligation
Retention: As long as relevant, then 1 year
Rights: Access, Rectification, Erasure
```

---

## 📋 Data Protection Impact Assessment (DPIA)

```
System: QES Flow - Prescription Management
Risk Level: HIGH (health data processing)

Key Risks Identified:
1. ✅ Large-scale processing of health data → MITIGATED
   └─ Encryption, access control, audit logs

2. ✅ Automated decision-making → MITIGATED
   └─ QTSP is verification, not profiling

3. ✅ Monitoring of behavior → MITIGATED
   └─ Audit logs for legitimate purposes only

4. ✅ Sensitive data processing → MITIGATED
   └─ AES-256 encryption, field-level controls

5. ✅ Data transfers outside EU → MITIGATED
   └─ Azure EU data centers, no transfers

Residual Risk: LOW
Conclusion: Processing can proceed with safeguards in place
```

---

## 🔐 Data Security Measures

### **Encryption**
```
Prescription Data Encryption:
├─ At Rest: AES-256 (Database + Blob Storage)
├─ In Transit: TLS 1.2+ (all connections)
├─ At Rest (Fields): AES-256-GCM (sensitive data)
└─ Key Management: Azure Key Vault (automatic rotation)

All Prescription-Related Data Is Encrypted:
✓ PDFs
✓ Patient IDs
✓ Medication names
✓ Dosage instructions
✓ Doctor/Pharmacist info
✓ Timestamps
✓ Signatures
```

### **Access Control**
```
Who Can Access Prescription Data:
├─ Authorized clinic (creator)
├─ Assigned pharmacist (for dispensing)
├─ System admin (with logging)
├─ Auditors (restricted read-only access)

Access Levels:
├─ Clinics: Own clinic prescriptions only
├─ Pharmacists: Assigned prescriptions only
├─ Admins: All (logged and audited)
└─ Regular users: Cannot access other's data
```

### **Audit Trail**
```
Immutable Record of:
├─ Who accessed data
├─ What they accessed
├─ When they accessed it
├─ What was changed
├─ IP address (for tracing)
└─ Purpose (if manually accessed)

Features:
├─ Hash-chained (cannot alter past events)
├─ HMAC verified (detect tampering)
├─ 1-7 year retention (depending on context)
└─ Exportable for audits/investigations
```

---

## 📝 Data Protection Documentation

### **1. Privacy Policy**
```
Covers:
├─ What data is collected
├─ How it's used
├─ How long it's retained
├─ Who has access
├─ User rights (GDPR rights)
└─ Contact for data requests
```

### **2. Data Processing Agreement (DPA)**
```
Between: System owner and service providers
Details:
├─ Microsoft Azure (data processor)
├─ Dokobit (QTSP provider)
├─ Other third parties
Obligations:
├─ Confidentiality
├─ Security measures
├─ Sub-processor management
└─ Data breach notification
```

### **3. Retention Schedule**
```
Prescription Data: 7 years (healthcare law)
Audit Logs: 1 year (compliance) → 7 years (if dispute)
User Accounts: Until deletion + 7 year archive
Deleted Data: Purged after retention period
Backups: Kept for DR, then purged
```

### **4. Data Breach Response Plan**
```
Detection: Automated alerts + manual review
Investigation: Severity assessment within 24 hours
Notification: To authorities within 72 hours (if applicable)
Communication: To affected users (if high risk)
Documentation: Full investigation report maintained
```

---

## ⚠️ Data Breach Notification

### **Breach Scenario**
```
IF: Data breach detected
THEN: Follow protocol:

1. Assess: Is it a breach requiring notification?
   ├─ Personal data compromised?
   ├─ Unauthorized access?
   └─ Risk to individuals?

2. Investigate: Scope and nature
   ├─ What data? (prescriptions, users, etc.)
   ├─ How many affected?
   └─ When did it happen?

3. Notify Authorities: Within 72 hours
   ├─ Data Protection Authority (DPA)
   ├─ Document: incident details, impact, measures taken
   └─ Reference: GDPR Article 33

4. Notify Users: If high risk
   ├─ Email notification
   ├─ Recommended actions
   └─ Support contact information
```

---

## 🏥 Healthcare Compliance (Beyond GDPR)

### **Prescription Retention (Health Law)**
```
Requirement: Prescriptions retained 7 years minimum
Why: Legal/medical record retention requirement
Implementation:
├─ Soft delete only (marked deleted, not removed)
├─ Legal hold prevents physical deletion
├─ Audit trail shows deletion request but data retained
└─ Automatic purge after 7 years (configurable)
```

### **Qualified Digital Signature (eIDAS)**
```
Requirement: Legally binding signature verification
Why: EU eIDAS regulation for digital healthcare documents
Implementation:
├─ QTSP provider (Dokobit) verifies signature
├─ Certificate chain validated
├─ Qualified timestamp verified
└─ Evidence stored for 7 years
```

---

## ✅ GDPR Compliance Checklist

### **For Data Controller (Your Organization)**
- [ ] Privacy policy published and accessible
- [ ] DPA in place with all processors
- [ ] Retention schedule documented
- [ ] Data breach response plan in place
- [ ] Legitimate basis documented for each processing
- [ ] Users informed of their GDPR rights
- [ ] Data export mechanism working
- [ ] Audit trail maintained for 1-7 years
- [ ] Encryption in place for sensitive data
- [ ] Access control implemented

### **For Users (Your Patients)**
- [ ] Know what data is collected
- [ ] Know why it's collected
- [ ] Know who has access
- [ ] Can request copy of their data (within 30 days)
- [ ] Can request corrections
- [ ] Can request deletion (with exceptions)
- [ ] Can object to processing
- [ ] Know their data is encrypted
- [ ] Notified of any breaches
- [ ] Can lodge complaints with DPA

---

## 📞 GDPR Contacts

- **Data Protection Officer**: dpo@company.com
- **GDPR Inquiries**: privacy@company.com
- **Data Breach Report**: security@company.com
- **Local DPA**: (varies by EU country)

---

## Next Steps

For more details, see:
- [ENCRYPTION.md](./05_ENCRYPTION.md) — How data is encrypted
- [AUDIT_TRAIL.md](./06_AUDIT_TRAIL.md) — Audit logging
- [SECURITY.md](./03_SECURITY.md) — Security measures

