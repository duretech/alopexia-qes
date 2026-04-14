# QTSP Integration Guide (Dokobit)

## 📋 What is a QTSP?

**QTSP = Qualified Trust Service Provider**

A QTSP is a company authorized by the EU to provide digital signature services that are legally binding. In QES Flow, Dokobit is our QTSP.

### **Why We Need QTSP?**

```
Healthcare Prescription Requirement:
├─ Prescriptions must be digitally signed by doctor
├─ Signature must be legally binding
├─ Must prove doctor actually authorized it
├─ Must prove signature hasn't been tampered with
├─ Evidence must be stored for 7 years

EU eIDAS Regulation:
├─ Requires qualified signature verification
├─ Only authorized QTSPs can do this
├─ Provides legal weight in court
└─ Complies with healthcare regulations
```

---

## 🏢 About Dokobit

**Dokobit** is a Lithuanian company that provides digital signature services authorized as a QTSP.

### **Qualifications**

```
Status: EU-Qualified Timestamp Provider
├─ Authorized by: Lithuanian Data Protection Authority
├─ Audited for: Security and compliance
├─ Certified: eIDAS regulation compliant
├─ Supported: Digital signatures, timestamps, sealing
└─ Available: 24/7 with 99.9% SLA
```

### **Services Offered**

1. **Signature Verification**
   - Verify digital signatures on documents
   - Validate signature certificate chain
   - Detect tampered documents
   - Return verification result (valid/invalid)

2. **Qualified Timestamp**
   - Create legally binding timestamp
   - Prove when document was signed
   - Cannot be forged or changed
   - Admissible in EU courts

3. **Evidence Storage**
   - Store signature evidence
   - Keep certificate details
   - Retain timestamp info
   - For 7+ years (legal requirement)

---

## 🚀 Getting Started with Dokobit

### **Step 1: Create Account**

1. Visit: https://www.dokobit.com
2. Sign up for account
3. Choose: "Signature Verification" service
4. Complete: Company information, contact details
5. Verify: Email address
6. Get: API credentials (API key)

### **Step 2: Get API Credentials**

After account creation, access:
- **API Key**: Unique identifier for your app
- **API URL**: Usually https://api.dokobit.com
- **Account ID**: Your account identifier
- **API Version**: Latest version (currently v3)

Store these in **Azure Key Vault** (never in code):
```
Key Vault Secrets:
├─ DOKOBIT_API_KEY = <your-api-key>
├─ DOKOBIT_API_URL = https://api.dokobit.com
├─ DOKOBIT_ACCOUNT_ID = <your-account-id>
└─ DOKOBIT_API_VERSION = v3
```

### **Step 3: Test Connection**

```bash
# Test API connectivity
curl -X POST https://api.dokobit.com/api/v3/signature/verify \
  -H "Authorization: Bearer <DOKOBIT_API_KEY>" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test-prescription.pdf"

# Response should return signature info or error
```

---

## 🔐 Signature Verification Flow

### **How It Works**

```
Step 1: Doctor Signs Prescription
├─ Doctor uses digital signature (e.g., EstEID, smartcard)
├─ Signature embedded in PDF
└─ Signature includes: certificate, timestamp, algorithm

Step 2: Doctor Uploads Prescription
├─ Browser sends PDF to API
├─ API receives PDF (not saved yet)
└─ Signature is still inside PDF

Step 3: API Calls Dokobit
├─ API extracts signature from PDF
├─ API sends to Dokobit for verification
└─ Dokobit checks:
   ├─ Signature mathematically valid?
   ├─ Certificate trusted (EU root CA)?
   ├─ Certificate not revoked?
   ├─ Timestamp valid?
   ├─ Issuer authorized?
   └─ Document not tampered with?

Step 4: Dokobit Returns Result
├─ If valid: { "status": "VALID", "certificate": {...} }
├─ If invalid: { "status": "INVALID", "error": "..." }
└─ If error: { "status": "ERROR", "message": "..." }

Step 5: API Stores Result
├─ Save verification status in database
├─ Save evidence (certificate, timestamp)
├─ Encrypt evidence with AES-256-GCM
├─ Audit log entry created
└─ Status: "verified" or "failed"

Step 6: Pharmacy Can See Status
├─ Download prescription only if verified
├─ See verification details (certificate info)
├─ Proof of verification in audit trail
└─ Legal proof of authenticity
```

