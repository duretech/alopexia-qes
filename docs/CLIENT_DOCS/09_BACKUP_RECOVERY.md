# Backup & Disaster Recovery

## 🔄 Backup Strategy

### **What Gets Backed Up?**

```
1. Database (PostgreSQL)
   ├─ Full backup: Daily at 2 AM UTC
   ├─ Retention: 30 days (configurable up to 35)
   ├─ Redundancy: Geo-redundant (automatic)
   ├─ Size: ~500MB-2GB depending on data
   └─ Encryption: AES-256 (Azure managed)

2. Prescription Files (Azure Blob Storage)
   ├─ Replication: Geo-redundant (automatic, no manual backup needed)
   ├─ Versioning: All versions retained
   ├─ Soft delete: 30-day recovery window
   ├─ Size: ~10MB-100MB per prescription
   └─ Encryption: AES-256 (server-side)

3. Audit Logs (Immutable Backup)
   ├─ Export: Daily JSON Lines export
   ├─ Destination: Archive Storage (Glacier equivalent)
   ├─ Retention: 7 years (legal requirement)
   ├─ Encryption: Separate backup encryption key
   └─ Purpose: Tamper-proof compliance archive

4. Encryption Keys
   ├─ Backup: Automatic by Azure Key Vault
   ├─ Redundancy: Geo-replicated
   ├─ Access: Requires Managed Identity
   └─ Note: Keys never leave Key Vault in plaintext
```

---

## 💾 Backup Process

### **Automated Backups (Database)**

```
Backup Frequency
├─ Full daily backup: 2 AM UTC
├─ Transaction log backup: Every 5 minutes
└─ Retention: Last 30 days (rolling window)

How It Works
1. Full backup starts at 2 AM UTC
2. Database is locked briefly (read-only)
3. All data written to backup storage
4. Backup encrypted with master key
5. Checksum calculated (verify integrity)
6. Old backup deleted (>30 days old)

Verification
├─ Backup size should be ~same as database size
├─ Backup should complete in <1 hour
├─ Checksum should match on restore
└─ Alert if backup >2 hours old
```

**Manual Backup (If Needed):**
```bash
# Create on-demand backup
az postgres server backup create \
  --resource-group myresourcegroup \
  --server-name qes-db \
  --backup-name manual_backup_20260413
```

### **Audit Log Backups (Daily Export)**

```
Export Schedule
├─ Time: 3 AM UTC (after database backup)
├─ Format: JSON Lines (one event per line)
├─ Compression: gzip
├─ Encryption: Encrypted before upload

Process
1. Query all new audit events since last export
2. Verify hash chain integrity before export
3. Format as JSON Lines
4. Compress (gzip)
5. Encrypt with backup encryption key
6. Upload to Archive Storage
7. Calculate manifest (list of events exported)
8. Log export in audit trail (recursive audit!)
9. Email summary to compliance team

Naming Convention
audit_export_2026_04_01.json.gz
└─ Contains all events from April 1, 2026
```

**Manual Export (If Needed):**
```bash
# Export audit logs via API
curl -X POST https://your-domain.com/api/v1/audit/export \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2026-04-01",
    "end_date": "2026-04-30",
    "format": "json_lines"
  }' \
  --output audit_april.json.gz
```

---

## 🔄 Recovery Time Objectives (RTO/RPO)

```
RTO = Recovery Time Objective (how long to get system back online)
RPO = Recovery Point Objective (how much data we're willing to lose)

QES Flow RTO/RPO Targets:

Database
├─ RTO: 1 hour
│  └─ Time to restore database from backup
├─ RPO: 5 minutes
│  └─ Lose at most 5 minutes of data (transaction logs)
└─ How: Automated backup + transaction log replay

Prescription Files
├─ RTO: 5 minutes
│  └─ Azure geo-redundancy automatic
├─ RPO: 0 (geo-redundant = no data loss)
└─ How: Automatic replication to secondary region

Audit Logs
├─ RTO: 24 hours (restore from daily export)
├─ RPO: 1 day
└─ How: Daily JSON export to Archive Storage

Encryption Keys
├─ RTO: Immediate
├─ RPO: 0 (Key Vault is managed, no backups needed)
└─ How: Key Vault automatic replication
```

---

## 🚨 Disaster Scenarios & Recovery

### **Scenario 1: Database Corruption**

