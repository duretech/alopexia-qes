# Operations & Maintenance Guide

## 📊 Day-to-Day Operations

### **Health Monitoring Dashboard**

Access the operations dashboard at:
```
https://your-domain.com/admin/health
```

**Key Metrics to Monitor:**

```
System Health
├─ API Server: Should be green (status 200)
├─ Database: Connection time <100ms
├─ Blob Storage: Access time <500ms
├─ QTSP Provider: Availability >99.9%
└─ Malware Scanner: Availability >99.5%

Performance
├─ API Response Time:
│  ├─ Upload: <2s (includes QTSP)
│  ├─ Download: <1s
│  └─ Login: <500ms
├─ Database Query Time:
│  ├─ Average: <50ms
│  └─ P99: <200ms
└─ Storage Access:
   ├─ Average: <100ms
   └─ P99: <500ms

Error Rates
├─ API errors: Should be <0.1%
├─ Database errors: Should be 0%
├─ Storage errors: Should be <0.01%
└─ QTSP errors: Normal variation 0-5%
```

---

## 🔄 Common Operational Tasks

### **Task 1: Check System Health**

```bash
# API Health Check
curl https://your-domain.com/health/live
# Response: {"status": "ok"}

# Deep Health Check
curl https://your-domain.com/health/deep
# Response includes: database latency, storage latency, scanner status

# Check Logs
az container logs --resource-group myresourcegroup --name qes-production
```

**What Normal Looks Like:**
```
database_latency_ms: 45-100
storage_latency_ms: 80-300
scanner_latency_ms: 200-1000
api_status: healthy
```

**What Abnormal Looks Like:**
```
database_latency_ms: >500 (very slow)
storage_latency_ms: >2000 (timing out)
scanner: unavailable
error_count: increasing
```

### **Task 2: Monitor Audit Trail Integrity**

**Run Daily (Automated):**
```
Purpose: Verify no one has tampered with audit logs

Process:
1. Calculate hash for every audit event
2. Verify chain: Event N's previous_hash == Event N-1's current_hash
3. Check for gaps (missing sequence numbers)
4. Alert if any mismatch detected

Frequency: Every 4 hours (automated)
```

**Manual Check (Weekly):**
```bash
# Export last 7 days of audit logs
curl -X POST https://your-domain.com/api/v1/audit/export \
  -H "Authorization: Bearer <admin-token>" \
  -d '{
    "start_date": "2026-04-06",
    "end_date": "2026-04-13",
    "format": "json_lines"
  }'

# Verify hash chain integrity
# Each event should have: previous_hash (match from last event)
```

---

## 🔑 Key Rotation (Every 90 Days)

### **Encryption Key Rotation Process**

```
Why Rotate?
├─ Industry best practice
├─ Limits damage if key compromised
├─ GDPR requirement
└─ Reduces key usage exposure

What Happens:
1. New key generated in Azure Key Vault (automated)
2. All NEW encryptions use new key
3. Old key retained for DECRYPTION of old data
4. After retention period, old key deleted
5. Zero downtime (transparent to users)
```

**Checklist:**
```
Before Rotation:
☐ Backup current encryption key
☐ Schedule rotation (off-peak hours)
☐ Notify stakeholders
☐ Test disaster recovery with old key

During Rotation:
☐ Monitor API logs for errors
☐ Check database decryption working
☐ Verify blob storage access working

After Rotation:
☐ All encryptions using new key
☐ All decryptions working
☐ Audit log entry created
☐ Key rotation verified
☐ Old key backed up securely
```

---

## 🔒 Certificate Management

### **TLS Certificate Rotation (Quarterly)**

```
Current Certificates
├─ Expiration: Check every month
├─ Provider: Azure Key Vault
└─ Auto-renewal: Let's Encrypt (if configured)

Manual Rotation Steps:
1. Request new certificate (via Azure or Let's Encrypt)
2. Store .pem files in Key Vault
3. Update Application Gateway configuration
4. Restart API container
5. Verify HTTPS working: curl -vI https://your-domain.com
```

**Set a Reminder:**
```
Schedule: 30 days before expiration
Action: Review certificate status
Alert: If expiration < 14 days, immediate action needed
```

---

## 📊 Database Maintenance

### **Daily Tasks**

```
Vacuum & Analyze (Automated)
├─ Time: 2 AM UTC
├─ Purpose: Optimize query performance
├─ Duration: ~30 minutes
└─ Impact: None (runs on replica)

Backup Verification
├─ Time: 3 AM UTC
├─ Purpose: Ensure backups successful
├─ Check: Latest backup size and time
└─ Alert: If backup >2 hours old
```

### **Weekly Tasks**

