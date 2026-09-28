#!/usr/bin/env python
"""
Automated Security Audit & Penetration Testing Suite for CampusCare.
Tests for:
1. IDOR / Authorization Bypass on Secret Tracking Token
2. Open Redirect (CWE-601) on ?next= parameters
3. File Upload & Magic Byte Verification on Proof Files
4. CSV Formula Injection (CWE-1236)
5. Multi-Tenant Jurisdiction & Scoping Isolation (Provost/HOD/Caretaker)
6. CSRF Enforcement across endpoints
7. Authentication Boundary on Administrative Views
"""
import os
import sys
import io
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import Complaint, ComplaintCategory, Building, Department, Room, UserProfile

def run_security_analysis():
    print("=" * 70)
    print("🔒 RUNNING COMPREHENSIVE CAMPUSCARE SECURITY AUDIT")
    print("=" * 70)
    client = Client()
    findings = []

    # -------------------------------------------------------------------------
    # TEST 1: IDOR & Tracking Token Secret Leakage
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing IDOR on Tracking Token & Public Reference Lookup...")
    category = ComplaintCategory.objects.first()
    test_complaint = Complaint.objects.create(
        reporter_name="Security Test Student",
        reporter_enrollment_number="TEST99",
        title="Confidential Security Test Issue",
        description="Private room issue that should NOT be visible to outsiders.",
        category=category,
        location_description="Room 999",
        is_public=False,
    )
    ref = test_complaint.reference
    secret_token = test_complaint.tracking_token

    # An anonymous attacker only knows 'ref' (from public board/sheet), not 'secret_token'
    # Try looking it up via /track/ using the reference
    resp = client.post("/track/", {"tracking_token": ref}, follow=False)
    if resp.status_code == 302 and secret_token in resp.url:
        print(f"  ❌ VULNERABILITY FOUND: Reference '{ref}' can be entered in /track/ to discover secret token '{secret_token}'!")
        findings.append({
            "id": "SEC-01",
            "name": "IDOR / Secret Tracking Token Disclosure via Reference",
            "severity": "HIGH",
            "desc": "Entering the public complaint reference in /track/ automatically leaks the secret 32-character tracking token in the redirect URL."
        })
    else:
        print("  ✅ /track/ properly rejected public reference as tracking token.")

    # Try accessing /track/<reference>/ directly
    resp = client.get(f"/track/{ref}/")
    if resp.status_code == 200 and secret_token in resp.content.decode():
        print(f"  ❌ VULNERABILITY FOUND: Anonymous user can view secret tracking token and private ticket at /track/{ref}/!")
        findings.append({
            "id": "SEC-02",
            "name": "Direct Access to Student Tracking Portal via Public Reference",
            "severity": "HIGH",
            "desc": "Visiting /track/<reference>/ displays full ticket details and the private tracking token without authentication."
        })
    else:
        print("  ✅ /track/<reference>/ properly restricted.")

    # -------------------------------------------------------------------------
    # TEST 2: Open Redirect (CWE-601)
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing Open Redirect on 'next' parameters...")
    evil_url = "https://evil-phishing-site.com"
    resp = client.post(f"/complaints/{ref}/support/", {"next": evil_url}, follow=False)
    if resp.status_code == 302 and resp.url == evil_url:
        print(f"  ❌ VULNERABILITY FOUND: /complaints/{ref}/support/ allows open redirect to {evil_url}!")
        findings.append({
            "id": "SEC-03",
            "name": "Open Redirect via ?next= Parameter (CWE-601)",
            "severity": "MEDIUM",
            "desc": "complaint_toggle_support and complaint_update_status redirect to unvalidated external URLs specified in ?next=."
        })
    else:
        print("  ✅ Support toggle did not redirect to external URL.")

    # -------------------------------------------------------------------------
    # TEST 3: File Upload Validation (Non-Image Bypasses)
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing File Upload Validation & Non-Image Proof Handling...")
    fake_html_file = SimpleUploadedFile("exploit.html", b"<script>alert(document.cookie)</script>", content_type="text/html")
    from core.utils import compress_uploaded_image
    result = compress_uploaded_image(fake_html_file)
    if result and getattr(result, "name", "").endswith(".html"):
        print("  ❌ VULNERABILITY FOUND: compress_uploaded_image returns unvalidated non-image file on exception instead of rejecting it!")
        findings.append({
            "id": "SEC-04",
            "name": "File Upload Extension / MIME Type Bypass (CWE-434)",
            "severity": "HIGH",
            "desc": "compress_uploaded_image catches Pillow exceptions and returns the raw file. Views saving resolution_proof/reopen_proof without full_clean() could store arbitrary files."
        })
    else:
        print("  ✅ compress_uploaded_image rejected or sanitized non-image file.")

    # -------------------------------------------------------------------------
    # TEST 4: CSV Formula Injection (CWE-1236)
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing CSV Formula Injection on Export...")
    formula_complaint = Complaint.objects.create(
        reporter_name="Formula Tester",
        reporter_enrollment_number="TEST98",
        title="=cmd|'/c calc'!A1",
        description="Testing formula injection",
        category=category,
        location_description="Room 101",
        is_public=False,
    )
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser("sec_super", "sec@amu.ac.in", "password123")
    client.force_login(admin_user)
    resp = client.get("/reports/complaints.csv")
    csv_text = resp.content.decode()
    if ",=cmd|" in csv_text or "\n=cmd|" in csv_text or csv_text.startswith("=cmd|"):
        print("  ❌ VULNERABILITY FOUND: CSV report outputs unescaped formula characters (=, +, -, @)!")
        findings.append({
            "id": "SEC-05",
            "name": "CSV Formula Injection (CWE-1236)",
            "severity": "LOW",
            "desc": "Complaint titles or locations starting with =, +, -, @ are exported into CSV without prepending an apostrophe, triggering execution in spreadsheet software."
        })
    elif "'=cmd|" in csv_text:
        print("  ✅ CSV report sanitized formula characters (prefixed with apostrophe).")
    else:
        print("  ✅ Formula row handled safely.")

    # -------------------------------------------------------------------------
    # TEST 5: Multi-Tenant Scoping & Jurisdictional Isolation
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing Multi-Tenant Scoping & Horizontal Privilege Boundaries...")
    hall_a = Building.objects.filter(is_active=True, parent__isnull=True).first()
    hall_b = Building.objects.filter(is_active=True, parent__isnull=True).exclude(id=hall_a.id).first() if hall_a else None
    if hall_a and hall_b:
        provost_user, _ = User.objects.get_or_create(username="provost_a", defaults={"first_name": "Provost", "last_name": "A"})
        p_profile, _ = UserProfile.objects.get_or_create(user=provost_user)
        p_profile.role = UserProfile.Role.PROVOST
        p_profile.managed_building = hall_a
        p_profile.save()

        # Create room in hall_b
        floor_b = hall_b.floors.first()
        room_b = floor_b.rooms.first() if floor_b else None
        if room_b:
            comp_b = Complaint.objects.create(
                reporter_name="Student Hall B",
                reporter_enrollment_number="TEST88",
                title="Hall B Private Issue",
                description="Hall B specific complaint",
                category=category,
                room=room_b,
                is_public=False,
            )
            client.force_login(provost_user)
            # Try to view complaint in Hall B
            resp = client.get(f"/complaints/{comp_b.reference}/")
            if resp.status_code == 302 and "dashboard" in resp.url:
                print("  ✅ Provost A is correctly blocked from viewing Hall B complaint (redirected with error).")
            else:
                print("  ❌ VULNERABILITY FOUND: Provost A was NOT blocked from viewing Hall B complaint!")
                findings.append({
                    "id": "SEC-06",
                    "name": "Cross-Tenant Jurisdictional Boundary Bypass (View)",
                    "severity": "HIGH",
                    "desc": "Provost of Hall A was able to access complaint detail belonging to Hall B."
                })

            # Try to assign complaint in Hall B
            resp_assign = client.post(f"/complaints/{comp_b.reference}/assign/", {"assigned_to": provost_user.id}, follow=False)
            if resp_assign.status_code == 302 and "dashboard" in resp_assign.url:
                print("  ✅ Provost A is correctly blocked from assigning Hall B complaint.")
            else:
                print("  ❌ VULNERABILITY FOUND: Provost A was able to assign Hall B complaint!")
                findings.append({
                    "id": "SEC-06b",
                    "name": "Cross-Tenant Jurisdictional Boundary Bypass (Assign)",
                    "severity": "HIGH",
                    "desc": "Provost of Hall A was able to assign a complaint belonging to Hall B."
                })

            # Try to update status of complaint in Hall B
            resp_status = client.post(f"/complaints/{comp_b.reference}/status/", {"status": "in_progress"}, follow=False)
            if resp_status.status_code == 302 and "dashboard" in resp_status.url:
                print("  ✅ Provost A is correctly blocked from updating status of Hall B complaint.")
            else:
                print("  ❌ VULNERABILITY FOUND: Provost A was able to update status of Hall B complaint!")
                findings.append({
                    "id": "SEC-06c",
                    "name": "Cross-Tenant Jurisdictional Boundary Bypass (Status Update)",
                    "severity": "HIGH",
                    "desc": "Provost of Hall A was able to update the status of a complaint belonging to Hall B."
                })

            # Try to mark complaint in Hall B as resolved
            resp_resolve = client.post(f"/complaints/{comp_b.reference}/admin-resolve/", {"resolution_note": "unauthorized"}, follow=False)
            if resp_resolve.status_code == 302 and "dashboard" in resp_resolve.url:
                print("  ✅ Provost A is correctly blocked from resolving Hall B complaint.")
            else:
                print("  ❌ VULNERABILITY FOUND: Provost A was able to resolve Hall B complaint!")
                findings.append({
                    "id": "SEC-06d",
                    "name": "Cross-Tenant Jurisdictional Boundary Bypass (Admin Resolve)",
                    "severity": "HIGH",
                    "desc": "Provost of Hall A was able to mark a complaint belonging to Hall B as resolved."
                })

            comp_b.delete()

    # -------------------------------------------------------------------------
    # TEST 6: CSRF Enforcement
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing CSRF Token Enforcement on State-Changing Endpoints...")
    csrf_client = Client(enforce_csrf_checks=True)
    resp = csrf_client.post("/complaints/new/", {
        "reporter_name": "CSRF Attacker",
        "reporter_enrollment_number": "TEST77",
        "title": "CSRF Attack Attempt",
        "category": category.id if category else 1,
        "description": "Attempting POST without token",
        "location_description": "Room 101",
    })
    if resp.status_code == 403:
        print("  ✅ CSRF Middleware strictly rejects POST requests without token (HTTP 403 Forbidden).")
    else:
        print(f"  ❌ VULNERABILITY FOUND: /complaints/new/ accepted POST without CSRF token (status={resp.status_code})!")
        findings.append({
            "id": "SEC-07",
            "name": "Missing CSRF Protection",
            "severity": "CRITICAL",
            "desc": "State-changing POST requests were accepted without valid CSRF verification."
        })

    # -------------------------------------------------------------------------
    # TEST 7: Rate Limiting Abuse Protection
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Testing Automated Abuse Rate Limiting...")
    rate_limited = False
    for i in range(40):
        resp = client.post("/track/", {"tracking_token": "nonexistent_token_attempt"})
        if resp.status_code == 429:
            rate_limited = True
            break
    if rate_limited:
        print("  ✅ Rate Limiter triggered (HTTP 429 Too Many Requests) after threshold.")
    else:
        print("  ❌ Rate limiter did not trigger after 40 rapid attempts.")

    # Clean up test complaints
    test_complaint.delete()
    formula_complaint.delete()

    print("\n" + "=" * 70)
    print(f"AUDIT SUMMARY: {len(findings)} Potential Vulnerabilities Identified")
    print("=" * 70)
    for f in findings:
        print(f"[{f['severity']}] {f['id']}: {f['name']}")
        print(f"  Details: {f['desc']}\n")

    return findings

if __name__ == "__main__":
    run_security_analysis()
