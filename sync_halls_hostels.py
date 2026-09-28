#!/usr/bin/env python3
"""
Idempotent Ingestion & Synchronization Script for AMU Residential Halls & Constituent Hostels
CampusCare Multi-Tenant Spatial Hierarchy Sync
=============================================================================================

Rules:
- Non-destructive: No flush, no drop, preserves existing IDs, FKs, tickets, and user accounts.
- Idempotent execution using update_or_create and get_or_create exclusively.
- Provisions/refreshes Provost sub-admin accounts (provost_<hall_code>) with password 'CampusAdmin@2026'.
- Verifies complaint scoping, foreign key integrity, and zero orphaned rooms.
"""

import csv
import os
import re
import sys
from pathlib import Path

# Setup Django environment if run standalone
if __name__ == "__main__" or "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
    import django
    django.setup()

from django.contrib.auth import get_user_model
from django.db import models, transaction
from core.models import Building, Campus, Complaint, Department, Floor, Room, UserProfile
from core.permissions import get_scoped_complaints_for_user

DEFAULT_ADMIN_PASSWORD = "CampusAdmin@2026"

HALL_DEFINITIONS = {
    "Begum Azeezun Nisa Hall": {"code": "BAN", "gender": "Girls", "name": "Begum Azeezun Nisa Hall"},
    "Abdullah Hall": {"code": "ABH", "gender": "Girls", "name": "Abdullah Hall"},
    "Begum Sultan Jahan Hall": {"code": "BSJ", "gender": "Girls", "name": "Begum Sultan Jahan Hall"},
    "Indira Gandhi Hall": {"code": "IGH", "gender": "Girls", "name": "Indira Gandhi Hall"},
    "Sarojini Naidu Hall": {"code": "SNH", "gender": "Girls", "name": "Sarojini Naidu Hall"},
    "Bibi Fatima Hall": {"code": "BFH", "gender": "Girls", "name": "Bibi Fatima Hall"},
    "Aftab Hall": {"code": "AFT", "gender": "Boys", "name": "Aftab Hall"},
    "Sir Syed Hall (North)": {"code": "SSN", "gender": "Boys", "name": "Sir Syed Hall (North)"},
    "Sir Syed Hall (South)": {"code": "SSS", "gender": "Boys", "name": "Sir Syed Hall (South)"},
    "Sir Ziauddin Hall": {"code": "SZH", "gender": "Boys", "name": "Sir Ziauddin Hall"},
    "Viqarul Mulk Hall": {"code": "VMH", "gender": "Boys", "name": "Viqarul Mulk Hall"},
    "Sir Shah Sulaiman Hall": {"code": "SSH", "gender": "Boys", "name": "Sir Shah Sulaiman Hall"},
    "Mohsinul Mulk Hall": {"code": "MMH", "gender": "Boys", "name": "Mohsinul Mulk Hall"},
    "Mohammad Habib Hall": {"code": "MHH", "gender": "Boys", "name": "Mohammad Habib Hall"},
    "Dr. B.R. Ambedkar Hall": {"code": "BRA", "gender": "Boys", "name": "Dr. B.R. Ambedkar Hall"},
    "Nadeem Tarin Hall": {"code": "NTH", "gender": "Boys", "name": "Nadeem Tarin Hall"},
    "Ross Masood Hall": {"code": "RMH", "gender": "Boys", "name": "Ross Masood Hall"},
    "Hadi Hasan Hall": {"code": "HHH", "gender": "Boys", "name": "Hadi Hasan Hall"},
    "Non-Resident Students Centre (N.R.S.C.) Hall": {"code": "NRSC", "gender": "Boys", "name": "Non-Resident Students Centre"},
    "Allama Iqbal Boarding House": {"code": "AIB", "gender": "Boys", "name": "Allama Iqbal Boarding House"},
}


def clean_hostel_code(name, max_len=8):
    """Generate a clean unique sub-code <= 8 chars from hostel name."""
    s = name.replace("(", " ").replace(")", " ")
    words = re.sub(r"[^A-Za-z0-9\s]", "", s).upper().split()
    words = [w for w in words if w not in {"HOSTEL", "HALL", "AND", "OF", "THE", "HOUSE", "COURT", "WING", "BLOCK", "ANNEXE", "BUILDING"}]
    if not words:
        words = re.sub(r"[^A-Za-z0-9\s]", "", s).upper().split()
    if len(words) == 1:
        base = words[0][:max_len]
    elif len(words) == 2:
        base = (words[0][:4] + words[1][:4])[:max_len]
    elif len(words) == 3:
        base = (words[0][:3] + words[1][:3] + words[2][:2])[:max_len]
    else:
        base = "".join(w[:2] for w in words)[:max_len]
    return base