```
Connection Pool Health
├─ Check: Active connections < 80
├─ Check: Idle connections < 20
├─ Action: If > 100 connections, investigate long-running queries

Index Health
├─ Check: Unused indexes
├─ Check: Index bloat (size > 10% of table)
├─ Action: Drop unused indexes, rebuild bloated ones

Query Performance
├─ Check: Slow queries (>1 second)
├─ Check: Full table scans
├─ Action: Review query plans, add indexes if needed
```

### **Monthly Tasks**

```
Data Integrity Check
├─ Check: Foreign key constraints
├─ Check: Unique constraint violations
├─ Check: NULL constraints
└─ Action: Alert if violations detected

Disk Space Monitoring
├─ Check: Used space < 80%
├─ Check: Growth trend
└─ Action: Scale up if growth rate high

Backup Restoration Test
├─ Action: Restore latest backup to test database
├─ Purpose: Verify backup integrity
├─ Check: Data matches production
└─ Schedule: Quarterly (more frequent if high-risk)
```

---

## 📈 Performance Tuning

### **When API Is Slow (Response Time > 2 seconds)**

```
Step 1: Identify Bottleneck
├─ Check database query time (via Azure Monitor)
├─ Check storage access time
├─ Check QTSP provider latency
└─ Check API request distribution

If Database Slow (>500ms):
├─ Check active queries: SELECT * FROM pg_stat_activity
├─ Look for long-running queries
├─ Check missing indexes on frequently filtered columns
├─ Consider increasing connection pool size

If Storage Slow (>2000ms):
├─ Check Azure Blob Storage performance
├─ Check network connectivity (latency)
├─ Consider adding CDN for file downloads

If QTSP Slow (>3000ms):
├─ Check Dokobit API status
├─ Implement client-side timeout (abort if >10s)
├─ Consider queueing verification for peak times
```

### **Database Query Optimization**

```
Tools:
├─ EXPLAIN ANALYZE (show query plan)
├─ pg_stat_statements (query statistics)
└─ pgAdmin (visual query planner)

Example Optimization:
-- Slow query (full table scan):
SELECT * FROM prescriptions WHERE status = 'verified'

-- Optimized (with index):
CREATE INDEX idx_prescriptions_status ON prescriptions(status);
-- Now query uses index instead of scanning all rows
```

---

## 🚨 Incident Response

### **Critical Issue: API Container Crashes**

```
Detection:
└─ Health check fails for 60 seconds

Automatic Response:
├─ Load balancer removes unhealthy container
├─ New container starts automatically
├─ Users routed to healthy containers
└─ Incident logged and alerted

Manual Investigation:
1. Check container logs: 
   az container logs --resource-group myresourcegroup --name qes-production
2. Look for error messages (database, key vault, storage)
3. Restart container:
   az container restart --resource-group myresourcegroup --name qes-production
4. Verify health check passes
5. Monitor for 5 minutes
6. If continues failing:
   ├─ Rollback to previous image
   ├─ Investigate root cause
   └─ Deploy fix
```

### **Critical Issue: Database Down**

```
Detection:
└─ API cannot connect to PostgreSQL

Automatic Response:
├─ Health check fails
├─ Alert sent to on-call team
└─ Users see error messages

Manual Recovery:
1. Check Azure Portal:
   az postgres show --resource-group myresourcegroup --name qes-db
2. Check server status:
   └─ If "Stopped": start server
   └─ If "Degraded": contact Azure support
3. Verify connectivity:
   psql -h qes-db.postgres.database.azure.com -U admin -d qes_prod
4. If network issue:
   └─ Check VNet rules and firewall
5. Restore from backup if corruption:
   az postgres server restore --resource-group myresourcegroup --name qes-db-restored --source-server qes-db --restore-point-in-time 2026-04-13T10:00:00Z

Timeout: If database not recovered within 1 hour:
├─ Activate disaster recovery plan
├─ Restore to alternative region
└─ Redirect traffic to DR environment
```

### **Critical Issue: Storage Down (Prescriptions Inaccessible)**

```
Detection:
└─ Blob storage access fails

Automatic Response:
├─ Health check fails
├─ API returns error on download requests
└─ Alert sent to ops team

Manual Recovery:
1. Check storage account status (Azure Portal)
2. Check access keys (may have been rotated):
   az storage account keys list --resource-group myresourcegroup --account-name myStorage
3. Update Key Vault with new access key if rotated
4. Restart API container to reload key
5. Test access:
   az storage blob list --account-name myStorage --container-name prescriptions
6. If storage corrupted:
   └─ Restore from geo-redundant backup (automatic)

Note: Azure automatically handles geo-redundancy, should be transparent
```

---

## 🔐 Security Incident Response

### **Audit Log Integrity Check Failed (Hash Mismatch)**

