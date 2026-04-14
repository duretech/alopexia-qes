# Integration Guide

## 🔗 External System Integrations

QES Flow integrates with several external services. This guide explains each integration and how it works.

---

## 📱 SMS Provider (OTP Delivery)

### **Current Setup: Twilio**

```
Flow:
1. User requests login → enters phone number
2. API calls Twilio API
3. Twilio sends SMS with OTP
4. User receives SMS
5. User enters OTP
6. API verifies against what was sent
```

### **Configuration**

Store in Azure Key Vault:
```
TWILIO_ACCOUNT_SID: AC1234567890abcdef
TWILIO_AUTH_TOKEN: <secret-token>
TWILIO_PHONE_NUMBER: +1-800-QESFLOW
```

### **API Call**

```bash
curl -X POST https://api.twilio.com/2010-04-01/Accounts/AC.../Messages.json \
  -u "AC...:auth_token" \
  --data-urlencode "From=+1-800-QESFLOW" \
  --data-urlencode "To=+44-20-1234-5678" \
  --data-urlencode "Body=Your QES Flow OTP: 123456 (expires in 10 minutes)"
```

### **Alternative Providers**

If you want to switch SMS providers:

| Provider | Pros | Cons | Cost |
|----------|------|------|------|
| **Twilio** | Reliable, global coverage, good documentation | Moderate cost | $0.01-0.05/SMS |
| **AWS SNS** | If already using AWS | Less documentation than Twilio | $0.00645/SMS |
| **Vonage (Nexmo)** | Good European coverage | Smaller developer community | $0.01-0.04/SMS |
| **Bandwidth** | Good for US | Limited international | $0.00594/SMS |

To switch:
1. Create account with new provider
2. Get API credentials
3. Update code (SMS sending module)
4. Update Key Vault with new credentials
5. Test with staging environment
6. Deploy to production

---

## 🔐 Qualified Trust Service Provider (QTSP)

### **Current Setup: Dokobit**

Dokobit is the Qualified Trust Service Provider (QTSP) that verifies digital signatures on prescriptions.

**Why Dokobit?**
```
Legal Requirement (eIDAS):
├─ Prescriptions must be digitally signed
├─ Signature verified by qualified provider
├─ Qualified timestamp required
├─ Certificate chain must be valid
└─ Evidence stored for 7 years

Dokobit Qualifications:
├─ EU-qualified timestamp provider
├─ Authorized by Lithuanian DPA
├─ Uses EU-trusted CAs
├─ Audited for security compliance
└─ Meets eIDAS regulation
```

### **Integration Points**

**1. Signature Verification**
```
Process:
1. Doctor uploads PDF with digital signature
2. API sends PDF to Dokobit
3. Dokobit verifies:
   ├─ Signature is valid
   ├─ Certificate is trusted
   ├─ Certificate not revoked
   ├─ Signature timestamp is valid
   └─ Issuer is authorized
4. Dokobit returns result (valid/invalid)
5. API stores result in database
6. Pharmacy can see verification status
```

**2. Qualified Timestamp**
```
Provides:
├─ Cryptographic proof of when document was signed
├─ Binds signature to specific time
├─ Cannot be changed later
└─ Legally admissible in court

Retrieved from Dokobit response:
{
  "qualified_timestamp": "2026-04-13T10:30:15Z",
  "tsa_server": "http://timestamp.dokobit.com",
  "issuer": "Lithuanian Post and Telecommunications Office"
}
```

**3. Evidence Storage**
```
Evidence includes:
├─ Original signature
├─ Certificate chain
├─ Qualified timestamp
├─ Verification result
├─ Issuer information
└─ Signature algorithm details

Stored in database:
├─ Encrypted with AES-256-GCM
├─ Retained for 7 years (legal requirement)
├─ Immutable (cannot be changed)
└─ Hash-chained in audit trail
```

### **Configuration**

Store in Azure Key Vault:
```
DOKOBIT_API_KEY: <secret-api-key>
DOKOBIT_API_URL: https://api.dokobit.com
DOKOBIT_ACCOUNT_ID: <account-id>
```

