# User Management & Roles

## 👥 User Roles Overview

QES Flow has 6 distinct roles with different permissions:

```
┌─────────────────────┐
│  Platform Admin      │ (System administrator)
└──────────┬──────────┘
           │ manages
┌──────────┴──────────┐
│  Tenant Admin        │ (Organization administrator)
└──────────┬──────────┘
           │ manages
┌──┬──────┴──────┬─────┐
│  │              │     │
▼  ▼              ▼     ▼
Clinic Ph    Clinic Admin   Compliance Officer
```

---

## 🔐 Role Definitions

### **1. Platform Admin**

**Access Level:** Highest (Full system access)

**Responsibilities:**
```
User Management:
├─ Create/delete tenant admins
├─ Create/suspend any user (any clinic)
├─ Reset passwords
├─ Manage user roles globally
└─ View any user's data

System Configuration:
├─ Configure system settings
├─ Manage encryption keys
├─ Configure external integrations (QTSP, SMS)
├─ Manage Azure infrastructure settings
└─ Enable/disable features

Monitoring:
├─ View health dashboard
├─ View system logs
├─ View all audit logs
├─ Generate compliance reports
└─ Investigate incidents

Permissions Count: 30+
```

**Who Should Have This?**
```
Typically:
├─ CTO / Chief Information Officer
├─ Lead DevOps/Infrastructure engineer
└─ 1-2 senior technical staff maximum

NOT:
├─ Regular clinicians
├─ Administrative assistants
└─ Receptionists
```

**Risk Level:** 🔴 CRITICAL
```
Can:
├─ Access all patient data
├─ Revoke any user's access
├─ Change system settings
├─ Read all audit logs
└─ Delete data (in theory, not practice)

Mitigation:
├─ MFA required (phone + PIN)
├─ All access logged
├─ IP whitelisting recommended
├─ Quarterly access review
└─ Immediate suspension if compromised
```

---

### **2. Tenant Admin**

**Access Level:** High (Clinic-level administrator)

**Responsibilities:**
```
User Management:
├─ Create users (clinics, pharmacists, clinic admins)
├─ Suspend/reactivate users
├─ Reset user passwords
├─ Manage user roles (within organization)
└─ View user activity logs

Clinic Configuration:
├─ Update clinic settings
├─ Manage clinic users
├─ Configure clinic integrations
└─ View clinic's audit logs

Prescriptions:
├─ View all clinic prescriptions
├─ Export prescription data
├─ View verification status
└─ Generate compliance reports

Monitoring:
├─ View clinic health status
├─ View clinic-specific audit logs
├─ Review user access patterns
└─ Generate monthly reports

Permissions Count: 9+
```

**Who Should Have This?**
```
Typically:
├─ Clinic director / manager
├─ Practice manager
├─ IT manager at clinic
└─ Senior administrator (1-3 per clinic)

NOT:
├─ Frontline staff
├─ Receptionists
└─ Medical assistants (without training)
```

**Scope:** 
```
✅ Can see: All users and prescriptions in their clinic
❌ Cannot see: Other clinics' data
❌ Cannot see: System-wide settings
❌ Cannot create other tenant admins
```

**Risk Level:** 🟠 HIGH
```
Can:
├─ Suspend any user in organization (including clinics)
├─ View all prescriptions in organization
├─ Access all prescription data in organization
└─ Generate reports with sensitive info

Mitigation:
├─ MFA required
├─ All access logged
├─ Audit every suspension
└─ Quarterly permission review
```

---

### **3. Clinic**

**Access Level:** Medium (Clinic-level access)

**Responsibilities:**
```
Prescriptions:
├─ Upload prescriptions for clinic
├─ View clinic prescriptions
├─ Revoke clinic prescriptions
├─ View verification status
└─ See which pharmacies dispensed

Profile:
├─ Update clinic profile (phone)
├─ Change clinic PIN
├─ View clinic activity log
└─ Request data export

What Clinics CANNOT Do:
├─ Access other clinics' prescriptions
├─ Create users
├─ Suspend users
├─ View audit logs
├─ Access admin settings
└─ See other clinics' activity

Permissions Count: 6
```

**Who Has This Role:**
```
Clinic Users:
├─ Clinic representatives
├─ Authorized clinic staff
├─ Clinic administrators at user level
└─ Clinic coordinators
```

