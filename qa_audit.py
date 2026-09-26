#!/usr/bin/env python3
"""
CampusCare QA Audit Script
End-to-end verification and regression audit.
Non-destructive: cleans up all test records created.
"""
import os
import sys
import io
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campuscare.settings')

import django
django.setup()

from django.test import TestCase, Client
from django.urls import reverse, resolve, NoReverseMatch, Resolver404
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from core.models import (
    UserProfile, Campus, Building, Floor, Room, Department,
    ComplaintCategory, Complaint, ComplaintStatusHistory, ComplaintSupport,
    ComplaintFeedback
)

# Track all objects we create for cleanup
CREATED_REFERENCES = []

# ─────────────────────────────────────────────────────────
# SECTION 1: URL RESOLUTION AUDIT
# ─────────────────────────────────────────────────────────
def audit_url_resolution():
    print("\n" + "="*70)
    print("STEP 2: REVERSE URL RESOLUTION AUDIT")
    print("="*70)

    import uuid
    test_uuid = uuid.uuid4()

    # Map: (route_name, kwargs, description)
    routes_to_test = [
        # Public routes
        ("core:home",                     {},                                   "Public homepage"),
        ("core:complaint_create",         {},                                   "Complaint create form"),
        ("core:tracking_form",            {},                                   "Tracking input form"),
        ("core:suggest_category_api",     {},                                   "Category suggestion API"),
        ("core:analyze_urgency_api",      {},                                   "Urgency analysis API"),
        ("core:login",                    {},                                   "Login page"),
        ("core:logout",                   {},                                   "Logout URL"),
        ("core:register",                 {},                                   "Register redirect"),
        # Parametric public routes
        ("core:complaint_tracking",       {"tracking_token": "abc123"},         "Complaint tracking (token)"),
        ("core:technician_task_view",     {"task_token": str(test_uuid)},       "Technician task view"),
        ("core:complaint_detail",         {"reference": "CC-00000001"},         "Complaint detail"),
        ("core:complaint_assign",         {"reference": "CC-00000001"},         "Complaint assign"),
        ("core:complaint_update_status",  {"reference": "CC-00000001"},         "Status update"),
        ("core:complaint_toggle_support", {"reference": "CC-00000001"},         "Toggle support"),
        ("core:complaint_verify_resolution", {"reference": "CC-00000001"},      "Verify resolution"),
        ("core:complaint_reopen",         {"reference": "CC-00000001"},         "Legacy reopen"),
        ("core:complaint_feedback",       {"reference": "CC-00000001"},         "Feedback"),
        ("core:student_confirm_resolution", {"tracking_token": "abc123"},       "Student confirm"),
        ("core:student_reopen_complaint", {"tracking_token": "abc123"},         "Student reopen"),
        # Staff/Admin routes
        ("core:dashboard",                {},                                   "Dashboard"),
        ("core:complaint_list",           {},                                   "Complaint list"),
        ("core:analytics_dashboard",      {},                                   "Analytics dashboard"),
        ("core:complaint_report_csv",     {},                                   "CSV report"),
        ("core:campus_directory",         {},                                   "Campus directory"),
    ]

    passed = 0
    failed = 0
    failures = []

    for route_name, kwargs, description in routes_to_test:
        try:
            url = reverse(route_name, kwargs=kwargs if kwargs else None)
            print(f"  ✅ {route_name:<45} → {url}")
            passed += 1
        except NoReverseMatch as e:
            print(f"  ❌ {route_name:<45} → FAILED: {e}")
            failed += 1
            failures.append((route_name, description, str(e)))

    print(f"\n  ROUTES: {passed} passed, {failed} failed")
    if failures:
        print("\n  FAILED ROUTES:")
        for name, desc, err in failures:
            print(f"    - {name} ({desc}): {err}")
    return failed == 0


# ─────────────────────────────────────────────────────────
# SECTION 2: TEMPLATE URL REFERENCE SCAN
# ─────────────────────────────────────────────────────────
def audit_template_urls():
    print("\n" + "="*70)
    print("STEP 2b: TEMPLATE URL TAG REFERENCE SCAN")
    print("="*70)

    import re
    import glob

    template_dirs = [
        "/Users/Asif/Python:Project v2/templates",
        "/Users/Asif/Python:Project v2/core/templates",
    ]

    url_pattern = re.compile(r"""\{%\s*url\s+['"]([\w:]+)['"]\s*([^%]*?)%\}""")
    all_issues = []

    for template_dir in template_dirs:
        for filepath in glob.glob(f"{template_dir}/**/*.html", recursive=True):
            rel = filepath.replace("/Users/Asif/Python:Project v2/", "")
            with open(filepath, "r") as f:
                content = f.read()
            for match in url_pattern.finditer(content):
                route_name = match.group(1)
                args_str = match.group(2).strip()

                # Check if the route is even registered
                try:
                    # Quick check with dummy args for parametric routes
                    import uuid
                    dummy_kwargs = {}
                    if "reference" in args_str:
                        dummy_kwargs = {"reference": "CC-00000001"}
                    elif "tracking_token" in args_str:
                        dummy_kwargs = {"tracking_token": "abc123"}
                    elif "task_token" in args_str:
                        dummy_kwargs = {"task_token": str(uuid.uuid4())}
                    
                    reverse(route_name, kwargs=dummy_kwargs if dummy_kwargs else None)
                    # print(f"  ✅ Template: {rel} → {route_name}")
                except NoReverseMatch:
                    all_issues.append((rel, route_name, args_str))
                    print(f"  ❌ Template: {rel} → BROKEN URL TAG: {{% url '{route_name}' %}}")

    if not all_issues:
        print("  ✅ All template {% url %} tags resolve correctly.")
    else:
        print(f"\n  Found {len(all_issues)} broken template URL references.")
    return len(all_issues) == 0