```
Detection
├─ Database queries return errors
├─ Health check fails
├─ Audit log integrity check fails
└─ Team receives alert

Recovery Process
1. Diagnose severity:
   ├─ Single table corruption? (specific restore)
   ├─ Multiple tables? (full database restore)
   └─ Encryption key issue? (use backup key)

2. Choose recovery point:
   ├─ Most recent backup (may have some errors)
   ├─ Earlier backup (lose more data)
   └─ Compare timestamps, choose least data loss

3. Restore database:
   az postgres server restore \
     --resource-group myresourcegroup \
     --name qes-db-recovered \
     --source-server qes-db \
     --restore-point-in-time 2026-04-13T10:00:00Z

4. Verify recovery:
   ├─ Check data integrity
   ├─ Run DBCC CHECKDB equivalent
   ├─ Verify audit log hash chain
   └─ Test application queries

5. Switchover to recovered database:
   ├─ Update connection strings
   ├─ Restart API containers
   ├─ Monitor for errors
   └─ Keep old database for forensics

Downtime: ~1 hour
Data Loss: ~5 minutes (since last transaction log)
```

### **Scenario 2: Ransomware Attack (Data Encrypted)**

```
Detection
├─ Cannot decrypt blob storage files
├─ Cannot decrypt database fields
├─ All recent backup integrity checks fail
└─ Security alert triggered

Recovery Process
1. Immediate action:
   ├─ Isolate system from network
   ├─ Do NOT restart services (prevents spread)
   ├─ Create forensic copy of database
   ├─ Preserve logs for investigation

2. Assess damage:
   ├─ Which files encrypted?
   ├─ When did encryption start?
   ├─ What encryption used?
   └─ Can we decrypt with our keys? (test on restored copy)

3. Restore from pre-attack backup:
   ├─ Restore database from backup before encryption detected
   ├─ Restore blob storage from geo-redundant copy
   ├─ Verify encryption keys not compromised
   └─ Update all access keys/secrets

4. Investigate breach:
   ├─ Review access logs (how was system accessed?)
   ├─ Check for lateral movement
   ├─ Identify vulnerability exploited
   └─ Patch vulnerability

5. Relaunch system:
   ├─ Deploy patched code
   ├─ Restart services
   ├─ Monitor closely
   └─ Notify affected users

Recovery Steps:
├─ Phase 1 (Diagnosis): 2-4 hours
├─ Phase 2 (Restore): 1-2 hours
├─ Phase 3 (Verification): 2-4 hours
├─ Phase 4 (Investigation): 8+ hours
└─ Total downtime: 4-8 hours before operational

Critical: Keep backups encrypted and offline if possible
```

### **Scenario 3: Region Failure (Azure Region Down)**

```
Detection
├─ All Azure services in region unreachable
├─ Health checks timeout
├─ All API requests failing
└─ Infrastructure alert from Azure

Recovery Process (Automated)
1. Azure automatically fails over:
   ├─ Database: Geo-redundant replica takes over
   ├─ Blob Storage: Geo-redundant copy accessed
   └─ Key Vault: Replicated in secondary region

2. DNS failover (if configured):
   ├─ your-domain.com points to secondary region
   └─ Users automatically routed to healthy region

Manual Steps (if auto-failover not configured):
1. Create new infrastructure in secondary region:
   ├─ Container instances
   ├─ Application Gateway
   └─ VNet (if not already replicated)

2. Restore database from backup:
   ├─ In secondary region
   ├─ Point to restore point
   └─ Verify integrity

3. Point Application Gateway to secondary region:
   ├─ Update backend pool IP addresses
   ├─ Health check endpoints

4. Test all services:
   ├─ API endpoints
   ├─ Frontends
   ├─ QTSP connectivity
   └─ Audit logs

5. Update DNS:
   ├─ Point to secondary region
   ├─ Set TTL to 5 minutes
   └─ Monitor for propagation

Recovery Time:
├─ If automatic: 5-15 minutes
├─ If manual: 1-2 hours
└─ Data loss: 0 (geo-redundant)

Post-Incident:
├─ Investigate what failed
├─ Update disaster recovery plan
├─ Test failover quarterly
└─ Document incident
```

### **Scenario 4: Key Compromise (Encryption Key Exposed)**