### **Complete API Request/Response**

**Request:**
```bash
curl -X POST https://api.dokobit.com/api/v3/signature/verify \
  -H "Authorization: Bearer abc123def456..." \
  -H "Content-Type: multipart/form-data" \
  -F "file=@prescription.pdf"
```

**Response (Valid Signature):**
```json
{
  "status": "success",
  "signature_verification_result": "VALID",
  "signature": {
    "status": "valid",
    "signer": {
      "name": "Dr. Jane Elizabeth Smith",
      "identifier": "PNOLV-49001010123"
    },
    "certificate": {
      "issuer": "EstEID2018",
      "issuer_cn": "ESTEID-SK 2016",
      "valid_from": "2020-01-15T00:00:00Z",
      "valid_until": "2025-12-31T23:59:59Z",
      "status": "valid",
      "serial_number": "123456"
    },
    "signing_time": "2026-04-13T10:30:00Z",
    "signature_method": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
    "signature_format": "XAdES-EPES"
  },
  "qualified_timestamp": {
    "time": "2026-04-13T10:30:15Z",
    "tsa_server": "http://timestamp.dokobit.com",
    "issuer": "Lithuanian Post and Telecommunications Office",
    "accuracy": "ms"
  },
  "document": {
    "name": "prescription.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 245821
  }
}
```

**Response (Invalid Signature):**
```json
{
  "status": "success",
  "signature_verification_result": "INVALID",
  "signature": {
    "status": "invalid",
    "error": "Signature does not match document",
    "error_code": "SIGNATURE_INVALID"
  }
}
```

**Response (Error Verifying):**
```json
{
  "status": "error",
  "error": "Cannot process PDF",
  "error_code": "PDF_PROCESSING_ERROR",
  "message": "PDF file appears to be corrupted"
}
```

---

## 💾 Storing Signature Evidence

### **What to Store**

After verification, store this evidence in the database:

```sql
INSERT INTO signature_evidence (
  prescription_id,
  signer_name,
  signer_identifier,
  certificate_issuer,
  certificate_valid_from,
  certificate_valid_until,
  certificate_status,
  signature_time,
  qualified_timestamp,
  tsa_issuer,
  verification_status,
  verification_timestamp,
  raw_response
) VALUES (
  'rx-12345...',
  'Dr. Jane Smith',
  'PNOLV-49001010123',
  'EstEID2018',
  '2020-01-15T00:00:00Z',
  '2025-12-31T23:59:59Z',
  'valid',
  '2026-04-13T10:30:00Z',
  '2026-04-13T10:30:15Z',
  'Lithuanian Post and Telecommunications Office',
  'VALID',
  '2026-04-13T10:30:20Z',
  '{...full response JSON...}'
);
```

### **Encryption**

```
All evidence fields encrypted:
├─ Algorithm: AES-256-GCM
├─ Key: From Azure Key Vault
├─ Authentication: Detects tampering
├─ Retention: 7 years
└─ Stored in PostgreSQL

Access Control:
├─ Read: Compliance officer, admin
├─ Write: System only
├─ Delete: Never (soft-delete only)
└─ Audit: All access logged
```

---

## ⚠️ Error Handling

### **Common Errors & Solutions**

| Error | Cause | Solution |
|-------|-------|----------|
| `INVALID_API_KEY` | Wrong API key | Check Key Vault, redeploy |
| `PDF_PROCESSING_ERROR` | Corrupted PDF | Ask doctor to re-upload |
| `SIGNATURE_NOT_FOUND` | No signature in PDF | Doctor must sign before upload |
| `CERTIFICATE_REVOKED` | Doctor's cert revoked | Contact doctor, suspend account |
| `TIMESTAMP_ERROR` | Can't get timestamp | Retry (temporal issue) |
| `TIMEOUT` | Dokobit slow | Retry with 10s timeout |