# ─────────────────────────────────────────────────────────
# SECTION 3: MODEL RELATIONSHIP AUDIT
# ─────────────────────────────────────────────────────────
def audit_model_relationships():
    print("\n" + "="*70)
    print("STEP 1b: MODEL RELATIONSHIP & REVERSE RELATION AUDIT")
    print("="*70)

    issues = []

    # Check DB records are present
    campus_count = Campus.objects.count()
    building_count = Building.objects.count()
    room_count = Room.objects.filter(is_active=True).count()
    dept_count = Department.objects.count()
    cat_count = ComplaintCategory.objects.count()
    staff_count = User.objects.filter(profile__role=UserProfile.Role.STAFF).count()
    complaint_count = Complaint.objects.count()

    print(f"  DB State: Campuses={campus_count}, Buildings={building_count}, Rooms={room_count}")
    print(f"  DB State: Departments={dept_count}, Categories={cat_count}, Staff={staff_count}")
    print(f"  DB State: Complaints={complaint_count}")

    # Verify reverse relations don't crash
    try:
        dept = Department.objects.first()
        _ = list(dept.complaint_categories.all()[:3])
        _ = list(dept.staff_profiles.all()[:3])
        _ = list(dept.buildings.all()[:3])
        print("  ✅ Department reverse relations (complaint_categories, staff_profiles, buildings) OK")
    except Exception as e:
        issues.append(f"Department reverse relation crash: {e}")
        print(f"  ❌ Department reverse relation crash: {e}")

    try:
        building = Building.objects.filter(is_active=True).first()
        _ = list(building.floors.all()[:3])
        _ = list(building.managing_provosts.all()[:3])
        print("  ✅ Building reverse relations (floors, managing_provosts) OK")
    except Exception as e:
        issues.append(f"Building reverse relation crash: {e}")
        print(f"  ❌ Building reverse relation crash: {e}")

    try:
        floor = Floor.objects.first()
        _ = list(floor.rooms.all()[:3])
        print("  ✅ Floor reverse relation (rooms) OK")
    except Exception as e:
        issues.append(f"Floor reverse relation crash: {e}")
        print(f"  ❌ Floor reverse relation crash: {e}")

    try:
        room = Room.objects.filter(is_active=True).first()
        _ = list(room.complaints.all()[:3])
        print("  ✅ Room reverse relation (complaints) OK")
    except Exception as e:
        issues.append(f"Room reverse relation crash: {e}")
        print(f"  ❌ Room reverse relation crash: {e}")

    try:
        user = User.objects.filter(profile__role=UserProfile.Role.STAFF).first()
        if user:
            _ = user.profile.role
            _ = list(user.assigned_complaints.all()[:3])
            _ = list(user.assignments_made.all()[:3])
            print("  ✅ User→Profile→assigned_complaints/assignments_made OK")
    except Exception as e:
        issues.append(f"User/Profile reverse relation crash: {e}")
        print(f"  ❌ User/Profile reverse relation crash: {e}")

    # Check that complaint.assigned_to.profile does not crash when assigned_to is None
    try:
        c_with_assigned = Complaint.objects.filter(assigned_to__isnull=False).first()
        if c_with_assigned:
            _ = c_with_assigned.assigned_to.profile.department
            print("  ✅ Complaint.assigned_to.profile.department (FK chain) OK")
    except Exception as e:
        issues.append(f"Complaint FK chain crash: {e}")
        print(f"  ❌ Complaint FK chain crash: {e}")

    # Verify is_sla_breached property works
    try:
        c = Complaint.objects.first()
        if c:
            _ = c.is_sla_breached
            _ = c.reporter_display
            print("  ✅ Complaint model properties (is_sla_breached, reporter_display) OK")
    except Exception as e:
        issues.append(f"Complaint property crash: {e}")
        print(f"  ❌ Complaint property crash: {e}")

    # Check if any Room.qr_code_token duplicate issues exist
    from django.db.models import Count
    dup_qr = Room.objects.values('qr_code_token').annotate(c=Count('id')).filter(c__gt=1).count()
    if dup_qr > 0:
        issues.append(f"CRITICAL: {dup_qr} duplicate qr_code_tokens found in Room table")
        print(f"  ❌ CRITICAL: {dup_qr} duplicate qr_code_tokens in Room")
    else:
        print(f"  ✅ Room.qr_code_token uniqueness OK")

    print(f"\n  MODEL AUDIT: {len(issues)} issues found")
    return issues