**Scope:**
```
✅ Can see: Own clinic prescriptions only
❌ Cannot see: Other clinics' prescriptions
❌ Cannot view audit logs
❌ Cannot view system settings
```

**Risk Level:** 🟡 MEDIUM
```
Can:
├─ Upload prescriptions
├─ Revoke prescriptions (undo sent prescription)
└─ View own clinic activity

Cannot:
├─ Access other clinics' data
├─ Delete data
└─ View system settings

Mitigation:
├─ MFA required
├─ All prescriptions verified by QTSP
└─ All actions logged
```

---

### **4. Pharmacist**

**Access Level:** Medium (Dispensing-level access)

**Responsibilities:**
```
Prescriptions:
├─ View assigned prescriptions
├─ Download prescriptions
├─ Confirm dispensing
├─ View verification status
└─ See prescription evidence

What Pharmacists CANNOT Do:
├─ Modify prescriptions
├─ Access other pharmacists' assignments
├─ View doctor information (except on prescription)
├─ Access system settings
└─ View audit logs

Permissions Count: 8
```

**Who Has This Role:**
```
Pharmacy Staff:
├─ Registered pharmacists
├─ Pharmacy technicians (may be limited)
└─ Pharmacy managers
```

**Scope:**
```
✅ Can see: Prescriptions assigned to their pharmacy
✅ Can download: After verifying is valid
❌ Cannot see: Prescriptions for other pharmacies
❌ Cannot modify: Prescription details
❌ Cannot delete: Anything
```

**Risk Level:** 🟡 MEDIUM
```
Can:
├─ Download prescription PDFs
├─ Confirm dispensing
└─ See patient names + medications

Cannot:
├─ Modify prescriptions
├─ Delete evidence
├─ View system settings

Mitigation:
├─ MFA required
├─ Download limited to assigned pharmacy
├─ All actions logged
└─ Dispensing cannot be undone (immutable)
```

---

### **5. Clinic Admin**

**Access Level:** Low-Medium (Administrative access within clinic)

**Responsibilities:**
```
Users:
├─ View clinic users
├─ Cannot create users (tenant admin does)
├─ Cannot suspend users (tenant admin does)
└─ View user status

Prescriptions:
├─ View all clinic prescriptions
├─ View verification status
├─ Cannot modify or delete
└─ Cannot dispense

Reports:
├─ View activity reports
├─ View dispensing reports
├─ Generate usage statistics
└─ Export for compliance

Permissions Count: 6
```

**Who Has This Role:**
```
Administrative Staff:
├─ Office managers
├─ Administrative coordinators
├─ Receptionists (senior)
└─ Clinic secretaries
```

**Scope:**
```
✅ Can see: All clinic users and prescriptions
✅ Can read: View-only access
❌ Cannot modify: Anything
❌ Cannot delete: Anything
❌ Cannot create users: (tenant admin only)
```

**Risk Level:** 🟢 LOW
```
Can:
├─ View prescription data
└─ View user list

Cannot:
├─ Modify or delete anything
├─ Create/suspend users
└─ Access system settings

Mitigation:
├─ MFA required
├─ Read-only permissions
└─ All access logged
```

---

### **6. Compliance Officer**

**Access Level:** High (Compliance and audit)

**Responsibilities:**
```
Audit Trail:
├─ View all audit logs (system-wide)
├─ Search audit logs by date/user/event
├─ Export audit logs (JSON format)
├─ Verify audit log integrity (hash-chain)
└─ Investigate suspected tampering

Compliance:
├─ Generate monthly compliance reports
├─ Generate GDPR access reports
├─ Generate security incident reports
├─ Verify encryption key rotations
└─ Review data protection measures

Prescriptions:
├─ View all prescriptions (all clinics)
├─ View verification evidence
├─ View dispensing records
├─ Extract data for audits
└─ Cannot modify or delete

Permissions Count: 18+
```

**Who Should Have This?**
```
Compliance Team:
├─ Data Protection Officer (DPO)
├─ Compliance manager
├─ Legal / regulatory affairs
├─ Internal audit team
└─ External auditors (temporary)
```

**Scope:**
```
✅ Can see: All audit logs (all clinics)
✅ Can read: All prescriptions (all clinics)
✅ Can access: All verification evidence
❌ Cannot modify: Anything
❌ Cannot delete: Anything
❌ Cannot access: System settings
```