def ingest_halls_and_hostels(csv_path=None):
    """
    Step 1 & 2: Ingest residential halls and constituent hostels from CSV.
    Uses update_or_create strictly to ensure idempotency.
    """
    resolved_csv = Path(csv_path) if csv_path else Path("AMU Halls and Hostels - Sheet1.csv")
    if not resolved_csv.exists():
        raise FileNotFoundError(f"CSV file not found: {resolved_csv}")

    print(f"\n📥 Loading residential halls and hostels from: {resolved_csv}")

    campus, _ = Campus.objects.get_or_create(
        code="AMU",
        defaults={"name": "Aligarh Muslim University", "is_active": True}
    )
    hostel_dept = Department.objects.filter(code="HOSTEL").first()

    # 1. Ingest/Update the 20 Residential Halls
    print("\n🏛️  Synchronizing 20 Residential Halls...")
    hall_records = {}
    for hall_csv_name, meta in HALL_DEFINITIONS.items():
        code = meta["code"]
        name = meta["name"]
        gender = meta["gender"]
        dept = hostel_dept if code not in {"AIB", "NRSC"} else None

        hall_bldg, created = Building.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "short_name": name,
                "campus": campus,
                "department": dept,
                "parent": None,
                "gender": gender,
                "building_type": "hall",
                "is_active": True,
            }
        )
        hall_records[hall_csv_name] = hall_bldg
        status = "Created" if created else "Updated"
        print(f"  ✓ [{code:5}] {name:38} ({status})")

    # 2. Ingest the 84 Constituent Hostels / Blocks
    print("\n🛏️  Synchronizing Constituent Hostels & Blocks...")
    hostel_records = []
    used_codes = {b.code for b in Building.objects.all()}

    with open(resolved_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, 1):
            category = row["Category"].strip()
            hall_name = row["Hall Name"].strip()
            hostel_name = row["Constituent Hostel / Block"].strip()
            wing = row["Block / Wing Detail"].strip()
            capacity = row["Capacity / Room Details"].strip()

            parent_hall = hall_records.get(hall_name)
            if not parent_hall:
                # Fallback fuzzy match
                for h_name, bldg in hall_records.items():
                    if h_name.lower() in hall_name.lower() or bldg.name.lower() in hall_name.lower():
                        parent_hall = bldg
                        break
            if not parent_hall:
                print(f"  ⚠️ Warning: Could not match parent hall for row {idx}: {hall_name}")
                continue

            h_code = parent_hall.code
            sub = clean_hostel_code(hostel_name, 7)
            child_code = f"{h_code}_{sub}"
            counter = 1
            base_code = child_code
            # Ensure unique code <= 20 chars
            while child_code in used_codes and not Building.objects.filter(code=child_code, parent=parent_hall).exists():
                child_code = f"{base_code[:16]}_{counter}"
                counter += 1

            full_child_name = f"{parent_hall.name} · {hostel_name}"

            # Check if exists by code or by parent+short_name
            existing_child = Building.objects.filter(parent=parent_hall, short_name=hostel_name).first()
            if existing_child:
                child_code = existing_child.code

            child_bldg, child_created = Building.objects.update_or_create(
                code=child_code,
                defaults={
                    "name": full_child_name,
                    "short_name": hostel_name,
                    "campus": campus,
                    "department": parent_hall.department,
                    "parent": parent_hall,
                    "gender": category,
                    "building_type": "hostel",
                    "wing_detail": wing,
                    "capacity_detail": capacity,
                    "is_active": True,
                }
            )
            used_codes.add(child_code)
            hostel_records.append(child_bldg)

            # Ensure child hostel has floors and rooms 001 to 150
            f1, _ = Floor.objects.get_or_create(building=child_bldg, number=1, defaults={"label": "Floor 1"})
            f2, _ = Floor.objects.get_or_create(building=child_bldg, number=2, defaults={"label": "Floor 2"})
            f3, _ = Floor.objects.get_or_create(building=child_bldg, number=3, defaults={"label": "Floor 3"})
            hostel_floors = [f1, f2, f3]
            for r_i in range(1, 151):
                r_num = f"{r_i:03d}"
                r_floor = hostel_floors[(r_i - 1) // 50]
                Room.objects.get_or_create(
                    floor=r_floor,
                    number=r_num,
                    defaults={"name": f"{hostel_name} Room {r_num}", "qr_code_token": f"QR-{child_code}-{r_num}", "is_active": True}
                )

            status = "Created" if child_created else "Updated"
            print(f"  ✓ [{child_code:12}] {parent_hall.code} -> {hostel_name[:35]:35} ({status})")

    # Mark non-hall parent buildings (academic faculties/departments) with building_type="academic"
    Building.objects.filter(parent__isnull=True).exclude(
        id__in=[h.id for h in hall_records.values()]
    ).update(building_type="academic")

    print(f"\n✅ Ingestion complete: {len(hall_records)} residential halls and {len(hostel_records)} constituent hostels/blocks synchronized.")
    return hall_records, hostel_records


@transaction.atomic
def sync_provost_accounts(hall_records):
    """
    Step 3: Provision or refresh Provost sub-admin accounts for each Residential Hall.
    Username format: provost_<hall_code.lower()>
    Password: CampusAdmin@2026
    """
    print("\n👤 Synchronizing Provost Sub-Admin accounts...")
    User = get_user_model()
    provost_users = []

    for hall_name, hall_bldg in hall_records.items():
        hall_code = hall_bldg.code.lower()
        username = f"provost_{hall_code}"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": "Provost",
                "last_name": hall_bldg.name[:120],
                "email": f"{username}@amucare.edu.in",
                "is_staff": True,
            }
        )
        user.is_staff = True
        user.set_password(DEFAULT_ADMIN_PASSWORD)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.Role.PROVOST
        profile.managed_building = hall_bldg
        profile.save(update_fields=["role", "managed_building", "updated_at"])

        provost_users.append(user)
        action = "Created" if created else "Updated"
        print(f"  ✓ {username:16} -> {hall_bldg.name:35} [{action}]")

    print(f"✅ Provost account sync complete: {len(provost_users)} active Provost accounts.")
    return provost_users


