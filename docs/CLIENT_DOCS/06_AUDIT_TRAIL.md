# Immutable Audit Trail & Logging

## 📋 What Is an Audit Trail?

An **audit trail** is a complete, chronological record of every action taken in the system. It answers:
- **Who** performed an action (user ID)
- **What** they did (action type)
- **When** they did it (timestamp)
- **Where** they did it (IP address, endpoint)
- **Why** they did it (context/resource)

**In QES Flow, the audit trail is IMMUTABLE** — once created, it cannot be altered, deleted, or modified. This is a legal requirement for healthcare and compliance systems.

---

## 🔗 Hash-Chaining (How Immutability Works)

### **What Is Hash-Chaining?**

Each audit event is cryptographically linked to the previous one, creating an unbreakable chain:

```
Event 1
├─ Action: "Prescription uploaded"
├─ Data: { doctor_id: ABC, file_size: 250KB, ... }
├─ Timestamp: 2024-01-15 10:30:00
└─ Hash: HMAC-SHA256(event_1_data) = abc123def456...

Event 2 (next event)
├─ Action: "Prescription verified"
├─ Data: { prescription_id: XYZ, status: "valid", ... }
├─ Previous Hash: abc123def456... (link to Event 1)
├─ Timestamp: 2024-01-15 10:35:00
└─ Hash: HMAC-SHA256(event_2_data + previous_hash) = xyz789abc123...

Event 3 (third event)
├─ Action: "Prescription downloaded"
├─ Data: { user_id: DEF, prescription_id: XYZ, ... }
├─ Previous Hash: xyz789abc123... (link to Event 2)
├─ Timestamp: 2024-01-15 10:40:00
└─ Hash: HMAC-SHA256(event_3_data + previous_hash) = def456xyz789...

Detection of Tampering:
If someone tries to change Event 2:
├─ Event 2's hash will change
├─ But Event 3 still points to old Event 2's hash
├─ Mismatch detected immediately
├─ Chain is broken = tampering confirmed!
```

### **Why Hash-Chaining Matters**

```
Without Hash-Chaining:
├─ Administrator could delete events
├─ Change timestamps
├─ Modify user IDs
├─ No way to detect tampering
└─ Risk: Hidden security breaches

With Hash-Chaining:
├─ Any change breaks the chain
├─ Tampering immediately obvious
├─ Cannot alter past events without detection
├─ Provides legal proof of integrity
└─ Satisfies GDPR audit requirements
```

---

## 📊 Audit Events Tracked

### **Prescription Events**

| Event | When | Data Logged |
|-------|------|-------------|
| `PRESCRIPTION_UPLOADED` | Doctor uploads PDF | File size, patient ID, doctor ID, file hash |
| `PRESCRIPTION_VERIFIED` | QTSP returns result | Status (valid/invalid), timestamp, cert details |
| `PRESCRIPTION_REVOKED` | Doctor revokes prescription | Reason, timestamp, doctor ID |
| `PRESCRIPTION_DISPENSED` | Pharmacy confirms dispensing | Pharmacist ID, quantity, timestamp |

### **User Events**

| Event | When | Data Logged |
|-------|------|-------------|
| `USER_LOGIN` | User logs in | User type, phone, IP address, timestamp |
| `USER_LOGOUT` | User logs out | User ID, session duration |
| `USER_CREATED` | New user registered | User type, email, role, created by |
| `USER_SUSPENDED` | Admin suspends user | User ID, reason, admin ID |
| `USER_REACTIVATED` | Admin reactivates user | User ID, admin ID |

### **Document Events**

| Event | When | Data Logged |
|-------|------|-------------|
| `DOCUMENT_DOWNLOADED` | File accessed | User ID, prescription ID, download timestamp |
| `DOCUMENT_EXPORTED` | Audit trail exported | Admin ID, date range, record count |
| `DOCUMENT_DELETED` | Data deletion request | User ID, deletion reason, timestamp |

### **System Events**

| Event | When | Data Logged |
|-------|------|-------------|
| `SYSTEM_CONFIG_CHANGED` | Settings modified | Setting name, old value, new value, admin ID |
| `ENCRYPTION_KEY_ROTATED` | Key updated | Old key ID, new key ID, timestamp |
| `BACKUP_CREATED` | Data backed up | Backup size, location, checksum |
| `BACKUP_RESTORED` | Restore operation | Backup date, records restored, timestamp |

