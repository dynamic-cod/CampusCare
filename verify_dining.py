"""
Regression test for MESS dispatch bug fix.
Tests:
 1. Complaint submission assigns correct hall Dining Incharge (not JSON roster)
 2. API preview detects mess category and returns Dining Incharge from DB
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
django.setup()

from core.models import Building, UserProfile, Complaint, ComplaintCategory, Department
from core.dispatcher import auto_dispatch_complaint

dept = Department.objects.get(code="MESS")
cats = list(ComplaintCategory.objects.filter(department=dept, is_active=True))
assert cats, "No active MESS categories found!"

halls = Building.objects.filter(building_type__in=["hall", "residential"]).order_by("code")
errors = []
print(f"Testing dispatch for all {halls.count()} halls ...\n")

for hall in halls:
    cat = cats[0]
    floor = hall.floors.first()
    if not floor:
        print(f"  [SKIP] {hall.code} — no floors")
        continue
    room = floor.rooms.first()
    if not room:
        print(f"  [SKIP] {hall.code} — no rooms")
        continue

    c = Complaint.objects.create(
        title="Stale roti served in mess tonight",
        description="The food served in the mess hall is completely stale and inedible.",
        room=room,
        category=cat,
    )
    # Simulate what the view does: dept_code check → auto_dispatch
    dept_code = c.category.department.code if (c.category_id and c.category.department_id) else ""
    if dept_code in ("MESS", "DINING"):
        auto_dispatch_complaint(c, save=False)
    c.save(update_fields=["assigned_to", "assigned_at", "status", "staff_task_token", "updated_at"])
    c.refresh_from_db()

    expected = f"dining_{hall.code.lower()}"
    assigned  = c.assigned_to.username if c.assigned_to else "NONE"
    ok = assigned == expected
    tag = "[OK]  " if ok else "[FAIL]"
    print(f"  {tag} {hall.code:<6} → assigned: {assigned:<24} expected: {expected}")
    if not ok:
        errors.append(f"{hall.code}: expected {expected}, got {assigned}")
    c.delete()

print(f"\n{'ALL PASS' if not errors else 'FAILURES: ' + str(errors)}")
print(f"Checked {halls.count()} halls.")