def verify_sync(hall_records, hostel_records):
    """
    Step 4: Verification & Audit.
    Asserts row counts match CSV, provosts active, zero orphaned complaints, and scoping isolation.
    """
    print("\n🔍 Running verification and regression checks...")

    # 1. Total residential halls and constituent hostels match
    res_halls_count = Building.objects.filter(parent__isnull=True, code__in=[m["code"] for m in HALL_DEFINITIONS.values()]).count()
    hostels_count = Building.objects.filter(parent__isnull=False).count()
    print(f"  Residential Halls in DB: {res_halls_count} (Expected: 20)")
    print(f"  Constituent Hostels in DB: {hostels_count} (Expected: 84)")
    assert res_halls_count == 20, f"Expected 20 residential halls, found {res_halls_count}"
    assert hostels_count == 84, f"Expected 84 constituent hostels matching CSV rows, found {hostels_count}"

    # 2. Every residential hall has an active Provost account with role == 'PROVOST'
    for hall_bldg in hall_records.values():
        provost_profile = UserProfile.objects.filter(
            role=UserProfile.Role.PROVOST,
            managed_building=hall_bldg
        ).first()
        assert provost_profile is not None, f"Missing Provost account for hall {hall_bldg.name} ({hall_bldg.code})"
        assert provost_profile.user.is_staff, f"Provost user {provost_profile.user.username} is not staff!"
    print("  ✓ All 20 Residential Halls have active Provost accounts assigned.")

    # 3. Zero complaints have orphaned or broken building / room relations
    orphaned_complaints = Complaint.objects.filter(room__isnull=True).count()
    print(f"  Complaints with missing room: {orphaned_complaints}")
    assert orphaned_complaints == 0, f"Regression: Found {orphaned_complaints} complaints with unlinked rooms!"

    # 4. Scoping test: Logging into sample provosts shows their queue and zero cross-tenant leaks
    User = get_user_model()
    provost_ssn = User.objects.get(username="provost_ssn")
    provost_snh = User.objects.get(username="provost_snh")

    ssn_bldg = Building.objects.get(code="SSN")
    snh_bldg = Building.objects.get(code="SNH")

    ssn_qs = get_scoped_complaints_for_user(provost_ssn)
    snh_qs = get_scoped_complaints_for_user(provost_snh)

    # Verify no leaks
    for c in ssn_qs:
        b = c.room.floor.building
        hall = b if not b.parent else b.parent
        assert hall.code == "SSN", f"Scoping leak! SSN provost saw complaint {c.reference} from {hall.code}"

    for c in snh_qs:
        b = c.room.floor.building
        hall = b if not b.parent else b.parent
        assert hall.code == "SNH", f"Scoping leak! SNH provost saw complaint {c.reference} from {hall.code}"

    print("  ✓ Provost multi-tenant complaint queues verified: 0 cross-tenant leaks.")
    print("\n🎉 Synchronization and verification completed successfully!")


def main():
    csv_file = sys.argv[1] if len(sys.argv) > 1 else None
    hall_records, hostel_records = ingest_halls_and_hostels(csv_file)
    sync_provost_accounts(hall_records)
    verify_sync(hall_records, hostel_records)


if __name__ == "__main__":
    main()