**Risk Level:** 🟠 HIGH
```
Can:
├─ View all patient data (for compliance)
├─ Export audit logs
├─ Search full history
└─ See who accessed what

Cannot:
├─ Modify or delete data
├─ Create/suspend users
└─ Access system settings

Mitigation:
├─ MFA required
├─ Access limited to read-only
├─ All exports logged
├─ Quarterly access review
└─ Background check recommended
```

---

## 📋 Permission Matrix

```
                    Platform  Tenant   Clinic  Compliance
                    Admin     Admin    Admin   Officer
────────────────────────────────────────────────────────
PRESCRIPTION_UPLOAD    ✅        ✅       ❌       ❌
PRESCRIPTION_DOWNLOAD  ✅        ✅       ❌       ✅ (read)
PRESCRIPTION_REVOKE    ✅        ✅       ❌       ❌
PRESCRIPTION_DISPENSE  ❌        ❌       ❌       ❌

USER_CREATE            ✅        ✅       ❌       ❌
USER_SUSPEND           ✅        ✅       ❌       ❌
USER_VIEW              ✅        ✅       ✅       ✅ (read)
USER_EDIT              ✅        ✅       ❌       ❌

AUDIT_VIEW_OWN         ✅        ✅       ✅       ✅
AUDIT_VIEW_ALL         ✅        ✅       ❌       ✅
AUDIT_EXPORT           ✅        ✅       ❌       ✅
AUDIT_VERIFY           ✅        ✅       ❌       ✅

CONFIG_VIEW            ✅        ✅       ❌       ❌
CONFIG_MODIFY          ✅        ✅       ❌       ❌

DATA_EXPORT            ✅        ✅       ❌       ✅
DATA_DELETE            ✅        ✅       ❌       ❌
```

---

## 👤 User Lifecycle

### **1. User Creation**

```
Process:
1. Tenant Admin (or Platform Admin) goes to "Manage Users"
2. Click "Create New User"
3. Enter:
   ├─ Phone number
   ├─ Role (Clinic, Pharmacist, Admin)
   ├─ License number (if pharmacist)
   └─ Clinic assignment
4. Click "Create"

System:
├─ Validate email not already used
├─ Create database record with status: pending_activation
├─ Send activation email to user
├─ Create audit log: USER_CREATED
└─ Notify creator

User Receives Email:
├─ Welcome message
├─ Login instructions
├─ Set PIN link
└─ Temporary password

User Setup:
1. Click link in email
2. Set PIN (4 digits, secret)
3. Account activated
4. Can now login
```

### **2. User Login**

```
First Login:
1. User opens portal
2. Enters phone number
3. Receives OTP via SMS
4. Enters OTP
5. Enters PIN
6. Logged in successfully

Subsequent Logins:
├─ Same process (phone + OTP + PIN)
├─ No "remember me" option (security)
├─ Session expires after 8 hours
└─ Must login again

Session Management:
├─ JWT token issued
├─ Stored in secure cookie (HttpOnly)
├─ Expires in 8 hours
├─ Can refresh with refresh token (24h validity)
└─ Logout invalidates tokens
```

### **3. User Suspension**

```
When to Suspend:
├─ License expired
├─ Employee left organization
├─ Security incident
├─ Performance issues
├─ Investigation needed
└─ GDPR deletion request

Who Can Suspend:
├─ Platform Admin (any user)
├─ Tenant Admin (users in their clinic)
└─ NOT: Clinic Admin or Doctor

Process:
1. Admin goes to "Manage Users"
2. Finds user (e.g., Clinic A)
3. Clicks "Suspend"
4. Enters reason (required)
5. Confirms suspension

System:
├─ Update user status: suspended
├─ Invalidate all active sessions
├─ Log who suspended and when
├─ Prevent login attempts
├─ Audit log entry: USER_SUSPENDED
└─ Notify supervisor (optional)

Suspended User Tries to Login:
├─ Phone OTP works (proves ownership)
├─ PIN entry works
├─ Final auth fails: "Account suspended"
├─ User sees reason (if set)
└─ Suggestion to contact admin

Data Access:
├─ Can still view own data (GDPR)
├─ Cannot create/modify anything
├─ Cannot upload/download
└─ Audit logs still searchable
```

### **4. User Reactivation**