### **Security Events**

| Event | When | Data Logged |
|-------|------|-------------|
| `FAILED_LOGIN` | Login attempt fails | Phone, attempt count, IP address |
| `UNAUTHORIZED_ACCESS` | Permission denied | User ID, resource requested, permission needed |
| `ENCRYPTION_FAILURE` | Cannot encrypt/decrypt | Field, error type, resolved? |
| `KEY_ACCESS` | Key Vault accessed | Key ID, purpose, user identity |

---

## 📝 Audit Log Entry Structure

```json
{
  "id": 12345,                      // Sequential, immutable ID
  "event_id": "uuid-string",        // Unique event identifier
  "tenant_id": "clinic-uuid",       // Which clinic (multi-tenancy)
  "event_type": "PRESCRIPTION_UPLOADED",
  "actor_id": "doctor-uuid",        // Who did it
  "action": "upload_prescription",  // What action
  "timestamp": "2024-01-15T10:30:00Z",
  "ip_address": "192.168.1.100",    // Where from
  "endpoint": "/api/v1/prescriptions/upload",
  "resource_type": "prescription",
  "resource_id": "rx-uuid",         // Which prescription
  "details": {
    "file_name": "prescription.pdf",
    "file_size_bytes": 250000,
    "patient_id": "patient-uuid",
    "status_before": null,
    "status_after": "pending_verification"
  },
  "result": "success",              // or "failure"
  "error_message": null,            // if failure
  "previous_hash": "abc123...",     // Hash of previous event
  "current_hash": "xyz789..."       // This event's hash
}
```

---

## 🔍 Viewing & Searching Audit Logs

### **Admin Dashboard Access**

```
Path: /admin/audit-explorer
Features:
├─ Filter by date range
├─ Filter by user
├─ Filter by event type
├─ Filter by resource
├─ Search by keyword
└─ Export results (JSON Lines)
```

### **Search Examples**

```
1. Find all prescriptions uploaded by doctor ABC
   Filter: event_type = PRESCRIPTION_UPLOADED
           AND actor_id = "doctor-abc-uuid"

2. Find all access to prescription XYZ
   Filter: resource_id = "prescription-xyz-uuid"
   Result: Who accessed it, when, what they did

3. Find all failed logins from IP 192.168.1.100
   Filter: event_type = FAILED_LOGIN
           AND ip_address = "192.168.1.100"
   Purpose: Detect brute force attempts

4. Find all dispensing events in January
   Filter: event_type = PRESCRIPTION_DISPENSED
           AND timestamp between 2024-01-01 and 2024-01-31
   Purpose: Monthly reconciliation
```

---

## 📤 Exporting Audit Logs

### **Export Process**

```
1. Admin selects date range and filters
   └─ e.g., "All prescriptions in Q1 2024"

2. System generates export
   ├─ Retrieves events from database
   ├─ Verifies hash-chain integrity
   ├─ Formats as JSON Lines (standard format)
   └─ Compresses (gzip)

3. File is created
   ├─ Named: audit_export_2024-Q1.json.gz
   ├─ Encrypted before download
   ├─ Stored in Azure Blob Storage
   └─ Link valid for 24 hours only

4. Admin downloads file
   ├─ Decrypted during download
   ├─ Can be opened in any text editor
   ├─ JSON Lines format (one event per line)
   └─ Ready for archiving or external audit

5. Audit event created
   ├─ DOCUMENT_EXPORTED event logged
   ├─ Who exported, when, how many records
   ├─ Included in future exports
   └─ Hash-chained to previous events
```

### **Export Format (JSON Lines)**

```json
{"id":1,"event_type":"USER_LOGIN","actor_id":"doctor-123","timestamp":"2024-01-01T08:00:00Z","ip_address":"192.168.1.100","result":"success"}
{"id":2,"event_type":"PRESCRIPTION_UPLOADED","actor_id":"doctor-123","timestamp":"2024-01-01T08:05:00Z","resource_id":"rx-456","result":"success"}
{"id":3,"event_type":"PRESCRIPTION_VERIFIED","actor_id":"system","timestamp":"2024-01-01T08:06:00Z","resource_id":"rx-456","details":{"status":"valid"},"result":"success"}
{"id":4,"event_type":"DOCUMENT_DOWNLOADED","actor_id":"pharmacy-789","timestamp":"2024-01-01T08:10:00Z","resource_id":"rx-456","result":"success"}
...
```

