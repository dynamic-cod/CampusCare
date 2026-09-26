# Admin-Only Restriction Testing Guide

## Test Accounts Available

### Admin Account (Full Access)
- **Username:** admin
- **Password:** admin123
- **Access Level:** Superuser (is_superuser=True)
- **Profile Role:** ADMIN
- **Permissions:** Can assign complaints and update status

### Staff Account (Limited Access)
- **Username:** staff_test
- **Password:** staff123
- **Access Level:** Staff but NOT Superuser (is_staff=True, is_superuser=False)
- **Profile Role:** STAFF
- **Permissions:** Cannot assign complaints or update status

## Testing Procedures

### Test 1: Admin Can Access Assignment and Status Forms

**Steps:**
1. Navigate to http://127.0.0.1:8001/accounts/login/
2. Login with admin credentials:
   - Username: `admin`
   - Password: `admin123`
3. Click "Complaints" in navigation
4. Click on any complaint (e.g., "Wifi not working" CC-414D023E)

**Expected Result - You Should See:**
```
🔐 Admin Management (Admin Only)

Note: Only administrators can assign complaints to staff and update status.

[Form with "Assign to maintenance staff" dropdown]
[Save assignment button]

---

[Form with "Status" dropdown, "Note" text field]
[Update status button]
```