```
When Reactivating:
├─ License renewed
├─ Employee rehired
├─ Investigation concluded
├─ Mistake (wrong person suspended)

Process:
1. Tenant Admin goes to "Manage Users"
2. Finds suspended user
3. Clicks "Reactivate"
4. Confirms reactivation
5. Notifies user (optional)

System:
├─ Update user status: active
├─ Sessions still invalid (security)
├─ User must login normally
├─ Audit log entry: USER_REACTIVATED
└─ User can now use system

Reactivated User:
├─ Logs in normally (OTP + PIN)
├─ Sees previous data (unchanged)
└─ Permissions restored
```

### **5. User Deletion (GDPR)**

```
User Requests Deletion:
├─ Submits GDPR deletion request
├─ 30-day fulfillment period starts

System Response:
├─ Personal data deleted:
│  ├─ Phone number
│  ├─ Email
│  ├─ User preferences
│  └─ Login history
├─ Prescriptions NOT deleted:
│  ├─ Healthcare record retention (7 years)
│  ├─ Legal obligation
│  └─ Soft-delete (marked, not removed)
├─ Audit trail NOT deleted:
│  ├─ Compliance requirement
│  └─ Hash-chaining prevents deletion anyway
└─ Evidence retained (signature, timestamp)

After Deletion:
├─ User cannot login (account deleted)
├─ Their prescriptions still visible (with anonymized creator)
├─ Audit logs show "deleted_user_123"
└─ Deletion request logged (recursive audit!)
```

---

## 🔐 Security Best Practices for Admins

### **For Platform Admins:**

```
✅ DO:
├─ Use very strong PIN (4+ unique digits)
├─ Never write down PIN or credentials
├─ Rotate PIN every 90 days
├─ Check login activity logs monthly
├─ Limit access time to off-hours if possible
├─ Use whitelisted IP if possible
├─ Immediately report suspicious activity
└─ Retire credentials when leaving role

❌ DON'T:
├─ Share admin credentials with anyone
├─ Login from public WiFi
├─ Use same PIN as personal accounts
├─ Leave computer unattended while logged in
├─ Suspend/delete users without documentation
├─ Give multiple people same admin account
└─ Perform dangerous ops without review
```

### **For Tenant Admins:**

```
✅ DO:
├─ Review monthly who has which roles
├─ Suspend users immediately upon termination
├─ Verify clinic credentials
├─ Update user permissions when roles change
├─ Document all user changes
├─ Review audit logs for suspicious activity
└─ Keep strong PIN

❌ DON'T:
├─ Defer suspending users who left
├─ Give multiple people admin account
├─ Make someone admin if not necessary
├─ Forget to change credentials in shared areas
└─ Share credentials
```

---

## 📊 Audit Trail - User Management

Every user action is logged:

```
Example Audit Log:

Event: USER_CREATED
├─ Created by: admin-abc123
├─ Timestamp: 2026-04-13T10:00:00Z
├─ New user: clinic-def456
├─ Role: clinic
└─ Organization: org-xyz789

Event: USER_SUSPENDED
├─ Suspended by: admin-abc123
├─ Timestamp: 2026-04-13T14:30:00Z
├─ Suspended user: clinic-def456
├─ Reason: Temporary closure (doc ref: #2026-04-15)
└─ Effective: immediate

Event: USER_REACTIVATED
├─ Reactivated by: admin-abc123
├─ Timestamp: 2026-04-20T09:00:00Z
├─ Reactivated user: clinic-def456
├─ Reason: Reopening verified
└─ Effective: immediate
```

---

## 📋 User Management Checklist

Before going to production:

- [ ] Roles defined and documented
- [ ] Permission matrix created
- [ ] MFA working for all users
- [ ] Password reset process defined
- [ ] User suspension procedure documented
- [ ] Audit logging for all user actions
- [ ] Access review process established
- [ ] Admin account security hardened
- [ ] GDPR deletion procedure tested
- [ ] Training provided to admins
- [ ] Incident response plan includes user management

---

## Next Steps

For more details, see:
- [SECURITY.md](./03_SECURITY.md) — Security controls
- [GDPR_COMPLIANCE.md](./04_GDPR_COMPLIANCE.md) — GDPR rights
- [AUDIT_TRAIL.md](./06_AUDIT_TRAIL.md) — Audit logging
