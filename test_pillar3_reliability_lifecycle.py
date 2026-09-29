#!/usr/bin/env python3
"""
Pillar 3: Reliability, Automation & Lifecycle Edge Cases Test Suite
Comprehensive testing for:
1. Complete State Machine Transitions (OPEN -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> CLOSED)
2. Anti-Fraud 5-Minute Dwell Time Enforcement
3. Technician Cannot Force-Close (HTTP 403)
4. Student Verification Closed-Loop & Automated Media Purge from Disk
5. Dispute & Reopen Workflow (Score Penalty, Priority Escalation to URGENT)
6. Automated SLA Breach Escalation Engine
7. Duplicate Detection & Auto-Linking
8. Nullable Foreign Keys & NoneType Crash Resilience
"""
import os
import io
import sys
from datetime import timedelta
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
django.setup()

from django.test import Client
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from core.models import (
    Complaint, ComplaintCategory, ComplaintStatusHistory,
    UserProfile, Building, Room, Department
)
from core.accountability import escalate_overdue_complaints

def make_test_image(color="blue", size=(200, 200)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format="JPEG", quality=80)
    buf.seek(0)
    return buf.read()

def run_tests():
    print("=" * 80)
    print("⚙️  PILLAR 3: RELIABILITY, AUTOMATION & LIFECYCLE EDGE CASES TEST SUITE")
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

    cat = ComplaintCategory.objects.first()
    hall = Building.objects.filter(is_active=True).first()
    room = Room.objects.filter(floor__building=hall).first()

    # Technician user
    tech_user, _ = User.objects.get_or_create(username="p3_technician")
    tech_prof, _ = UserProfile.objects.get_or_create(user=tech_user)
    tech_prof.role = UserProfile.Role.STAFF
    tech_prof.accountability_score = 100
    tech_prof.save()

    # --- 3.1 ZERO-LOGIN TECHNICIAN & ANTI-FRAUD DWELL TIME ---
    print("\n[3.1] Technician Task Portal & Anti-Fraud Timing:")
    c1 = Complaint.objects.create(
        reporter_name="Lifecycle Student 1",
        reporter_enrollment_number="GQ1001",
        title="Burnt Wiring in Room",
        description="Electrical wiring sparking",
        category=cat,
        room=room,
        assigned_to=tech_user,
        status=Complaint.Status.ASSIGNED,
        location_description=hall.name
    )
    task_url = f"/task/{c1.staff_task_token}/"

    # Start task
    client.logout()
    resp_start = client.post(task_url, {"action": "start"})
    c1.refresh_from_db()
    check(c1.status == Complaint.Status.IN_PROGRESS and c1.in_progress_at is not None,
          "Technician 'start' action sets status=IN_PROGRESS and records in_progress_at")

    # Anti-fraud: Attempt resolve before 5 min dwell time
    proof_early = SimpleUploadedFile("early_proof.jpg", make_test_image(), content_type="image/jpeg")
    resp_early = client.post(task_url, {"action": "resolve", "resolution_proof": proof_early})
    check(resp_early.status_code == 400, "Anti-fraud timing rejects resolution under 5 minutes (HTTP 400)")

    # Anti-fraud: Technician cannot close ticket directly
    resp_close = client.post(task_url, {"action": "close"})
    check(resp_close.status_code == 403, "Technician is forbidden from closing ticket directly (HTTP 403)")

    # Backdate in_progress_at to 6 minutes ago and resolve
    c1.in_progress_at = timezone.now() - timedelta(minutes=6)
    c1.save(update_fields=["in_progress_at"])

    proof_ok = SimpleUploadedFile("valid_proof.jpg", make_test_image("green"), content_type="image/jpeg")
    resp_resolve = client.post(task_url, {
        "action": "resolve",
        "resolution_proof": proof_ok,
        "resolution_note": "Replaced damaged switchboard wiring cleanly."
    })
    c1.refresh_from_db()
    check(c1.status == Complaint.Status.RESOLVED and c1.resolution_verification == Complaint.ResolutionVerification.PENDING,
          "Valid resolve moves status to RESOLVED (pending verification), NOT auto-closed")

    # --- 3.2 STUDENT VERIFICATION & DISK MEDIA PURGE ---
    print("\n[3.2] Student Verification & Disk Media Purge:")
    proof_path = c1.resolution_proof.path if c1.resolution_proof else None
    check(bool(proof_path and os.path.exists(proof_path)), "Resolution proof file exists on disk prior to student confirmation")

    # Student confirms resolution
    confirm_url = f"/complaints/{c1.tracking_token}/confirm/"
    resp_confirm = client.post(confirm_url, {"rating": 5, "comment": "Excellent fix!"})
    c1.refresh_from_db()
    check(c1.status == Complaint.Status.CLOSED and c1.closed_at is not None,
          "Student confirmation successfully transitions ticket to CLOSED")
    check(c1.feedback.rating == 5, "Student 5-star rating recorded in feedback model")

    # Verify media purge on disk
    file_still_on_disk = os.path.exists(proof_path) if proof_path else False
    check(not file_still_on_disk and not bool(c1.resolution_proof),
          "Media purge deletes proof image from server storage upon closure (Privacy & Storage Protection)")

    # --- 3.3 DISPUTE & REOPEN WORKFLOW ---
    print("\n[3.3] Dispute & Reopen Workflow:")
    tech_prof.accountability_score = 100
    tech_prof.save()

    c2 = Complaint.objects.create(
        reporter_name="Lifecycle Student 2",
        reporter_enrollment_number="GQ1002",
        title="Tap Still Leaking After Fix",
        description="Water tap is still leaking",
        category=cat,
        room=room,
        assigned_to=tech_user,
        status=Complaint.Status.RESOLVED,
        location_description=hall.name,
        priority=Complaint.Priority.NORMAL
    )
    reopen_url = f"/complaints/{c2.tracking_token}/reopen/"

    # Reopen without image proof -> Rejected
    resp_no_img = client.post(reopen_url, {"reopen_reason": "Still leaking heavily here!"})
    check(resp_no_img.status_code == 400, "Reopen without photo evidence is rejected (HTTP 400)")

    # Reopen with short explanation (< 10 chars) -> Rejected
    proof_reopen = SimpleUploadedFile("reopen_evidence.jpg", make_test_image("red"), content_type="image/jpeg")
    resp_short = client.post(reopen_url, {"reopen_reason": "bad", "reopen_proof": proof_reopen})
    check(resp_short.status_code == 400, "Reopen with explanation under 10 chars is rejected (HTTP 400)")

    # Valid reopen with >= 10 chars and photo proof
    proof_reopen_valid = SimpleUploadedFile("reopen_evidence2.jpg", make_test_image("red"), content_type="image/jpeg")
    resp_reopen_ok = client.post(reopen_url, {
        "reopen_reason": "The tap continues to leak at full pressure after repair.",
        "reopen_proof": proof_reopen_valid
    })
    c2.refresh_from_db()
    tech_prof.refresh_from_db()

    check(c2.status == Complaint.Status.REOPENED, "Ticket status updated to REOPENED")
    check(c2.priority == Complaint.Priority.URGENT, "Priority automatically escalated to URGENT upon dispute")
    check(tech_prof.accountability_score == 85, f"Technician accountability score decremented: 100 -> {tech_prof.accountability_score} (-15 penalty)")

    # --- 3.4 AUTOMATED SLA BREACH ESCALATION ---
    print("\n[3.4] Automated SLA Breach Escalation Engine:")
    c3 = Complaint.objects.create(
        reporter_name="SLA Test Student",
        reporter_enrollment_number="GQ1003",
        title="Overdue Corridor Light",
        description="Corridor light dark for 3 days",
        category=cat,
        room=room,
        status=Complaint.Status.OPEN,
        sla_due_at=timezone.now() - timedelta(hours=2),
        escalation_level=0,
        location_description=hall.name
    )
    escalated_items = escalate_overdue_complaints()
    c3.refresh_from_db()

    check(c3 in escalated_items, "Overdue ticket identified by escalate_overdue_complaints()")
    check(c3.escalation_level == 1, "Ticket escalation_level incremented to 1")
    history_entry = ComplaintStatusHistory.objects.filter(complaint=c3, note__icontains="SLA escalation").first()
    check(history_entry is not None, "Audit trail records SLA escalation in ComplaintStatusHistory")

    # --- 3.5 DUPLICATE DETECTION & LINKING ---
    print("\n[3.5] Duplicate Detection & Auto-Linking:")
    c_original = Complaint.objects.create(
        reporter_name="First Reporter",
        reporter_enrollment_number="GQ1004",
        title="Water cooler not cooling water in hostel",
        description="Cooler on 1st floor is giving warm water",
        category=cat,
        location_description="Sir Syed Hall North Floor 1",
        is_public=True
    )
    # Submit second report with same title & location
    resp_dup = client.post("/complaints/new/", {
        "reporter_name": "Second Reporter",
        "reporter_enrollment_number": "GQ1005",
        "title": "Water cooler not cooling water in hostel",
        "description": "Cooler on 1st floor is giving warm water",
        "category": cat.id,
        "location_description": "Sir Syed Hall North Floor 1",
        "is_public": True
    })
    c_duplicate = Complaint.objects.filter(reporter_enrollment_number="GQ1005").last()
    check(c_duplicate is not None and c_duplicate.duplicate_of == c_original,
          "Similar public complaint is automatically linked to duplicate_of master ticket")

    # --- 3.6 NULL / ORPHAN RESILIENCE ---
    print("\n[3.6] Null & Orphan Foreign Key Resilience:")
    # Complaint with room=None and assigned_to=None
    c_orphan = Complaint.objects.create(
        reporter_name="Orphan Reporter",
        reporter_enrollment_number="GQ1006",
        title="General Campus Greenery Issue",
        description="Fallen tree branch near main road",
        category=cat,
        room=None,
        assigned_to=None,
        location_description="Main Road Garden"
    )
    # Check detail page rendering without error
    admin_u = User.objects.filter(is_superuser=True).first()
    client.force_login(admin_u)
    resp_orphan_detail = client.get(f"/complaints/{c_orphan.reference}/")
    check(resp_orphan_detail.status_code == 200, "Complaint detail renders cleanly with room=None and assigned_to=None (HTTP 200)")

    # Cleanup test tickets
    c1.delete()
    c2.delete()
    c3.delete()
    c_original.delete()
    if c_duplicate:
        c_duplicate.delete()
    c_orphan.delete()
    client.logout()

    print("\n" + "=" * 80)
    print(f"PILLAR 3 SUMMARY: {passed} PASSED | {failed} FAILED (Total: {passed + failed})")
    print("=" * 80)
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
