# API Reference Guide

## 🔌 API Overview

**Base URL:** `https://your-domain.com/api/v1`

**Authentication:** JWT Bearer Token (obtained after login)

**Response Format:** JSON

**Rate Limiting:**
- Default: 100 requests/minute per IP
- Login: 10 requests/minute per IP
- Upload: 20 requests/minute per IP

---

## 🔐 Authentication Endpoints

### **POST /auth/phone/send-otp**

Send OTP to phone number.

**Request:**
```json
{
  "phone_number": "+44-20-1234-5678"
}
```

**Response (200 OK):**
```json
{
  "message": "OTP sent to phone",
  "expires_in_seconds": 600,
  "contact_hint": "+44-20-****-5678"
}
```

**Why OTP?**
- More secure than passwords (no phishing)
- Complies with SCA (Strong Customer Authentication)
- User proves they own the phone number

---

### **POST /auth/phone/verify-otp**

Verify OTP and get challenge token.

**Request:**
```json
{
  "phone_number": "+44-20-1234-5678",
  "otp_code": "123456"
}
```

**Response (200 OK):**
```json
{
  "challenge_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in_seconds": 300
}
```

**Why Challenge Token?**
- Temporary credential (5 minutes)
- Only proves phone ownership
- Need PIN to actually authenticate

---

### **POST /auth/pin/verify**

Verify PIN and get session token.

**Headers:**
```
Authorization: Bearer <challenge_token>
```

**Request:**
```json
{
  "pin": "1234"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in_seconds": 28800
}
```

**Token Details:**
```
access_token:
├─ Expires: 8 hours
├─ Used for: API requests
└─ Contains: user_id, role, permissions, tenant_id

refresh_token:
├─ Expires: 24 hours
├─ Used for: Getting new access_token
└─ Contains: user_id, tenant_id
```

**Why PIN?**
- Second factor of authentication (MFA)
- PIN is encrypted and hashed in database
- User is the only one who knows it
- Even if phone stolen, attacker can't login

---

### **POST /auth/refresh**

Get new access token using refresh token.

**Headers:**
```
Authorization: Bearer <refresh_token>
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in_seconds": 28800
}
```

---

### **POST /auth/logout**

Logout and invalidate tokens.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "message": "Logged out successfully",
  "audit_logged": true
}
```

---

## 📋 Prescription Endpoints

### **POST /prescriptions/upload**

Upload a new prescription.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Request Body:**
```
File upload fields:
├─ file: <PDF file> [binary, max 50MB]
├─ patient_id: <UUID or identifier>
├─ medication_name: <string>
├─ dosage: <string>
├─ clinic_id: <UUID>
└─ idempotency_key: <UUID> [optional, for preventing duplicates]
```

**Response (201 Created):**
```json
{
  "prescription_id": "rx-12345678-90ab-cdef-1234-567890abcdef",
  "idempotency_key": "upload-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending_verification",
  "uploaded_at": "2026-04-13T10:30:00Z",
  "verification_status": "pending",
  "message": "Prescription uploaded successfully, verification in progress"
}
```

**Why Idempotency Key?**
```
Problem Without It:
├─ User clicks upload, network fails
├─ User doesn't see response, clicks again
├─ Same prescription uploaded twice
└─ Pharmacy dispenses duplicate

