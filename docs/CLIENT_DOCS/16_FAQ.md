# Frequently Asked Questions (FAQ)

## 📚 General Questions

### **Q: What is QES Flow?**

A: QES Flow is a cloud-based prescription management system that allows clinics to upload digitally signed prescriptions, which are verified by a Qualified Trust Service Provider (Dokobit), encrypted, and made available to pharmacies for dispensing. All actions are logged in an immutable audit trail.

---

### **Q: Is QES Flow safe? Is my patient data protected?**

A: Yes. QES Flow implements enterprise-grade security:

```
Data Encryption:
├─ Prescriptions: AES-256 encryption
├─ Patient data: AES-256-GCM encryption
├─ Backup: AES-256 encrypted
└─ Transit: TLS 1.2+ (HTTPS)

Access Control:
├─ Role-based permissions
├─ Multi-tenancy (clinic isolation)
├─ Two-factor authentication (phone + PIN)
└─ Immutable audit trail

Compliance:
├─ GDPR compliant (encryption, auditing, retention)
├─ eIDAS compliant (digital signatures)
├─ Healthcare standards (data protection)
└─ Regular security audits
```

---

### **Q: Is QES Flow GDPR compliant?**

A: Yes. QES Flow implements all GDPR requirements:

```
✅ Data Protection:
├─ Encryption at rest and in transit
├─ Field-level encryption for sensitive data
├─ Access controls (RBAC)
└─ Immutable audit trail

✅ User Rights:
├─ Right to access (data export)
├─ Right to rectification (update profile)
├─ Right to erasure (with exceptions for healthcare records)
├─ Right to data portability (JSON export)
└─ Right to object (processing restrictions)

✅ Data Governance:
├─ Data retention schedule (7 years for prescriptions)
├─ Data breach notification (72 hours)
├─ Data protection officer contact
└─ Privacy policy
```

---

### **Q: Is my data stored in EU?**

A: Yes. By default, data is stored in EU data centers (Azure EU regions). This ensures:

```
✅ GDPR compliant storage (no transfer outside EU)
✅ Data sovereignty
✅ EU legal jurisdiction
✅ No US government access
```

To verify: Check your contract and deployment settings. If international deployment needed, it must be explicitly configured.

---

### **Q: What happens if Dokobit (QTSP) is down?**

A: QES Flow can handle QTSP downtime:

```
If Dokobit Unavailable:
├─ Prescriptions still accepted (stored as pending)
├─ System automatically retries every 5 minutes
├─ User sees: "Verification in progress"
├─ After 24 hours: marked as failed
├─ Clinic notified to resubmit

During Outage:
├─ Clinic: Can upload (stored)
├─ Pharmacy: Cannot download (not verified)
├─ System: Retrying verification automatically
└─ Timeline: Usually resolves within hours

Maximum Downtime Impact:
├─ Prescriptions can be verified for 24 hours after upload
├─ If not verified in 24h: marked failed
├─ Clinic must resubmit
```

---

## 🔐 Security Questions

### **Q: What if my password is compromised?**

A: QES Flow doesn't use passwords. Instead:

```
System Uses:
├─ Phone OTP (SMS one-time password)
├─ PIN (secret 4-digit code)
└─ JWT token (session)

If Phone Stolen:
├─ Attacker cannot login (needs PIN)
├─ PIN only known to user
├─ Phone stolen ≠ account compromised

If PIN Compromised:
├─ Account at risk
├─ Immediately contact admin
├─ Admin suspends account
├─ Request account reactivation

If Suspicious Activity:
1. Contact admin immediately
2. Admin suspends your account
3. Verify your identity
4. Reset PIN
5. Re-enable access
```

---

### **Q: Can anyone delete prescription records?**

A: No. Prescriptions are immutable and legally protected:

```
Cannot Delete:
├─ Clinic cannot delete
├─ Pharmacist cannot delete
├─ Clinic admin cannot delete
└─ Even platform admin cannot fully delete

Can Be "Revoked":
├─ Clinic can revoke (mark as cancelled)
├─ Shows in audit trail (reason logged)
├─ Prescription not available to pharmacy
└─ Immutable (cannot undo revocation)

Can Be Soft-Deleted:
├─ After 7 years (retention period)
├─ Only via GDPR request
├─ Even then: audit log entry remains
└─ Impossible to fully erase
```

---

### **Q: Is the audit trail really immutable?**

A: Yes, using hash-chaining:

```
How It Works:
├─ Event 1: hash = HMAC-SHA256(data)
├─ Event 2: hash = HMAC-SHA256(data + Event1_hash)
├─ Event 3: hash = HMAC-SHA256(data + Event2_hash)
└─ ...

If Someone Changes Event 2:
├─ Event 2's hash changes
├─ Event 3's "previous_hash" no longer matches
├─ Mismatch detected automatically
├─ Tampering proven
└─ Investigation triggered

Impossible to:
├─ Delete an event (gap in chain)
├─ Modify an event (hash changes)
├─ Reorder events (sequence broken)
└─ Forge an event (need all subsequent hashes)

Verification:
├─ Automatic: Every 4 hours (system)
├─ Manual: On demand (audit export)
└─ Alert: If tampering detected
```