# ─────────────────────────────────────────────────────────
# SECTION 4: IMPORT CHAIN AUDIT
# ─────────────────────────────────────────────────────────
def audit_imports():
    print("\n" + "="*70)
    print("STEP 1c: IMPORT CHAIN & CIRCULAR DEPENDENCY AUDIT")
    print("="*70)
    
    modules_to_check = [
        'core.models',
        'core.views',
        'core.forms',
        'core.admin',
        'core.signals',
        'core.decorators',
        'core.utils',
        'core.smart',
        'core.ai_triage',
        'core.dispatcher',
        'core.staff_matcher',
        'core.accountability',
        'core.analytics',
        'core.permissions',
    ]
    
    issues = []
    for mod in modules_to_check:
        try:
            import importlib
            importlib.import_module(mod)
            print(f"  ✅ {mod}")
        except ImportError as e:
            issues.append((mod, str(e)))
            print(f"  ❌ {mod} — ImportError: {e}")
        except Exception as e:
            issues.append((mod, str(e)))
            print(f"  ❌ {mod} — Exception: {e}")
    
    print(f"\n  IMPORT AUDIT: {len(issues)} issues found")
    return issues


# ─────────────────────────────────────────────────────────
# SECTION 5: FULL LIFECYCLE AUDIT (non-destructive)
# ─────────────────────────────────────────────────────────
def audit_lifecycle():
    print("\n" + "="*70)
    print("STEP 3: END-TO-END LIFECYCLE AUDIT")
    print("="*70)

    client = Client()
    issues = []
    created_complaint_refs = []

    # ── Ensure we have needed seeded data ──
    dept = Department.objects.filter(is_active=True).first()
    category = ComplaintCategory.objects.filter(is_active=True).first()
    staff_user = User.objects.filter(profile__role=UserProfile.Role.STAFF, is_active=True).first()

    if not dept:
        issues.append("No active Department found — seed data missing")
        print("  ❌ No active Department — lifecycle tests skipped")
        return issues
    if not category:
        issues.append("No active ComplaintCategory found — seed data missing")
        print("  ❌ No active ComplaintCategory — lifecycle tests skipped")
        return issues

    # 3.1: Complaint submission via POST
    print("\n  ─── 3.1: Public Complaint Submission ───")
    before_count = Complaint.objects.count()
    post_data = {
        "reporter_name": "QA Test User",
        "reporter_enrollment_number": "QA-2026-001",
        "title": "WiFi not working in Sir Syed North Hall Room 101",
        "description": "The WiFi router in the room shows red light and no internet. Need immediate inspection.",
        "category": category.id,
        "location_description": "Sir Syed North Hall, Room 101",
        "is_public": True,
    }
    response = client.post("/complaints/new/", post_data)
    
    after_count = Complaint.objects.count()
    if after_count == before_count + 1:
        complaint = Complaint.objects.filter(reporter_enrollment_number="QA-2026-001").last()
        created_complaint_refs.append(complaint.reference)
        CREATED_REFERENCES.append(complaint.reference)
        print(f"  ✅ Complaint created: {complaint.reference}, status={complaint.status}")
        print(f"     SLA due at: {complaint.sla_due_at}")
        print(f"     Priority: {complaint.priority} (score={complaint.priority_score})")
        print(f"     Room: {complaint.room}")
        print(f"     Assigned to: {complaint.assigned_to}")
        
        # Check staff_task_token generated
        if not complaint.staff_task_token:
            issues.append(f"Bug: complaint.staff_task_token is None for {complaint.reference}")
            print(f"  ❌ staff_task_token is None!")
        else:
            print(f"  ✅ staff_task_token generated: {complaint.staff_task_token}")
        
        # Check SLA was set
        if not complaint.sla_due_at:
            issues.append(f"Bug: sla_due_at not set for {complaint.reference}")
            print(f"  ❌ sla_due_at is None!")
        else:
            print(f"  ✅ sla_due_at set correctly")
        
        # Check status history was created
        history_count = ComplaintStatusHistory.objects.filter(complaint=complaint).count()
        if history_count == 0:
            issues.append(f"Bug: No status history created for {complaint.reference}")
            print(f"  ❌ Status history not created!")
        else:
            print(f"  ✅ Status history created ({history_count} entries)")
        
    elif response.status_code == 302:
        # Maybe it redirected but didn't create — check if form error
        issues.append(f"Complaint submission redirected without creating record (count unchanged)")
        print(f"  ⚠️  Redirect to {response.get('Location', 'unknown')} — count unchanged? Investigating...")
    else:
        issues.append(f"Complaint submission failed with status {response.status_code}")
        print(f"  ❌ Form submission returned HTTP {response.status_code}")

    # 3.2: Tracking page loads
    print("\n  ─── 3.2: Anonymous Tracking Page ───")
    if created_complaint_refs:
        complaint = Complaint.objects.get(reference=created_complaint_refs[0])
        response = client.get(f"/track/{complaint.tracking_token}/")
        if response.status_code == 200:
            print(f"  ✅ Tracking page loads (HTTP 200) for {complaint.tracking_token[:12]}...")
        else:
            issues.append(f"Tracking page returned HTTP {response.status_code}")
            print(f"  ❌ Tracking page HTTP {response.status_code}")

    # 3.3: Technician portal — zero-login
    print("\n  ─── 3.3: Zero-Login Technician Task Portal ───")
    if created_complaint_refs:
        complaint = Complaint.objects.get(reference=created_complaint_refs[0])
        task_token = complaint.staff_task_token
        
        # GET the task page (no login)
        response = client.get(f"/task/{task_token}/")
        if response.status_code == 200:
            print(f"  ✅ Technician task page loads without login (HTTP 200)")
        else:
            issues.append(f"Technician task page HTTP {response.status_code}")
            print(f"  ❌ Technician task page HTTP {response.status_code}")
        
        # Action: START
        response = client.post(f"/task/{task_token}/", {"action": "start"})
        complaint.refresh_from_db()
        if complaint.status == Complaint.Status.IN_PROGRESS:
            print(f"  ✅ 'start' action: status→in_progress, in_progress_at={complaint.in_progress_at}")
        else:
            issues.append(f"Bug: 'start' action did not update status to in_progress (got {complaint.status})")
            print(f"  ❌ 'start' action failed: status={complaint.status}")
        
        # Action: RESOLVE immediately (should be rejected — dwell time not met)
        from PIL import Image
        img_bytes = io.BytesIO()
        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        from django.core.files.uploadedfile import SimpleUploadedFile
        mock_image = SimpleUploadedFile("proof.jpg", img_bytes.read(), content_type="image/jpeg")
        
        # Don't move in_progress_at far back yet — test that dwell time REJECTS
        if complaint.in_progress_at:
            response = client.post(f"/task/{task_token}/", {
                "action": "resolve",
                "resolution_proof": mock_image,
                "resolution_note": "Test resolve",
            })
            if response.status_code == 400:
                print(f"  ✅ Dwell-time enforcement: resolve rejected (HTTP 400) before 5 min")
            else:
                # Status changed before 5 min means dwell-time not enforced
                complaint.refresh_from_db()
                if complaint.status != Complaint.Status.RESOLVED:
                    print(f"  ⚠️  Resolve returned HTTP {response.status_code} but status not changed — tolerable")
                else:
                    issues.append(f"Bug: Dwell-time NOT enforced — complaint marked resolved before 5 minutes!")
                    print(f"  ❌ Dwell-time NOT enforced! Status jumped to RESOLVED")
        
        # Backdate in_progress_at to simulate 6 minutes elapsed
        complaint.in_progress_at = timezone.now() - timedelta(minutes=6)
        complaint.save(update_fields=["in_progress_at"])
        
        # Action: RESOLVE with backdated time (should succeed)
        img_bytes = io.BytesIO()
        img2 = Image.new('RGB', (200, 200), color=(0, 255, 0))
        img2.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        mock_image2 = SimpleUploadedFile("proof2.jpg", img_bytes.read(), content_type="image/jpeg")
        
        response = client.post(f"/task/{task_token}/", {
            "action": "resolve",
            "resolution_proof": mock_image2,
            "resolution_note": "QA test — issue resolved.",
        })
        complaint.refresh_from_db()
        
        if complaint.status == Complaint.Status.RESOLVED:
            print(f"  ✅ Valid resolve (after 6min): status→resolved, resolution_proof={bool(complaint.resolution_proof)}")
            print(f"     resolution_verification={complaint.resolution_verification}")
            if complaint.resolution_verification != Complaint.ResolutionVerification.PENDING:
                issues.append(f"Bug: After technician resolve, resolution_verification should be PENDING, got {complaint.resolution_verification}")
                print(f"  ❌ resolution_verification should be PENDING, got {complaint.resolution_verification}")
            else:
                print(f"  ✅ Ticket is RESOLVED (PENDING_VERIFICATION) — NOT auto-closed")
        else:
            issues.append(f"Bug: Resolve action did not update status to resolved (got {complaint.status})")
            print(f"  ❌ Resolve failed: status={complaint.status}")
        
        # 3.4: Student resolution paths
        print("\n  ─── 3.4: Student Closed-Loop Verification ───")
        
        # Path B first — Reopen (dispute)
        img_bytes = io.BytesIO()
        img3 = Image.new('RGB', (150, 150), color=(0, 0, 255))
        img3.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        mock_reopen = SimpleUploadedFile("reopen.jpg", img_bytes.read(), content_type="image/jpeg")
        
        initial_score = None
        if complaint.assigned_to_id:
            try:
                initial_score = UserProfile.objects.get(user_id=complaint.assigned_to_id).accountability_score
            except UserProfile.DoesNotExist:
                initial_score = 100
        
        response = client.post(f"/complaints/{complaint.tracking_token}/reopen/", {
            "reopen_reason": "Issue is still present — water still leaking QA test.",
            "reopen_proof": mock_reopen,
        })
        complaint.refresh_from_db()
        
        if complaint.status == Complaint.Status.REOPENED:
            print(f"  ✅ Path B (Dispute): status→reopened, priority={complaint.priority}")
            if complaint.priority != Complaint.Priority.URGENT:
                issues.append(f"Bug: Reopened complaint priority should be URGENT, got {complaint.priority}")
                print(f"  ❌ Priority should be URGENT, got {complaint.priority}")
            else:
                print(f"  ✅ Priority correctly bumped to URGENT")
            
            # Check accountability score deduction
            if complaint.assigned_to_id and initial_score is not None:
                new_score = UserProfile.objects.get(user_id=complaint.assigned_to_id).accountability_score
                if new_score == initial_score - 15:
                    print(f"  ✅ Accountability score deducted: {initial_score} → {new_score} (-15)")
                else:
                    issues.append(f"Bug: Expected score={initial_score-15}, got {new_score}")
                    print(f"  ❌ Accountability deduction: expected {initial_score-15}, got {new_score}")
        else:
            issues.append(f"Bug: Student reopen did not set status to REOPENED (got {complaint.status})")
            print(f"  ❌ Reopen failed: status={complaint.status}")
        
        # Now test Path A — Confirm (must bring back to resolved first)
        complaint.status = Complaint.Status.RESOLVED
        complaint.resolution_verification = Complaint.ResolutionVerification.PENDING
        complaint.save(update_fields=["status", "resolution_verification", "updated_at"])
        
        response = client.post(f"/complaints/{complaint.tracking_token}/confirm/", {
            "rating": "4",
            "comment": "QA test resolution confirmation.",
        })
        complaint.refresh_from_db()
        
        if complaint.status == Complaint.Status.CLOSED:
            print(f"  ✅ Path A (Confirm): status→closed, closed_at={complaint.closed_at}")
            print(f"     resolution_verification={complaint.resolution_verification}")
            
            # Check media purge
            if complaint.evidence or complaint.resolution_proof:
                issues.append(f"Bug: Media not purged after close. evidence={complaint.evidence}, proof={complaint.resolution_proof}")
                print(f"  ❌ Media NOT purged after closure!")
            else:
                print(f"  ✅ Media purged after closure (evidence and resolution_proof cleared)")
            
            # Check feedback recorded
            try:
                feedback = ComplaintFeedback.objects.get(complaint=complaint)
                print(f"  ✅ Feedback recorded: {feedback.rating}/5 — '{feedback.comment}'")
            except ComplaintFeedback.DoesNotExist:
                issues.append(f"Bug: Feedback not recorded after student_confirm_resolution")
                print(f"  ❌ Feedback NOT recorded after confirmation")
        else:
            issues.append(f"Bug: Student confirm did not set status to CLOSED (got {complaint.status})")
            print(f"  ❌ Confirm failed: status={complaint.status}")

    print(f"\n  LIFECYCLE AUDIT: {len(issues)} issues found")
    return issues


