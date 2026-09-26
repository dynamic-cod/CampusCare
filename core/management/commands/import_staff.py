"""
Management command: python manage.py import_staff

Reads core/staff_data.json and creates Django User + UserProfile records
for every staff member listed in the staff list xlsx.

Safe to run multiple times — uses get_or_create (idempotent).
"""
import json
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import Department, UserProfile


DEPT_CODE_MAP = {
    "Electrical (ELEC)": "ELEC",
    "Plumbing (PLUMB)": "PLUMB",
    "Civil (CIVIL)": "CIVIL",
    "IT & AV (ITINF)": "ITINF",
    "Sanitation (CLEAN)": "CLEAN",
}

DEPT_NAME_MAP = {
    "ELEC": "Electrical Maintenance",
    "PLUMB": "Plumbing & Water Supply",
    "CIVIL": "Civil, Carpentry & Masonry",
    "ITINF": "IT & Audio-Visual Support",
    "CLEAN": "Sanitation & Housekeeping",
}


class Command(BaseCommand):
    help = "Import staff from core/staff_data.json into Django User + UserProfile"

    def handle(self, *args, **options):
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "staff_data.json",
        )
        with open(data_path, "r", encoding="utf-8") as f:
            staff_list = json.load(f)

        created_users = 0
        updated_users = 0

        for member in staff_list:
            username = member["username"]
            name = member["name"]
            dept_label = member["dept"]
            role_title = member["role"]
            location = member["location"]
            contact = member["contact"]

            dept_code = DEPT_CODE_MAP.get(dept_label)
            dept_name = DEPT_NAME_MAP.get(dept_code, dept_label)

            # Ensure Department exists
            department, _ = Department.objects.get_or_create(
                code=dept_code,
                defaults={"name": dept_name, "is_active": True},
            )

            # Split name into first/last
            parts = name.split(None, 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

            # Create or update User
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"{username}@amucare.edu.in",
                    "is_staff": True,
                },
            )
            if not created:
                user.first_name = first_name
                user.last_name = last_name
                user.is_staff = True
                user.save(update_fields=["first_name", "last_name", "is_staff"])

            # Set a default password (staff must change on first login)
            if created:
                user.set_password("AMUCare@2024!")
                user.save(update_fields=["password"])

            # Update UserProfile
            profile = user.profile
            profile.role = UserProfile.Role.STAFF
            profile.department = department
            profile.phone = contact
            profile.hall_location = location
            profile.save(update_fields=["role", "department", "phone", "hall_location"])

            if created:
                created_users += 1
                self.stdout.write(f"  [NEW] {name} (@{username}) — {dept_label}")
            else:
                updated_users += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone! Created: {created_users}, Updated: {updated_users} staff accounts."
            )
        )
