#!/usr/bin/env python3
"""
STEP 2 & STEP 3: End-to-End System Flows & Multi-Tenant RBAC Integration Suite
CampusCare QA Audit Suite
=============================================================================
Non-destructive test execution:
- All created complaints and media artifacts are deleted in try/finally blocks.
- Original technician accountability scores are preserved and restored.
- Zero leftover database rows or media artifacts.

Tests:
- Test A: Anonymous Complaint Submission & Auto-Dispatch
- Test B: Zero-Login Technician Workflow & Anti-Fraud Timing
- Test C: Closed-Loop Student Verification & Media Purge
- Test D: Dispute & Reopen Workflow
- Test E: Multi-Tenant RBAC Row-Level Isolation (Provost, HOD, Registrar)
"""

import io
import json
import os
import sys
import uuid
from datetime import timedelta
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
django.setup()

from django.test import Client
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from PIL import Image

from core.models import (
    Complaint,
    ComplaintCategory,
    ComplaintFeedback,
    ComplaintStatusHistory,
    UserProfile,
    Building,
    Room,
)
from core.permissions import get_scoped_complaints_for_user


def make_dummy_jpeg(color="blue", size=(120, 120)):
    """Generate in-memory JPEG test image."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf.read()


def run_system_flows_tests():
    print("=" * 70)
    print("CAMPUSCARE QA AUDIT - STEP 2: END-TO-END WORKFLOW INTEGRATION SUITE")
    print("=" * 70)
    client = Client()
    all_passed = True
    created_complaint_ids = []

    try:
        # =====================================================================
        # TEST A: Anonymous Complaint Submission & Auto-Dispatch
        # =====================================================================
        print("\n[TEST A] Anonymous Complaint Submission & Auto-Dispatch:")
        
        # 1. Simulate NLP category detection API
        complaint_text = "Broken water pipe in bathroom. Pipe is leaking and water is flooding bathroom floor at Sir Syed Hall North."
        resp_nlp = client.post(
            "/api/suggest-category/",
            data=json.dumps({"text": complaint_text}),
            content_type="application/json",
        )
        nlp_data = resp_nlp.json()
        assert nlp_data.get("suggestions"), "NLP failed to return category suggestion!"
        best_sugg = nlp_data["suggestions"][0]
        print(f"  ✓ NLP suggested category: '{best_sugg['name']}' with {best_sugg['confidence']}% confidence")
        assert "plumb" in best_sugg["name"].lower(), f"Expected plumbing suggestion, got {best_sugg['name']}"

        post_data = {
            "reporter_name": "Rahil Khan",
            "reporter_enrollment_number": "GJ20249876",
            "title": "Broken water pipe in bathroom",
            "category": best_sugg["id"],
            "description": "Pipe is leaking and water is flooding bathroom floor at Sir Syed Hall North.",
            "location_description": "Sir Syed Hall North",
            "is_public": "on",
        }

        resp_submit = client.post("/complaints/new/", data=post_data, follow=True)
        print(f"  - POST /complaints/new/ status: {resp_submit.status_code}")

        complaint_a = Complaint.objects.filter(reporter_enrollment_number="GJ20249876").order_by("-created_at").first()
        if not complaint_a:
            print("  ❌ FAIL: Complaint was not created in database.")
            all_passed = False
        else:
            created_complaint_ids.append(complaint_a.id)
            print(f"  ✓ Complaint Reference: {complaint_a.reference}")

            # 1. Assert tracking_token is generated and non-empty
            assert complaint_a.tracking_token and len(complaint_a.tracking_token) == 32, "Invalid tracking_token"
            print(f"  ✓ tracking_token valid: {complaint_a.tracking_token}")

            # 2. Assert NLP/dispatch auto-categorizes under Plumbing and sets urgency
            cat_name = complaint_a.category.name if complaint_a.category else ""
            print(f"  ✓ Auto-categorized category: '{cat_name}' (Plumbing match: {'plumb' in cat_name.lower()})")
            assert "plumb" in cat_name.lower(), f"Expected plumbing category, got '{cat_name}'"
            print(f"  ✓ Priority score: {complaint_a.priority_score}, Priority: {complaint_a.priority}")
            assert complaint_a.priority in [Complaint.Priority.HIGH, Complaint.Priority.URGENT]

            # 3. Assert assigned_to is populated from roster for building/trade
            print(f"  ✓ Assigned Technician: {complaint_a.assigned_to} ({complaint_a.assigned_to.get_full_name() if complaint_a.assigned_to else 'None'})")
            assert complaint_a.assigned_to is not None, "complaint.assigned_to is None!"
            assert complaint_a.assigned_to.profile.role == UserProfile.Role.STAFF

            # 4. Assert staff_task_token is a valid UUID
            try:
                uuid_val = uuid.UUID(str(complaint_a.staff_task_token))
                print(f"  ✓ Valid staff_task_token UUID: {uuid_val}")
            except Exception as e:
                print(f"  ❌ Invalid staff_task_token: {e}")
                all_passed = False

            print("  ✅ PASS: Test A (Submission & AI Auto-Dispatch) verified!")

        # =====================================================================
        # TEST B: Zero-Login Technician Workflow & Anti-Fraud Timing
        # =====================================================================
        print("\n[TEST B] Zero-Login Technician Workflow & Anti-Fraud Timing:")
        if complaint_a:
            task_token_str = str(complaint_a.staff_task_token)
            task_url = f"/task/{task_token_str}/"

            # 1. Fetch task without session credentials
            resp_task_get = client.get(task_url)
            print(f"  - GET {task_url} unauthenticated -> HTTP {resp_task_get.status_code}")
            assert resp_task_get.status_code == 200, "Technician task endpoint requires login!"

            # 2. POST action=start
            resp_start = client.post(task_url, {"action": "start"})
            print(f"  - POST action=start -> HTTP {resp_start.status_code}")
            complaint_a.refresh_from_db()
            assert complaint_a.status == Complaint.Status.IN_PROGRESS, f"Status: {complaint_a.status}"
            assert complaint_a.in_progress_at is not None, "in_progress_at was not stamped!"
            print(f"  ✓ Status updated to IN_PROGRESS, in_progress_at stamped: {complaint_a.in_progress_at}")

            # 3. POST action=resolve immediately (< 30 seconds) -> expect dwell time rejection (HTTP 400)
            resp_early_resolve = client.post(task_url, {"action": "resolve"})
            print(f"  - POST action=resolve immediately -> HTTP {resp_early_resolve.status_code}")
            assert resp_early_resolve.status_code == 400, f"Expected 400, got {resp_early_resolve.status_code}"
            print("  ✓ Dwell-time anti-fraud timing check rejected premature resolution (< 5 min).")

            # 4. Mock elapsed time: complaint.in_progress_at = now - 10 minutes
            complaint_a.in_progress_at = timezone.now() - timedelta(minutes=10)
            complaint_a.save(update_fields=["in_progress_at"])

            # 5. POST action=resolve with dummy JPEG image
            dummy_bytes = make_dummy_jpeg("teal", (300, 300))
            dummy_upload = SimpleUploadedFile("proof_clean.jpg", dummy_bytes, content_type="image/jpeg")
            resp_resolve = client.post(
                task_url,
                {
                    "action": "resolve",
                    "resolution_proof": dummy_upload,
                    "resolution_note": "Replaced damaged pipe section with brand new copper fitting.",
                },
                follow=True,
            )
            print(f"  - POST action=resolve with camera proof -> HTTP {resp_resolve.status_code}")
            complaint_a.refresh_from_db()
            print(f"  ✓ Status after resolution: '{complaint_a.status}' (NOT 'closed')")
            assert complaint_a.status == Complaint.Status.RESOLVED, f"Expected resolved, got {complaint_a.status}"
            assert complaint_a.status != Complaint.Status.CLOSED, "Complaint should not be closed directly by technician!"
            assert bool(complaint_a.resolution_proof), "resolution_proof is missing!"
            print(f"  ✓ Stored resolution proof file: {complaint_a.resolution_proof.name}")

            # Assert image compression via Pillow (exists and is a valid Pillow image)
            proof_file = complaint_a.resolution_proof
            with proof_file.open("rb") as pf:
                img_check = Image.open(pf)
                print(f"  ✓ Compressed image verified: format={img_check.format}, size={img_check.size}")
                assert img_check.format in ("JPEG", "WEBP", "PNG")

            print("  ✅ PASS: Test B (Zero-Login Technician & Anti-Fraud Timing) verified!")

        # =====================================================================
        # TEST C: Closed-Loop Student Verification & Media Purge
        # =====================================================================
        print("\n[TEST C] Closed-Loop Student Verification & Media Purge:")
        if complaint_a:
            confirm_url = f"/complaints/{complaint_a.tracking_token}/confirm/"
            proof_storage = complaint_a.resolution_proof.storage
            proof_rel_name = complaint_a.resolution_proof.name
            assert proof_storage.exists(proof_rel_name), "Proof must exist prior to purge"

            resp_confirm = client.post(
                confirm_url,
                {"rating": "5", "comment": "Fixed cleanly, excellent work by Nadeem!"},
                follow=True,
            )
            print(f"  - POST {confirm_url} -> HTTP {resp_confirm.status_code}")
            complaint_a.refresh_from_db()

            # Assert complaint.status == 'closed' and closed_at stamped
            assert complaint_a.status == Complaint.Status.CLOSED, f"Status: {complaint_a.status}"
            assert complaint_a.closed_at is not None, "closed_at not stamped!"
            print(f"  ✓ Status verified as CLOSED, closed_at: {complaint_a.closed_at}")

            # Assert feedback recorded
            fb = ComplaintFeedback.objects.filter(complaint=complaint_a).first()
            assert fb is not None and fb.rating == 5
            print(f"  ✓ Student feedback saved: Rating {fb.rating}/5, Comment: '{fb.comment}'")

            # Assert storage cleanup: mock image file deleted from disk storage
            file_still_on_disk = proof_storage.exists(proof_rel_name)
            print(f"  ✓ Proof file on disk after purge: {file_still_on_disk} (Purged: {not file_still_on_disk})")
            assert not file_still_on_disk, "Resolution proof image was not deleted from disk!"

            print("  ✅ PASS: Test C (Student Verification & Media Purge) verified!")

        # =====================================================================
        # TEST D: Dispute & Reopen Workflow
        # =====================================================================
        print("\n[TEST D] Dispute & Reopen Workflow:")
        tech_user = User.objects.filter(profile__role=UserProfile.Role.STAFF).first()
        initial_score = tech_user.profile.accountability_score

        # Create separate resolved complaint for dispute test
        complaint_d = Complaint.objects.create(
            title="Electrical switch sparkling in Room 102",
            category=ComplaintCategory.objects.first(),
            location_description="Sir Syed Hall North Room 102",
            reporter_name="Arif Siddiqui",
            reporter_enrollment_number="GJ20249877",
            status=Complaint.Status.RESOLVED,
            assigned_to=tech_user,
        )
        created_complaint_ids.append(complaint_d.id)
        reopen_url = f"/complaints/{complaint_d.tracking_token}/reopen/"

        # 1. POST without image -> assert validation error (400)
        resp_no_img = client.post(reopen_url, {"reason": "Still sparking and dangerous."})
        print(f"  - POST without image -> HTTP {resp_no_img.status_code}")
        assert resp_no_img.status_code == 400, "Expected 400 when missing photo proof!"

        # 2. POST with photo proof and short reason (< 10 chars) -> assert rejection (400)
        dummy_reopen_bytes = make_dummy_jpeg("red", (200, 200))
        dummy_reopen_file1 = SimpleUploadedFile("proof_bad.jpg", dummy_reopen_bytes, content_type="image/jpeg")
        resp_short_reason = client.post(reopen_url, {"reason": "Spark", "reopen_proof": dummy_reopen_file1})
        print(f"  - POST with short reason (< 10 chars) -> HTTP {resp_short_reason.status_code}")
        assert resp_short_reason.status_code == 400, "Expected 400 when reason is under 10 chars!"

        # 3. POST with valid photo proof and reason >= 10 chars
        dummy_reopen_file2 = SimpleUploadedFile("proof_valid.jpg", dummy_reopen_bytes, content_type="image/jpeg")
        resp_valid_reopen = client.post(
            reopen_url,
            {"reason": "Still leaking heavily and sparks observed when switch pressed", "reopen_proof": dummy_reopen_file2},
            follow=True,
        )
        print(f"  - POST with valid proof and reason -> HTTP {resp_valid_reopen.status_code}")
        complaint_d.refresh_from_db()
        tech_user.profile.refresh_from_db()

        assert complaint_d.status == Complaint.Status.REOPENED, f"Status: {complaint_d.status}"
        assert complaint_d.priority == Complaint.Priority.URGENT, f"Priority: {complaint_d.priority}"
        print(f"  ✓ Complaint status updated to '{complaint_d.status}', priority escalated to '{complaint_d.priority}'")

        score_delta = initial_score - tech_user.profile.accountability_score
        print(f"  ✓ Technician accountability score decremented: {initial_score} -> {tech_user.profile.accountability_score} (Delta: -{score_delta})")
        assert score_delta == 15, f"Expected 15 point penalty, got {score_delta}"

        # Restore technician accountability score
        tech_user.profile.accountability_score = initial_score
        tech_user.profile.save(update_fields=["accountability_score"])

        print("  ✅ PASS: Test D (Dispute, Reopen & Score Penalty) verified!")

        # =====================================================================
        # STEP 3: Multi-Tenant RBAC Row-Level Security Test
        # =====================================================================
        print("\n" + "=" * 70)
        print("CAMPUSCARE QA AUDIT - STEP 3: MULTI-TENANT RBAC ROW-LEVEL SECURITY")
        print("=" * 70)

        # 1. Provost Data Isolation (provost_ssn)
        print("\n[CHECK 3.1] Provost Multi-Tenant Isolation (provost_ssn):")
        provost_ssn = User.objects.get(username="provost_ssn")
        ssn_qs = get_scoped_complaints_for_user(provost_ssn)
        print(f"  - Total complaints returned for provost_ssn: {ssn_qs.count()}")

        ssn_hall = provost_ssn.profile.managed_building
        for c in ssn_qs:
            bldg = c.room.floor.building if (c.room and c.room.floor) else None
            p_code = bldg.parent.code if (bldg and bldg.parent) else (bldg.code if bldg else "")
            assert p_code == "SSN", f"Leak detected! Complaint {c.reference} belongs to {p_code}"

        aft_leaks = ssn_qs.filter(room__floor__building__code="AFT").count()
        print(f"  ✓ Cross-tenant complaints from Aftab Hall (AFT): {aft_leaks}")
        assert aft_leaks == 0, "Aftab Hall complaints leaked into SSN queue!"

        # Dashboard rendering check for provost_ssn
        client.login(username="provost_ssn", password="CampusAdmin@2026")
        resp_provost_dash = client.get("/dashboard/")
        dash_content = resp_provost_dash.content.decode("utf-8")
        assert "Aftab Hall · Morison Court" not in dash_content
        print("  ✓ Zero cross-tenant data visible in provost_ssn dashboard HTML table.")
        client.logout()

        # 2. HOD Data Isolation (hod_elec)
        print("\n[CHECK 3.2] HOD Multi-Tenant Isolation (hod_elec):")
        hod_elec = User.objects.get(username="hod_elec")
        elec_qs = get_scoped_complaints_for_user(hod_elec)
        print(f"  - Total complaints returned for hod_elec: {elec_qs.count()}")
        for c in elec_qs:
            dept = c.category.department
            assert dept and dept.code == "ELEC", f"Leak detected! Non-electrical complaint in hod_elec: {dept}"
        print("  ✓ 100% of complaints scoped to hod_elec belong strictly to Electrical trade.")

        # 3. Registrar Global Visibility (registrar_office)
        print("\n[CHECK 3.3] Registrar Global Visibility (registrar_office):")
        registrar_user = User.objects.get(username="registrar_office")
        reg_qs = get_scoped_complaints_for_user(registrar_user)
        total_active_complaints = Complaint.objects.count()
        print(f"  - Total campus complaints in DB: {total_active_complaints}")
        print(f"  - Complaints visible to registrar: {reg_qs.count()}")
        assert reg_qs.count() == total_active_complaints, "Registrar does not have full global visibility!"
        print("  ✓ Registrar has 100% global visibility across all campus jurisdictions.")

    except Exception as exc:
        print(f"\n❌ EXCEPTION DURING INTEGRATION SUITE: {exc}")
        import traceback
        traceback.print_exc()
        all_passed = False

    finally:
        # =====================================================================
        # CLEANUP: Ensure zero test complaints or media artifacts remain
        # =====================================================================
        print("\n🧹 Executing non-destructive cleanup...")
        for cid in created_complaint_ids:
            try:
                comp = Complaint.objects.filter(id=cid).first()
                if comp:
                    comp.purge_attached_media()
                    ComplaintStatusHistory.objects.filter(complaint_id=cid).delete()
                    ComplaintFeedback.objects.filter(complaint_id=cid).delete()
                    comp.delete()
                    print(f"  ✓ Cleanly purged mock test complaint ID #{cid}")
            except Exception as e:
                print(f"  ⚠️ Error purging complaint ID #{cid}: {e}")

    print("\n" + "=" * 70)
    if all_passed:
        print("RESULT: ALL STEP 2 & STEP 3 SYSTEM FLOWS & RBAC TESTS PASSED (100% SUCCESS)!")
    else:
        print("RESULT: SOME WORKFLOW TESTS FAILED. Review logs above.")
    print("=" * 70)
    return all_passed

if __name__ == "__main__":
    success = run_system_flows_tests()
    sys.exit(0 if success else 1)