Solution With Idempotency Key:
├─ Generate UUID before upload
├─ Send with prescription
├─ Server checks: "Have I seen this UUID?"
├─ If yes: return existing response (don't re-upload)
├─ If no: upload and save UUID
└─ Guarantees exactly-once semantics (critical for healthcare)
```

**Error Response (400 Bad Request):**
```json
{
  "detail": "Invalid PDF format",
  "error_code": "INVALID_FILE_TYPE"
}
```

**Error Response (413 Payload Too Large):**
```json
{
  "detail": "File too large (max 50MB)",
  "error_code": "FILE_TOO_LARGE"
}
```

---

### **GET /prescriptions/:prescription_id**

Get prescription details.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "prescription_id": "rx-12345678-90ab-cdef-1234-567890abcdef",
  "patient_id": "pat-98765432-10fe-dcba-9876-543210fedcba",
  "medication_name": "Amoxicillin",
  "dosage": "500mg, 3 times daily",
  "status": "verified",
  "created_by": "doctor-abc123",
  "created_at": "2026-04-13T10:30:00Z",
  "verified_at": "2026-04-13T10:35:00Z",
  "verification_status": "valid",
  "evidence": {
    "signature_valid": true,
    "certificate_valid": true,
    "qualified_timestamp": "2026-04-13T10:30:15Z",
    "issuer": "Lithuanian Post and Telecommunications Office"
  }
}
```

---

### **POST /prescriptions/:prescription_id/download**

Download (decrypt and retrieve) a prescription.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```
Binary PDF file
Headers:
├─ Content-Type: application/pdf
├─ Content-Disposition: attachment; filename="prescription.pdf"
└─ Cache-Control: no-cache, no-store
```

**What Happens:**
```
1. API checks authorization:
   ├─ Is user doctor (owner)? OR
   ├─ Is user assigned pharmacist? OR
   ├─ Is user admin?
   └─ If none: return 403 Forbidden

2. API retrieves encrypted PDF from blob storage
3. API decrypts with encryption key from Key Vault
4. API generates temporary signed URL (5 minutes)
5. API logs access in audit trail
6. Client downloads decrypted PDF
7. Browser displays in viewer
8. User cannot download/forward (frontend prevents)
```

**Why Temporary URL?**
```
Security Benefits:
├─ URL expires after 5 minutes (prevents sharing)
├─ Signature proves Azure issued it (can't forge)
├─ Each user gets own URL (can't reuse)
├─ Logged in audit trail (we know who downloaded)
└─ If URL leaked, attacker has 5 minute window
```

---

### **PATCH /prescriptions/:prescription_id/revoke**

Revoke a prescription (clinic only).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "reason": "Patient requested cancellation"
}
```

**Response (200 OK):**
```json
{
  "prescription_id": "rx-12345678-90ab-cdef-1234-567890abcdef",
  "status": "revoked",
  "revoked_at": "2026-04-13T11:00:00Z",
  "revoked_by": "doctor-abc123",
  "reason": "Patient requested cancellation"
}
```

**Audit Trail:**
```
Created entry:
{
  "event_type": "PRESCRIPTION_REVOKED",
  "actor_id": "doctor-abc123",
  "resource_id": "rx-12345678...",
  "details": {
    "reason": "Patient requested cancellation",
    "previous_status": "verified"
  },
  "timestamp": "2026-04-13T11:00:00Z"
}
```

---

### **POST /prescriptions/:prescription_id/dispense**

Confirm dispensing of prescription (pharmacist only).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "quantity_dispensed": 10,
  "batch_number": "LOT123456"
}
```

**Response (200 OK):**
```json
{
  "prescription_id": "rx-12345678-90ab-cdef-1234-567890abcdef",
  "status": "dispensed",
  "dispensed_at": "2026-04-13T11:30:00Z",
  "dispensed_by": "pharmacist-xyz789",
  "quantity_dispensed": 10,
  "batch_number": "LOT123456"
}
```

---

## 📊 Audit Trail Endpoints

### **GET /audit**

Get audit events (admin/compliance only).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
```
?event_type=PRESCRIPTION_UPLOADED
 &actor_id=doctor-abc123
 &resource_id=rx-12345...
 &start_date=2026-04-01
 &end_date=2026-04-30
 &page=1
 &limit=50
```

**Response (200 OK):**
```json
{
  "total_count": 1234,
  "page": 1,
  "limit": 50,
  "events": [
    {
      "id": 1001,
      "event_type": "PRESCRIPTION_UPLOADED",
      "actor_id": "doctor-abc123",
      "action": "upload_prescription",
      "timestamp": "2026-04-13T10:30:00Z",
      "ip_address": "192.168.1.100",
      "resource_type": "prescription",
      "resource_id": "rx-12345678...",
      "result": "success",
      "previous_hash": "abc123def456...",
      "current_hash": "xyz789abc123..."
    },
    {
      "id": 1002,
      "event_type": "PRESCRIPTION_VERIFIED",
      "actor_id": "system",
      "action": "verify_prescription",
      "timestamp": "2026-04-13T10:35:00Z",
      "resource_id": "rx-12345678...",
      "result": "success",
      "details": {
        "verification_status": "valid",
        "signature_valid": true
      },
      "previous_hash": "xyz789abc123...",
      "current_hash": "def456xyz789..."
    }
  ]
}
```

**Hash Chain Verification:**
```
Event 1001:
├─ current_hash: xyz789abc123

Event 1002:
├─ previous_hash: xyz789abc123 ← matches Event 1001!
└─ current_hash: def456xyz789

This proves Event 1002 came right after Event 1001
and nothing was deleted or modified between them
```

---

### **POST /audit/export**

Export audit logs (admin/compliance only).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "start_date": "2026-04-01",
  "end_date": "2026-04-30",
  "format": "json_lines"
}
```

**Response (200 OK):**
```
File download (.json.gz)

Content (after decompression):
{"id":1,"event_type":"USER_LOGIN","actor_id":"doctor-123",...}
{"id":2,"event_type":"PRESCRIPTION_UPLOADED","actor_id":"doctor-123",...}
{"id":3,"event_type":"PRESCRIPTION_VERIFIED","actor_id":"system",...}
...
```

**Security:**
```
Export Encryption:
├─ File encrypted before download
├─ Download link valid 24 hours only
├─ One-time use (link expires after use)
└─ Audit log entry created for export

