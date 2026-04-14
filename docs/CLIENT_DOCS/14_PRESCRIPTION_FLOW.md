# Complete Prescription Workflow

## 🔄 End-to-End Prescription Flow

This document shows the complete lifecycle of a prescription from creation to dispensing, with all system steps.

---

## 📋 Phase 1: Preparation (Doctor)

### **Step 1: Doctor Prepares Prescription**

```
Doctor's Computer:
├─ Opens PDF editor or Word
├─ Creates prescription document:
│  ├─ Patient name
│  ├─ Patient ID
│  ├─ Date
│  ├─ Medication name
│  ├─ Dosage instructions
│  ├─ Doctor signature (digital)
│  └─ Doctor license number
├─ Saves as PDF
└─ Example: prescription.pdf (200KB)
```

**What Should Be Included:**
```
Required Fields:
├─ Patient ID (unique identifier)
├─ Patient name
├─ Medication name
├─ Dosage (e.g., "500mg, 3 times daily")
├─ Duration (e.g., "7 days")
├─ Doctor name
├─ Doctor license number
├─ Date issued
└─ Digital signature (from digital certificate)

Optional:
├─ Instructions (e.g., "Take with food")
├─ Contraindications
├─ Patient allergies
└─ Special notes
```

### **Step 2: Doctor Signs Prescription**

```
Doctor Uses Digital Signature:
├─ Source: Digital certificate (smartcard or USB key)
├─ Format: X.509 certificate from trusted authority
├─ Examples:
│  ├─ Estonia: EstEID (national digital ID)
│  ├─ Lithuania: KES
│  ├─ Latvia: eSignature tokens
│  └─ EU: Any eIDAS-qualified certificate
├─ Process:
│  ├─ Open PDF in signature-capable software
│  ├─ Insert signature (software signs with private key)
│  ├─ Embedded in PDF (signature is part of file)
│  └─ Cannot be removed or altered
└─ Result: Signed PDF with certificate embedded
```

**Why Digital Signature?**
```
Requirements:
├─ Legal: Must be digitally signed per eIDAS
├─ Healthcare: Prescription must be authentic
├─ Non-repudiation: Doctor cannot deny signing
├─ Proof: Signature proves doctor authorized

Legal Value:
├─ Legally binding in EU courts
├─ Equivalent to handwritten signature
├─ Admissible as evidence
└─ 7-year retention required
```

---

## 🚀 Phase 2: Upload (Doctor Portal)

### **Step 3: Doctor Logs In**

```
Doctor Opens Doctor Portal:
1. URL: https://your-domain.com/doctor
2. Sees login page
3. Enters phone number: +44-20-1234-5678
4. Clicks "Send OTP"

API Process:
├─ Validate phone format
├─ Generate 6-digit OTP
├─ Call Twilio (SMS provider)
├─ Twilio sends SMS
└─ Twilio returns success

Result:
├─ SMS arrives: "Your QES Flow OTP: 123456 (expires in 10 min)"
└─ Doctor sees: "OTP sent, check your phone"
```

### **Step 4: Doctor Enters OTP**

```
Doctor Receives SMS:
├─ Phone ding: new message
├─ Message: "QES Flow OTP: 123456"
└─ Expires in: 10 minutes

Doctor Portal:
├─ Enters OTP: 123456
├─ Clicks "Verify"

API Process:
├─ Check: Is OTP correct?
├─ Check: Is OTP not expired?
├─ If yes: Generate challenge token
├─ Challenge token expires in 5 minutes
└─ Return to frontend

Result:
├─ Challenge token issued
└─ Frontend shows: "Enter PIN"
```

### **Step 5: Doctor Enters PIN**

```
Frontend Shows:
├─ PIN input field
├─ 4-digit PIN (set during account creation)
└─ "Verify PIN" button

Doctor Enters:
├─ PIN: 1234 (only doctor knows this)
├─ Clicks "Verify"

API Process:
├─ Hash PIN with bcrypt (not stored plaintext)
├─ Compare with stored hash
├─ If match: Issue JWT token
├─ Token expires in: 8 hours

Result:
├─ JWT token issued
├─ Stored in browser cookie (secure, HttpOnly)
├─ Frontend redirects to dashboard
└─ Doctor logged in
```

