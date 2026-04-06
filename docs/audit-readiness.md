# QES Flow — Audit Readiness

## Purpose

This document describes how QES Flow demonstrates compliance readiness during regulatory inspections (AEMPS, data protection authorities, eIDAS supervisory bodies).

## What an Inspector Can Verify

### 1. Signature Verification Process
- Every prescription has a QTSP verification result
- Raw QTSP response preserved alongside normalized data
- Certificate chain, validity, and timestamp details recorded
- Failed verifications tracked with manual review evidence
- **Evidence location**: `signature_verification_results` table + evidence files in S3

### 2. Full Traceability
- Every prescription tracked from upload through dispensing
- Chain of custody model with audit events at every transition
- Actor identity, timestamp, IP address on every action
- **Evidence location**: `audit_events` table, exportable as JSON Lines

### 3. Tamper-Proof Audit Trail
- Append-only event store with hash chaining
- Integrity verification routine validates chain
- WORM-compatible export to S3 Object Lock storage
- No UPDATE/DELETE capability on audit tables
- **Evidence location**: integrity verification reports, WORM exports

### 4. Secure Storage
- Prescription PDFs in encrypted S3 with Object Lock
- No public URLs — signed URLs only with short TTL
- Checksums computed at upload and verified on access
- **Evidence location**: storage configuration, checksum records

### 5. Controlled Access
- RBAC + ABAC authorization on every request
- Tenant isolation enforced at query level
- All access events logged
- Failed access attempts logged
- **Evidence location**: `audit_events` filtered by access events

### 6. Retention and Deletion Controls
- Configurable retention schedules per resource type
- Legal hold capability overrides retention expiry
- Hard delete requires dual approval
- All deletions recorded in audit trail
- **Evidence location**: `retention_schedules`, `legal_holds`, `deletion_requests` tables

### 7. System Validation Evidence
- Test suites covering authorization, audit, tamper detection
- CI/CD pipeline with security gates
- Infrastructure-as-code with security defaults
- **Evidence location**: test reports, CI/CD logs, Terraform state

## Audit Export Procedure

1. Compliance officer authenticates to admin portal
2. Selects date range and event types for export
3. System generates JSON Lines export of audit events
4. Export includes integrity verification summary
5. Export stored in WORM-compatible bucket
6. Export event itself recorded in audit trail

## Regulatory Assumptions

### Real Decreto 1718/2010
- Prescription traceability requirements mapped to chain of custody model
- Compounding pharmacy events include formulation registration number field
- REQUIRES CONFIRMATION BY SPANISH HEALTHCARE / PHARMA COUNSEL: exact retention periods for prescriptions

### eIDAS
- QTSP integration verifies qualified electronic signatures
- Certificate and timestamp validation per eIDAS standards
- Trust list status recordable
- REQUIRES CONFIRMATION BY SPANISH HEALTHCARE / PHARMA COUNSEL: whether qualified timestamps are mandatory for this workflow

### GDPR
- Health data protected as special category (Art. 9)
- Lawful basis documented (legal obligation for prescription records)
- Data minimization applied
- Right to erasure subject to legal retention requirements
- REQUIRES CONFIRMATION BY SPANISH HEALTHCARE / PHARMA COUNSEL: data subject rights handling for prescription records under retention

### AEMPS
- Formulacion magistral traceability maintained
- Inspector access via read-only auditor role
- Full evidence export capability
- REQUIRES CONFIRMATION BY SPANISH HEALTHCARE / PHARMA COUNSEL: specific AEMPS inspection data format requirements
