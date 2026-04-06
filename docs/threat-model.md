# QES Flow — Threat Model

## Threat Modeling Methodology

STRIDE-per-element applied to the prescription workflow, supplemented with healthcare-specific threats.

---

## T01: Forged Prescription Upload

**Category**: Spoofing, Tampering  
**Actor**: External attacker or compromised doctor account  
**Target**: Prescription ingestion endpoint  

**Attack**: Upload a PDF with a forged or invalid signature to create a fraudulent prescription.

**Mitigations (Implemented)**:
- PDF is sent to QTSP for qualified signature verification — forged signatures will fail verification
- Prescription remains in `pending_verification` state until QTSP confirms
- Failed verifications enter a quarantine/manual review state
- Upload requires authenticated doctor session with MFA
- Checksum computed at upload prevents post-upload tampering
- Anti-replay: idempotency key per upload prevents duplicate submission

**Detective Controls**:
- Audit event on every upload with actor identity, IP, timestamp
- Alert on repeated failed verifications from same doctor
- Alert on unusual upload patterns (volume, timing)

**Recovery**:
- Quarantined prescriptions cannot reach pharmacy
- Manual review queue for compliance officers
- Incident record created for failed verifications

---

## T02: Compromised Doctor Account

**Category**: Spoofing, Elevation of Privilege  
**Actor**: Attacker with stolen doctor credentials  
**Target**: Doctor portal, prescription records  

**Attack**: Use compromised credentials to upload fraudulent prescriptions or access patient data.

**Mitigations (Implemented)**:
- MFA-ready authentication model
- Session controls: timeout, concurrent session limits, IP binding option
- All actions tied to authenticated identity in audit trail
- Unusual login detection hooks (new IP, new device, unusual time)
- Account lockout after repeated failed attempts

**Detective Controls**:
- Audit trail of all login events with IP, user agent, timestamp
- Failed login attempt tracking and alerting
- Session anomaly detection hooks

**Recovery**:
- Immediate session revocation capability
- Account suspension by clinic admin or platform admin
- All prescriptions uploaded during compromise window flagged for review

---

## T03: Unauthorized Pharmacy Access

**Category**: Information Disclosure, Spoofing  
**Actor**: Unauthorized pharmacy user or compromised pharmacy account  
**Target**: Prescription documents, patient data  

**Attack**: Access prescriptions not assigned to the pharmacy, or access without authorization.

**Mitigations (Implemented)**:
- ABAC policy: pharmacy users can only access prescriptions assigned to their pharmacy
- Tenant isolation: cross-tenant access denied at query level
- Clinic scoping: prescriptions scoped to authorized clinic-pharmacy relationships
- Signed URLs for document download with short TTL
- No direct object storage access

**Detective Controls**:
- Audit event on every prescription access with actor, resource, outcome
- Alert on access denied events
- Alert on unusual access patterns

**Recovery**:
- Access revocation for compromised pharmacy accounts
- Incident record for unauthorized access attempts

---

## T04: Tampering with Audit Logs

**Category**: Tampering, Repudiation  
**Actor**: Insider (admin, operator) or attacker with database access  
**Target**: Audit event store  

**Attack**: Modify or delete audit records to cover tracks.

**Mitigations (Implemented)**:
- Append-only audit event table with no UPDATE/DELETE grants to application role
- Hash chain: each event includes hash of previous event — tampering breaks chain
- Periodic integrity verification job that validates chain
- Audit events exported to WORM-compatible S3 storage
- Database triggers prevent deletion at DB level
- Separate database credentials for audit write vs application read

**Detective Controls**:
- Chain integrity verification runs on schedule
- Gap detection: missing sequence numbers flagged
- External integrity verification script for auditors
- Alert on any DELETE attempt against audit tables

**Recovery**:
- WORM export provides tamper-proof backup
- Chain break point identifies exact tamper location
- Incident response triggered on integrity failure

---

## T05: Insider Admin Abuse

**Category**: Elevation of Privilege, Tampering  
**Actor**: Platform admin, support user  
**Target**: Any resource, user accounts, audit data  

**Attack**: Abuse admin privileges to access PHI, modify records, or suppress audit evidence.

**Mitigations (Implemented)**:
- Privileged actions require justification field (stored in audit)
- Break-glass access logged with mandatory justification
- JIT elevation: admin rights granted temporarily, not permanently
- Dual approval required for destructive operations (hard delete, user suspension)
- Admin actions are a separate audit event category with enhanced detail
- No admin can modify audit records (technical control, not policy)

**Detective Controls**:
- All admin actions logged with justification
- Access review screens for compliance officers
- Suspicious action queue (unusual admin patterns)
- Break-glass event alerting

**Recovery**:
- Admin access revocation
- Incident record with full audit trail of admin actions
- Access review triggered

---

## T06: API Abuse

**Category**: Denial of Service, Information Disclosure  
**Actor**: External attacker, bot  
**Target**: Public API endpoints  

**Attack**: Brute force, credential stuffing, enumeration, or DoS.