**Why Two Factors?**
```
Factor 1: OTP (Phone)
├─ Proves doctor has their phone
├─ Attacker cannot intercept SMS
├─ One-time use (can't reuse)

Factor 2: PIN (Knowledge)
├─ Proves doctor knows their PIN
├─ Even if phone stolen, attacker can't login
├─ Combination: very secure

Result:
├─ Hacker needs: phone + PIN knowledge
├─ Nearly impossible to compromise
├─ GDPR compliant
└─ Healthcare standard security
```

### **Step 6: Doctor Opens Upload Page**

```
Doctor Portal Dashboard:
├─ Shows: Recent prescriptions
├─ Shows: Verification status
├─ Shows: Pending actions
└─ Navigation menu

Doctor Clicks:
└─ "Upload Prescription"

Frontend Shows:
├─ Drag-and-drop area
├─ "Select File" button
├─ Patient ID field
├─ Medication name field
├─ Dosage field
├─ Preview button (to check PDF)
├─ Upload button
└─ Help text
```

### **Step 7: Doctor Selects PDF**

```
Doctor Actions:
├─ Click "Select File" OR drag PDF onto zone
├─ Browser file picker opens
├─ Doctor selects: prescription.pdf
├─ Browser shows filename and size

Frontend Validation:
├─ Check file type: Is it PDF? ✅
├─ Check file size: < 50MB? ✅
├─ Check not empty: > 0 bytes? ✅
├─ Show in file list: ✅

If Validation Fails:
├─ "Invalid file type (must be PDF)"
├─ OR "File too large (max 50MB)"
└─ User cannot proceed
```

### **Step 8: Doctor Enters Details**

```
For the PDF, Doctor Fills:
├─ Patient ID: pat-12345678-90ab-cdef-1234-567890abcdef
├─ Medication Name: Amoxicillin
├─ Dosage: 500mg, 3 times daily for 7 days
└─ Clinic ID: (pre-filled from profile)

Frontend Shows:
├─ File preview (doctor can see PDF)
├─ Details in form
├─ "Edit" button (can change details)
├─ "Upload" button (ready to go)

Idempotency Key:
├─ Auto-generated by system: upload-a1b2c3d4-e5f6-7890...
├─ Prevents duplicate uploads
└─ Included with request (invisible to doctor)
```

### **Step 9: Doctor Uploads**

```
Doctor Clicks:
└─ "Upload All" (or "Upload" for single)

Frontend:
├─ Validates all fields filled
├─ Shows progress: "Uploading..."
├─ Displays upload progress bar
└─ Sends to API with JWT token
```

---

## 🔐 Phase 3: Server Processing

### **Step 10: API Validates Request**

```
API Receives:
├─ HTTP POST /api/v1/prescriptions/upload
├─ Headers:
│  ├─ Authorization: Bearer <JWT_TOKEN>
│  └─ Content-Type: multipart/form-data
├─ Body:
│  ├─ file: <binary PDF data>
│  ├─ patient_id: pat-12345678...
│  ├─ medication_name: Amoxicillin
│  ├─ dosage: 500mg, 3 times daily
│  ├─ clinic_id: clinic-abc123
│  └─ idempotency_key: upload-a1b2c3d4...

API Process:
1. Verify JWT token:
   ├─ Check signature (not tampered)
   ├─ Check expiration (not expired)
   ├─ Extract user_id: doctor-123
   └─ Validate: User is a doctor ✅

2. Check idempotency key:
   ├─ Query: Have we seen this UUID?
   ├─ If yes: Return previous response (skip processing)
   ├─ If no: Continue

3. Validate input:
   ├─ Patient ID: Non-empty string ✅
   ├─ Medication: Non-empty string ✅
   ├─ Dosage: Non-empty string ✅
   ├─ File: PDF file ✅
   └─ Size: 200KB < 50MB ✅

4. Check permissions:
   ├─ Does doctor have PRESCRIPTION_UPLOAD permission? ✅
   └─ Is doctor in same tenant as clinic? ✅
```

### **Step 11: Malware Scanning**

```
API Sends PDF to ClamAV:
├─ Connects to ClamAV service (port 3310)
├─ Streams PDF bytes to scanner
├─ Sets timeout: 10 seconds
└─ Waits for result

ClamAV Process:
├─ Receives PDF bytes
├─ Scans against virus database:
│  ├─ 100 million+ known virus signatures
│  ├─ Looks for malicious code patterns
│  ├─ Checks file headers
│  └─ Analyzes embedded objects
├─ Returns result:
│  ├─ None: File clean ✅
│  ├─ {'virus_name': 'Trojan.X'}: Infected ❌
│  └─ Error: Scanning error ⚠️
└─ Measures scan time: 234ms
```