### **API Call Example**

```bash
curl -X POST https://api.dokobit.com/api/signature/verify \
  -H "Authorization: Bearer <DOKOBIT_API_KEY>" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@prescription.pdf" \
  -F "return_data=true"
```

**Response (Success):**
```json
{
  "signature": {
    "status": "valid",
    "signer": {
      "name": "Dr. Jane Smith",
      "identifier": "PNOLV-123456789ABC"
    },
    "certificate": {
      "issuer": "EstEID2018",
      "valid_from": "2020-01-01T00:00:00Z",
      "valid_until": "2025-12-31T23:59:59Z",
      "status": "valid"
    },
    "signature_timestamp": "2026-04-13T10:30:15Z",
    "timestamp_authority": "Lithuanian Post and Telecommunications Office"
  },
  "signature_verification_result": "VALID"
}
```

**Response (Invalid Signature):**
```json
{
  "signature_verification_result": "INVALID",
  "error": "Signature does not match document content"
}
```

### **Fallback Strategy**

If Dokobit is down:
```
Option 1: Queue for retry (Recommended)
├─ Store prescription as pending
├─ Retry verification every 5 minutes
├─ Notify doctor of delay
└─ Auto-verify when service recovers

Option 2: Manual review
├─ System admin manually verifies
├─ Requires audit log entry
└─ Not recommended (defeats compliance)

Option 3: Reject upload
├─ Return error to doctor
├─ Doctor must retry later
└─ Not recommended (poor UX)
```

### **Monitoring Dokobit**

```
Health Check (every 5 minutes):
1. Call Dokobit API with test request
2. Measure response time
3. Alert if:
   ├─ Response time > 10 seconds
   ├─ 5 consecutive failures
   └─ Service unavailable

Dashboard Metrics:
├─ Verification latency (should be <3s)
├─ Verification success rate (should be >95%)
├─ Dokobit availability (should be >99.9%)
└─ Failed verifications (investigate spikes)
```

---

## 🛡️ Antivirus Scanning (ClamAV)

### **Current Setup: ClamAV**

ClamAV scans uploaded prescription PDFs for malware before they're stored.

**Why Scan?**
```
Security:
├─ Prevent infected files from being stored
├─ Stop malware propagation
├─ Protect all users from threats
└─ Quarantine suspicious files

Compliance:
├─ ISO 27001 requirement
├─ Security best practice
└─ Demonstrate risk mitigation
```

### **Scanning Process**

```
1. Doctor uploads prescription PDF
2. API receives file (not saved yet)
3. API scans with ClamAV
   ├─ ClamAV checks against virus definitions
   ├─ Measures scan time
   ├─ Returns result (clean/infected/suspicious)
4. If infected:
   ├─ File rejected
   ├─ Error returned to doctor
   ├─ File never stored
   └─ Quarantine log created
5. If clean:
   ├─ File encrypted and stored
   ├─ Signature verification proceeds
   └─ User continues upload
```

### **Configuration**

```
ClamAV Service
├─ Runs in separate container
├─ Listens on port 3310
├─ Virus definitions updated daily
└─ Memory: ~1GB (database of known malware)

Storage in Azure Key Vault:
├─ CLAMAV_HOST: clamav-container:3310
└─ CLAMAV_TIMEOUT: 10 seconds
```

### **API Call Example**

```python
import pyclamd

# Connect to ClamAV
clam = pyclamd.ClamdNetworking('clamav-container', 3310)

# Scan file
result = clam.scan_stream(file_content)

# Result formats:
# - None: File is clean
# - {'file': ('FOUND', 'virus_name')}: File infected
# - {'file': ('ERROR', 'error_message')}: Scanning error
```

### **Infected File Handling**