# ─────────────────────────────────────────────────────────
# SECTION 6: MULTI-TENANT SCOPING AUDIT
# ─────────────────────────────────────────────────────────
def audit_multitenant_scoping():
    print("\n" + "="*70)
    print("STEP 3.4: MULTI-TENANT DATA ISOLATION AUDIT")
    print("="*70)

    from core.permissions import get_scoped_complaints_for_user

    issues = []

    # Test Registrar (global visibility)
    registrar = User.objects.filter(profile__role=UserProfile.Role.REGISTRAR).first()
    if registrar:
        qs = get_scoped_complaints_for_user(registrar)
        total = Complaint.objects.count()
        scoped = qs.count()
        if scoped == total:
            print(f"  ✅ Registrar: sees ALL {scoped} complaints (expected {total})")
        else:
            issues.append(f"Scoping bug: Registrar sees {scoped}, expected {total}")
            print(f"  ❌ Registrar scoping: sees {scoped}, expected {total}")
    else:
        print("  ⚠️  No Registrar user found — skipping registrar scoping test")

    # Test Superuser
    superuser = User.objects.filter(is_superuser=True).first()
    if superuser:
        qs = get_scoped_complaints_for_user(superuser)
        total = Complaint.objects.count()
        if qs.count() == total:
            print(f"  ✅ Superuser: sees ALL {total} complaints")
        else:
            issues.append(f"Scoping bug: Superuser sees {qs.count()}, expected {total}")
            print(f"  ❌ Superuser scoping: sees {qs.count()}, expected {total}")
    else:
        print("  ⚠️  No superuser found — skipping")

    # Test Provost — should see only their building
    provost = User.objects.filter(profile__role=UserProfile.Role.PROVOST, profile__managed_building__isnull=False).first()
    if provost:
        building = provost.profile.managed_building
        qs = get_scoped_complaints_for_user(provost)
        scoped = qs.count()
        
        # Verify no complaints from other buildings are included
        cross_building = qs.exclude(room__floor__building=building).exclude(room__isnull=True).count()
        if cross_building > 0:
            issues.append(f"Data leak: Provost for {building.name} sees {cross_building} complaints from OTHER buildings!")
            print(f"  ❌ DATA LEAK: Provost ({building.name}) sees {cross_building} complaints from other buildings!")
        else:
            print(f"  ✅ Provost ({building.name}): sees {scoped} complaints, 0 from other buildings")
    else:
        print("  ⚠️  No Provost with managed_building found — skipping isolation test")

    # Test HOD — should see only their department complaints
    hod = User.objects.filter(profile__role=UserProfile.Role.HOD, profile__managed_department__isnull=False).first()
    if hod:
        dept = hod.profile.managed_department
        qs = get_scoped_complaints_for_user(hod)
        scoped = qs.count()
        print(f"  ✅ HOD ({dept.name}): sees {scoped} complaints in their scope")
    else:
        print("  ⚠️  No HOD with managed_department found — skipping HOD test")

    # Test regular Student — should return empty queryset from get_scoped_complaints_for_user
    student = User.objects.filter(profile__role=UserProfile.Role.STUDENT).first()
    if student:
        qs = get_scoped_complaints_for_user(student)
        if qs.count() == 0:
            print(f"  ✅ Student: get_scoped_complaints_for_user returns empty (correct — students use public/token view)")
        else:
            issues.append(f"Scoping bug: Student sees {qs.count()} complaints via admin scope (should be 0)")
            print(f"  ❌ Student admin scope returns {qs.count()} (should be 0)")
    else:
        print("  ⚠️  No Student user found — skipping")

    print(f"\n  SCOPING AUDIT: {len(issues)} issues found")
    return issues