---

### **Q: Where are encryption keys stored?**

A: In Azure Key Vault (never in code):

```
Keys Are:
├─ Generated in Key Vault
├─ Never exposed in plaintext
├─ Encrypted at rest (by Azure)
├─ Accessed via Managed Identity
├─ Rotated every 90 days
└─ Access logged

Application Cannot:
├─ Store keys in code ❌
├─ Write keys to disk ❌
├─ Log key values ❌
├─ Share keys in email ❌
└─ Use same key in dev/prod ❌

Application Can:
├─ Request key from Key Vault
├─ Use key in memory
├─ Return key to Key Vault after use
└─ Never see actual key values (API only)
```

---

## 👥 User & Access Questions

### **Q: How do I create a new user?**

A: Only admins can create users:

```
For Clinic Users (Tenant Admin):
1. Go to: https://your-domain.com/admin/users
2. Click: "Create New User"
3. Enter:
   ├─ Email
   ├─ Phone number
   ├─ Role (Doctor, Pharmacist)
   ├─ License number
   └─ Clinic
4. Click: "Create"
5. System sends activation email
6. User sets PIN and logs in

For System Users (Platform Admin Only):
1. Similar process
2. Can assign to multiple clinics
3. Can create other admins
```

---

### **Q: Can I have multiple accounts?**

A: No. One person = One account in one clinic.

```
Policy:
├─ Each phone number = one account
├─ One email = one account
├─ Cannot have duplicate registrations
└─ If needed in multiple clinics: contact admin

Why:
├─ Audit trail accountability (who did what?)
├─ Prevents unauthorized access
├─ GDPR compliance (identity verification)
└─ Security (one PIN, one authentication)

Exception:
├─ Platform admin: can have multiple
├─ If person moves to different clinic: new account
├─ Old account suspended
```

---

### **Q: I forgot my PIN. How do I reset it?**

A: Contact your clinic admin:

```
Process:
1. Contact: clinic-admin@your-clinic.com
2. Verify: Your identity (email, phone)
3. Admin: Suspends your account
4. Admin: Sends password reset link
5. You: Click link, set new PIN
6. You: Can login with new PIN

Time:
├─ Same-day response expected
├─ If urgent: call your clinic
└─ Cannot reset own PIN (security)
```

---

## 💊 Prescription Questions

### **Q: How do I upload a prescription?**

A: Follow these steps:

```
1. Login to clinic portal
2. Click: "Upload Prescription"
3. Select: Signed PDF file
4. Enter:
   ├─ Patient ID (or identifier)
   ├─ Medication name
   ├─ Dosage instructions
   └─ Click "Upload"
5. System:
   ├─ Scans for malware
   ├─ Verifies signature (Dokobit)
   ├─ Encrypts and stores
   └─ Shows: Verification results
6. Status: "Verified" or "Failed"
7. If failed: Doctor must resubmit
8. If verified: Pharmacy can dispense

Time Required:
├─ Upload: ~5 seconds
├─ Malware scan: ~0.5 seconds
├─ QTSP verification: ~3 seconds
└─ Total: ~10 seconds (varies)
```

---

### **Q: The prescription failed verification. What now?**

A: Resubmit with a properly signed PDF:

```
Verification Failed Because:
├─ No digital signature in PDF (not signed)
├─ Invalid signature (corrupted file)
├─ Certificate expired (clinic's cert outdated)
├─ Certificate revoked (license issue)
└─ Not trusted issuer (wrong type of signature)

What to Do:
1. Contact doctor
2. Check: Is PDF properly signed?
3. Advice: Use approved signature software
4. Verify: Doctor's certificate is valid
5. Resubmit: New signed PDF
6. System: Retries verification

For Clinic:
├─ Use proper signature tool (not just "sign document")
├─ Ensure digital certificate is valid
├─ Update certificate if expired
├─ Contact doctor's certificate provider if revoked
└─ Resubmit

Support:
├─ Contact: support@qesflow.com
└─ Include: Clinic name, error message
```

---

### **Q: Can I revoke a prescription after uploading?**

A: Yes, but only before dispensing:

```
Before Dispensing:
├─ Clinic: Click "Revoke"
├─ Select: Reason
├─ Confirm: Revocation
├─ Result: Pharmacy cannot download
├─ Status: "Revoked"

After Dispensing:
├─ Too late to revoke
├─ Already dispensed
├─ Must contact pharmacy directly
└─ Follow drug recall procedures

Why Limit?
├─ Prescription legally dispensed
├─ Patient might take medication
├─ Must follow proper procedures
└─ Audit trail shows what happened
```

---

### **Q: How long is prescription data retained?**

A: Depending on type:

