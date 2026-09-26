"""
seed_dining_staff.py  —  Idempotent provisioning for Dining Incharge feature.

Creates / updates:
  1. MESS department
  2. Four dining-specific ComplaintCategory rows
  3. One Dining Incharge user + UserProfile per residential hall

Run:
    ./.venv/bin/python manage.py shell -c "exec(open('seed_dining_staff.py').read())"
"""

import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
import django; django.setup()

from django.contrib.auth.models import User
from core.models import Department, ComplaintCategory, Building, UserProfile

PASSWORD = "CampusAdmin@2026"

# ─── STEP 1: MESS department ──────────────────────────────────────────────────
mess_dept, created = Department.objects.update_or_create(
    code="MESS",
    defaults={
        "name": "Dining & Mess Services",
        "email": "mess.services@amu.ac.in",
        "phone": "+91-571-2700920",
        "is_active": True,
    },
)
print(f"{'[NEW]' if created else '[OK] '} Department: {mess_dept}")

# ─── STEP 2: Four canonical categories ───────────────────────────────────────
CATEGORIES = [
    {
        "name": "Dining Hall Maintenance & Hygiene",
        "description": (
            "Cleanliness of dining tables, floor, handwash area, pest control, "
            "sanitation of serving counters and utensil areas."
        ),
        "default_sla_hours": 6,
    },
    {
        "name": "Food Quality & Preparation",
        "description": (
            "Undercooked food, tasteless diet, stale or spoiled meals, "
            "contamination, insect or foreign object in food."
        ),
        "default_sla_hours": 4,
    },
    {
        "name": "Mess Timings & Ration Supply",
        "description": (
            "Late serving, early shutdown, inadequate meal portions, token or "
            "diet-registration issues, sudden menu changes."
        ),
        "default_sla_hours": 8,
    },
    {
        "name": "Dining Hall Water & Utilities",
        "description": (
            "Broken or warm water coolers, geyser faults, utensil-washing area "
            "plumbing, general dining hall infrastructure failures."
        ),
        "default_sla_hours": 12,
    },
]

# Also deactivate the old names we created in the first pass so they don't clutter dropdowns
OLD_CAT_NAMES = [
    "Food Quality & Hygiene",
    "Mess Timings & Quantity",
    "Water Cooler & Dining Hall Maintenance",
]
deactivated = ComplaintCategory.objects.filter(department=mess_dept, name__in=OLD_CAT_NAMES).update(is_active=False)
if deactivated:
    print(f"[  ] Deactivated {deactivated} obsolete category name(s)")

for cat_data in CATEGORIES:
    cat, cat_created = ComplaintCategory.objects.update_or_create(
        name=cat_data["name"],
        defaults={
            "department": mess_dept,
            "description": cat_data["description"],
            "default_sla_hours": cat_data["default_sla_hours"],
            "is_active": True,
        },
    )
    print(f"{'[NEW]' if cat_created else '[OK] '} Category: {cat.name}  (SLA {cat.default_sla_hours}h)")

# ─── STEP 3: One Dining Incharge per residential hall ─────────────────────────
halls = Building.objects.filter(building_type__in=["hall", "residential"]).order_by("code")
print(f"\nProvisioning Dining Incharges for {halls.count()} halls …\n")

PHONE_BASE = 9897010000
created_count = updated_count = 0

for i, hall in enumerate(halls):
    code_lower = hall.code.lower()
    username   = f"dining_{code_lower}"
    email      = f"dining.{code_lower}@amu.ac.in"
    raw_phone  = str(PHONE_BASE + i)
    phone      = f"+91-{raw_phone[:5]}-{raw_phone[5:]}"

    user, u_created = User.objects.get_or_create(
        username=username,
        defaults={
            "first_name": "Dining Incharge",
            "last_name": hall.name[:100],
            "email": email,
            "is_active": True,
        },
    )
    if u_created:
        user.set_password(PASSWORD)
        user.save()
    else:
        user.first_name = "Dining Incharge"
        user.last_name  = hall.name[:100]
        user.email      = email
        user.is_active  = True
        user.set_password(PASSWORD)
        user.save(update_fields=["first_name", "last_name", "email", "is_active", "password"])

    UserProfile.objects.update_or_create(
        user=user,
        defaults={
            "role":               UserProfile.Role.STAFF,
            "managed_building":   hall,
            "managed_department": mess_dept,
            "department":         mess_dept,
            "accountability_score": 100,
            "phone":              phone,
            "hall_location":      hall.name,
        },
    )

    tag = "[NEW]" if u_created else "[OK] "
    print(f"  {tag} {username:<24} → {hall.code} · {hall.name}")
    if u_created:
        created_count += 1
    else:
        updated_count += 1

print(f"\n✓ Done.  Created: {created_count}  |  Updated/Verified: {updated_count}")
print(f"✓ MESS department + {len(CATEGORIES)} canonical dining categories ready.")
print(f"✓ All Dining Incharges accessible via /task/<staff_task_token>/")