```
This is a CRITICAL security incident

Immediate Actions:
1. Isolate system (disconnect from external traffic)
2. Create full backup before any investigation
3. Log the detection:
   ├─ Which event hash failed
   ├─ Previous events affected
   └─ Estimated time of tampering
4. Check access logs (who had database access)
5. Alert management and legal team
6. Do NOT delete or modify audit logs

Investigation:
├─ Review database access logs
├─ Check for unauthorized logins
├─ Verify encryption key access
└─ Check system logs for suspicious activity

Recovery:
├─ Restore database from backup
├─ Verify new copy has integrity
├─ Identify compromise window
└─ Notify affected users if data breach confirmed

Prevention:
├─ Increase audit log integrity checks (hourly instead of daily)
├─ Review and restrict database access permissions
├─ Enable database activity monitoring
└─ Implement write-once storage for audit exports
```

### **Suspicious Login Attempts (Brute Force)**

```
Automatic Detection:
└─ More than 10 failed logins from same IP in 1 minute

Automatic Response:
├─ IP address temporarily blocked (24 hours)
├─ Alert sent to security team
└─ Incident logged in audit trail

Manual Investigation:
1. Check login patterns:
   SELECT event_type, actor_id, ip_address, COUNT(*) as attempts
   FROM audit_events
   WHERE event_type = 'FAILED_LOGIN' 
   GROUP BY ip_address, actor_id
   ORDER BY attempts DESC;

2. Identify source:
   ├─ Legitimate user (forgot password)?
   └─ Attacker?

3. Take action:
   ├─ If legitimate: whitelist IP, reset password
   ├─ If attacker: block IP, investigate for breaches
   └─ If distributed: implement CAPTCHA

4. Notify user:
   └─ Email: "Failed login attempts detected on your account"
```

---

## 📋 Operational Checklists

### **Weekly Operations Checklist**

```
Monday Morning:
☐ Check weekend errors in logs
☐ Review health dashboard
☐ Verify all health checks passing
☐ Check backup completion
☐ Review new audit log entries

Anytime (Weekly):
☐ Monitor database connections
☐ Review slow query logs
☐ Check disk space usage
☐ Verify encryption key access logs
☐ Review failed login attempts
☐ Check certificate expiration (notify if <30 days)
☐ Review any open incidents
```

### **Monthly Operations Checklist**

```
First of Month:
☐ Generate compliance report:
   ├─ Total prescriptions processed
   ├─ Total verifications (passed/failed)
   ├─ Data access by role
   ├─ Security incidents summary
   └─ Audit log integrity verified

Mid-Month:
☐ Database backup restoration test
☐ Disaster recovery drill (documentation update)
☐ Security assessment:
   ├─ Review access permissions
   ├─ Check for unused accounts
   └─ Verify encryption keys rotated within 90 days

End of Month:
☐ Performance review:
   ├─ API latency trends
   ├─ Database performance
   ├─ Storage usage growth
   └─ Error rate analysis
☐ Cost review (if using Azure)
☐ Plan for next month's operations
```

### **Quarterly Operations Checklist**

```
Every 3 Months:
☐ Full security audit:
   ├─ Review access logs
   ├─ Verify RBAC configuration
   ├─ Check TLS certificate status
   └─ Penetration test (or simulation)
☐ Encryption key rotation:
   ├─ Generate new keys
   ├─ Verify old key decryption working
   ├─ Test disaster recovery with old key
   └─ Document key rotation in audit trail
☐ Backup strategy review:
   ├─ Test full database restore
   ├─ Test file restoration from backup
   ├─ Verify audit log backup integrity
   └─ Update RPO/RTO if changed
☐ Compliance documentation update:
   ├─ DPA with vendors still valid
   ├─ Privacy policy reflects current practices
   ├─ Retention schedule documented
   └─ Incident response plan current
☐ Capacity planning:
   ├─ Database size trending
   ├─ Storage usage growth rate
   ├─ Predict when scaling needed
   └─ Plan scaling work
```

---

## 📞 Support Escalation

### **Common Issues and Solutions**

| Issue | Cause | Solution | On-Call? |
|-------|-------|----------|----------|
| Upload fails with timeout | QTSP slow | Increase timeout to 10s, check Dokobit | No |
| Download fails | Storage unreachable | Check blob storage status, verify keys | Yes |
| Login not working | OTP provider down | Check SMS provider status, manual override | Yes |
| Database slow | High connections | Check active queries, kill long-running | No |
| Disk full | Data growth | Increase storage quota, archive old data | Yes |
| Certificate expired | Rotation missed | Renew certificate, update Key Vault | Yes |
| Audit log mismatch | Tampering (rare) | Emergency protocol, isolate, restore backup | CRITICAL |

---

## Next Steps

For more details, see:
- [BACKUP_RECOVERY.md](./09_BACKUP_RECOVERY.md) — Backup and recovery procedures
- [SECURITY.md](./03_SECURITY.md) — Security implementation
- [TROUBLESHOOTING.md](./17_TROUBLESHOOTING.md) — Troubleshooting guide