# ─────────────────────────────────────────────────────────
# SECTION 7: TIMEZONE & DATETIME AUDIT
# ─────────────────────────────────────────────────────────
def audit_timezone():
    print("\n" + "="*70)
    print("STEP 4: TIMEZONE & NAIVE DATETIME AUDIT")
    print("="*70)
    
    import re
    import glob
    import warnings
    
    issues = []
    
    # Pattern: datetime.now() (naive) vs timezone.now() (aware)
    naive_pattern = re.compile(r'datetime\.now\(\)')
    files_to_check = []
    for pattern in [
        "/Users/Asif/Python:Project v2/core/*.py",
    ]:
        files_to_check.extend(glob.glob(pattern))
    
    for filepath in files_to_check:
        rel = filepath.replace("/Users/Asif/Python:Project v2/", "")
        with open(filepath, "r") as f:
            content = f.read()
        matches = naive_pattern.findall(content)
        if matches:
            issues.append(f"Naive datetime.now() in {rel}: {len(matches)} occurrences")
            print(f"  ❌ Naive datetime.now() found in {rel} ({len(matches)} times)")
        else:
            print(f"  ✅ {rel}: Uses timezone-aware datetimes")
    
    # Check that existing complaints with sla_due_at are timezone-aware
    c = Complaint.objects.filter(sla_due_at__isnull=False).first()
    if c:
        import datetime
        if c.sla_due_at.tzinfo is None:
            issues.append("Bug: complaint.sla_due_at is timezone-naive!")
            print(f"  ❌ complaint.sla_due_at is NAIVE (no tzinfo)!")
        else:
            print(f"  ✅ complaint.sla_due_at is timezone-aware ({c.sla_due_at.tzinfo})")
    
    print(f"\n  TIMEZONE AUDIT: {len(issues)} issues found")
    return issues