Why Encryption?
└─ Even if URL intercepted, file is encrypted
   Cannot read without decryption key
```

---

## 👥 User Management Endpoints

### **GET /users**

List users (admin only).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
```
?role=doctor
 &status=active
 &page=1
 &limit=50
```

**Response (200 OK):**
```json
{
  "total_count": 45,
  "page": 1,
  "limit": 50,
  "users": [
    {
      "user_id": "doctor-abc123",
      "email": "dr.smith@clinic.com",
      "phone": "+44-20-****-5678",
      "role": "doctor",
      "status": "active",
      "created_at": "2026-01-15T08:00:00Z",
      "last_login": "2026-04-13T09:30:00Z",
      "license_number": "MED123456"
    }
  ]
}
```

---

### **POST /users**

Create new user (admin only).

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request:**
```json
{
  "email": "dr.jones@clinic.com",
  "phone_number": "+44-20-1234-5678",
  "role": "doctor",
  "clinic_id": "clinic-abc123",
  "license_number": "MED654321"
}
```

**Response (201 Created):**
```json
{
  "user_id": "doctor-def456",
  "email": "dr.jones@clinic.com",
  "phone": "+44-20-1234-5678",
  "role": "doctor",
  "status": "pending_activation",
  "created_at": "2026-04-13T10:00:00Z",
  "message": "User created. Activation email sent to doctor."
}
```

---

### **PATCH /users/:user_id/suspend**

Suspend a user (admin only).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "reason": "License expired"
}
```

**Response (200 OK):**
```json
{
  "user_id": "doctor-abc123",
  "status": "suspended",
  "suspended_at": "2026-04-13T10:30:00Z",
  "suspended_by": "admin-xyz789",
  "reason": "License expired"
}
```

---

## 📊 Health & Status Endpoints

### **GET /health/live**

Liveness probe (is service running?).

**Response (200 OK):**
```json
{
  "status": "ok"
}
```

**Used by:** Load balancer, Docker, Kubernetes

---

### **GET /health/ready**

Readiness probe (is service ready for traffic?).

**Response (200 OK):**
```json
{
  "status": "ok",
  "database": "connected",
  "database_latency_ms": 45
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "degraded",
  "database": "disconnected",
  "reason": "Cannot connect to database"
}
```

---

### **GET /health/deep**

Deep health check (dependencies working?).

**Response (200 OK):**
```json
{
  "status": "ok",
  "database": "healthy",
  "database_latency_ms": 52,
  "storage": "healthy",
  "storage_latency_ms": 234,
  "scanner": "healthy",
  "scanner_latency_ms": 567,
  "timestamp": "2026-04-13T10:35:00Z"
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "degraded",
  "database": "unhealthy",
  "database_latency_ms": 5012,
  "storage": "healthy",
  "storage_latency_ms": 245,
  "scanner": "unhealthy",
  "scanner_error": "Connection timeout",
  "timestamp": "2026-04-13T10:36:00Z"
}
```

---

## 🚫 Error Responses

All errors follow this format:

```json
{
  "detail": "Description of what went wrong",
  "error_code": "ERROR_CODE",
  "request_id": "req-12345..."
}
```

**Common HTTP Status Codes:**

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created (prescription uploaded) |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | User lacks permission |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists (duplicate upload) |
| 413 | Payload Too Large | File too large (max 50MB) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Error | Server error (contact support) |
| 503 | Service Unavailable | Dependencies down (database, storage) |

---

## 📝 SDK Examples

### **JavaScript/TypeScript**

```typescript
// Login
const otpResponse = await fetch('/api/v1/auth/phone/send-otp', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ phone_number: '+44-20-1234-5678' })
});

// Verify OTP
const challengeResponse = await fetch('/api/v1/auth/phone/verify-otp', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    phone_number: '+44-20-1234-5678',
    otp_code: '123456'
  })
});
const { challenge_token } = await challengeResponse.json();

// Verify PIN
const tokenResponse = await fetch('/api/v1/auth/pin/verify', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${challenge_token}`
  },
  body: JSON.stringify({ pin: '1234' })
});
const { access_token } = await tokenResponse.json();

// Upload prescription
const formData = new FormData();
formData.append('file', pdfFile);
formData.append('patient_id', 'pat-123');
formData.append('medication_name', 'Amoxicillin');
formData.append('dosage', '500mg');

const uploadResponse = await fetch('/api/v1/prescriptions/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`
  },
  body: formData
});
```

---

## Next Steps

For more details, see:
- [INTEGRATION_GUIDE.md](./11_INTEGRATION_GUIDE.md) — Integrating with external systems
- [QTSP_INTEGRATION.md](./12_QTSP_INTEGRATION.md) — QTSP provider setup
- [SYSTEM_OVERVIEW.md](./01_SYSTEM_OVERVIEW.md) — Architecture overview
