# QES Flow — Security Design

## Security Principles

1. **Fail closed**: Deny by default, permit explicitly
2. **Defense in depth**: Multiple layers of controls
3. **Least privilege**: Minimum access necessary
4. **Audit everything**: Every sensitive action recorded
5. **Assume breach**: Design for detection and containment
6. **Immutable evidence**: Audit records cannot be modified

## Authentication Architecture

### External Identity Provider Integration
- OIDC/SAML abstraction layer
- Platform does not store passwords
- IdP handles credential management, MFA enrollment
- Platform receives authenticated identity claims

### Session Management
- Server-side session store (PostgreSQL-backed)
- Cryptographically random session tokens (32 bytes)
- Secure cookie attributes: HttpOnly, Secure, SameSite=Strict
- Configurable timeouts: 30 min idle, 8 hour absolute
- Session revocation: immediate on logout, password change, admin action

### MFA Model
- MFA enforcement delegated to IdP
- Platform can require MFA claim for sensitive operations
- `mfa_verified` attribute available in ABAC policy evaluation

## Authorization Architecture

### RBAC Layer
Predefined roles with permission sets. Roles assigned per user, scoped to tenant.

### ABAC Layer
Policy evaluation on every request considering actor, resource, action, and context attributes.

### Tenant Isolation
- Tenant ID from authenticated session only
- ORM-level query filter on all queries
- Cross-tenant access is hard deny with alerting

## Data Protection

### Encryption at Rest
- PostgreSQL: TDE for production
- S3: SSE-S3 or SSE-KMS
- PII columns: application-level encryption
- Key management via KMS abstraction

### Encryption in Transit
- TLS 1.3 for all connections

### PII Handling
- GDPR Art. 9 special category data
- Minimum data principle
- Access requires explicit authorization + audit

## Input Validation
- Pydantic schemas on all request bodies
- MIME type, size, structure validation on file uploads
- No server-side PDF rendering

## Rate Limiting
- Per-IP and per-user limits
- Stricter on login and upload
- Violations logged

## Secure Headers
- HSTS, CSP, X-Content-Type-Options, X-Frame-Options
- Referrer-Policy, Permissions-Policy

## Secret Management
- Environment variables, never in code
- Production: vault integration
- Credential rotation support

## Incident Response Hooks
- Security events classified by severity
- High-severity triggers alerts
- Break-glass always high severity
- Audit integrity failures always critical
