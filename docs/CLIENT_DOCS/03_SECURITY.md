# Security & Controls

## 🔒 Security Layers

### **Layer 1: Network Security**
```
┌─────────────────────────────────┐
│   Internet (Untrusted)          │
└──────────────┬──────────────────┘
               ↓
         WAF (Web Application Firewall)
         ├─ DDoS Protection
         ├─ SQL Injection Detection
         └─ Bot Detection
               ↓
         TLS 1.2+ Encryption
         ├─ HTTPS Only (redirect HTTP)
         ├─ Certificate Pinning
         └─ Perfect Forward Secrecy
               ↓
         Azure Network Security Groups
         ├─ Inbound rules (only API port)
         ├─ Outbound rules (controlled)
         └─ Private endpoints for DB
               ↓
      ┌────────────────┐
      │  Azure VNet    │
      │  (Isolated)    │
      └────────────────┘
```

### **Layer 2: Application Security**
```
Authentication
├─ Phone OTP (One-Time Password)
├─ PIN Verification (MFA)
├─ JWT Tokens (8-hour expiry)
└─ Refresh Tokens (24-hour expiry)

Authorization
├─ Role-Based Access Control (RBAC)
├─ Permission Matrix (per role)
├─ Tenant Isolation
└─ Resource-level checks

Input Validation
├─ Type checking (Pydantic schemas)
├─ Size limits (50MB per file)
├─ Whitelist validation (allowed types)
└─ Sanitization (XSS prevention)

Rate Limiting
├─ 100 req/min (default)
├─ 10 req/min (login endpoints)
├─ 20 req/min (upload endpoints)
└─ Per-IP tracking
```

### **Layer 3: Data Security**
```
At Rest
├─ Database: TDE (Transparent Data Encryption)
│   └─ AES-256 (Azure managed keys)
├─ Files: Azure Blob Storage encryption
│   └─ AES-256 (Server-side)
└─ Field-Level: AES-256-GCM (application)
    └─ Phone, PIN, OTP encrypted

In Transit
├─ Client ↔ Server: TLS 1.2+
└─ Server ↔ Database: SSL/TLS

Keys Management
├─ Azure Key Vault (central management)
├─ Key rotation (every 90 days)
├─ Separate keys per environment
└─ Access logging (who accessed key)
```

### **Layer 4: Audit & Compliance**
```
Immutable Audit Trail
├─ Every action logged (upload, download, etc.)
├─ Hash-chained (cannot alter past events)
├─ HMAC verified (detect tampering)
├─ 1-year retention minimum
└─ Exportable for audits

Data Masking
├─ Sensitive fields masked in logs
│   ├─ Phone numbers
│   ├─ PINs/OTPs
│   ├─ Email addresses
│   └─ Tokens
├─ Patterns replaced (e.g., credit cards)
└─ Full encryption in database
```

---

## 🛡️ Security Controls (OWASP Top 10)

### **1. Injection Prevention**
| Control | Implementation |
|---------|-----------------|
| SQL Injection | Parameterized queries (SQLAlchemy ORM) |
| Command Injection | No shell commands in app code |
| LDAP Injection | Not applicable (no LDAP) |

### **2. Broken Authentication**
| Control | Implementation |
|---------|-----------------|
| Password Policy | N/A (using OTP instead) |
| Session Management | JWT tokens with 8-hour expiry |
| MFA | Phone OTP + PIN required |
| Brute Force | Rate limiting (10/min on login) |

### **3. Sensitive Data Exposure**
| Control | Implementation |
|---------|-----------------|
| Data Encryption | AES-256 (rest & transit) |
| Secure Transport | TLS 1.2+ mandatory |
| Error Messages | No sensitive info in errors |
| Data Masking | Logs automatically mask PII |

### **4. XML External Entities (XXE)**
| Control | Implementation |
|---------|-----------------|
| XML Parsing | PDF only, no XML processing |
| File Upload | Strict file type validation |
| Parser Config | Secure defaults |