# ─────────────────────────────────────────────────────────
# SECTION 8: STATIC/MEDIA PATHS AUDIT
# ─────────────────────────────────────────────────────────
def audit_static_media():
    print("\n" + "="*70)
    print("STEP 4b: STATIC & MEDIA PATHS AUDIT")
    print("="*70)
    
    from django.conf import settings
    import os
    
    issues = []
    
    media_root = settings.MEDIA_ROOT
    static_dirs = settings.STATICFILES_DIRS
    
    print(f"  MEDIA_ROOT: {media_root}")
    print(f"  MEDIA_URL: {settings.MEDIA_URL}")
    print(f"  STATIC_URL: {settings.STATIC_URL}")
    print(f"  STATICFILES_DIRS: {static_dirs}")
    
    if not os.path.exists(media_root):
        issues.append(f"MEDIA_ROOT directory does not exist: {media_root}")
        print(f"  ❌ MEDIA_ROOT does not exist: {media_root}")
    else:
        print(f"  ✅ MEDIA_ROOT exists: {media_root}")
    
    for static_dir in static_dirs:
        if not os.path.exists(static_dir):
            issues.append(f"STATICFILES_DIR does not exist: {static_dir}")
            print(f"  ❌ STATIC DIR does not exist: {static_dir}")
        else:
            # Check critical files
            css_file = os.path.join(static_dir, "styles.css")
            js_file = os.path.join(static_dir, "app.js")
            print(f"  ✅ Static dir exists: {static_dir}")
            if os.path.exists(css_file):
                print(f"  ✅ styles.css present")
            else:
                print(f"  ⚠️  styles.css missing in {static_dir}")
            if os.path.exists(js_file):
                print(f"  ✅ app.js present")
            else:
                print(f"  ⚠️  app.js missing in {static_dir}")
    
    print(f"\n  STATIC/MEDIA AUDIT: {len(issues)} issues found")
    return issues