### **Retry Strategy**

```
First Failure:
├─ Wait 5 seconds
├─ Retry immediately
└─ If fails: proceed to next

Second Failure:
├─ Wait 30 seconds
├─ Retry
└─ If fails: proceed to next

Third Failure:
├─ Queue for manual review
├─ Notify admin
├─ Retry every 5 minutes
├─ Max 24 hours
└─ Then fail permanently

Permanent Failure:
├─ Mark prescription as failed
├─ Notify doctor
├─ Doctor must resubmit
└─ Audit log entry created
```

---

## 🔄 Asynchronous Verification

### **Why Asynchronous?**

```
Problem with Synchronous (wait for result):
├─ Doctor's upload request takes 3+ seconds
├─ Poor user experience (slow)
├─ Server threads blocked (scalability issue)
└─ Timeout risk (Dokobit slow)

Solution: Asynchronous (fire and forget):
├─ Doctor uploads → API returns 202 (Accepted)
├─ Doctor sees "verifying..." status
├─ Verification happens in background
├─ Status updates via polling/webhook
├─ Fast response (good UX)
└─ Scalable (threads not blocked)
```

### **Asynchronous Flow**

```
1. Doctor uploads prescription
2. API validates file (malware scan)
3. API creates database record:
   {
     "status": "pending_verification",
     "created_at": "2026-04-13T10:30:00Z"
   }
4. API returns 202 Accepted:
   {
     "prescription_id": "rx-123...",
     "status": "pending_verification"
   }
5. Background job calls Dokobit:
   ├─ Job runs every 10 seconds
   ├─ Calls verification endpoint
   ├─ Stores result
   └─ Updates status in DB
6. Doctor polls for status:
   ├─ Calls GET /prescriptions/rx-123
   ├─ Sees status change to "verified"
   └─ Can now share with pharmacy
```

### **Implementation (Python/FastAPI)**

```python
from celery import shared_task
from datetime import datetime

@shared_task
def verify_prescription_signature(prescription_id):
    """Background job to verify prescription signature"""
    
    prescription = Prescription.query.get(prescription_id)
    if not prescription or prescription.status != 'pending_verification':
        return
    
    # Get PDF from storage
    pdf_bytes = blob_storage.download_blob(prescription.file_path)
    
    # Call Dokobit
    try:
        response = dokobit_client.verify_signature(pdf_bytes)
        
        # Store evidence
        evidence = SignatureEvidence(
            prescription_id=prescription_id,
            signer_name=response['signature']['signer']['name'],
            verification_status=response['signature_verification_result'],
            verified_at=datetime.utcnow()
        )
        db.session.add(evidence)
        
        # Update prescription status
        if response['signature_verification_result'] == 'VALID':
            prescription.status = 'verified'
        else:
            prescription.status = 'failed'
        
        # Audit log
        audit_log.create_event(
            event_type='PRESCRIPTION_VERIFIED',
            prescription_id=prescription_id,
            details=response
        )
        
        db.session.commit()
        
    except Exception as e:
        # Log error, will retry later
        logger.error(f"Verification failed: {e}")
        # Don't change status, will retry
```

---

## 📊 Monitoring Dokobit Integration

### **Health Checks**

```
Every 5 minutes:
1. Call Dokobit with test PDF
2. Verify response time:
   ├─ <1s: Perfect
   ├─ 1-3s: Good
   ├─ 3-5s: Acceptable
   └─ >5s: Alert
3. Check success rate:
   ├─ 100%: Perfect
   ├─ 95-100%: Good
   ├─ 90-95%: Monitor
   └─ <90%: Alert

Dashboard Metrics:
├─ Average verification time
├─ Success rate (%)
├─ Error rate by type
├─ API uptime (%)
└─ Queue depth (pending verifications)
```