**Result: Clean ✅**
```
Continue to next step (QTSP verification)
```

**Result: Infected ❌**
```
API Response (400 Bad Request):
{
  "detail": "File infected with Trojan.PDF.Exploit",
  "error_code": "MALWARE_DETECTED",
  "quarantine_id": "q-78901234..."
}

Doctor Sees:
├─ Error: "File infected with malware"
├─ Suggestion: "Try again with clean file"
└─ Option: Contact support

Backend:
├─ Create quarantine log entry
├─ Alert admin
├─ Do NOT store infected file anywhere
└─ Audit log: MALWARE_DETECTED event
```

### **Step 12: QTSP Verification (Dokobit)**

```
API Extracts PDF:
├─ Reads PDF bytes from request
└─ Calls Dokobit API

API Call to Dokobit:
POST https://api.dokobit.com/api/v3/signature/verify
Authorization: Bearer <DOKOBIT_API_KEY>
Content: [PDF bytes]

Dokobit Process:
├─ Receives PDF
├─ Extracts embedded signature
├─ Checks signature is valid:
│  ├─ Signature mathematically valid? ✅
│  ├─ Signature matches document content? ✅
│  └─ Signature timestamp valid? ✅
├─ Validates certificate:
│  ├─ Issued by trusted CA (EstEID2018)? ✅
│  ├─ Certificate not expired? ✅
│  ├─ Certificate not revoked? ✅
│  └─ Issuer authorized for eSignature? ✅
├─ Qualified timestamp:
│  ├─ Created: 2026-04-13T10:30:15Z
│  ├─ Issued by: Lithuanian PTT
│  └─ Legally binding proof: ✅
└─ Returns response

Dokobit Response (Valid Signature):
{
  "signature_verification_result": "VALID",
  "signature": {
    "status": "valid",
    "signer": {
      "name": "Dr. Jane Smith",
      "identifier": "PNOLV-49001010123"
    },
    "certificate": {
      "issuer": "EstEID2018",
      "valid_from": "2020-01-15T00:00:00Z",
      "valid_until": "2025-12-31T23:59:59Z",
      "status": "valid"
    },
    "signing_time": "2026-04-13T10:30:00Z"
  },
  "qualified_timestamp": {
    "time": "2026-04-13T10:30:15Z",
    "tsa_server": "http://timestamp.dokobit.com",
    "issuer": "Lithuanian Post and Telecommunications Office"
  }
}
```

### **Step 13: Store Prescription**

```
API Process:

1. Create database record:
   INSERT INTO prescriptions (
     id: rx-12345678-90ab-cdef-1234-567890abcdef
     tenant_id: clinic-abc123
     created_by: doctor-123
     patient_id: pat-12345678... (encrypted)
     medication_name: Amoxicillin (encrypted)
     dosage: 500mg... (encrypted)
     status: verified
     created_at: 2026-04-13T10:30:25Z
     file_path: /prescriptions/rx-12345678...
   )

2. Encrypt PDF:
   ├─ Get encryption key from Azure Key Vault
   ├─ Encrypt PDF with AES-256
   ├─ Result: garbage binary (unreadable)
   └─ Measure time: 45ms

3. Upload encrypted PDF to Azure:
   ├─ Blob: prescriptions/rx-12345678...
   ├─ Container: prescriptions
   ├─ Server-side encryption: AES-256
   ├─ Geo-redundancy: automatic
   └─ Measure time: 234ms

4. Store verification evidence:
   INSERT INTO signature_evidence (
     prescription_id: rx-12345678...
     signer_name: Dr. Jane Smith (encrypted)
     certificate_issuer: EstEID2018
     signature_valid: true
     qualified_timestamp: 2026-04-13T10:30:15Z
     tsa_issuer: Lithuanian PTT
     evidence: {...full Dokobit response...} (encrypted)
     created_at: 2026-04-13T10:30:30Z
   )

5. Create audit log entry:
   INSERT INTO audit_events (
     id: 9847 (sequential)
     event_type: PRESCRIPTION_UPLOADED
     actor_id: doctor-123
     action: upload_prescription
     timestamp: 2026-04-13T10:30:30Z
     ip_address: 192.168.1.100
     resource_type: prescription
     resource_id: rx-12345678...
     details: {
       file_name: prescription.pdf
       file_size: 200000
       malware_scan: clean
       verification_status: valid
     }
     result: success
     previous_hash: xyz789abc123... (from last event)
     current_hash: SHA256(event_data + previous_hash)
   )
```

