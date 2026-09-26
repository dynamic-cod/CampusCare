#!/usr/bin/env python3
"""
STEP 1: Automated Reverse URL Resolution & Endpoint Integrity Test
CampusCare QA Audit Suite
==================================================================
Tests:
1. Public / Login-Free Routes:
   - GET /complaints/new/ -> HTTP 200
   - GET /complaints/<sample_tracking_token>/ -> HTTP 200
   - GET /api/suggest-category/ or core:suggest_category -> Resolves cleanly (HTTP 200)
2. Technician Zero-Login Task Route:
   - GET /task/<sample_staff_task_token>/ -> HTTP 200 without requiring @login_required
3. Administrative Protected Routes:
   - GET /dashboard/ unauthenticated -> HTTP 302 (redirects to /login/ or /accounts/login/)
   - GET /dashboard/ as registrar_office -> HTTP 200
   - GET /dashboard/ as provost_ssn -> HTTP 200
   - GET /dashboard/ as hod_elec -> HTTP 200
"""

import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
django.setup()

from django.test import Client
from django.urls import reverse
from core.models import Complaint

def run_route_integrity_tests():
    print("=" * 70)
    print("CAMPUSCARE QA AUDIT - STEP 1: ROUTE INTEGRITY & RESOLUTION")
    print("=" * 70)
    client = Client()
    all_passed = True

    # Fetch a sample complaint for tokens
    sample_complaint = Complaint.objects.first()
    if not sample_complaint:
        print("❌ ERROR: No complaints found in database to sample tokens from.")
        return False

    sample_tracking_token = sample_complaint.tracking_token
    sample_staff_task_token = str(sample_complaint.staff_task_token)

    # 1. Reverse URL Resolution checks
    print("\n[CHECK 1.1] Reverse URL Mappings Resolution:")
    urls_to_resolve = [
        ("core:home", {}),
        ("core:complaint_create", {}),
        ("core:suggest_category", {}),
        ("core:suggest_category_api", {}),
        ("core:dashboard", {}),
        ("core:technician_task_view", {"task_token": sample_staff_task_token}),
        ("core:complaint_tracking", {"tracking_token": sample_tracking_token}),
        ("core:student_confirm_resolution", {"tracking_token": sample_tracking_token}),
        ("core:student_reopen_complaint", {"tracking_token": sample_tracking_token}),
        ("core:room_lookup_api", {}),
    ]

    for name, kwargs in urls_to_resolve:
        try:
            resolved_url = reverse(name, kwargs=kwargs)
            print(f"  ✓ reverse('{name}'): {resolved_url}")
        except Exception as e:
            print(f"  ❌ Failed to reverse '{name}': {e}")
            all_passed = False

    # 2. Public / Login-Free Routes
    print("\n[CHECK 1.2] Public / Login-Free Endpoints:")
    
    # GET /complaints/new/
    resp_new = client.get("/complaints/new/")
    print(f"  - GET /complaints/new/ -> HTTP {resp_new.status_code}")
    if resp_new.status_code == 200:
        print("    ✓ PASS: Public complaint submission form is accessible.")
    else:
        print(f"    ❌ FAIL: Expected 200, got {resp_new.status_code}")
        all_passed = False

    # GET /complaints/<sample_tracking_token>/
    token_url = f"/complaints/{sample_tracking_token}/"
    resp_token = client.get(token_url)
    print(f"  - GET {token_url} -> HTTP {resp_token.status_code}")
    if resp_token.status_code == 200:
        print("    ✓ PASS: Anonymous student tracking by token is accessible (HTTP 200).")
    else:
        print(f"    ❌ FAIL: Expected 200, got {resp_token.status_code}")
        all_passed = False

    # GET /api/suggest-category/
    resp_suggest = client.get("/api/suggest-category/")
    print(f"  - GET /api/suggest-category/ -> HTTP {resp_suggest.status_code}")
    if resp_suggest.status_code == 200:
        print("    ✓ PASS: suggest-category endpoint resolves and responds with JSON.")
    else:
        print(f"    ❌ FAIL: Expected 200, got {resp_suggest.status_code}")
        all_passed = False

    # 3. Technician Zero-Login Task Route
    print("\n[CHECK 1.3] Technician Zero-Login Task Route:")
    task_url = f"/task/{sample_staff_task_token}/"
    resp_task = client.get(task_url)
    print(f"  - GET {task_url} -> HTTP {resp_task.status_code}")
    if resp_task.status_code == 200:
        print("    ✓ PASS: Technician task view renders without requiring authentication.")
    else:
        print(f"    ❌ FAIL: Expected 200, got {resp_task.status_code}")
        all_passed = False

    # 4. Administrative Protected Routes
    print("\n[CHECK 1.4] Administrative Protected Routes & Login Gating:")
    
    # GET /dashboard/ unauthenticated
    resp_dash_unauth = client.get("/dashboard/")
    print(f"  - GET /dashboard/ (unauthenticated) -> HTTP {resp_dash_unauth.status_code} (Redirect: {resp_dash_unauth.headers.get('Location')})")
    if resp_dash_unauth.status_code in (301, 302) and "login" in resp_dash_unauth.headers.get("Location", ""):
        print("    ✓ PASS: Unauthenticated access is redirected to login.")
    else:
        print(f"    ❌ FAIL: Expected 302 redirect to login, got {resp_dash_unauth.status_code}")
        all_passed = False

    admin_accounts = [
        ("registrar_office", "Registrar Global Console"),
        ("provost_ssn", "Provost Console (SSN)"),
        ("hod_elec", "HOD Console (ELEC)"),
    ]

    for username, role_desc in admin_accounts:
        logged_in = client.login(username=username, password="CampusAdmin@2026")
        if not logged_in:
            print(f"    ❌ FAIL: Could not authenticate user '{username}' with CampusAdmin@2026")
            all_passed = False
            continue
        
        resp_admin = client.get("/dashboard/")
        print(f"  - GET /dashboard/ as {username} ({role_desc}) -> HTTP {resp_admin.status_code}")
        if resp_admin.status_code == 200:
            print(f"    ✓ PASS: {role_desc} rendered successfully.")
        else:
            print(f"    ❌ FAIL: Expected 200 for {username}, got {resp_admin.status_code}")
            all_passed = False
        client.logout()

    print("\n" + "=" * 70)
    if all_passed:
        print("RESULT: ALL STEP 1 ROUTE INTEGRITY TESTS PASSED (100% SUCCESS)!")
    else:
        print("RESULT: SOME ROUTE INTEGRITY CHECKS FAILED.")
    print("=" * 70)
    return all_passed

if __name__ == "__main__":
    success = run_route_integrity_tests()
    sys.exit(0 if success else 1)