**Mitigations (Implemented)**:
- Rate limiting per IP and per authenticated user
- Request size limits
- Input validation on all endpoints
- Authentication required for all non-public endpoints
- Correlation IDs for request tracing
- Secure error messages (no stack traces, no internal details)

**Detective Controls**:
- Rate limit violation logging
- Failed authentication attempt tracking
- Request pattern analysis hooks

**Recovery**:
- IP blocking capability
- Account lockout
- Incident response procedures

---

## T07: Malware / Ransomware via PDF

**Category**: Tampering  
**Actor**: External attacker  
**Target**: Ingestion pipeline, storage  

**Attack**: Upload a malicious PDF that exploits rendering vulnerabilities or contains embedded malware.

**Mitigations (Implemented)**:
- MIME type validation (must be application/pdf)
- PDF structural validation (valid PDF header, structure)
- File size limits
- Malware scan hook (ClamAV integration point)
- Quarantine state for suspicious files
- PDFs stored as opaque blobs — not rendered server-side

**Detective Controls**:
- Malware scan results logged
- Quarantine events tracked
- Alert on repeated malware detections

**Recovery**:
- Quarantined files isolated from normal workflow
- Incident record for malware detections

---

## T08: Evidence File Mismatch

**Category**: Tampering  
**Actor**: Attacker with storage access, or bug in evidence linking  
**Target**: Evidence chain integrity  

**Attack**: Replace evidence file with a different file, or link evidence to wrong prescription.

**Mitigations (Implemented)**:
- Evidence file checksum computed and stored at creation
- Evidence linked to prescription by ID with checksum verification
- Original QTSP response stored verbatim alongside normalized data
- Evidence file stored in WORM-compatible storage
- Integrity verification routine checks evidence checksums

**Detective Controls**:
- Checksum mismatch detection
- Evidence chain verification in integrity job
- Alert on evidence modification attempts

**Recovery**:
- Original QTSP response available for re-verification
- Incident record for evidence integrity failures

---

## T09: Replay Attack on Upload

**Category**: Tampering, Spoofing  
**Actor**: Attacker intercepting or replaying upload requests  
**Target**: Ingestion endpoint  

**Attack**: Replay a captured upload request to create duplicate prescriptions.

**Mitigations (Implemented)**:
- Idempotency key required per upload (client-generated UUID)
- Duplicate detection by content checksum
- Upload nonce bound to authenticated session
- Short-lived upload authorization tokens
- TLS for all transport

**Detective Controls**:
- Duplicate upload attempt logging
- Idempotency key collision alerting

**Recovery**:
- Duplicate prescriptions prevented from creation
- Incident record for replay attempts

---

## T10: Broken Chain of Custody

**Category**: Repudiation  
**Actor**: System bug, operational error  
**Target**: Prescription lifecycle  

**Attack**: Gap in audit trail that breaks the ability to prove chain of custody.

**Mitigations (Implemented)**:
- Every state transition emits an audit event (mandatory, not optional)
- Audit middleware intercepts all API calls automatically
- State machine enforcement: prescription cannot transition without audit
- Hash chain provides ordering proof
- Sequence numbers provide gap detection

**Detective Controls**:
- Chain integrity verification
- Sequence gap detection
- State transition validation

**Recovery**:
- Gap identified and investigated
- Manual audit event insertion by compliance officer (itself audited)
- Incident record for chain breaks

---

## T11: Insecure Deletion

**Category**: Information Disclosure  
**Actor**: Insider or attacker  
**Target**: Prescription data, patient data  

**Attack**: Delete records without authorization or without proper evidence.

**Mitigations (Implemented)**:
- Soft delete by default (records marked, not removed)
- Hard delete requires dual approval workflow
- WORM storage prevents premature deletion of documents
- Deletion events recorded in audit trail
- Cryptographic erase abstraction for key destruction approach
- Legal hold prevents any deletion

**Detective Controls**:
- Deletion attempt logging
- Unauthorized deletion alerting
- Retention compliance checking

**Recovery**:
- Soft-deleted records recoverable
- WORM-stored documents preserved
- Incident record for unauthorized deletion attempts

---

## T12: Cloud Misconfiguration

**Category**: Information Disclosure  
**Actor**: Operational error  
**Target**: S3 buckets, database, network  

**Attack**: Publicly accessible storage, unencrypted database, open security groups.

**Mitigations (Implemented)**:
- Terraform IaC with security defaults
- No public bucket policies in code
- Encryption at rest enabled by default
- Private subnets for database and internal services
- Security group rules in IaC

**Detective Controls**:
- Infrastructure scanning hooks
- Terraform plan review in CI/CD

**Recovery**:
- IaC-driven remediation
- Incident response for exposure events

---

## T13: Privilege Escalation

**Category**: Elevation of Privilege  
**Actor**: Authenticated user  
**Target**: Authorization system  

**Attack**: Manipulate role, tenant, or scope parameters to gain unauthorized access.