### **Step 14: Return Response**

```
API Response (201 Created):
{
  "prescription_id": "rx-12345678-90ab-cdef-1234-567890abcdef",
  "idempotency_key": "upload-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "verified",
  "uploaded_at": "2026-04-13T10:30:25Z",
  "verified_at": "2026-04-13T10:30:30Z",
  "verification_status": "valid",
  "message": "Prescription uploaded and verified successfully"
}
```

---

## ✅ Phase 4: Availability (Pharmacy)

### **Step 15: Pharmacy Receives Notification**

```
Notification Method:
├─ Email or in-app notification
├─ Message: "New prescription from Dr. Smith"
├─ Link: "View prescription"
└─ Patient name (limited info for privacy)
```

### **Step 16: Pharmacist Logs In**

```
Similar to doctor:
1. Enter phone number
2. Receive OTP via SMS
3. Enter OTP
4. Enter PIN
5. Login successful
6. See dashboard with new prescriptions
```

### **Step 17: Pharmacist Downloads Prescription**

```
Pharmacist Actions:
1. Click on prescription from Dr. Smith
2. See:
   ├─ Patient name (decrypted, visible to pharmacist only)
   ├─ Medication: Amoxicillin
   ├─ Dosage: 500mg, 3 times daily
   ├─ Doctor name: Dr. Jane Smith
   ├─ Verification status: ✅ Valid
   ├─ Signature info (certificate, timestamp)
   └─ "Download" button

API Process (Download Request):
1. Verify JWT token (pharmacist logged in)
2. Check permissions:
   ├─ Is pharmacist assigned to this prescription? ✅
   ├─ Does pharmacist have DOCUMENT_DOWNLOAD permission? ✅
3. Check authorization:
   ├─ Is prescription in pharmacist's clinic? ✅
   └─ Is prescription not revoked? ✅
4. Retrieve encrypted PDF from Azure
5. Decrypt with key from Key Vault:
   ├─ Encrypted PDF → decrypted PDF
   ├─ Result: readable PDF
   └─ Measure time: 89ms
6. Generate temporary download URL:
   ├─ URL expires in: 5 minutes
   ├─ One-time use
   ├─ Signature: HMAC to prevent forgery
   └─ Return temporary URL to client
7. Create audit log entry:
   {
     event_type: DOCUMENT_DOWNLOADED
     actor_id: pharmacist-456
     resource_id: rx-12345678...
     timestamp: 2026-04-13T10:45:00Z
     ip_address: 192.168.1.101
     previous_hash: abc123...
     current_hash: def456...
   }

Browser:
1. Receives temporary URL from API
2. Browser navigates to URL
3. URL handler:
   ├─ Validates signature
   ├─ Checks expiration
   ├─ Serves decrypted PDF
   └─ Sets headers:
      ├─ Content-Type: application/pdf
      ├─ Cache-Control: no-cache, no-store
      └─ Content-Disposition: inline (view, not download)

Pharmacist:
├─ Sees PDF in viewer (not saved to disk)
├─ Can read: Patient name, medication, dosage
├─ Cannot: Save, forward, or print (prevented by app)
└─ Proceeds to dispense
```

---

## 💊 Phase 5: Dispensing

### **Step 18: Pharmacist Dispenses Medication**

```
Real World:
├─ Pharmacist retrieves medication from shelf
├─ Counts out correct amount (10 tablets)
├─ Puts in labeled container
├─ Checks batch number: LOT123456
├─ Hands to patient
├─ Patient leaves pharmacy

In System:
├─ Click "Confirm Dispensing"
├─ Enter quantity: 10
├─ Enter batch number: LOT123456
├─ Click "Confirm"
```

### **Step 19: Dispense Confirmation**