---

## 🔐 Audit Log Security

### **How Audit Logs Are Protected**

```
1. Encryption
   ├─ Stored in encrypted database
   ├─ Backup encrypted separately
   └─ Export encrypted during download

2. Access Control
   ├─ Only admins can view audit logs
   ├─ Cannot be deleted (soft-delete violations detected)
   ├─ Cannot be modified (hash-chain breaks)
   └─ Export logged and audited

3. Integrity Verification
   ├─ Hash-chaining verifies no tampering
   ├─ Regular hash verification runs
   ├─ Alerts if integrity broken
   └─ Can be imported to external verifier

4. Retention
   ├─ Kept for 1-7 years depending on type
   ├─ Legal holds prevent deletion
   ├─ After retention, purged securely
   └─ Backup copies archived to Glacier
```

---

## 🆘 Detecting Tampering

### **Hash Verification Process**

```
System regularly verifies audit log integrity:

1. Calculate all hashes
   For each event:
   ├─ Take event data
   ├─ Add previous hash
   ├─ Calculate HMAC-SHA256
   └─ Compare with stored hash

2. Verify chain
   For each event:
   ├─ Check previous hash matches
   ├─ Check sequence is unbroken
   └─ Detect any gaps/deletions

3. Alert if tampering
   If any mismatch:
   ├─ Create security alert
   ├─ Notify administrators immediately
   ├─ Log integrity check failure (recursive audit!)
   └─ Lock system for investigation

4. Investigation
   └─ Review change logs
       ├─ What changed?
       ├─ When was it changed?
       ├─ Who had access?
       └─ Was it authorized?
```

---

## 📊 Audit Log Analytics

### **Compliance Reports**

```
Reports Generated Automatically:

1. Monthly Activity Report
   ├─ Total prescriptions uploaded
   ├─ Total prescriptions dispensed
   ├─ Failed verifications
   └─ Data access by role

2. User Access Report
   ├─ Login frequency by user
   ├─ Failed login attempts
   ├─ Documents accessed by user
   └─ User action timeline

3. Security Incident Report
   ├─ Failed logins (brute force?)
   ├─ Unauthorized access attempts
   ├─ Encryption failures
   └─ Key access anomalies

4. Audit Trail Integrity Report
   ├─ Hash verification status
   ├─ Events successfully audited
   ├─ Any integrity issues
   └─ Last verification date
```

---

## ⚠️ Audit Trail Limitations & Considerations

### **What Is NOT Logged**

```
System health checks
├─ Reason: Too noisy, thousands per day
├─ Mitigation: Separate monitoring logs

API errors without user action
├─ Reason: System events, not user actions
├─ Mitigation: Available in error logs

Session keep-alive pings
├─ Reason: No actionable event occurred
├─ Mitigation: Login/logout events captured

File content changes within DB
├─ Reason: Encrypted, immutable anyway
├─ Mitigation: File hashes logged
```

### **Data Retention Trade-off**

```
Keep 7 Years (Legal Requirement)
├─ Prescriptions
├─ Signatures
├─ Verification proofs
└─ Related audit events

Keep 1 Year (Compliance)
├─ User login/logout
├─ Data access
├─ Administrative actions
└─ System configuration changes

Purged After Retention
├─ Securely deleted
├─ Backups archived to Glacier
├─ Unrecoverable after purge
└─ Destruction verified
```

---

## ✅ Audit Trail Checklist

- ✅ Every action logged (prescribed list)
- ✅ Immutable (hash-chained)
- ✅ Encrypted at rest
- ✅ Accessible to admins only
- ✅ Searchable and filterable
- ✅ Exportable for compliance
- ✅ Regularly integrity-checked
- ✅ 1-7 year retention
- ✅ Alerts on tampering attempts
- ✅ GDPR Article 32 compliant

---

## Next Steps

For more details, see:
- [SECURITY.md](./03_SECURITY.md) — Security measures
- [GDPR_COMPLIANCE.md](./04_GDPR_COMPLIANCE.md) — GDPR requirements
- [OPERATIONS.md](./08_OPERATIONS.md) — Day-to-day operations