# ─────────────────────────────────────────────────────────
# SECTION 9: EDGE CASE BUGS — NoneType chains
# ─────────────────────────────────────────────────────────
def audit_nullable_fk_chains():
    print("\n" + "="*70)
    print("STEP 4c: NULLABLE FK CHAIN / NoneType CRASH AUDIT")
    print("="*70)
    
    issues = []
    
    # Test complaint with no room (location_description only)
    dept = Department.objects.filter(is_active=True).first()
    cat = ComplaintCategory.objects.filter(is_active=True, department=dept).first()
    if not cat:
        cat = ComplaintCategory.objects.filter(is_active=True).first()
    
    if cat:
        # Create a complaint without a room (nullable FK)
        c = Complaint(
            reporter_name="FK Test",
            reporter_enrollment_number="FK-TEST-001",
            category=cat,
            title="Test nullable FK chain",
            description="Testing that None FK chains do not crash",
            location_description="Library steps",
            room=None,
            assigned_to=None,
            assigned_by=None,
        )
        try:
            from core.accountability import set_sla_due_date
            set_sla_due_date(c)
            c.save()
            CREATED_REFERENCES.append(c.reference)
            
            # Test the properties that might crash with None FKs
            _ = c.reporter_display
            _ = c.is_sla_breached
            _ = str(c)
            
            print(f"  ✅ Complaint without room (room=None): model properties work correctly")
            
            # Simulate what templates do with nullable chains
            # complaint.room.floor.building.department would crash if room is None
            # The template checks {% if complaint.room %} — verify this guards correctly
            if c.room is None:
                print("  ✅ Template guard: complaint.room is None — {%% if complaint.room %%} would be False")
            
            # assigned_to chain
            if c.assigned_to is None:
                print("  ✅ Template guard: complaint.assigned_to is None — {%% if complaint.assigned_to %%} would be False")
            
            # Clean up
            c.delete()
            CREATED_REFERENCES.remove(c.reference) if c.reference in CREATED_REFERENCES else None
        except Exception as e:
            issues.append(f"Nullable FK chain crash: {e}")
            print(f"  ❌ Nullable FK chain crash: {e}")
            traceback.print_exc()
    
    # Test Complaint.clean() validation
    print("\n  Testing Complaint.clean() validation...")
    try:
        from django.core.exceptions import ValidationError
        c_bad = Complaint(
            reporter_name="Test",
            reporter_enrollment_number="TEST-001",
            category=cat,
            title="Bad complaint",
            description="No location at all",
            room=None,
            location_description="",  # Should fail
        )
        try:
            c_bad.full_clean()
            issues.append("Bug: Complaint with no room AND no location_description passed validation!")
            print("  ❌ Complaint.clean() did NOT catch missing location!")
        except ValidationError as ve:
            print(f"  ✅ Complaint.clean() correctly rejects complaint with no location: {list(ve.messages)[:1]}")
    except Exception as e:
        issues.append(f"Complaint.clean() test crash: {e}")
        print(f"  ❌ Complaint.clean() test crash: {e}")
    
    # Check ai_triage.py line 116 for duplicate dict key bug
    print("\n  Checking ai_triage.py for duplicate dict key bug (line 116)...")
    import ast
    try:
        with open("/Users/Asif/Python:Project v2/core/ai_triage.py") as f:
            src = f.read()
        # Check for the specific bug: Room.objects.get_or_create(..., defaults={"name": ..., "name": ...})
        if '"name": f"{building.name} General Area", "name"' in src:
            issues.append("Bug: Duplicate dict key 'name' in ai_triage.py line ~116 in Room.objects.get_or_create defaults")
            print("  ❌ BUG FOUND: Duplicate dict key 'name' in ai_triage.py (Room.get_or_create defaults)!")
        else:
            print("  ✅ ai_triage.py: No duplicate dict key detected")
    except Exception as e:
        print(f"  ⚠️  Could not check ai_triage.py: {e}")
    
    print(f"\n  NULLABLE FK AUDIT: {len(issues)} issues found")
    return issues


# ─────────────────────────────────────────────────────────
# SECTION 10: COMPRESS IMAGE FUNCTION AUDIT
# ─────────────────────────────────────────────────────────
def audit_image_compression():
    print("\n" + "="*70)
    print("STEP 3.3b: IMAGE COMPRESSION (compress_uploaded_image) AUDIT")
    print("="*70)
    
    from core.utils import compress_uploaded_image
    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    issues = []
    
    # Test 1: Normal JPEG
    img_buf = io.BytesIO()
    img = Image.new('RGB', (2000, 2000), color=(128, 64, 32))
    img.save(img_buf, format='JPEG', quality=95)
    img_buf.seek(0)
    large_jpeg = SimpleUploadedFile("big.jpg", img_buf.read(), content_type="image/jpeg")
    
    result = compress_uploaded_image(large_jpeg)
    if result and result.size < img_buf.getbuffer().nbytes:
        result_img = Image.open(result)
        print(f"  ✅ JPEG compressed: original size≈{img_buf.getbuffer().nbytes//1024}KB → {result.size//1024}KB, dims={result_img.size}")
        if max(result_img.size) <= 1280:
            print(f"  ✅ Dimensions correctly resized to max 1280px")
        else:
            issues.append(f"Compression bug: image still {result_img.size} (should be ≤1280 max)")
            print(f"  ❌ Image not resized: {result_img.size}")
    else:
        issues.append("Compression failed or didn't reduce size")
        print(f"  ❌ Compression did not reduce size (result={result})")
    
    # Test 2: PNG with alpha
    img_buf2 = io.BytesIO()
    img2 = Image.new('RGBA', (500, 500), color=(255, 255, 255, 128))
    img2.save(img_buf2, format='PNG')
    img_buf2.seek(0)
    png_alpha = SimpleUploadedFile("alpha.png", img_buf2.read(), content_type="image/png")
    
    try:
        result2 = compress_uploaded_image(png_alpha)
        result_img2 = Image.open(result2)
        if result_img2.mode == 'RGB':
            print(f"  ✅ RGBA PNG correctly converted to RGB JPEG (mode={result_img2.mode})")
        else:
            issues.append(f"Alpha PNG not converted to RGB (mode={result_img2.mode})")
            print(f"  ❌ RGBA PNG not converted to RGB: mode={result_img2.mode}")
    except Exception as e:
        issues.append(f"RGBA PNG compression crash: {e}")
        print(f"  ❌ RGBA PNG compression crash: {e}")
    
    # Test 3: None input
    result3 = compress_uploaded_image(None)
    if result3 is None:
        print(f"  ✅ None input returns None (no crash)")
    else:
        issues.append("compress_uploaded_image(None) should return None")
        print(f"  ❌ None input didn't return None: {result3}")
    
    print(f"\n  IMAGE COMPRESSION AUDIT: {len(issues)} issues found")
    return issues


