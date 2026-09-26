# Admin-Only Restriction Implementation

## Summary
Restricted assignment and status update operations to administrators only, preventing regular staff from modifying these sensitive complaint properties.

## Changes Made

### 1. **core/decorators.py** - New Decorator
Added `admin_only_required` decorator to enforce admin-only access:

```python
def admin_only_required(view_func):
    """Restrict sensitive operations to administrators only."""

    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        messages.error(request, "This action is available to administrators only.")
        return redirect("core:complaint_detail", reference=kwargs.get("reference", ""))

    return wrapped
```

**Key Points:**
- Checks `request.user.is_superuser` (Django admin superuser flag)
- Displays user-friendly error message
- Redirects to complaint detail page (or dashboard if no reference)
- Uses `@login_required` to ensure user is authenticated first

### 2. **core/views.py** - Apply Admin-Only Decorator

#### Import Addition
```python
from .decorators import staff_or_admin_required, admin_only_required
```

#### complaint_assign() - Line 239
**Before:** `@staff_or_admin_required`
**After:** `@admin_only_required`

Only administrators can assign complaints to maintenance staff.

#### complaint_update_status() - Line 262
**Before:** `@staff_or_admin_required`
**After:** `@admin_only_required`

Only administrators can update complaint status.

#### complaint_detail() - Line 166
Added new context variable:
```python
can_assign_and_update_status = request.user.is_superuser
```

Changed form rendering logic:
```python
# Before
"assignment_form": ComplaintAssignmentForm(instance=complaint) if can_manage else None,
"status_form": ComplaintStatusForm(initial={"status": complaint.status}) if can_manage else None,

# After
"assignment_form": ComplaintAssignmentForm(instance=complaint) if can_assign_and_update_status else None,
"status_form": ComplaintStatusForm(initial={"status": complaint.status}) if can_assign_and_update_status else None,
```

### 3. **templates/core/complaint_detail.html** - Template Updates

#### Management Section Redesign
**Before:**
```django
{% if can_manage %}
  <section class="card" style="margin-top:1.5rem">
    <h2>Manage complaint</h2>
    <!-- Forms for assignment and status -->
  </section>
{% endif %}
```

**After:**
```django
{% if can_assign_and_update_status %}
  <section class="card" style="margin-top:1.5rem; background-color: #f0f7ff; border-left: 4px solid #2196F3;">
    <h2>🔐 Admin Management (Admin Only)</h2>
    <p><strong>Note:</strong> Only administrators can assign complaints to staff and update status.</p>
    <!-- Forms for assignment and status -->
  </section>
{% elif can_manage %}
  <section class="card" style="margin-top:1.5rem; background-color: #fff3cd; border-left: 4px solid #FF9800;">
    <h2>⚠️ Staff Access Limited</h2>
    <p><strong>Assignment and status updates are restricted to administrators only.</strong> Administrators use these tools to manage and track complaint resolution.</p>
    <p>If you need to update a complaint, please contact an administrator.</p>
  </section>
{% endif %}
```

**Key Features:**
- Admin sees: Blue section with 🔐 icon and management forms
- Staff sees: Orange alert explaining why they can't access these features
- Students see: Nothing (neither section appears)

## User Experience Changes

### For Administrators
✅ Can view and use assignment and status update forms
✅ Forms are clearly labeled as "Admin Only"
✅ Blue color scheme indicates privileged operations
✅ Clear note: "Only administrators can assign complaints to staff and update status"

### For Maintenance Staff
⚠️ Cannot access assignment or status update forms (views reject with error message)
⚠️ On complaint detail page, see orange alert explaining the restriction
⚠️ Can still view complaints and provide feedback
⚠️ Encouraged to contact an administrator if they need to update

### For Students
✅ No change - still cannot see admin management sections
✅ Can report, support, verify, and reopen complaints

## Security Benefits

1. **Reduced Risk of Unauthorized Modifications**: Only superusers can change complaint status
2. **Clear Audit Trail**: All status changes are tracked with the admin who made the change
3. **Prevents Accidental Updates**: Staff cannot accidentally modify complaint state
4. **Better Access Control**: Separate decorators for different permission levels

## Testing Recommendations

### Test 1: Admin Access
1. Login as admin (username: admin, password: admin123)
2. Navigate to any complaint
3. ✅ Should see "🔐 Admin Management (Admin Only)" section with blue background
4. ✅ Should see assignment and status forms
5. ✅ Should be able to save changes

### Test 2: Staff Access (Create Staff User)
1. Create a new staff user in Django admin
2. Make user is_staff=True but NOT superuser
3. Login as staff user
4. Navigate to any complaint
5. ✅ Should see "⚠️ Staff Access Limited" orange alert
6. ✅ Should NOT see assignment/status forms
7. Try to POST to /complaints/<ref>/assign/ or /complaints/<ref>/status/
8. ✅ Should see error message and redirect to complaint detail

### Test 3: Student Access
1. Login as regular student
2. Navigate to any public complaint
3. ✅ Should NOT see any admin management section
4. ✅ Can still see support button and verification forms (if applicable)

## Rollback Instructions

If needed, revert to staff_or_admin_required:

1. **core/decorators.py**: Delete the `admin_only_required` function
2. **core/views.py**: 
   - Change `@admin_only_required` back to `@staff_or_admin_required` on complaint_assign() and complaint_update_status()
   - Change `can_assign_and_update_status = request.user.is_superuser` to use `can_manage`
3. **templates/core/complaint_detail.html**: Restore the single `{% if can_manage %}` section

## Database Impact
None - No migrations required. This is a pure authorization layer change.

## Performance Impact
Minimal - One additional superuser check per admin detail page view.
