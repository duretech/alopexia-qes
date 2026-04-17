# Troubleshooting Guide

## 🆘 Common Issues & Solutions

---

## 📱 Login Issues

### **Issue: "OTP not received"**

**Symptoms:**
- User clicks "Send OTP" but SMS doesn't arrive
- After 10 minutes, still no message

**Causes:**
```
Most Likely:
├─ Phone number incorrect (typo)
├─ SMS service temporarily down
└─ Network issue (no cell signal)

Less Likely:
├─ Phone blocked SMS from provider
├─ Country not supported
└─ SMS provider quota exceeded
```

**Solutions:**

1. **Check phone number:**
   - Verify number is correct
   - Use international format: +44-20-1234-5678
   - Check for extra spaces

2. **Try again:**
   - Wait 2 minutes
   - Click "Send OTP" again
   - SMS sometimes delayed

3. **Check network:**
   - Ensure good cell signal
   - Try different network (WiFi → cellular)
   - Restart phone

4. **Contact support:**
   - If still no SMS after 5 minutes
   - Email: support@qesflow.com
   - Include: Phone number (last 4 digits only), timestamp

**Prevention:**
- Add QES Flow phone to contacts
- Ask SMS provider to whitelist Twilio
- Test login weekly

---

### **Issue: "PIN is incorrect" (but I'm sure it's right)**

**Symptoms:**
- Entering PIN multiple times
- Says "incorrect" but PIN hasn't changed

**Causes:**
```
Most Likely:
├─ Typo (number looks right but isn't)
├─ Different PIN than you think
└─ Caps lock on (if app were password)

Less Likely:
├─ PIN expired (no, PINs don't expire)
└─ Account suspended
```

**Solutions:**

1. **Double-check PIN:**
   - Look at keyboard: Is 4 correct?
   - Count digits: Is it 4 digits?
   - Try again slowly

2. **Reset PIN:**
   - Contact clinic admin
   - Verify your identity
   - Admin will reset PIN
   - You'll get reset link via email
   - Set new PIN
   - Try again

3. **Account suspended?**
   - If message says "Account suspended"
   - Contact clinic admin
   - Ask for reactivation

---

### **Issue: "Session expired" after 8 hours**

**Symptoms:**
- Working fine
- After 8 hours, redirected to login

**This is expected behavior:**
```
Security Feature:
├─ Sessions expire after 8 hours
├─ Prevents unauthorized access if device stolen
├─ Refresh token extends for 24 hours
└─ Not a bug, it's a feature
```

**Solution:**
- Simply login again
- Choose "Remember me" (not offered - security)
- Just re-authenticate

---

## 📤 Upload Issues

### **Issue: "File rejected - invalid PDF"**

**Symptoms:**
- Select PDF file
- Get error: "Invalid file type"
- But file IS a PDF

**Causes:**
```
Likely:
├─ File is actually not PDF (wrong extension)
├─ PDF is corrupted (not readable)
└─ PDF too large (>50MB)

Less Likely:
├─ Browser issue
└─ Upload service down
```

**Solutions:**

1. **Check file size:**
   - Right-click file
   - Check size
   - If >50MB: system cannot accept
   - Reduce or split file

2. **Verify file type:**
   - Open file with PDF reader
   - Does it open correctly?
   - If not: not a valid PDF

3. **Check file name:**
   - Ensure ends with .pdf
   - If .PDF (caps): might matter
   - Try renaming

4. **Re-save PDF:**
   - Open in PDF editor
   - Export/Save as PDF
   - Try uploading again

5. **Try different browser:**
   - Chrome, Firefox, Safari
   - Sometimes browser issue

---

### **Issue: "Malware detected" error**

**Symptoms:**
- Upload rejected
- Error: "File infected with [virus name]"
- File claims to be clean

**Causes:**
```
Likely:
├─ Actual infection (download from unsafe source)
├─ False positive (ClamAV sometimes flags safe files)
└─ PDF contains suspicious code

Less Likely:
├─ ClamAV misconfigured
└─ Virus definitions outdated
```

**Solutions:**

1. **Check if file is clean:**
   - Scan with local antivirus
   - Use VirusTotal.com (multiple engines)
   - If clean: likely false positive

2. **If false positive:**
   - Contact support: security@qesflow.com
   - Include: filename, file hash
   - Our team can investigate
   - If approved: we whitelist

3. **If actually infected:**
   - Do NOT upload
   - Clean file on clinic's computer
   - Use antivirus to remove malware
   - Re-save/export PDF
   - Then upload

4. **Workaround (if urgent):**
   - Contact your clinic admin
   - Request manual upload (with verification)
   - Will be flagged in audit trail

**Prevention:**
- Only download from trusted sources
- Run antivirus before uploading
- Use ClamAV locally to test

---

### **Issue: Upload hangs or times out**

