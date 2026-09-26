"""
seed_dining_staff.py
Idempotent provisioning of:
  1. MESS department + 3 food-quality categories
  2. One Dining Incharge user per residential hall (20 halls)

Run with:
    ./.venv/bin/python manage.py shell < seed_dining_staff.py
or:
    ./.venv/bin/python manage.py shell -c "exec(open('seed_dining_staff.py').read())"
"""

import sys, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")

import django
django.setup()

from django.contrib.auth.models import User
from core.models import Department, ComplaintCategory, Building, UserProfile

PASSWORD = "CampusAdmin@2026"

# ─── STEP 1: MESS department ─────────────────────────────────────────────────
mess_dept, created = Department.objects.update_or_create(
    code="MESS",
    defaults={
        "name": "Mess & Dining Services",
        "email": "mess.services@amu.ac.in",
        "phone": "+91-571-2700920",
        "is_active": True,
    },
)
print(f"{'[NEW]' if created else '[OK] '} Department: {mess_dept}")

# ─── STEP 2: Three categories under MESS ─────────────────────────────────────
CATEGORIES = [
    {
        "name": "Food Quality & Hygiene",
        "description": "Complaints about food quality, hygiene, contamination, insect/worm presence, or stale/undercooked meals.",
        "default_sla_hours": 4,
    },
    {
        "name": "Mess Timings & Quantity",
        "description": "Complaints about mess schedule violations, insufficient meal portions, or abrupt menu changes.",
        "default_sla_hours": 12,
    },
    {
        "name": "Water Cooler & Dining Hall Maintenance",
        "description": "Complaints about broken water coolers, unclean dining area, damaged furniture, or poor dining hall upkeep.",
        "default_sla_hours": 24,
    },
]

for cat_data in CATEGORIES:
    cat, created = ComplaintCategory.objects.update_or_create(
        name=cat_data["name"],
        defaults={
            "department": mess_dept,
            "description": cat_data["description"],
            "default_sla_hours": cat_data["default_sla_hours"],
            "is_active": True,
        },
    )
    print(f"{'[NEW]' if created else '[OK] '} Category: {cat.name}")

# ─── STEP 3: Dining Incharge per hall ────────────────────────────────────────
halls = Building.objects.filter(building_type__in=["hall", "residential"]).order_by("code")
print(f"\nProvisioning Dining Incharges for {halls.count()} halls …\n")

# Phone seed (placeholder numbers, unique per hall)
PHONE_BASE = 9897000000

created_count = updated_count = 0

for i, hall in enumerate(halls):
    code_lower = hall.code.lower()
    username = f"dining_{code_lower}"
    email = f"dining.{code_lower}@amu.ac.in"
    phone = f"+91-{str(PHONE_BASE + i)[:5]}-{str(PHONE_BASE + i)[5:]}"

    # Create / retrieve the Django User
    user, u_created = User.objects.get_or_create(
        username=username,
        defaults={
            "first_name": "Dining Incharge",
            "last_name": hall.name,
            "email": email,
            "is_active": True,
        },
    )
    if u_created:
        user.set_password(PASSWORD)
        user.save()
    else:
        # Ensure password is set correctly even for pre-existing accounts
        user.first_name = "Dining Incharge"
        user.last_name = hall.name
        user.email = email
        user.is_active = True
        user.set_password(PASSWORD)
        user.save(update_fields=["first_name", "last_name", "email", "is_active", "password"])

    # Create / update the UserProfile
    profile, p_created = UserProfile.objects.update_or_create(
        user=user,
        defaults={
            "role": UserProfile.Role.STAFF,
            "managed_building": hall,
            "managed_department": mess_dept,
            "department": mess_dept,
            "accountability_score": 100,
            "phone": phone,
            "hall_location": hall.name,
        },
    )

    status = "[NEW]" if u_created else "[OK] "
    print(f"  {status} {username:<22} → {hall.code} · {hall.name}")
    if u_created:
        created_count += 1
    else:
        updated_count += 1

print(f"\n✓ Done.  Created: {created_count}  |  Updated/Verified: {updated_count}")
print(f"✓ MESS department + {len(CATEGORIES)} categories ready.")
print(f"✓ All Dining Incharges accessible via /task/<staff_task_token>/")