```
If File Is Infected:

1. Reject upload:
   HTTP 400 Bad Request
   {
     "detail": "File infected with malware: Trojan.PDF.Exploit",
     "error_code": "MALWARE_DETECTED",
     "quarantine_id": "q-12345..."
   }

2. Log incident:
   {
     "event_type": "MALWARE_DETECTED",
     "file_hash": "abc123...",
     "virus_name": "Trojan.PDF.Exploit",
     "actor_id": "doctor-123",
     "timestamp": "2026-04-13T10:30:00Z"
   }

3. Alert administrator:
   Email: "Malware detected in upload by Dr. Smith"
   Action: Review quarantine, contact user

4. Never store infected file:
   ├─ Not in database
   ├─ Not in blob storage
   └─ Only reference in quarantine log
```

### **Virus Definition Updates**

```
Automatic (Daily):
├─ ClamAV pulls latest virus signatures
├─ Definitions updated from official sources
├─ Typically 100,000+ new signatures daily
└─ No downtime (existing connections continue)

Manual Update (if needed):
freshclam  # Update virus signatures
systemctl restart clamav-daemon  # Restart
```

### **Alternative Providers**

| Provider | Pros | Cons |
|----------|------|------|
| **ClamAV** | Free, open-source, reliable | Requires manual setup |
| **Windows Defender API** | Windows-native, good detection | Only Windows, cost |
| **Kaspersky** | Enterprise-grade detection | Expensive, less transparent |
| **VirusTotal** | Multiple engines, cloud | External dependency, privacy |

---

## 📧 Email Service (Notifications)

### **Current Setup: SendGrid**

SendGrid sends email notifications to users (password reset, alerts, etc.).

### **Use Cases**

```
User Notifications:
├─ Welcome email (account created)
├─ Password reset link
├─ Verification alerts (prescription verified)
├─ Compliance alerts (audit trail integrity check)
└─ Security alerts (unauthorized access attempt)

Admin Notifications:
├─ Daily summary (prescriptions processed)
├─ Error alerts (system failures)
├─ Security alerts (potential breach)
└─ Compliance reports
```

### **Configuration**

Store in Azure Key Vault:
```
SENDGRID_API_KEY: <secret-api-key>
SENDGRID_SENDER_EMAIL: noreply@your-domain.com
```

### **Email Templates**

All emails should:
- Include unsubscribe link
- Be GDPR compliant
- Mask sensitive data
- Not contain embedded files
- Use plain text + HTML alternatives

### **Alternative Providers**

| Provider | Pros | Cons | Cost |
|----------|------|------|------|
| **SendGrid** | Good API, reliable | Cost for volume | $0.10-0.30/email |
| **AWS SES** | Cheap, if using AWS | Less documentation | $0.0001/email |
| **Azure Communication Services** | If using Azure | Newer service | Variable |
| **Mailgun** | Developer-friendly API | Smaller scale | $0.05-0.50/email |

---

## 🔐 Key Management (Azure Key Vault)

### **Integration Flow**

```
1. Application starts
2. Authenticate with Azure:
   ├─ Using Managed Identity (recommended)
   └─ Or Service Principal
3. Request key from Key Vault:
   └─ POST /secrets/<key-name>?api-version=7.3
4. Azure verifies permissions (RBAC)
5. Azure returns decrypted key (only in memory)
6. Application uses key for encryption/decryption
7. Key never stored locally (only in RAM)
8. Key automatically rotated every 90 days
```

### **Why Key Vault?**

```
Benefits:
├─ Keys never in code or config files
├─ Keys never in git repository
├─ Keys never in Docker images
├─ Access audit logged
├─ Automatic rotation
├─ Disaster recovery
└─ Backup and restore

Security:
├─ FIPS 140-2 Level 2 certified
├─ Multi-tenant isolation
├─ Encryption keys encrypted at rest
├─ Network isolation via private endpoints
└─ MFA required for admin access
```

### **Configuration**

Managed Identity (no credentials needed):
```csharp
// .NET example
var credential = new DefaultAzureCredential();
var client = new SecretClient(new Uri(keyVaultUrl), credential);
KeyVaultSecret secret = await client.GetSecretAsync("encryption-key");
```

---

## 🌐 Cloud Storage (Azure Blob Storage)

### **Integration Flow**