### **Alerts**

```
Alert if:
├─ Dokobit API unavailable (5 min timeout)
├─ Verification success rate < 95%
├─ Average response time > 5 seconds
├─ Error rate increasing (spike)
└─ Queue depth > 100 (backlog)

Action:
├─ Check Dokobit status page
├─ Contact Dokobit support
├─ Switch to fallback (manual review)
├─ Update status page (notify users)
└─ Document incident
```

---

## 🔐 Security Considerations

### **API Key Security**

```
DO:
✅ Store in Azure Key Vault
✅ Rotate every 90 days
✅ Log all access
✅ Use with Managed Identity

DON'T:
❌ Commit to git
❌ Put in environment variables
❌ Log the key value
❌ Hardcode in code
❌ Share via email
```

### **Certificate Validation**

```
Always Validate:
├─ Certificate issuer (must be EU trusted CA)
├─ Certificate dates (valid_from, valid_until)
├─ Certificate status (not revoked)
├─ Signature algorithm (strong: SHA-256+)
└─ Signature format (XAdES or CAdES)

Never Accept:
├─ Self-signed certificates
├─ Expired certificates
├─ Certificates from untrusted issuers
├─ Weak algorithms (MD5, SHA1)
└─ Altered certificate data
```

### **Evidence Integrity**

```
Stored Evidence Must:
├─ Be encrypted (AES-256-GCM)
├─ Be immutable (database constraints)
├─ Include timestamp
├─ Include certificate chain
├─ Be hash-chained in audit log
└─ Be retained 7 years

Access Control:
├─ Read: Only authorized users
├─ Write: System only
├─ Delete: Never
└─ Audit: All access logged
```

---

## 🚨 Troubleshooting

### **Verification Always Failing**

```
Check:
1. Is API key valid?
   ├─ Verify in Key Vault
   ├─ Test with curl
   └─ Check expiration

2. Is Dokobit running?
   ├─ Check status page
   ├─ Health check endpoint
   └─ Network connectivity

3. Are certificates valid?
   ├─ Check issuer
   ├─ Check dates
   └─ Check revocation status

4. Is PDF signed?
   ├─ Doctor must use digital signature
   ├─ Not just a scanned image
   └─ Signature must be embedded in PDF
```

### **Verification Always Passing (Even Bad Signatures)**

```
Check:
1. Is validation logic correct?
   ├─ Are we checking "status" field?
   ├─ Are we checking "signature_verification_result"?
   └─ Are we handling errors?

2. Is response being parsed correctly?
   ├─ Check Dokobit response format
   ├─ Check for errors in response
   └─ Don't assume success

3. Are we logging results?
   ├─ Check audit logs
   ├─ Check database records
   └─ Verify evidence stored
```

---

## 📋 Dokobit Checklist

Before production:
- [ ] Account created with Dokobit
- [ ] API key generated
- [ ] API credentials in Azure Key Vault
- [ ] Test connection successful
- [ ] Signature verification tested
- [ ] Error handling implemented
- [ ] Retry strategy implemented
- [ ] Evidence storage implemented
- [ ] Encryption configured
- [ ] Audit logging implemented
- [ ] Health checks configured
- [ ] Monitoring/alerts configured
- [ ] Fallback procedure documented
- [ ] Team trained on QTSP flow
- [ ] Support contact saved

---

## 📞 Support

**Dokobit Support:**
- Email: support@dokobit.com
- Phone: +370 5 213 3377
- Status Page: https://status.dokobit.com

**For QES Flow Issues:**
- Internal: Check QTSP_INTEGRATION.md
- Contact: your-support@your-domain.com

---

## Next Steps

For more details, see:
- [INTEGRATION_GUIDE.md](./11_INTEGRATION_GUIDE.md) — All integrations overview
- [API_GUIDE.md](./10_API_GUIDE.md) — API endpoints
- [OPERATIONS.md](./08_OPERATIONS.md) — Operations and monitoring
