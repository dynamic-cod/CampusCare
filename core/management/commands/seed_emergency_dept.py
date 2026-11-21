"""
Management command: seed_emergency_dept
Seeds the EMERG department, its 4 life-safety categories, and 6 emergency staff.
Fully idempotent — safe to run repeatedly.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from core.models import Building, ComplaintCategory, Department, UserProfile

User = get_user_model()

EMERG_STAFF_PASSWORD = "CampusStaff@2026"


EMERG_CATEGORIES = [
    {
        "name": "Snake / Reptile Sighting",
        "description": "Live snake, lizard, or reptile spotted inside hostel rooms, corridors, or campus grounds.",
        "default_sla_hours": 1,
    },
    {
        "name": "Beehive / Venomous Pest Hazard",
        "description": "Active beehive, hornet nest, wasp colony, or venomous insect swarm near student areas.",
        "default_sla_hours": 2,
    },
    {
        "name": "Fire / Smoke / Gas Leak",
        "description": "Fire outbreak, smoke accumulation, gas cylinder leak, or gas smell in any campus area.",
        "default_sla_hours": 1,
    },
    {
        "name": "Aggressive Animal / Campus Safety Threat",
        "description": "Aggressive monkey, dog bite, rabid animal, or any campus safety threat requiring rapid response.",
        "default_sla_hours": 1,
    },
]

# 10 EMERG staff: Emergency Response Team (Emergency Assistance)
EMERG_STAFF = [
    {
        "username": "emerg_centra_1",
        "first_name": "Tariq",
        "last_name": "Hussain",
        "email": "emerg_centra_1@amucare.edu.in",
        "hall_location": "Central Campus Works",
        "phone": "+91 94121 00001",
        "title": "Wildlife & Snake Rescue Lead",
    },
    {
        "username": "emerg_centra_2",
        "first_name": "Javed",
        "last_name": "Ansari",
        "email": "emerg_centra_2@amucare.edu.in",
        "hall_location": "Central Campus Works",
        "phone": "+91 94121 00002",
        "title": "Venomous Reptile Rescue Specialist",
    },
    {
        "username": "emerg_centra_3",
        "first_name": "Farrukh",
        "last_name": "Siddiqui",
        "email": "emerg_centra_3@amucare.edu.in",
        "hall_location": "Central Campus Works",
        "phone": "+91 94121 00003",
        "title": "Campus Fire & Gas Safety Officer",
    },
    {
        "username": "emerg_centra_4",
        "first_name": "Mohd",
        "last_name": "Irfan",
        "email": "emerg_centra_4@amucare.edu.in",
        "hall_location": "Central Campus Works",
        "phone": "+91 94121 00004",
        "title": "Proctorial Rapid Response Guard",
    },
    {
        "username": "emerg_centra_5",
        "first_name": "Shahnawaz",
        "last_name": "Khan",
        "email": "emerg_centra_5@amucare.edu.in",
        "hall_location": "Central Campus Works",
        "phone": "+91 94121 00005",
        "title": "Proctorial Rapid Response Guard",
    },
    {
        "username": "emerg_centra_6",
        "first_name": "Abdul",
        "last_name": "Rauf",
        "email": "emerg_centra_6@amucare.edu.in",
        "hall_location": "Central Campus Works",
        "phone": "+91 94121 00006",
        "title": "Night Shift Emergency Coordinator",
    },
    {
        "username": "emerg_centra_7",
        "first_name": "Salman",
        "last_name": "Qureshi",
        "email": "emerg_centra_7@amucare.edu.in",
        "hall_location": "Central Campus Works",
        "phone": "+91 94121 00007",
        "title": "Wildlife & Reptile Rescue Handler",
    },
    {
        "username": "emerg_centra_8",
        "first_name": "Waseem",
        "last_name": "Akram",
        "email": "emerg_centra_8@amucare.edu.in",
        "hall_location": "Central Campus Works",
        "phone": "+91 94121 00008",
        "title": "Aggressive Animal & Canine Squad Officer",
    },
    {
        "username": "emerg_centra_9",
        "first_name": "Rashid",
        "last_name": "Mehmood",
        "email": "emerg_centra_9@amucare.edu.in",
        "hall_location": "Central Campus Works",
        "phone": "+91 94121 00009",
        "title": "Beehive, Wasp & Toxic Pest Controller",
    },
    {
        "username": "emerg_centra_10",
        "first_name": "Imran",
        "last_name": "Zaidi",
        "email": "emerg_centra_10@amucare.edu.in",
        "hall_location": "Central Campus Works",
        "phone": "+91 94121 00010",
        "title": "Disaster & Structural Evacuation Officer",
    },
]


def seed_emergency(stdout=None):
    def log(msg):
        if stdout:
            stdout.write(msg)
        else:
            print(msg)

    # 1. Create/get EMERG department
    dept, dept_created = Department.objects.get_or_create(
        code="EMERG",
        defaults={
            "name": "Campus Safety & Emergency Response",
            "email": "emergency@amucare.edu.in",
            "phone": "9412100000",
            "is_active": True,
        },
    )
    if dept_created:
        log(f"✓ Created department: {dept.name} ({dept.code})")
    else:
        log(f"⟳ Department already exists: {dept.name}")

    # 2. Create/update categories
    for cat_data in EMERG_CATEGORIES:
        cat, cat_created = ComplaintCategory.objects.get_or_create(
            name=cat_data["name"],
            defaults={
                "description": cat_data["description"],
                "department": dept,
                "default_sla_hours": cat_data["default_sla_hours"],
                "is_active": True,
            },
        )
        if not cat_created:
            # Ensure it points to EMERG even if previously mis-assigned
            cat.department = dept
            cat.default_sla_hours = cat_data["default_sla_hours"]
            cat.is_active = True
            cat.save(update_fields=["department", "default_sla_hours", "is_active", "updated_at"])
        log(f"{'✓' if cat_created else '⟳'} Category: {cat.name} (SLA {cat_data['default_sla_hours']}h)")

    # 3. Create/update 6 emergency staff
    for s in EMERG_STAFF:
        user, u_created = User.objects.get_or_create(
            username=s["username"],
            defaults={
                "first_name": s["first_name"],
                "last_name": s["last_name"],
                "email": s["email"],
                "is_active": True,
                "is_staff": False,
            },
        )
        user.set_password(EMERG_STAFF_PASSWORD)
        user.first_name = s["first_name"]
        user.last_name = s["last_name"]
        user.is_active = True
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.Role.STAFF
        profile.department = dept
        profile.hall_location = s["hall_location"]
        profile.phone = s["phone"]
        profile.save(update_fields=["role", "department", "hall_location", "phone", "updated_at"])

        log(f"{'✓' if u_created else '⟳'} Staff: {s['username']} – {s['title']}")

    total_staff = User.objects.filter(username__startswith="emerg_centra_").count()
    log(f"\n✅ EMERG department seeded. {total_staff} emergency staff active.")


class Command(BaseCommand):
    help = "Seed Campus Safety & Emergency Response department, categories, and 6 rapid-response staff (idempotent)"

    def handle(self, *args, **options):
        seed_emergency(stdout=self.stdout)