```
API Receives:
POST /api/v1/prescriptions/rx-12345.../dispense
{
  "quantity_dispensed": 10,
  "batch_number": "LOT123456"
}

API Process:
1. Verify pharmacist logged in
2. Check permissions (PRESCRIPTION_DISPENSE)
3. Update prescription:
   UPDATE prescriptions
   SET status = 'dispensed'
   WHERE id = 'rx-12345...'

4. Create dispense record:
   INSERT INTO dispensing_records (
     prescription_id: rx-12345...
     pharmacist_id: pharmacist-456
     quantity_dispensed: 10
     batch_number: LOT123456
     dispensed_at: 2026-04-13T11:00:00Z
   )

5. Create audit log entry:
   {
     event_type: PRESCRIPTION_DISPENSED
     actor_id: pharmacist-456
     resource_id: rx-12345...
     timestamp: 2026-04-13T11:00:00Z
     details: {
       quantity_dispensed: 10
       batch_number: LOT123456
     }
     previous_hash: def456...
     current_hash: ghi789...
   }

Response (200 OK):
{
  "prescription_id": "rx-12345...",
  "status": "dispensed",
  "dispensed_at": "2026-04-13T11:00:00Z",
  "dispensed_by": "pharmacist-456"
}

Pharmacist Sees:
├─ ✅ Dispensing confirmed
├─ Status: Dispensed
└─ Ready for next prescription
```

---

## 📊 Summary of Audit Trail

All events from prescription creation to dispensing:

```
Audit Trail (Hash-Chained):

Event 1: PRESCRIPTION_UPLOADED
├─ Actor: doctor-123
├─ Time: 2026-04-13T10:30:25Z
└─ current_hash: abc123...

Event 2: PRESCRIPTION_VERIFIED
├─ Actor: system
├─ Time: 2026-04-13T10:30:30Z
├─ previous_hash: abc123... ✅ matches Event 1
└─ current_hash: def456...

Event 3: DOCUMENT_DOWNLOADED
├─ Actor: pharmacist-456
├─ Time: 2026-04-13T10:45:00Z
├─ previous_hash: def456... ✅ matches Event 2
└─ current_hash: ghi789...

Event 4: PRESCRIPTION_DISPENSED
├─ Actor: pharmacist-456
├─ Time: 2026-04-13T11:00:00Z
├─ previous_hash: ghi789... ✅ matches Event 3
└─ current_hash: jkl012...

Security:
├─ If someone tries to change Event 2:
│  ├─ Event 2's hash changes
│  ├─ But Event 3 still points to old hash
│  ├─ Mismatch detected
│  └─ Tampering proven!
├─ Cannot change all subsequent hashes (would be detected)
└─ Immutability guaranteed
```

---

## 🔄 Alternative Flows

### **Doctor Revokes Prescription**

```
Scenario: Doctor realizes mistake before dispensing

Doctor Actions:
1. Opens prescription
2. Clicks "Revoke"
3. Selects reason: "Wrong medication"
4. Confirms

API Process:
1. Update status: revoked
2. Audit log: PRESCRIPTION_REVOKED
3. Notify pharmacy (if not yet dispensed)

Pharmacy Impact:
├─ Cannot download anymore
├─ Sees: "Revoked" status
└─ Does not dispense

After Revocation:
├─ Prescription cannot be dispensed
├─ Doctor must upload new prescription
└─ All actions logged (accountability)
```

### **Prescription Already Dispensed**

```
Scenario: Doctor tries to revoke after pharmacy dispensed

Doctor Actions:
└─ Clicks "Revoke"

API Response:
├─ Error: "Cannot revoke already dispensed"
├─ Reason: Too late (patient already has medication)
├─ Option: Contact pharmacy and patient

Pharmacy Actions:
├─ Already dispensed, cannot undo
├─ Prescription marked: dispensed
└─ If patient has bad reaction, contact doctor/poison control
```

---

## 📈 Prescription Lifecycle States

```
pending_verification
├─ Uploaded but not yet verified by QTSP
├─ Doctor can still revoke
└─ Pharmacy cannot download

verified
├─ Signature valid, ready for dispensing
├─ Pharmacy can download
├─ Doctor can revoke
└─ Stable state (main state)

failed
├─ Signature verification failed
├─ Doctor must resubmit
├─ Not dispendable
└─ Doctor contacted (error message)

revoked
├─ Doctor cancelled it
├─ Pharmacy cannot download
├─ Cannot be dispensed
└─ Audit trail shows reason

dispensed
├─ Pharmacy confirmed dispensing
├─ Final state (immutable)
├─ Medication given to patient
└─ Cannot be changed
```

---

## Next Steps

For more details, see:
- [API_GUIDE.md](./10_API_GUIDE.md) — API endpoints
- [FEATURES.md](./13_FEATURES.md) — Feature descriptions
- [SECURITY.md](./03_SECURITY.md) — Security controls
