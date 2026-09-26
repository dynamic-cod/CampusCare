#!/usr/bin/env python3
"""
Provision multi-tenant sub-admin accounts for CampusCare:
- Registrar Office (`registrar_office`)
- Provosts for each Residential Hall (`provost_<hall_code>`)
- HODs for each Department (`hod_<dept_code>`)
Default password: `CampusAdmin@2026`
"""
import os
import sys
import django

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
    django.setup()

from django.contrib.auth import get_user_model
from core.models import Building, Department, UserProfile

DEFAULT_ADMIN_PASSWORD = "CampusAdmin@2026"


def seed_subadmins(stdout=None):
    User = get_user_model()
    created_or_updated = []

    # 1. Link Buildings to matching Departments where codes match (for HOD scoping)
    dept_by_code = {d.code.upper(): d for d in Department.objects.all()}
    hostel_dept = dept_by_code.get("HOSTEL")
    for building in Building.objects.all():
        b_code = building.code.upper()
        if b_code in dept_by_code and building.department_id != dept_by_code[b_code].id:
            building.department = dept_by_code[b_code]
            building.save(update_fields=["department", "updated_at"])
        elif not building.department_id and hostel_dept and "hall" in building.name.lower():
            building.department = hostel_dept
            building.save(update_fields=["department", "updated_at"])

    # 2. Provision Registrar Office account (`registrar_office`)
    reg_user, _ = User.objects.get_or_create(
        username="registrar_office",
        defaults={
            "first_name": "Registrar",
            "last_name": "Office",
            "email": "registrar@amucare.edu.in",
            "is_staff": True,
        },
    )
    reg_user.is_staff = True
    reg_user.set_password(DEFAULT_ADMIN_PASSWORD)
    reg_user.save()
    reg_profile, _ = UserProfile.objects.get_or_create(user=reg_user)
    reg_profile.role = UserProfile.Role.REGISTRAR
    reg_profile.save(update_fields=["role", "updated_at"])
    created_or_updated.append(reg_user.username)

    # 3. Provision Provosts for each Residential Hall (`provost_<hall_code>`)
    for building in Building.objects.filter(is_active=True):
        hall_code = building.code.lower()
        username = f"provost_{hall_code}"
        p_user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": "Provost",
                "last_name": building.name[:120],
                "email": f"{username}@amucare.edu.in",
                "is_staff": True,
            },
        )
        p_user.is_staff = True
        p_user.set_password(DEFAULT_ADMIN_PASSWORD)
        p_user.save()
        p_profile, _ = UserProfile.objects.get_or_create(user=p_user)
        p_profile.role = UserProfile.Role.PROVOST
        p_profile.managed_building = building
        p_profile.save(update_fields=["role", "managed_building", "updated_at"])
        created_or_updated.append(username)

    # 4. Provision HODs for each Department (`hod_<dept_code>`)
    for dept in Department.objects.filter(is_active=True):
        dept_code = dept.code.lower()
        username = f"hod_{dept_code}"
        h_user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": "HOD",
                "last_name": dept.name[:120],
                "email": f"{username}@amucare.edu.in",
                "is_staff": True,
            },
        )
        h_user.is_staff = True
        h_user.set_password(DEFAULT_ADMIN_PASSWORD)
        h_user.save()
        h_profile, _ = UserProfile.objects.get_or_create(user=h_user)
        h_profile.role = UserProfile.Role.HOD
        h_profile.managed_department = dept
        h_profile.department = dept
        h_profile.save(update_fields=["role", "managed_department", "department", "updated_at"])
        created_or_updated.append(username)

    if stdout:
        stdout.write(f"Seeded {len(created_or_updated)} sub-admin accounts (Registrar, Provosts, HODs).")
    return created_or_updated


if __name__ == "__main__":
    accounts = seed_subadmins()
    print(f"Successfully provisioned {len(accounts)} sub-admin accounts.")
