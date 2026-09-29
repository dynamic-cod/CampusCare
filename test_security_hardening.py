#!/usr/bin/env python3
"""
Test Suite: Production Security Hardening Verification
Validates:
1. Rate Limiting on public complaint creation and token tracking.
2. Max cap of 3 concurrent active tickets per enrollment number (and resolved exclusion).
3. File Upload Magic Bytes, Decompression Bomb (10MP), and UUID Filename Hardening.
4. Tenant Isolation & IDOR Protection for ID lookups, plus Technician Task Read-Only after resolution.
5. Environment & Security Headers verification.
"""

import io
import os
import sys
import uuid
import django
from PIL import Image

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
django.setup()

from django.conf import settings
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from core.models import Complaint, ComplaintCategory, Building, Room, UserProfile
from core.utils import compress_uploaded_image, validate_image_magic_bytes
from core.forms import ComplaintSubmissionForm
from core.views.helpers import is_rate_limited
from django.core.cache import cache


def run_tests():
    print("=" * 80)
    print("🔒 SECURITY HARDENING VERIFICATION TEST SUITE")
    print("=" * 80)

    passed = 0
    failed = 0

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

    # -------------------------------------------------------------------------
    # TEST 1: Rate Limiting & Anti-Enumeration
    # -------------------------------------------------------------------------
    print("\n[1] Rate Limiting & Anti-Enumeration:")
    cache.clear()
    client = Client()

    # 1.1 IP Rate limit helper function works with ip_only
    class MockRequest:
        def __init__(self, ip):
            self.META = {"REMOTE_ADDR": ip}
            self.user = None

    mock_req = MockRequest("198.51.100.1")
    # Simulate exceeding 3 requests in test window
    is_rate_limited(mock_req, key_prefix="test_rl", max_requests=3, window_seconds=60, ip_only=True)
    is_rate_limited(mock_req, key_prefix="test_rl", max_requests=3, window_seconds=60, ip_only=True)
    is_rate_limited(mock_req, key_prefix="test_rl", max_requests=3, window_seconds=60, ip_only=True)
    over_limit = is_rate_limited(mock_req, key_prefix="test_rl", max_requests=3, window_seconds=60, ip_only=True)
    check(over_limit is True, "is_rate_limited correctly flags requests exceeding threshold for IP")

    # 1.2 Max cap of 3 concurrent active tickets per enrollment number
    cat = ComplaintCategory.objects.first()
    test_enrollment = "GQ1111"
    Complaint.objects.filter(reporter_enrollment_number=test_enrollment).delete()

    # Create 3 active complaints
    c1 = Complaint.objects.create(
        reporter_name="Student Limit Test",
        reporter_enrollment_number=test_enrollment,
        title="Active Issue 1",
        description="First issue",
        category=cat,
        location_description="Sir Syed Hall",
        status=Complaint.Status.OPEN,
    )
    c2 = Complaint.objects.create(
        reporter_name="Student Limit Test",
        reporter_enrollment_number=test_enrollment,
        title="Active Issue 2",
        description="Second issue",
        category=cat,
        location_description="Sir Syed Hall",
        status=Complaint.Status.ASSIGNED,
    )
    c3 = Complaint.objects.create(
        reporter_name="Student Limit Test",
        reporter_enrollment_number=test_enrollment,
        title="Active Issue 3",
        description="Third issue",
        category=cat,
        location_description="Sir Syed Hall",
        status=Complaint.Status.IN_PROGRESS,
    )

    form_data = {
        "reporter_name": "Student Limit Test",
        "reporter_enrollment_number": test_enrollment,
        "title": "Blocked 4th Active Issue",
        "description": "Should be rejected because 3 active tickets exist",
        "category": cat.id,
        "location_description": "Sir Syed Hall Room 101",
    }
    form = ComplaintSubmissionForm(data=form_data)
    form_is_valid = form.is_valid()
    check(
        form_is_valid is False and "Active ticket limit reached" in str(form.errors),
        "Complaint form enforces max cap of 3 active tickets per enrollment number",
    )

    # Now mark one complaint as RESOLVED -> form should now be accepted
    c1.status = Complaint.Status.RESOLVED
    c1.save(update_fields=["status"])
    form_after_resolve = ComplaintSubmissionForm(data=form_data)
    check(
        form_after_resolve.is_valid(),
        "Resolved ticket does NOT count towards active ticket cap, allowing new submission",
    )

    # Cleanup
    Complaint.objects.filter(reporter_enrollment_number=test_enrollment).delete()

    # -------------------------------------------------------------------------
    # TEST 2: File Upload & Media Hardening
    # -------------------------------------------------------------------------
    print("\n[2] File Upload & Media Hardening:")

    # 2.1 Magic byte validation
    jpeg_buf = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 30)
    png_buf = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 30)
    webp_buf = io.BytesIO(b"RIFF\x20\x00\x00\x00WEBPVP8 " + b"\x00" * 20)
    fake_buf = io.BytesIO(b"<!DOCTYPE html><html><body>malicious</body></html>")

    check(validate_image_magic_bytes(jpeg_buf) == "image/jpeg", "Magic bytes recognize image/jpeg")
    check(validate_image_magic_bytes(png_buf) == "image/png", "Magic bytes recognize image/png")
    check(validate_image_magic_bytes(webp_buf) == "image/webp", "Magic bytes recognize image/webp")
    check(validate_image_magic_bytes(fake_buf) is None, "Magic bytes reject non-image payloads")

    # 2.2 Decompression bomb protection (10_000_000 pixels)
    check(Image.MAX_IMAGE_PIXELS == 10_000_000, "Image.MAX_IMAGE_PIXELS is set to 10,000,000")
    bomb_buf = io.BytesIO()
    img_bomb = Image.new("RGB", (4000, 3000), color="red")  # 12 MP
    img_bomb.save(bomb_buf, format="JPEG")
    bomb_buf.seek(0)
    f_bomb = SimpleUploadedFile("bomb.jpg", bomb_buf.read(), content_type="image/jpeg")
    compressed_bomb = compress_uploaded_image(f_bomb)
    check(compressed_bomb is None, "Decompression bomb (> 10MP) is strictly rejected")

    # 2.3 Randomized UUID Filenames (original filename stripped)
    valid_buf = io.BytesIO()
    img_valid = Image.new("RGB", (400, 300), color="blue")
    img_valid.save(valid_buf, format="PNG")
    valid_buf.seek(0)
    f_valid = SimpleUploadedFile("../../secret_student_name_exploit.png", valid_buf.read(), content_type="image/png")
    compressed_valid = compress_uploaded_image(f_valid)
    check(
        compressed_valid is not None
        and compressed_valid.name.endswith(".jpg")
        and len(compressed_valid.name) == 36
        and "secret" not in compressed_valid.name
        and "exploit" not in compressed_valid.name,
        "Original filename stripped and replaced by randomized UUID hex filename (.jpg)",
    )

    # -------------------------------------------------------------------------
    # TEST 3: Tenant Isolation & IDOR Protection
    # -------------------------------------------------------------------------
    print("\n[3] Tenant Isolation & IDOR Protection:")
    halls = list(Building.objects.filter(is_active=True, parent__isnull=True)[:2])
    if len(halls) >= 2:
        hall_a, hall_b = halls[0], halls[1]
        provost_user, _ = User.objects.get_or_create(username="provost_tenant_test")
        p_prof, _ = UserProfile.objects.get_or_create(user=provost_user)
        p_prof.role = UserProfile.Role.PROVOST
        p_prof.managed_building = hall_a
        p_prof.save()

        # Ticket in Hall B
        c_hall_b = Complaint.objects.create(
            reporter_name="Hall B Student",
            reporter_enrollment_number="GQ2222",
            title="Hall B Issue",
            description="Tenant isolation check",
            category=cat,
            location_description=hall_b.name,
            status=Complaint.Status.OPEN,
        )

        client.force_login(provost_user)
        # Direct integer ID lookup on complaints in another jurisdiction must be blocked (HTTP 404)
        resp_id_detail = client.get(f"/dashboard/complaints/{c_hall_b.id}/")
        check(
            resp_id_detail.status_code == 404,
            "Direct integer ID lookup for out-of-scope ticket returns HTTP 404 (IDOR blocked)",
        )

        resp_id_status = client.post(f"/dashboard/complaints/{c_hall_b.id}/status/", {"status": "in_progress"})
        check(
            resp_id_status.status_code == 404,
            "Direct integer ID status update for out-of-scope ticket returns HTTP 404 (IDOR blocked)",
        )
        client.logout()
        c_hall_b.delete()

    # 3.2 Staff task token reuse prevention (read-only once resolved)
    staff_user, _ = User.objects.get_or_create(username="staff_task_tester", is_staff=True)
    c_task = Complaint.objects.create(
        reporter_name="Task Test Student",
        reporter_enrollment_number="GQ3333",
        title="Technician Token Reuse Test",
        description="Verify task cannot be modified after resolution",
        category=cat,
        assigned_to=staff_user,
        location_description="Campus",
        status=Complaint.Status.RESOLVED,
    )
    task_url = f"/task/{c_task.staff_task_token}/"
    client.logout()

    # GET must show read-only
    resp_task_get = client.get(task_url)
    check(
        resp_task_get.status_code == 200 and "READ-ONLY" in resp_task_get.content.decode(),
        "Technician task GET page displays READ-ONLY badge when resolved",
    )

    # POST must be rejected with 400
    resp_task_post = client.post(task_url, {"action": "start"})
    check(
        resp_task_post.status_code == 400 and "read-only" in resp_task_post.content.decode().lower(),
        "Technician task POST is blocked with HTTP 400 once task is resolved (Token reuse prevented)",
    )
    c_task.delete()

    # -------------------------------------------------------------------------
    # TEST 4: Environment & Security Headers
    # -------------------------------------------------------------------------
    print("\n[4] Environment & Security Headers:")
    check(settings.SECURE_CONTENT_TYPE_NOSNIFF is True, "SECURE_CONTENT_TYPE_NOSNIFF is True")
    check(settings.X_FRAME_OPTIONS == "DENY", "X_FRAME_OPTIONS is 'DENY'")
    check(settings.CSRF_COOKIE_HTTPONLY is True, "CSRF_COOKIE_HTTPONLY is True")
    check(settings.SESSION_COOKIE_HTTPONLY is True, "SESSION_COOKIE_HTTPONLY is True")
    check(
        len(settings.SECRET_KEY) >= 50 and not settings.SECRET_KEY.startswith("django-insecure"),
        "SECRET_KEY is loaded securely (length >= 50, not django-insecure)",
    )

    print("\n" + "=" * 80)
    print(f"SECURITY HARDENING SUMMARY: {passed} PASSED | {failed} FAILED (Total: {passed + failed})")
    print("=" * 80)
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