### **5. Broken Access Control**
| Control | Implementation |
|---------|-----------------|
| RBAC | 6 roles, permission matrix |
| Tenant Isolation | All queries filtered by tenant_id |
| Resource Ownership | Verify user owns resource |
| Admin Checks | Permission checks before each action |

### **6. Security Misconfiguration**
| Control | Implementation |
|---------|-----------------|
| Default Credentials | All changed, no defaults used |
| Unnecessary Services | Only required services enabled |
| Security Headers | HSTS, CSP, X-Frame-Options set |
| Debug Mode | Disabled in production |

### **7. Cross-Site Scripting (XSS)**
| Control | Implementation |
|---------|-----------------|
| Input Encoding | All user input validated |
| CSP Headers | Content-Security-Policy: default-src 'none' |
| Output Encoding | React auto-escapes by default |

### **8. Insecure Deserialization**
| Control | Implementation |
|---------|-----------------|
| JSON Only | No Python pickle, only JSON |
| Type Validation | Pydantic validates all inputs |
| Version Control | API versioning prevents issues |

### **9. Using Components with Known Vulnerabilities**
| Control | Implementation |
|---------|-----------------|
| Dependency Scanning | Automated with Dependabot |
| Updates | Security patches applied immediately |
| Monitoring | Continuous vulnerability scanning |

### **10. Insufficient Logging & Monitoring**
| Control | Implementation |
|---------|-----------------|
| Structured Logging | JSON logs with context |
| Alert Rules | Auto-alerts for anomalies |
| Audit Trail | Immutable, hash-chained |
| Retention | 1-year minimum |

---

## 🔑 Cryptographic Standards

### **Encryption**
```
Algorithm: AES-256 (Advanced Encryption Standard)
Mode: GCM (Galois/Counter Mode) - Authenticated encryption
Key Size: 256 bits
Implementation: Industry-standard libraries (cryptography.io)
```

### **Hashing (Audit Trail)**
```
Algorithm: HMAC-SHA256 (Hash-based Message Authentication Code)
Purpose: Verify audit log integrity
Verification: Chain previous hash to current for tamper detection
```

### **Digital Signatures**
```
Verification: QTSP Provider (Dokobit)
Standard: ETSI EN 319 102-1 (EU qualified timestamp)
Certificate: Qualified Electronic Signature Certificate
```

### **Key Derivation**
```
PINs: Hashed with bcrypt (not stored in plaintext)
OTPs: Generated with TOTP (Time-based One-Time Password)
Tokens: Signed with HS256 (HMAC-SHA256)
```

---

## 🚨 Threat Model & Mitigation

### **Threat 1: Data Breach**
```
Threat: Attacker gains DB access
Impact: Patient data exposed
Mitigation:
├─ Field-level encryption (data encrypted even if DB accessed)
├─ Network isolation (private endpoints, no public access)
├─ Azure Key Vault (keys not in DB)
├─ Access logging (detect unauthorized access)
├─ Firewall rules (IP-based access control)
└─ Regular audits (vulnerability scans)
```

### **Threat 2: Man-in-the-Middle (MITM)**
```
Threat: Attacker intercepts network traffic
Impact: Credentials or documents stolen
Mitigation:
├─ TLS 1.2+ (encrypted channel)
├─ Certificate pinning (app verifies cert)
├─ HSTS (browser enforces HTTPS)
└─ Secure headers (prevent downgrades)
```

### **Threat 3: Malicious File Upload**
```
Threat: Malware uploaded as PDF
Impact: System compromise, infection spread
Mitigation:
├─ File type validation (PDF only)
├─ Size limits (max 50MB)
├─ Malware scanning (ClamAV)
├─ Isolated storage (Azure encrypted blob)
└─ Quarantine (infected files blocked)
```

### **Threat 4: Unauthorized Access**
```
Threat: User gains access to other user's data
Impact: Privacy violation, GDPR breach
Mitigation:
├─ RBAC (role-based permissions)
├─ Tenant isolation (data separated)
├─ Resource ownership checks (verify user owns resource)
├─ Rate limiting (prevent brute force)
└─ MFA (phone OTP + PIN)
```