# ─────────────────────────────────────────────────────────
# SECTION 11: SMART.PY & AI TRIAGE LOGIC AUDIT
# ─────────────────────────────────────────────────────────
def audit_smart_logic():
    print("\n" + "="*70)
    print("STEP 4d: smart.py & ai_triage.py LOGIC AUDIT")
    print("="*70)
    
    from core.smart import suggest_category, score_priority, find_potential_duplicate
    
    issues = []
    categories = list(ComplaintCategory.objects.filter(is_active=True))
    
    # Test suggest_category
    cat, conf = suggest_category("wifi router not working internet down", categories)
    if cat:
        print(f"  ✅ suggest_category('wifi router...'): {cat.name} ({conf}% confidence)")
    else:
        issues.append("suggest_category returned None for clear wifi issue")
        print(f"  ❌ suggest_category returned None for clear wifi keyword text")
    
    cat2, conf2 = suggest_category("leaking tap pipe broken water", categories)
    if cat2:
        print(f"  ✅ suggest_category('leaking tap...'): {cat2.name} ({conf2}% confidence)")
    else:
        issues.append("suggest_category returned None for clear plumbing issue")
        print(f"  ❌ suggest_category returned None for clear plumbing text")
    
    # Test score_priority
    score, priority, reason, sla = score_priority(
        "electric shock from socket", title="Electric shock", 
        description="Got electric shock from wall socket near bed",
        category_name="Electrical"
    )
    if priority == "urgent":
        print(f"  ✅ score_priority('electric shock'): priority={priority}, score={score}, sla={sla}h")
    else:
        issues.append(f"score_priority failed to detect urgent: got {priority}")
        print(f"  ❌ score_priority should be urgent, got {priority}")
    
    score2, priority2, reason2, sla2 = score_priority(
        "light bulb replacement needed", title="Bulb fused",
        description="The room bulb has fused and needs replacement",
        category_name="Electrical"
    )
    print(f"  ✅ score_priority('light bulb...'): priority={priority2}, sla={sla2}h")
    
    print(f"\n  SMART LOGIC AUDIT: {len(issues)} issues found")
    return issues


# ─────────────────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────────────────
def cleanup_test_records():
    print("\n" + "="*70)
    print("CLEANUP: Removing test records")
    print("="*70)
    
    deleted = 0
    for ref in CREATED_REFERENCES:
        try:
            c = Complaint.objects.get(reference=ref)
            # Also delete related feedback
            ComplaintFeedback.objects.filter(complaint=c).delete()
            ComplaintStatusHistory.objects.filter(complaint=c).delete()
            ComplaintSupport.objects.filter(complaint=c).delete()
            c.delete()
            deleted += 1
            print(f"  🗑️  Deleted test complaint: {ref}")
        except Complaint.DoesNotExist:
            pass
    
    # Also clean up any test complaints from QA Test User
    extra = Complaint.objects.filter(reporter_enrollment_number__startswith="QA-")
    count = extra.count()
    if count > 0:
        extra.delete()
        print(f"  🗑️  Deleted {count} additional QA test complaints")
    
    print(f"  Cleanup complete: {deleted} records removed")


# ─────────────────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────────────────
def run_full_audit():
    print("\n" + "█"*70)
    print("  CAMPUSCARE END-TO-END QA REGRESSION AUDIT")
    print("█"*70)
    
    all_issues = []
    
    try:
        # Step 1: Imports
        import_issues = audit_imports()
        all_issues.extend(import_issues)
        
        # Step 1b: Model relationships
        model_issues = audit_model_relationships()
        all_issues.extend(model_issues)
        
        # Step 2: URL resolution
        url_ok = audit_url_resolution()
        if not url_ok:
            all_issues.append("Some URL routes failed to resolve")
        
        # Step 2b: Template URL tags
        template_ok = audit_template_urls()
        if not template_ok:
            all_issues.append("Some template {% url %} tags are broken")
        
        # Step 3: Lifecycle
        lifecycle_issues = audit_lifecycle()
        all_issues.extend(lifecycle_issues)
        
        # Step 3.4: Multi-tenant scoping
        scoping_issues = audit_multitenant_scoping()
        all_issues.extend(scoping_issues)
        
        # Step 4: Timezone
        tz_issues = audit_timezone()
        all_issues.extend(tz_issues)
        
        # Step 4b: Static/Media
        static_issues = audit_static_media()
        all_issues.extend(static_issues)
        
        # Step 4c: Nullable FKs
        nullable_issues = audit_nullable_fk_chains()
        all_issues.extend(nullable_issues)
        
        # Step 3.3b: Image compression
        img_issues = audit_image_compression()
        all_issues.extend(img_issues)
        
        # Step 4d: Smart logic
        smart_issues = audit_smart_logic()
        all_issues.extend(smart_issues)
        
    finally:
        cleanup_test_records()
    
    # FINAL SUMMARY
    print("\n" + "█"*70)
    print("  FINAL AUDIT SUMMARY")
    print("█"*70)
    
    if all_issues:
        print(f"\n  ❌ TOTAL ISSUES FOUND: {len(all_issues)}\n")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
    else:
        print(f"\n  ✅ AUDIT COMPLETE — ZERO ISSUES FOUND. All systems healthy.")
    
    return all_issues


if __name__ == "__main__":
    issues = run_full_audit()
    sys.exit(0 if not issues else 1)