```
Prescription Files & Data:
├─ Retention: 7 years
├─ Reason: Healthcare legal requirement
├─ After 7 years: Securely purged
└─ Backups: Archived to Glacier

Audit Logs:
├─ Retention: 1-7 years (depends on context)
├─ Reason: Compliance, dispute resolution
├─ After retention: Purged or archived
└─ GDPR deletion: May not apply

User Activity:
├─ Login logs: 1 year
├─ Action logs: 1 year
└─ Admin actions: 7 years

Access Request:
├─ GDPR "right to access": within 30 days
├─ Export data: JSON format
└─ No cost: Provided free
```

---

## 📱 Technical Questions

### **Q: What browsers are supported?**

A: Modern browsers with TLS 1.2+ support:

```
Supported:
├─ Chrome 90+
├─ Firefox 88+
├─ Safari 14+
├─ Edge 90+
└─ Mobile browsers (iOS Safari, Chrome Android)

Recommended:
├─ Latest version (auto-update)
├─ Hardware-backed encryption (if available)
└─ JavaScript enabled

Not Supported:
├─ Internet Explorer (deprecated)
├─ Older browsers (<2020)
└─ Text-only browsers
```

---

### **Q: Is there a mobile app?**

A: Web app works on mobile (responsive design):

```
Access via:
├─ Mobile browser (Chrome, Safari)
├─ URL: https://your-domain.com/clinic
├─ URL: https://your-domain.com/pharmacy
├─ URL: https://your-domain.com/admin

Features:
├─ Full access (all functions)
├─ Touch-optimized UI
├─ OTP auto-fill (iOS 14+, Android)
├─ Offline: Limited (read-only)

Native Apps:
├─ Not planned (web app sufficient)
├─ Mobile-first design
└─ All features in browser

Storage:
├─ No cached data (security)
├─ No offline prescriptions (compliance)
└─ All data in cloud
```

---

### **Q: What if the system is down?**

A: Depending on what's down:

```
Website Down:
├─ Check: Status page (status.qesflow.com)
├─ Expected: Resolved within 1 hour
├─ Cannot: Upload or download
├─ Workaround: Manually send prescriptions (via email)

Database Down:
├─ No access to any prescriptions
├─ Automatic failover (should be transparent)
├─ Expected: Resolved within 1 hour
├─ Already-uploaded: Data safe (backed up)

Dokobit Down:
├─ Prescriptions: Can still upload
├─ Verification: Delayed (queued)
├─ Pharmacy: Cannot download (not verified)
├─ Expected: Resolved within hours

During Outage:
├─ Check: Status page for updates
├─ Contact: support@qesflow.com
├─ Emergency: Call clinic admin
└─ Workaround: Temporary paper prescriptions
```

---

## 💰 Cost & Licensing Questions

### **Q: How much does QES Flow cost?**

A: Pricing depends on deployment and usage:

```
Typical Models:
├─ Per prescription: $0.10 - $0.50
├─ Per user per month: $10 - $50
├─ Per clinic per month: $100 - $500
└─ Enterprise: Custom pricing

Included:
├─ Data storage (encrypted)
├─ QTSP verification (Dokobit)
├─ Audit logs and compliance
├─ Support and maintenance
└─ Backups and disaster recovery

Not Included:
├─ SMS service (SMS per message)
├─ Email service (if external)
└─ Custom integrations

For Details:
└─ Contact: sales@qesflow.com
```

---

## 📞 Support Questions

### **Q: How do I contact support?**

A: Multiple support channels:

```
Email:
├─ General: support@qesflow.com
├─ Security: security@qesflow.com
├─ Billing: billing@qesflow.com
└─ Response time: 4 business hours

Phone:
├─ +370 5 213 3377 (Dokobit, QTSP support)
├─ Hours: 9 AM - 5 PM, Monday-Friday
└─ Time zone: UTC+2

Portal:
├─ https://support.qesflow.com
├─ Submit: Support tickets
├─ Track: Ticket status
└─ Self-service: Knowledge base

Emergency:
├─ If: System down or security incident
├─ Call: On-call engineer (phone number in portal)
├─ Available: 24/7
└─ Response: Within 15 minutes
```

---

### **Q: How do I report a security issue?**

A: Follow responsible disclosure:

```
Process:
1. Email: security@qesflow.com
2. Include:
   ├─ Issue description
   ├─ How to reproduce
   ├─ Impact assessment
   ├─ Your contact info
   └─ Optional: Proof of concept
3. System: Confirms receipt within 24 hours
4. Investigation: Begins immediately
5. Resolution: Prioritized by severity
6. Notification: Once patched
7. Credit: Offered (optional)

Do NOT:
├─ Post publicly
├─ Tell other users
├─ Sell to third parties
├─ Test without permission
└─ Access data beyond PoC

Do:
├─ Give us time to fix (90-day window)
├─ Work with us on coordinated disclosure
├─ Accept credit offer
└─ Help us understand impact

Thanks:
├─ You help keep patients safe
├─ Your feedback improves security
└─ Responsible disclosure appreciated
```

---

## Next Steps

For more details, see:
- [TROUBLESHOOTING.md](./17_TROUBLESHOOTING.md) — Common issues and solutions
- [SUPPORT.md](./18_SUPPORT.md) — Support procedures
- [API_GUIDE.md](./10_API_GUIDE.md) — Technical API reference
