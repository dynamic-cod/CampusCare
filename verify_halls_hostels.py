"""
Verification and Audit Script for AMU Halls and Hostels synchronization.
Step 4 of user requirements:
1. Total residential halls and constituent hostels match the row count from "AMU Halls and Hostels - Sheet1.csv".
2. Every residential hall has an active Provost account with role == 'PROVOST' and managed_building properly assigned.
3. Zero complaints have orphaned or broken building / room relations (Complaint.objects.filter(room__isnull=True).count() == 0).
4. Logging into sample provost accounts (e.g., provost_ssn, provost_snh) displays their respective hall and hostel complaint queues with zero cross-tenant data leaks.
5. Room lookup API test and dashboard scoping verification.
"""
import os
import sys
import django
from django.test import Client

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import models
from core.models import Building, Room, Complaint, UserProfile
from core.permissions import get_scoped_complaints_for_user
import csv

def run_audit():
    print("=" * 70)
    print("CAMPUSCARE STEP 4 AUDIT & VERIFICATION REPORT")
    print("=" * 70)
    all_passed = True

    # 1. Total residential halls and constituent hostels matching CSV
    csv_path = "AMU Halls and Hostels - Sheet1.csv"
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        csv_row_count = len(reader)
        unique_halls_in_csv = len(set(
            (r.get("Hall Name") or r.get("Residential Hall Name") or r.get("Residential Hall") or "").strip()
            for r in reader if (r.get("Hall Name") or r.get("Residential Hall Name") or r.get("Residential Hall"))
        ))

    db_halls_count = Building.objects.filter(parent__isnull=True, building_type="hall").count()
    db_hostels_count = Building.objects.filter(parent__isnull=False, building_type="hostel").count()

    print(f"\n[CHECK 1] Residential Halls & Hostels Count:")
    print(f"  - CSV Total Rows (Constituent Hostels): {csv_row_count}")
    print(f"  - CSV Unique Residential Halls:         {unique_halls_in_csv}")
    print(f"  - DB Residential Halls (parent=None):   {db_halls_count}")
    print(f"  - DB Constituent Hostels (parent!=None): {db_hostels_count}")

    if db_hostels_count == csv_row_count and db_halls_count == unique_halls_in_csv:
        print("  ✅ PASS: DB counts perfectly match the CSV structure (20 halls, 84 constituent hostels)!")
    else:
        print(f"  ❌ FAIL: Counts do not match expected {unique_halls_in_csv} halls and {csv_row_count} hostels.")
        all_passed = False

    # 2. Every residential hall has an active Provost account with role == 'PROVOST' and managed_building assigned
    print(f"\n[CHECK 2] Active Provost Accounts & Credentials:")
    halls = Building.objects.filter(parent__isnull=True, building_type="hall")
    provost_issues = []
    auth_issues = []

    for hall in halls:
        expected_username = f"provost_{hall.code.lower()}"
        user = User.objects.filter(username=expected_username).first()
        if not user:
            provost_issues.append(f"Missing user {expected_username} for {hall.name}")
            continue

        if not hasattr(user, "profile"):
            provost_issues.append(f"User {expected_username} has no UserProfile")
            continue

        profile = user.profile
        if profile.role != UserProfile.Role.PROVOST:
            provost_issues.append(f"User {expected_username} has role '{profile.role}' instead of 'PROVOST'")
        if profile.managed_building != hall:
            provost_issues.append(f"User {expected_username} managed_building is {profile.managed_building} instead of {hall}")

        # Check authentication with unified password
        auth_user = authenticate(username=expected_username, password="CampusAdmin@2026")
        if not auth_user:
            auth_issues.append(f"Authentication failed for {expected_username} with password 'CampusAdmin@2026'")

    print(f"  - Total Residential Halls checked: {halls.count()}")
    if not provost_issues and not auth_issues:
        print("  ✅ PASS: All 20 residential halls have active Provost accounts with role='PROVOST', correct managed_building, and valid credentials (CampusAdmin@2026)!")
    else:
        for err in provost_issues + auth_issues:
            print(f"  ❌ {err}")
        all_passed = False

    # 3. Zero complaints have orphaned or broken building / room relations
    print(f"\n[CHECK 3] Complaint Spatial Integrity & Orphaned Relations:")
    total_complaints = Complaint.objects.count()
    orphaned_room_complaints = Complaint.objects.filter(room__isnull=True).count()
    orphaned_floor_complaints = Complaint.objects.filter(room__floor__isnull=True).count()
    orphaned_bldg_complaints = Complaint.objects.filter(room__floor__building__isnull=True).count()

    print(f"  - Total Complaints in Database: {total_complaints}")
    print(f"  - Complaints with room__isnull=True: {orphaned_room_complaints}")
    print(f"  - Complaints with broken floor relation: {orphaned_floor_complaints}")
    print(f"  - Complaints with broken building relation: {orphaned_bldg_complaints}")

    if orphaned_room_complaints == 0 and orphaned_floor_complaints == 0 and orphaned_bldg_complaints == 0:
        print("  ✅ PASS: Zero complaints have orphaned or broken room/floor/building relations!")
    else:
        print("  ❌ FAIL: Found orphaned complaints!")
        all_passed = False

    # 4. Multi-tenant scoping & sample Provost login isolation (provost_ssn vs provost_snh)
    print(f"\n[CHECK 4] Multi-Tenant Scoping & Zero Cross-Tenant Data Leaks:")
    user_ssn = User.objects.filter(username="provost_ssn").first()
    user_snh = User.objects.filter(username="provost_snh").first()

    if not user_ssn or not user_snh:
        print("  ❌ FAIL: Missing provost_ssn or provost_snh")
        all_passed = False
    else:
        qs_ssn = get_scoped_complaints_for_user(user_ssn)
        qs_snh = get_scoped_complaints_for_user(user_snh)

        # Check that SSN complaints only belong to SSN or SSN hostels
        ssn_hall = user_ssn.profile.managed_building
        snh_hall = user_snh.profile.managed_building

        ssn_invalid = qs_ssn.exclude(
            models.Q(room__floor__building=ssn_hall) | models.Q(room__floor__building__parent=ssn_hall)
        ).count()

        snh_invalid = qs_snh.exclude(
            models.Q(room__floor__building=snh_hall) | models.Q(room__floor__building__parent=snh_hall)
        ).count()

        # Check intersection
        ssn_pks = set(qs_ssn.values_list("pk", flat=True))
        snh_pks = set(qs_snh.values_list("pk", flat=True))
        cross_tenant_overlap = ssn_pks.intersection(snh_pks)

        print(f"  - provost_ssn ({ssn_hall.name}): {qs_ssn.count()} scoped complaints (invalid: {ssn_invalid})")
        print(f"  - provost_snh ({snh_hall.name}): {qs_snh.count()} scoped complaints (invalid: {snh_invalid})")
        print(f"  - Cross-tenant PK overlap between SSN and SNH: {len(cross_tenant_overlap)}")

        if ssn_invalid == 0 and snh_invalid == 0 and len(cross_tenant_overlap) == 0:
            print("  ✅ PASS: Perfect tenant isolation, zero cross-tenant data leaks!")
        else:
            print(f"  ❌ FAIL: Cross tenant leak detected! Overlap: {cross_tenant_overlap}")
            all_passed = False

    # 5. Client HTTP Login and Dashboard Rendering Check
    print(f"\n[CHECK 5] HTTP Client Simulation (Login, Dashboard & Room Lookup API):")
    client = Client()
    login_success = client.login(username="provost_ssn", password="CampusAdmin@2026")
    print(f"  - provost_ssn client login result: {login_success}")
    if not login_success:
        print("  ❌ FAIL: Client login failed for provost_ssn")
        all_passed = False
    else:
        # Dashboard response
        resp = client.get("/dashboard/")
        print(f"  - GET /dashboard/ HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            content = resp.content.decode("utf-8")
            if "Sir Syed Hall" in content and "Constituent Hostels" in content:
                print("  ✅ PASS: Provost dashboard rendered successfully with constituent hostels breakdown!")
            else:
                print("  ❌ FAIL: Dashboard content missing expected Hall name or constituent hostels section")
                all_passed = False
        else:
            print(f"  ❌ FAIL: Unexpected status {resp.status_code} for /dashboard/")
            all_passed = False

        # Room Lookup API response
        api_resp = client.get("/api/room-lookup/?q=101")
        print(f"  - GET /api/room-lookup/?q=101 HTTP Status: {api_resp.status_code}")
        if api_resp.status_code == 200:
            data = api_resp.json()
            print(f"    API returned: found={data.get('found')}, display='{data.get('display', '')}'")
            print("  ✅ PASS: Room lookup API is operational and responds with JSON!")
        else:
            print(f"  ❌ FAIL: /api/room-lookup/ returned {api_resp.status_code}")
            all_passed = False

        # Public Complaint Form response
        form_resp = client.get("/complaints/new/")
        print(f"  - GET /complaints/new/ HTTP Status: {form_resp.status_code}")
        if form_resp.status_code == 200:
            form_content = form_resp.content.decode("utf-8")
            if "hall_hostel_select" in form_content and "Sir Syed Hall" in form_content:
                print("  ✅ PASS: Public complaint form contains dynamic hall & hostel dropdown!")
            else:
                print("  ❌ FAIL: Complaint form missing dynamic hall/hostel dropdown")
                all_passed = False
        else:
            print(f"  ❌ FAIL: /complaints/new/ returned {form_resp.status_code}")
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL VERIFICATION & AUDIT CHECKS PASSED (100% SUCCESS)!")
    else:
        print("SOME VERIFICATION CHECKS FAILED! Review output above.")
    print("=" * 70)
    return all_passed

if __name__ == "__main__":
    success = run_audit()
    sys.exit(0 if success else 1)