**Symptoms:**
- Click upload
- Progress bar stops
- After 30+ seconds, error or timeout

**Causes:**
```
Likely:
├─ Slow internet (< 1 Mbps)
├─ Large file (>20MB)
├─ Server temporarily slow
└─ Dokobit verification slow

Less Likely:
├─ Browser cache issue
└─ Network interruption
```

**Solutions:**

1. **Check internet speed:**
   - Use speedtest.net
   - Should be >5 Mbps upload
   - If <1 Mbps: upgrade connection

2. **Check file size:**
   - Right-click, check size
   - Ideal: <10MB
   - Max: 50MB
   - If >20MB: takes longer

3. **Close other apps:**
   - Music streaming (uses bandwidth)
   - Video calls (uses bandwidth)
   - Close them, try again

4. **Try different network:**
   - WiFi → mobile hotspot
   - Mobile → WiFi
   - Determine if network-specific

5. **Try later:**
   - Server might be busy
   - Try off-peak hours
   - Early morning is usually faster

---

## ✅ Verification Issues

### **Issue: "Signature verification failed"**

**Symptoms:**
- Upload successful
- Status shows: "Failed" or "Invalid"
- Cannot proceed to pharmacy

**Causes:**
```
Clinic's Certificate:
├─ Expired (past valid date)
├─ Revoked (license issue)
├─ Not trusted (wrong issuer)
└─ Invalid (corrupted)

PDF Signature:
├─ Not signed (clinic forgot)
├─ Corrupted (file damaged)
├─ Tampered with (file modified after signing)
└─ Wrong format
```

**Solutions:**

1. **Tell clinic to check certificate:**
   - Certificate expiration date (past?)
   - Contact certificate issuer if expired
   - Request new certificate
   - Install new certificate

2. **Check signature process:**
   - Is doctor using proper signature tool?
   - Example: Adobe, Acrobat, DocuSign
   - Does tool support XAdES signatures?

3. **Verify PDF:**
   - Clinic: re-sign PDF before upload
   - Don't modify PDF after signing
   - Upload freshly signed version

4. **Contact support:**
   - If still fails after re-signing
   - Email: support@qesflow.com
   - Include: Doctor name, clinic, timestamp
   - Attach: Failed PDF (encrypted acceptable)

5. **Workaround:**
   - Doctor may re-sign with updated cert
   - Request new signature tool if needed
   - Dokobit support: support@dokobit.com

---

### **Issue: "Verification in progress" (forever)**

**Symptoms:**
- Uploaded 2+ hours ago
- Status still shows: "pending"
- Should be verified by now

**Causes:**
```
System Issue:
├─ Dokobit service down
├─ Network connectivity issue
├─ Background job failed
└─ Database error

File Issue:
├─ Signature corrupt
├─ Certificate revoked
└─ Certificate expired
```

**Solutions:**

1. **Check status page:**
   - status.dokobit.com
   - status.qesflow.com
   - Is Dokobit down?

2. **Refresh browser:**
   - F5 or Cmd+R
   - Status might have updated

3. **Contact support:**
   - Provide: Prescription ID
   - Timestamp of upload
   - Clinic name
   - Email: support@qesflow.com

4. **Workaround:**
   - Upload again (new idempotency key)
   - System will process both
   - Use one, ignore duplicate

---

## 📥 Download Issues

### **Issue: "Permission denied" when downloading**

**Symptoms:**
- Pharmacist tries to download
- Error: "You don't have permission"
- But should be assigned to clinic

**Causes:**
```
Likely:
├─ Pharmacist not assigned to clinic
├─ Prescription for different clinic
├─ Role doesn't have permission
└─ Account suspended

Less Likely:
├─ Database inconsistency
└─ System error
```

**Solutions:**

1. **Check assignment:**
   - Clinic admin: go to user management
   - Verify pharmacist is in correct clinic
   - If not: assign to clinic

2. **Verify clinic:**
   - Check prescription clinic matches
   - Clinic A, Pharmacist in Clinic A? ✅
   - Clinic A, Pharmacist in Clinic B? ❌

3. **Check account status:**
   - Is your account active?
   - If suspended: admin must reactivate
   - Contact clinic admin

4. **Check role:**
   - Are you a pharmacist (not assistant)?
   - Do you have DOCUMENT_DOWNLOAD permission?
   - Contact admin if not

---

### **Issue: "Download link expired"**

**Symptoms:**
- Click download
- Error: "Link expired" or "Access denied"

**This is expected:**
```
Security Feature:
├─ Download links valid for 5 minutes
├─ Prevents sharing permanent links
├─ Forces re-authentication each time
└─ Not a bug, it's a feature
```