**Mitigations (Implemented)**:
- ABAC policy evaluated server-side on every request
- Tenant ID from authenticated session, not from request parameters
- Role from database, not from client tokens
- No client-side role/scope manipulation possible
- Cross-tenant queries rejected at ORM level

**Detective Controls**:
- Authorization denial logging with full context
- Pattern detection for repeated authorization failures

**Recovery**:
- Account review and potential suspension
- Incident record for escalation attempts

---

## T14: Multi-Tenant Data Exposure

**Category**: Information Disclosure  
**Actor**: Authenticated user in Tenant A  
**Target**: Data belonging to Tenant B  

**Attack**: Access data from another tenant through API manipulation, query injection, or authorization bypass.

**Mitigations (Implemented)**:
- Tenant ID injected from session into all database queries
- ORM-level query filter enforces tenant scoping
- No API endpoint accepts tenant_id as a parameter (derived from auth)
- Foreign key constraints ensure referential integrity within tenant
- Integration tests verify tenant isolation

**Detective Controls**:
- Cross-tenant access attempt logging
- Tenant isolation verification in test suite

**Recovery**:
- Immediate investigation of any cross-tenant access
- Incident record and notification

---

## T15: Weak Session Management

**Category**: Spoofing  
**Actor**: Attacker  
**Target**: User sessions  

**Attack**: Session hijacking, fixation, or failure to invalidate.

**Mitigations (Implemented)**:
- Server-side sessions (not JWT-only)
- Secure session token generation (cryptographically random)
- Session timeout (configurable, conservative default)
- Session invalidation on logout
- Session invalidation on password change
- Concurrent session limits
- Session binding to IP/user-agent (configurable)

**Detective Controls**:
- Session creation/destruction audit events
- Concurrent session alerting
- Session anomaly detection hooks

**Recovery**:
- Force logout capability for admins
- All sessions revocable per user

---

## T16: Compromised QTSP Integration

**Category**: Tampering, Information Disclosure  
**Actor**: Compromised QTSP provider or man-in-the-middle  
**Target**: Signature verification results  

**Attack**: Return false verification results or intercept prescription documents.

**Mitigations (Implemented)**:
- Mutual TLS or API key authentication with QTSP
- QTSP response validated against expected schema
- Raw response preserved for independent verification
- Circuit breaker prevents cascading failures
- Multiple QTSP provider abstraction (failover capability)
- Verification result does not auto-approve — human review path exists

**Detective Controls**:
- QTSP response anomaly detection
- Verification result pattern monitoring
- Raw response audit trail

**Recovery**:
- Manual verification path for suspicious results
- Re-verification capability against different provider
- Incident record for QTSP anomalies

---

## T17: Backdated or Manipulated Timestamps

**Category**: Tampering, Repudiation  
**Actor**: Insider or attacker  
**Target**: Audit timestamps, prescription dates  

**Attack**: Manipulate timestamps to forge timeline of events.

**Mitigations (Implemented)**:
- Server-side UTC timestamps only (never trust client timestamps)
- NTP synchronization required for all servers
- QTSP provides qualified timestamps for verification events
- Hash chain provides temporal ordering independent of wall clock
- Sequence numbers provide additional ordering proof

**Detective Controls**:
- Timestamp consistency checks in integrity verification
- Out-of-order event detection
- Clock skew monitoring

**Recovery**:
- Hash chain and sequence numbers provide ordering proof even with clock issues
- Incident record for timestamp anomalies

---

## Threat-to-Control Mapping Summary

| Threat | Primary Control | Detective Control | Audit Evidence |
|--------|----------------|-------------------|----------------|
| T01 Forged Upload | QTSP verification | Failed verification alerts | upload, verification events |
| T02 Compromised Account | MFA, session controls | Login anomaly detection | login, session events |
| T03 Unauth Pharmacy | ABAC, tenant isolation | Access denied alerting | access events |
| T04 Audit Tampering | Hash chain, WORM export | Integrity verification | meta-audit events |
| T05 Admin Abuse | Justification, JIT elevation | Admin action review | admin events |
| T06 API Abuse | Rate limiting, validation | Rate limit violation logs | request logs |
| T07 Malware PDF | MIME/PDF validation, scan | Quarantine alerts | scan events |
| T08 Evidence Mismatch | Checksum, WORM storage | Integrity verification | evidence events |
| T09 Replay Attack | Idempotency, nonce | Duplicate detection | upload events |
| T10 Chain Break | Mandatory audit emission | Gap detection | chain verification |
| T11 Insecure Deletion | Soft delete, dual approval | Deletion alerting | deletion events |
| T12 Cloud Misconfig | IaC defaults | Infra scanning | deployment events |
| T13 Privilege Escalation | Server-side ABAC | AuthZ denial logging | authz events |
| T14 Multi-Tenant Leak | ORM tenant filter | Isolation tests | access events |
| T15 Weak Sessions | Server-side sessions | Session anomaly detection | session events |
| T16 QTSP Compromise | mTLS, response validation | Response anomaly detection | verification events |
| T17 Timestamp Manipulation | Server-side UTC, hash chain | Consistency checks | timestamp events |