```
1. Doctor uploads prescription PDF
2. API encrypts PDF (AES-256)
3. API uploads encrypted blob to Azure:
   ├─ Container: prescriptions
   ├─ Blob name: <prescription_id>
   └─ Server-side encryption: AES-256
4. Azure stores in geo-redundant location
5. Database stores reference (blob URL)
6. Pharmacy requests download
7. API retrieves encrypted blob
8. API decrypts and returns to pharmacy
```

### **Configuration**

Store in Azure Key Vault:
```
AZURE_STORAGE_ACCOUNT_NAME: mystorageaccount
AZURE_STORAGE_ACCOUNT_KEY: <secret-key>
AZURE_STORAGE_CONTAINER_NAME: prescriptions
```

### **Blob Storage Features**

```
Encryption (Server-Side):
├─ Azure manages encryption automatically
├─ Encryption: AES-256
├─ Key management: Azure-managed or customer-managed
├─ Transparent: application sees decrypted data
└─ No performance overhead

Geo-Redundancy:
├─ Data replicated across regions
├─ Automatic failover if region fails
├─ No manual configuration needed
└─ Ensures high availability

Versioning:
├─ All versions of blob retained
├─ Soft delete: recover deleted blobs (30 days)
├─ Point-in-time restore: restore to any version
└─ Helps with accidental deletion recovery
```

---

## 📊 Monitoring & Logging (Azure Monitor)

### **Integration**

```
Application sends logs to Azure Monitor:

1. Application logs JSON event:
   {
     "timestamp": "2026-04-13T10:30:00Z",
     "level": "INFO",
     "message": "Prescription uploaded",
     "actor_id": "doctor-123",
     "prescription_id": "rx-456"
   }

2. Azure Monitor receives (via agent)

3. Logs searchable in Log Analytics:
   SELECT * FROM logs
   WHERE event_type = "PRESCRIPTION_UPLOADED"
   AND timestamp > ago(7d)

4. Alerts triggered on anomalies:
   ├─ Error rate > 1%
   ├─ Response time > 2s
   └─ Service unavailable
```

### **Metrics Collected**

```
Performance:
├─ API response time (p50, p99)
├─ Database query time
├─ Storage access time
└─ QTSP verification time

Errors:
├─ HTTP 4xx errors (user errors)
├─ HTTP 5xx errors (server errors)
├─ Database connection failures
└─ Storage access failures

Business Metrics:
├─ Prescriptions uploaded (per hour)
├─ Prescriptions verified (per hour)
├─ Prescriptions dispensed (per hour)
└─ Failed verifications (per hour)
```

---

## 🔄 Webhook Integrations (Future)

### **Planned Integrations**

```
External Healthcare System:
├─ Notify pharmacy of new prescriptions
├─ Send verification results
└─ Receive dispensing confirmation

External Accounting System:
├─ Send audit logs for compliance
├─ Send monthly reports
└─ Receive billing updates

External HRIS:
├─ Update user status on hire/termination
├─ Sync license information
└─ Manage team assignments
```

### **Implementation**

When implementing webhooks:
1. Generate signing key for external system
2. Sign webhook requests with HMAC-SHA256
3. External system verifies signature
4. Implement retry logic (exponential backoff)
5. Store webhook delivery logs in audit trail
6. Alert on repeated failures

---

## 📋 Integration Checklist

Before going to production:
- [ ] SMS provider credentials in Key Vault
- [ ] QTSP provider API key configured
- [ ] Antivirus scanning operational
- [ ] Email service credentials configured
- [ ] Azure Key Vault accessible
- [ ] Blob Storage accessible
- [ ] Monitor/logging configured
- [ ] All integrations tested in staging
- [ ] Fallback procedures documented
- [ ] Monitoring alerts configured
- [ ] Integration support contacts documented

---

## Next Steps

For more details, see:
- [QTSP_INTEGRATION.md](./12_QTSP_INTEGRATION.md) — Detailed QTSP setup
- [DEPLOYMENT.md](./07_DEPLOYMENT.md) — Production deployment
- [OPERATIONS.md](./08_OPERATIONS.md) — Operations and monitoring