**Solution:**
- Simply download again
- Click link immediately (don't wait)
- Download will complete

**Why expire?**
- If link leaked: only valid 5 min
- Cannot be shared (would be expired)
- Forces audit trail per download
- Increases security

---

## 🔐 Security & Account Issues

### **Issue: "Suspicious activity" - account locked**

**Symptoms:**
- Try to login
- Error: "Account locked due to suspicious activity"

**Causes:**
```
Likely:
├─ Failed login attempts from new location
├─ Multiple failed OTP codes
├─ Unusual time of day
└─ Different device/browser
```

**Solutions:**

1. **Contact clinic admin:**
   - Explain where you are
   - Verify your identity (something only you know)
   - Admin will unlock

2. **Next time:**
   - Expect 2FA (it's normal)
   - Try again, it might auto-unlock
   - Change PIN if needed

---

### **Issue: "Audit log integrity check failed"**

**Symptoms (Compliance Officers):**
- Trying to export audit logs
- Error: "Hash chain mismatch at event 1234"
- System blocks export

**This is SERIOUS - do NOT ignore:**

**What it means:**
```
Something Tampered With Audit Trail:
├─ Someone tried to change an event
├─ Or system/database corrupted
├─ Or hash calculation error
└─ All bad scenarios
```

**Immediate Actions:**

1. **Do NOT:**
   - Modify anything
   - Restart system
   - Delete database
   - Continue normal operations

2. **IMMEDIATELY:**
   - Contact: security@qesflow.com
   - Call on-call engineer (phone in portal)
   - Document everything
   - Take screenshots

3. **Preserve Evidence:**
   - Export logs if possible
   - Backup database
   - Note exact error
   - Save system logs

4. **Investigation:**
   - Is this a real breach?
   - Or database corruption?
   - Or hash calculation bug?
   - Determine root cause

5. **Recovery:**
   - May need to restore from backup
   - Investigate who had access
   - Legal notification (if breach)
   - Document incident

---

## 💾 Data & Export Issues

### **Issue: "Data export failed" or "Export incomplete"**

**Symptoms:**
- Request data export
- After 30 seconds: error
- Or export file is tiny (not all data)

**Causes:**
```
Likely:
├─ Too much data (large date range)
├─ System memory issue
├─ Network interrupted
└─ Database slow

Less Likely:
├─ Bug in export code
└─ Database error
```

**Solutions:**

1. **Try smaller date range:**
   - Instead of: 1 year
   - Try: 1 month
   - Export multiple chunks

2. **Try off-peak:**
   - Night time or early morning
   - System less busy
   - Faster processing

3. **Use API directly:**
   - If available in your role
   - POST /api/v1/audit/export
   - More control over parameters

4. **Contact support:**
   - If export fails consistently
   - Provide: User ID, date range, error
   - Email: support@qesflow.com

---

## 🌐 Connectivity & Performance

### **Issue: Site is very slow**

**Symptoms:**
- Buttons take 5+ seconds to respond
- Uploads times out
- General lag

**Causes:**
```
Your Network:
├─ Slow internet (<1 Mbps)
├─ High latency (>200ms ping)
└─ Too many devices on network

System Side:
├─ High server load
├─ Database slow
├─ QTSP slow
└─ Network between regions

Browser:
├─ Too many tabs
├─ Extensions causing issues
└─ Cache full
```

**Solutions:**

1. **Test your connection:**
   - speedtest.net
   - Should be: >5 Mbps down, >2 Mbps up
   - If slower: contact ISP

2. **Close unnecessary apps:**
   - Close downloads
   - Close video calls
   - Close streaming
   - Try again

3. **Try different browser:**
   - Chrome vs Firefox vs Safari
   - Extension issues?
   - Try private/incognito mode

4. **Check system status:**
   - status.qesflow.com
   - Is system degraded?
   - When will it recover?

5. **Try different time:**
   - Off-peak hours: 2-6 AM
   - Weekends sometimes slower
   - Try early morning

6. **Contact support:**
   - If persistent issue
   - Provide: Network test results
   - Email: support@qesflow.com

---

## 📞 Still Need Help?

If issue not listed:

1. **Check:**
   - [FAQ.md](./16_FAQ.md) — Common questions
   - [SUPPORT.md](./18_SUPPORT.md) — How to contact support

2. **Contact Support:**
   - Email: support@qesflow.com
   - Phone: [clinic phone number]
   - Include:
     - Your name and clinic
     - What you were trying to do
     - Exact error message
     - Screenshots
     - When it started
     - How often it happens

3. **For Emergencies:**
   - Call on-call engineer (24/7)
   - Number in your clinic's emergency contacts
   - For: System down or security issue

---

## Next Steps

For more details, see:
- [FAQ.md](./16_FAQ.md) — Frequently asked questions
- [SUPPORT.md](./18_SUPPORT.md) — Support procedures
- [OPERATIONS.md](./08_OPERATIONS.md) — System operations