**Verification:**
- ✅ Section has blue background (#f0f7ff)
- ✅ Padlock emoji 🔐 appears in title
- ✅ Both assignment and status forms are visible
- ✅ Buttons are clickable and functional

---

### Test 2: Staff Cannot Access Assignment and Status Forms

**Steps:**
1. Navigate to http://127.0.0.1:8001/accounts/logout/
2. Navigate to http://127.0.0.1:8001/accounts/login/
3. Login with staff credentials:
   - Username: `staff_test`
   - Password: `staff123`
4. Click "Complaints" in navigation
5. Click on any complaint (e.g., "Wifi not working" CC-414D023E)

**Expected Result - You Should See:**
```
⚠️ Staff Access Limited

Assignment and status updates are restricted to administrators only. 
Administrators use these tools to manage and track complaint resolution.

If you need to update a complaint, please contact an administrator.
```

**Verification:**
- ✅ Section has orange background (#fff3cd)
- ✅ Warning emoji ⚠️ appears in title
- ✅ No assignment form visible
- ✅ No status update form visible
- ✅ Clear message about administrator requirement

---

### Test 3: Staff Cannot Access Assignment Endpoint

**Steps:**
1. As staff user (staff_test), try to POST to the assignment endpoint

**Terminal Command:**
```bash
curl -X POST http://127.0.0.1:8001/complaints/CC-414D023E/assign/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Cookie: sessionid=<your_session_id>" \
  -d "assigned_to=<staff_user_id>"
```

**Expected Result:**
- ❌ Request rejected with 302 redirect
- ❌ Error message displayed: "This action is available to administrators only."
- ❌ Redirected back to complaint detail page

---

### Test 4: Staff Cannot Access Status Update Endpoint

**Steps:**
1. As staff user (staff_test), try to POST to the status endpoint

**Terminal Command:**
```bash
curl -X POST http://127.0.0.1:8001/complaints/CC-414D023E/status/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Cookie: sessionid=<your_session_id>" \
  -d "status=in_progress"
```

**Expected Result:**
- ❌ Request rejected with 302 redirect
- ❌ Error message displayed: "This action is available to administrators only."
- ❌ Status not updated in database

---

### Test 5: Admin Can Successfully Update Status

**Steps:**
1. Login as admin
2. Navigate to a complaint
3. In the "Admin Management" section, select a new status (e.g., "In progress")
4. Enter an optional note
5. Click "Update status"

**Expected Result:**
- ✅ Form submitted successfully
- ✅ Status history updated in database
- ✅ Page shows new status
- ✅ Timestamp and admin name recorded in history
- ✅ Success message appears

---

### Test 6: Admin Can Successfully Assign Staff

**Steps:**
1. Login as admin
2. Navigate to a complaint with status "Open"
3. In the "Admin Management" section, select a maintenance staff member from dropdown
4. Click "Save assignment"

**Expected Result:**
- ✅ Form submitted successfully
- ✅ Complaint assigned_to field updated
- ✅ Status changed from "Open" to "Assigned" (if it was "Open")
- ✅ Status history created with assignment note
- ✅ Success message appears

---

## Expected Database Changes After Admin Tests

After admin successfully assigns and updates status, verify in database:

```bash
python3 manage.py shell << 'EOF'
from core.models import Complaint, ComplaintStatusHistory
from django.contrib.auth.models import User

complaint = Complaint.objects.get(reference='CC-414D023E')
admin = User.objects.get(username='admin')

print(f"Complaint: {complaint.reference}")
print(f"  - Status: {complaint.status}")
print(f"  - Assigned to: {complaint.assigned_to}")
print(f"  - Assigned by: {complaint.assigned_by}")
print(f"  - Assigned at: {complaint.assigned_at}")

print(f"\nStatus History:")
for event in complaint.status_history.all().order_by('-created_at'):
    print(f"  - {event.status} by {event.changed_by.username if event.changed_by else 'N/A'} at {event.created_at}")
    if event.note:
        print(f"    Note: {event.note}")
EOF
```

---

## Security Verification Checklist

- ✅ Staff user cannot see assignment form
- ✅ Staff user cannot see status update form
- ✅ Staff user cannot POST to /complaints/<ref>/assign/
- ✅ Staff user cannot POST to /complaints/<ref>/status/
- ✅ Admin user can see both forms
- ✅ Admin user can successfully submit both forms
- ✅ Decorator properly checks is_superuser flag
- ✅ Error messages display to unauthorized users
- ✅ Redirects work correctly for unauthorized access attempts
- ✅ Database auditing captures who made changes

---

## UI Appearance Reference

### Admin View (Blue Section)
```
┌─────────────────────────────────────────────┐
│ 🔐 Admin Management (Admin Only)           │
│                                             │
│ Note: Only administrators can assign        │
│ complaints to staff and update status.      │
│                                             │
│ Assign to maintenance staff: [Dropdown]    │
│ [Save assignment]                          │
│                                             │
│ ─────────────────────────────────────────   │
│                                             │
│ Status: [Open ▼]                           │
│ Note: [Optional note...]                    │
│ [Update status]                             │
└─────────────────────────────────────────────┘
```
(Background: Light blue #f0f7ff, Left border: Blue)

### Staff View (Orange Alert Section)
```
┌─────────────────────────────────────────────┐
│ ⚠️ Staff Access Limited                     │
│                                             │
│ Assignment and status updates are          │
│ restricted to administrators only.         │
│ Administrators use these tools to manage   │
│ and track complaint resolution.            │
│                                             │
│ If you need to update a complaint,         │
│ please contact an administrator.           │
└─────────────────────────────────────────────┘
```
(Background: Light orange #fff3cd, Left border: Orange)

### Student View
- No admin management section visible
- Can still see complaint details, support button, verification forms if applicable

---

## Quick Reference: Changes Made

| Component | Change | Impact |
|-----------|--------|--------|
| `core/decorators.py` | Added `admin_only_required` decorator | New permission level: admin-only |
| `core/views.py` import | Added `admin_only_required` to imports | Decorator available for use |
| `complaint_assign()` | Changed decorator to `@admin_only_required` | Restricted to admins |
| `complaint_update_status()` | Changed decorator to `@admin_only_required` | Restricted to admins |
| `complaint_detail()` view context | Added `can_assign_and_update_status` flag | Template knows who can manage |
| `complaint_detail.html` template | Split `can_manage` into two sections | Admin vs Staff messages |

---

## Troubleshooting

### Issue: Staff user still sees admin forms
**Solution:** 
1. Clear browser cache (Cmd+Shift+R on Mac)
2. Logout and login again
3. Verify user's is_superuser is False in database

### Issue: Admin user gets access denied
**Solution:**
1. Verify admin user has is_superuser=True
2. Check that user is actually logged in
3. Verify Django session is valid

### Issue: Forms submit but nothing happens
**Solution:**
1. Check browser console for JavaScript errors
2. Check Django server logs for exceptions
3. Verify CSRF token is present in form

### Issue: Wrong error message displays
**Solution:**
1. Clear Django message storage
2. Check messages framework is enabled in MIDDLEWARE
3. Verify template displays messages correctly
