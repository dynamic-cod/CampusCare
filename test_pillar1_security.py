#!/usr/bin/env python3
"""
Pillar 1: Security, Access Control & Anti-Abuse Test Suite
Comprehensive testing for:
1. Multi-Tenant Role Isolation (Superuser, Registrar, Provost, HOD, Staff, Student, Anon)
2. IDOR / Token Leakage Protection (Reference vs. Tracking Token vs. Task Token)
3. Open Redirect (CWE-601) Prevention
4. File Upload Security & Magic Byte / Non-Image Rejection (CWE-434)
5. CSV Formula Injection Sanitization (CWE-1236)
6. CSRF Enforcement on All State-Changing Endpoints
7. Anti-Abuse Rate Limiting
8. Enrollment Number Format Regex Enforcement
"""
import os
import io
import sys
import json
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
django.setup()

from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from PIL import Image

from core.models import Complaint, ComplaintCategory, Building, Department, Room, UserProfile
from core.utils import compress_uploaded_image

def run_tests():
    print("=" * 80)
    print("🛡️  PILLAR 1: SECURITY, ACCESS CONTROL & ANTI-ABUSE TEST SUITE")
    print("=" * 80)
    client = Client()
    passed = 0
    failed = 0
    failures = []

    def check(condition, test_name, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ [PASS] {test_name}")
            if detail:
                print(f"       ↳ {detail}")
        else:
            failed += 1
            print(f"  ❌ [FAIL] {test_name}")
            if detail:
                print(f"       ↳ {detail}")
            failures.append((test_name, detail))

    # --- 1. IDOR & TOKEN ISOLATION ---
    print("\n[1.1] IDOR & Token Boundary Isolation:")
    cat = ComplaintCategory.objects.first()
    bldg = Building.objects.first()
    room = Room.objects.filter(floor__building=bldg).first() if bldg else None

    c = Complaint.objects.create(
        reporter_name="Security Tester",
        reporter_enrollment_number="GQ9999",
        title="Pillar 1 Security Test Ticket",
        description="Confidential ticket content",
        category=cat,
        room=room,
        location_description=bldg.name if bldg else "Campus",
        is_public=False
    )
    ref = c.reference
    token = c.tracking_token
    task_token = str(c.staff_task_token)

    # 1.1a Public reference lookup in /track/ must NOT redirect or leak secret token
    resp = client.post("/track/", {"tracking_token": ref}, follow=False)
    check(token not in (resp.url if resp.status_code == 302 else resp.content.decode()),
          "Public reference in /track/ does NOT leak secret tracking token")

    # 1.1b Direct URL access to /track/<ref>/ must fail or not expose private token
    resp_ref = client.get(f"/track/{ref}/")
    check(resp_ref.status_code in [404, 302] or token not in resp_ref.content.decode(),
          "Accessing /track/<reference>/ does not reveal secret tracking token")

    # 1.1c Student tracking view MUST NOT leak technician task token
    resp_track = client.get(f"/track/{token}/")
    check(task_token not in resp_track.content.decode(),
          "Student tracking portal NEVER leaks technician task token")

    # 1.1d Logged-in student cannot access technician portal
    student_user, _ = User.objects.get_or_create(username="sec_student_1")
    s_profile, _ = UserProfile.objects.get_or_create(user=student_user)
    s_profile.role = UserProfile.Role.STUDENT
    s_profile.save()
    client.force_login(student_user)
    resp_task_student = client.get(f"/task/{task_token}/")
    check(resp_task_student.status_code == 403,
          "Logged-in student accessing technician portal returns HTTP 403 Forbidden")
    client.logout()

    # --- 1.2 OPEN REDIRECT (CWE-601) ---
    print("\n[1.2] Open Redirect (CWE-601) Defense:")
    evil_redirects = [
        "https://evil-attacker.com",
        "//evil-attacker.com",
        "javascript:alert(1)",
        "http://malicious-phishing.org/login"
    ]
    for target in evil_redirects:
        resp_support = client.post(f"/complaints/{ref}/support/", {"next": target}, follow=False)
        check(resp_support.url != target and not resp_support.url.startswith("http://malicious") and not resp_support.url.startswith("https://evil"),
              f"Prevent open redirect to {target}")

    # --- 1.3 FILE UPLOAD & MAGIC BYTES (CWE-434) ---
    print("\n[1.3] File Upload Security & Magic Byte Sanitization:")
    malicious_files = [
        ("exploit.html", b"<script>alert('xss')</script>", "text/html"),
        ("shell.php", b"<?php phpinfo(); ?>", "application/x-php"),
        ("virus.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-msdownload"),
        ("fake_image.jpg", b"NOT AN IMAGE FILE AT ALL", "image/jpeg"),
    ]
    for filename, content, ctype in malicious_files:
        upload = SimpleUploadedFile(filename, content, content_type=ctype)
        sanitized = compress_uploaded_image(upload)
        # It must either return None or NOT return the raw malicious file
        is_safe = (sanitized is None) or (not getattr(sanitized, "name", "").endswith((".html", ".php", ".exe")))
        check(is_safe, f"Reject/sanitize unsafe upload: {filename}")

    # --- 1.4 CSV FORMULA INJECTION (CWE-1236) ---
    print("\n[1.4] CSV Formula Injection (CWE-1236):")
    csv_injection_c = Complaint.objects.create(
        reporter_name="=cmd|'/C calc'!A0",
        reporter_enrollment_number="GQ8888",
        title="+2+5+cmd|' /C calc'!A0",
        description="@SUM(1+1)*cmd|' /C calc'!A0",
        category=cat,
        location_description="-DDE('cmd';'/C calc';'__test__')",
        is_public=False
    )
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser("sec_super_admin", "admin@sec.amu.edu", "Password123!")
    client.force_login(admin_user)
    resp_csv = client.get("/reports/complaints.csv")
    csv_content = resp_csv.content.decode()

    # Vulnerability check: Any unescaped cell starting with =, +, -, @
    raw_formula_found = any(bad in csv_content for bad in [",=cmd|", "\n=cmd|", ",+2+5+", "\n+2+5+", ",-DDE", "\n-DDE", ",@SUM", "\n@SUM"])
    check(not raw_formula_found, "CSV export sanitizes spreadsheet formula triggers (=, +, -, @)")
    csv_injection_c.delete()

    # --- 1.5 MULTI-TENANT RBAC ROW-LEVEL BOUNDARIES ---
    print("\n[1.5] Multi-Tenant RBAC Row-Level Isolation:")
    halls = list(Building.objects.filter(is_active=True, parent__isnull=True)[:2])
    if len(halls) >= 2:
        hall_1, hall_2 = halls[0], halls[1]
        provost_1, _ = User.objects.get_or_create(username="provost_sec_1")
        p1_prof, _ = UserProfile.objects.get_or_create(user=provost_1)
        p1_prof.role = UserProfile.Role.PROVOST
        p1_prof.managed_building = hall_1
        p1_prof.save()

        # Ticket in Hall 2
        r2 = Room.objects.filter(floor__building=hall_2).first()
        comp_hall2 = Complaint.objects.create(
            reporter_name="Student Hall 2",
            reporter_enrollment_number="GQ7777",
            title="Private Hall 2 Issue",
            description="Details for Hall 2 only",
            category=cat,
            room=r2,
            location_description=hall_2.name,
            is_public=False
        )

        client.force_login(provost_1)
        # Provost 1 tries to view Hall 2 ticket
        resp_v = client.get(f"/complaints/{comp_hall2.reference}/")
        check(resp_v.status_code == 302 and "dashboard" in resp_v.url,
              "Provost 1 cannot view complaints from Hall 2 (Redirected with Access Denied)")

        # Provost 1 tries to assign Hall 2 ticket
        resp_a = client.post(f"/complaints/{comp_hall2.reference}/assign/", {"assigned_to": provost_1.id})
        check(resp_a.status_code == 302 and "dashboard" in resp_a.url,
              "Provost 1 cannot assign complaints from Hall 2")

        # Provost 1 tries to update status of Hall 2 ticket
        resp_s = client.post(f"/complaints/{comp_hall2.reference}/status/", {"status": "in_progress"})
        check(resp_s.status_code == 302 and "dashboard" in resp_s.url,
              "Provost 1 cannot update status of complaints from Hall 2")

        # Provost 1 tries to resolve Hall 2 ticket
        resp_r = client.post(f"/complaints/{comp_hall2.reference}/admin-resolve/", {"resolution_note": "unauth"})
        check(resp_r.status_code == 302 and "dashboard" in resp_r.url,
              "Provost 1 cannot resolve complaints from Hall 2")

        comp_hall2.delete()
        client.logout()

    # --- 1.6 CSRF ENFORCEMENT ---
    print("\n[1.6] CSRF Protection Enforcement:")
    csrf_client = Client(enforce_csrf_checks=True)
    post_endpoints = [
        "/complaints/new/",
        f"/complaints/{ref}/assign/",
        f"/complaints/{ref}/status/",
        f"/complaints/{ref}/support/",
    ]
    for ep in post_endpoints:
        resp_csrf = csrf_client.post(ep, {"test": "data"})
        check(resp_csrf.status_code == 403, f"CSRF strictly enforced on {ep} (HTTP 403)")

    # --- 1.7 ANTI-ABUSE RATE LIMITING ---
    print("\n[1.7] Anti-Abuse Rate Limiting:")
    # We test with rate limiting enabled
    rate_limited_hit = False
    rate_client = Client()
    for _ in range(75):
        resp_rl = rate_client.post("/track/", {"tracking_token": "probe_attack_token"})
        if resp_rl.status_code == 429:
            rate_limited_hit = True
            break
    check(rate_limited_hit, "Rate limiting triggers HTTP 429 on abuse attempts")

    # --- 1.8 ENROLLMENT REGEX ENFORCEMENT ---
    print("\n[1.8] Enrollment Number Strict Pattern Validation:")
    invalid_enrollments = ["123456", "abc1234", "gq123", "gq12345", "!@1234", "GQ-1234", "   "]
    val_client = Client()
    for bad_enr in invalid_enrollments:
        r_enr = val_client.post("/complaints/new/", {
            "reporter_name": "Test Student",
            "reporter_enrollment_number": bad_enr,
            "title": "Broken Switch",
            "category": cat.id,
            "description": "Switch is broken.",
            "location_description": "Room 101"
        })
        # Must not redirect to tracking, must redisplay form with error
        check(r_enr.status_code == 200 and "Invalid Enrollment Number" in r_enr.content.decode() or "required" in r_enr.content.decode(),
              f"Reject invalid enrollment format: '{bad_enr}'")

    # Cleanup test ticket
    c.delete()

    print("\n" + "=" * 80)
    print(f"PILLAR 1 SUMMARY: {passed} PASSED | {failed} FAILED (Total: {passed + failed})")
    print("=" * 80)
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