```
Detection
├─ Unauthorized access to Key Vault detected
├─ Encryption key logs show suspicious activity
├─ Alert triggered by monitoring
└─ Suspicion: key may be exposed to attacker

Recovery Process (Critical - Do Immediately)
1. Rotate encryption key (EMERGENCY):
   az keyvault key create \
     --vault-name mykeyvault \
     --name encryption-key-new \
     --protection software

2. Mark old key as compromised:
   ├─ Lock in Key Vault
   ├─ Disable further use
   └─ Retain for decryption only

3. Re-encrypt all data with new key:
   ├─ Decrypt with old key
   ├─ Encrypt with new key
   ├─ Update database records
   └─ Update blob storage files
   
   Time required: Depends on data volume
   - Small (<1GB): 1-2 hours
   - Medium (1-10GB): 4-8 hours
   - Large (>10GB): 1-2 days
   
   Recommendation: Do offline (don't keep system running with compromised key)

4. Verify re-encryption:
   ├─ Spot check decryption with new key
   ├─ Verify hash chains intact
   ├─ Check file integrity

5. Investigate compromise:
   ├─ How was key accessed?
   ├─ Was it in code/config? (Check git history)
   ├─ Was it in logs? (Check log export)
   ├─ Was Key Vault access logged? (Check Azure audit logs)
   └─ Review and fix vulnerability

6. Notify stakeholders:
   ├─ Inform leadership
   ├─ May need to notify data protection authority
   ├─ Document incident timeline
   └─ Implement preventive measures

Prevention:
├─ Never commit keys to git
├─ Use Managed Identity (not keys in env vars)
├─ Audit Key Vault access regularly
├─ Rotate keys every 90 days
└─ Monitor for suspicious access patterns
```

---

## ✅ Backup Verification Checklist

### **Daily Verification**

```
Automated Checks (Run Every 6 Hours):
☐ Database backup completed successfully
  └─ Check: Last backup timestamp < 6 hours
☐ Backup encryption verified
  └─ Check: Backup encrypted with master key
☐ Checksum valid
  └─ Check: Backup integrity checksum matches
☐ Backup size reasonable
  └─ Check: Size within 80-120% of database size
```

### **Weekly Verification**

```
Manual Restore Test:
1. ☐ Select random restore point
2. ☐ Create test database instance
3. ☐ Restore from backup to test instance
4. ☐ Run verification queries:
     - SELECT COUNT(*) FROM users;
     - SELECT COUNT(*) FROM prescriptions;
     - SELECT COUNT(*) FROM audit_events;
5. ☐ Compare counts with production:
     - Numbers should match
     - Or be slightly less (restore point is in past)
6. ☐ Verify audit log integrity:
     - Check hash chain is valid
     - No gaps in sequence numbers
7. ☐ Delete test database
8. ☐ Document results in restore log
```

### **Monthly Verification**

```
Full Disaster Recovery Drill:
1. ☐ Document current system state:
     - Database size
     - Active prescriptions count
     - Last audit event ID
2. ☐ Simulate region failure:
     - Block access to primary region
     - Attempt to access secondary
3. ☐ Perform full database restore:
     - Restore from backup to test environment
     - Point to secondary region's blob storage
4. ☐ Test all application functions:
     - Login (phone OTP)
     - Upload prescription
     - Download prescription
     - Verify status
     - Create audit log entry
5. ☐ Verify audit log integrity:
     - Export audit logs
     - Check hash chain
     - Verify no tampering
6. ☐ Document recovery time:
     - Record actual time taken
     - Compare to RTO target
     - Note any issues
7. ☐ Update recovery procedures:
     - Did anything go wrong?
     - Update documentation
     - Train team on procedures
8. ☐ Archive drill results:
     - Store documentation
     - Report to management
     - Update disaster recovery plan

Target: Should complete within RTO (1 hour for DB)
```

---

## 🛡️ Backup Security Best Practices

### **Protecting Your Backups**

```
Encryption
├─ Always encrypt backups with master key
├─ Never store unencrypted backups
├─ Test decryption regularly
└─ Key Vault protected

Access Control
├─ Only backups admin can access
├─ MFA required for backup operations
├─ Log all backup access
└─ Alert on unusual access

Immutability
├─ Backups should be write-once
├─ Cannot be deleted by users
├─ Can only be deleted by admin after retention
└─ Audit all deletion requests

Geographic Separation
├─ Backups in different region than primary
├─ No shared infrastructure
├─ Independent availability zone
└─ Automatic failover if primary fails

Testing
├─ Test restore quarterly
├─ Verify backup integrity weekly
├─ Keep test environment separate
└─ Document all test results
```

---

## 📋 Backup Checklist

Before going live:
- [ ] Database backup automated and tested
- [ ] Restore procedure documented
- [ ] Blob storage geo-redundancy enabled
- [ ] Audit log exports automated
- [ ] Archive storage configured for 7-year retention
- [ ] Encryption keys backed up in Key Vault
- [ ] RTO/RPO targets documented and achievable
- [ ] Disaster recovery plan written
- [ ] Team trained on recovery procedures
- [ ] Recovery drill scheduled (quarterly)
- [ ] Backup monitoring alerts configured
- [ ] Backup access logs reviewed regularly

---

## Next Steps

For more details, see:
- [OPERATIONS.md](./08_OPERATIONS.md) — Day-to-day operations
- [DEPLOYMENT.md](./07_DEPLOYMENT.md) — Production deployment
- [SECURITY.md](./03_SECURITY.md) — Security implementation