### **Threat 5: Forged Digital Signature**
```
Threat: Fake prescription uploaded with forged signature
Impact: Pharmacy dispenses invalid prescription
Mitigation:
├─ QTSP verification (signature validation)
├─ Certificate chain validation (trusted CAs only)
├─ Qualified timestamp (proof of when signed)
├─ Audit trail (evidence of who uploaded)
└─ Immutable records (cannot alter after upload)
```

### **Threat 6: Audit Log Tampering**
```
Threat: Attacker modifies audit logs to hide actions
Impact: Non-repudiation violated, compliance breach
Mitigation:
├─ Hash-chaining (logs linked cryptographically)
├─ HMAC verification (detect tampering)
├─ Immutable storage (database constraints)
├─ Write-once backup (to Glacier)
└─ Export validation (hash verification on export)
```

---

## 🔐 Secure Deployment Practices

### **Secrets Management**
```
NOT in Code
├─ No hardcoded passwords
├─ No API keys in git
├─ No encryption keys in config files

Azure Key Vault
├─ Central secrets repository
├─ Access logging (who accessed secret)
├─ Rotation policies (automatic)
├─ Backup & disaster recovery
└─ RBAC (only authorized apps access)

Environment Variables
├─ Loaded from Key Vault
├─ Never logged
├─ Rotated automatically
└─ Different per environment (dev/stage/prod)
```

### **Container Security**
```
Docker Image
├─ Base image: Official minimal images
├─ Vulnerability scan: Trivy scan before deploy
├─ No privileged mode (--user app)
├─ Read-only filesystem where possible
├─ Network policies (only needed ports exposed)

Container Registry
├─ Azure Container Registry (private)
├─ Image signing (code signing)
├─ Access control (RBAC)
└─ Vulnerability scanning (continuous)
```

### **Infrastructure Security**
```
Network
├─ VNet (Virtual Network, isolated)
├─ Subnets (app tier, DB tier separated)
├─ Network Security Groups (firewall rules)
├─ Private endpoints (no public IPs for DB)
└─ DDoS protection (Azure DDoS Standard)

Access Control
├─ Service Principal (app authentication)
├─ Managed Identity (no secrets needed)
├─ Role-based access (Azure RBAC)
└─ MFA for admin access
```

---

## 🔄 Security Incident Response

### **Detection**
```
Automated Alerts
├─ Failed login attempts (>5/min)
├─ Unauthorized access (403 errors)
├─ File upload failures (scanning errors)
├─ Audit log integrity failure (hash mismatch)
└─ System errors (500+ errors)

Manual Reviews
├─ Daily audit log summary
├─ Weekly access review
├─ Monthly security audit
└─ Quarterly penetration testing
```

### **Response Plan**
```
1. Detect → Alert triggered
2. Investigate → Review logs, identify scope
3. Contain → Disable affected accounts, isolate system
4. Eradicate → Patch vulnerability, update signatures
5. Recover → Restore from backups if needed
6. Document → Post-incident review, lessons learned
7. Notify → Inform users if data breach (GDPR requirement)
```

---

## ✅ Compliance Checklist

- ✅ GDPR (encryption, audit logs, data deletion)
- ✅ eIDAS (qualified signatures, timestamp)
- ✅ HIPAA (if US deployment, access controls)
- ✅ ISO 27001 (via Azure compliance)
- ✅ SOC 2 Type II (via Azure audit)
- ✅ PCI DSS (if payment integration needed)

---

## 📞 Security Contacts

- **Security Issue**: security@company.com
- **Incident Response**: incident@company.com
- **Vulnerability Disclosure**: Follow responsible disclosure policy

---

## Next Steps

For more details, see:
- [ENCRYPTION.md](./05_ENCRYPTION.md) — Encryption implementation
- [GDPR_COMPLIANCE.md](./04_GDPR_COMPLIANCE.md) — GDPR compliance
- [AUDIT_TRAIL.md](./06_AUDIT_TRAIL.md) — Audit logging

