from datetime import timedelta

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from .accountability import escalate_overdue_complaints
from .models import Building, Campus, Complaint, ComplaintCategory, ComplaintStatusHistory, Department, Floor, Room, UserProfile


class HomePageTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AMU Care")


class CampusModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Estates & Maintenance", code="ESTATE")
        self.campus = Campus.objects.create(name="Main Campus", code="MAIN")
        self.building = Building.objects.create(campus=self.campus, name="Academic Block A", code="ABA")
        self.floor = Floor.objects.create(building=self.building, number=2)

    def test_room_has_a_readable_location(self):
        room = Room.objects.create(floor=self.floor, number="204", name="Computer Lab")
        self.assertIn("Room 204", str(room))
        self.assertIn("Academic Block A", str(room))

    def test_category_is_assigned_to_department(self):
        category = ComplaintCategory.objects.create(
            name="Electrical", department=self.department, default_sla_hours=24
        )
        self.assertEqual(category.department, self.department)
        self.assertEqual(category.default_sla_hours, 24)


class AuthenticationTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get("/dashboard/")
        self.assertRedirects(response, "/login/?next=/dashboard/")

    def test_superuser_receives_administrator_role(self):
        administrator = User.objects.create_superuser("admin", "admin@example.edu", "Strong-pass-123")
        self.assertEqual(administrator.profile.role, UserProfile.Role.ADMIN)

    def test_student_cannot_open_campus_directory(self):
        student = User.objects.create_user("student", "student@example.edu", "Strong-pass-123")
        self.client.force_login(student)
        response = self.client.get("/campus-directory/")
        self.assertRedirects(response, "/dashboard/")

    def test_staff_can_open_campus_directory(self):
        staff_member = User.objects.create_user("staff", "staff@example.edu", "Strong-pass-123")
        staff_member.profile.role = UserProfile.Role.STAFF
        staff_member.profile.save()
        self.client.force_login(staff_member)
        response = self.client.get("/campus-directory/")
        self.assertEqual(response.status_code, 200)


class ComplaintWorkflowTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Estates", code="EST")
        self.category = ComplaintCategory.objects.create(name="Plumbing", department=self.department)
        self.student = User.objects.create_user("student", "student@example.edu", "Strong-pass-123")
        self.staff_member = User.objects.create_user("technician", "technician@example.edu", "Strong-pass-123")
        self.staff_member.profile.role = UserProfile.Role.STAFF
        self.staff_member.profile.department = self.department
        self.staff_member.profile.save()
        self.admin_user = User.objects.create_superuser("admin", "admin@example.edu", "Strong-pass-123")

    def test_student_can_submit_and_view_own_complaint(self):
        response = self.client.post(
            "/complaints/new/",
            {
                "reporter_name": "Asha Sharma", "reporter_enrollment_number": "GQ0001",
                "title": "Leaking tap", "category": self.category.id,
                "location_description": "Hostel 2 washroom", "description": "Tap is leaking continuously.",
            },
        )
        complaint = Complaint.objects.get()
        self.assertRedirects(response, f"/track/{complaint.tracking_token}/")
        self.assertEqual(complaint.reporter_name, "Asha Sharma")
        self.assertEqual(complaint.reporter_enrollment_number, "GQ0001")
        self.assertIn(complaint.status, {Complaint.Status.OPEN, Complaint.Status.ASSIGNED})
        self.assertTrue(ComplaintStatusHistory.objects.filter(complaint=complaint, status=Complaint.Status.OPEN).exists())

    def test_anonymous_student_can_open_private_tracking_link(self):
        complaint = Complaint.objects.create(
            category=self.category, reporter_name="Asha Sharma", reporter_enrollment_number="UNI2026001",
            title="Track this", description="Issue details.", location_description="Library",
        )
        response = self.client.get(f"/track/{complaint.tracking_token}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, complaint.reference)

    def test_admin_can_assign_and_update_status(self):
        """Only superusers/admins can assign complaints and update their status."""
        complaint = Complaint.objects.create(
            reporter=self.student, category=self.category, title="Broken light", description="No light.",
            location_description="Library entrance",
        )
        self.client.force_login(self.admin_user)
        response = self.client.post(f"/complaints/{complaint.reference}/assign/", {"assigned_to": self.staff_member.id})
        self.assertRedirects(response, f"/complaints/{complaint.reference}/")
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.ASSIGNED)
        response = self.client.post(
            f"/complaints/{complaint.reference}/status/",
            {"status": Complaint.Status.RESOLVED, "note": "Bulb replaced."},
        )
        self.assertRedirects(response, f"/complaints/{complaint.reference}/")
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.RESOLVED)
        self.assertIsNotNone(complaint.resolved_at)

    def test_category_is_required_for_complaint_submission(self):
        """Category is mandatory - form should show error if missing."""
        response = self.client.post(
            "/complaints/new/",
            {
                "reporter_name": "Asha Sharma", "reporter_enrollment_number": "GQ0001",
                "title": "Water leak from pipe", "location_description": "Hostel 2 washroom",
                "description": "Water is leaking continuously from the pipe.",
                "is_public": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Complaint.objects.count(), 0)
        self.assertContains(response, "category")

    def test_support_can_be_added_and_removed(self):
        complaint = Complaint.objects.create(
            reporter=self.student, category=self.category, title="Leaking tap", description="Tap leaks.",
            location_description="Hostel 1", is_public=True,
        )
        supporter = User.objects.create_user("supporter", "supporter@example.edu", "Strong-pass-123")
        self.client.force_login(supporter)
        response = self.client.post(f"/complaints/{complaint.reference}/support/", {"next": "/"})
        self.assertRedirects(response, "/")
        self.assertEqual(complaint.supports.count(), 1)
        self.client.post(f"/complaints/{complaint.reference}/support/", {"next": "/"})
        self.assertEqual(complaint.supports.count(), 0)

    def test_similar_public_report_is_linked_as_a_potential_duplicate(self):
        existing = Complaint.objects.create(
            reporter=self.student, category=self.category, title="Leaking tap in washroom",
            description="Water is leaking continuously from the tap.", location_description="Hostel 2 washroom",
            is_public=True,
        )
        another_student = User.objects.create_user("newstudent", "newstudent@example.edu", "Strong-pass-123")
        response = self.client.post(
            "/complaints/new/",
            {
                "reporter_name": "Ravi Patel", "reporter_enrollment_number": "GQ0002",
                "title": "Leaking tap in washroom", "category": self.category.id,
                "description": "Water is leaking continuously from the tap.", "location_description": "Hostel 2 washroom",
                "priority": Complaint.Priority.NORMAL, "is_public": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        new_report = Complaint.objects.exclude(pk=existing.pk).get()
        self.assertEqual(new_report.duplicate_of, existing)

    def test_overdue_complaint_is_automatically_escalated(self):
        complaint = Complaint.objects.create(
            reporter=self.student, category=self.category, title="Broken light", description="No light.",
            location_description="Library", sla_due_at=timezone.now() - timedelta(minutes=1),
        )
        escalated = escalate_overdue_complaints()
        complaint.refresh_from_db()
        self.assertIn(complaint, escalated)
        self.assertEqual(complaint.escalation_level, 1)
        self.assertTrue(ComplaintStatusHistory.objects.filter(complaint=complaint, note__icontains="SLA escalation").exists())

    def test_student_can_verify_resolution_and_leave_feedback(self):
        complaint = Complaint.objects.create(
            reporter=self.student, category=self.category, title="Fixed fan", description="Fan issue.",
            location_description="Block A", status=Complaint.Status.RESOLVED, resolved_at=timezone.now(),
        )
        self.client.force_login(self.student)
        response = self.client.post(
            f"/complaints/{complaint.reference}/verify-resolution/",
            {"decision": Complaint.ResolutionVerification.VERIFIED, "note": "Working well."},
        )
        self.assertRedirects(response, f"/complaints/{complaint.reference}/")
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.CLOSED)
        self.assertEqual(complaint.resolution_verification, Complaint.ResolutionVerification.VERIFIED)
        response = self.client.post(f"/complaints/{complaint.reference}/feedback/", {"rating": 5, "comment": "Quick repair."})
        self.assertRedirects(response, f"/complaints/{complaint.reference}/")
        self.assertEqual(complaint.feedback.rating, 5)

    def test_student_can_reject_a_resolution_and_reopen(self):
        complaint = Complaint.objects.create(
            reporter=self.student, category=self.category, title="Still leaking", description="Leak issue.",
            location_description="Block A", status=Complaint.Status.RESOLVED, resolved_at=timezone.now(),
        )
        self.client.force_login(self.student)
        self.client.post(
            f"/complaints/{complaint.reference}/verify-resolution/",
            {"decision": Complaint.ResolutionVerification.REJECTED, "note": "The tap still leaks."},
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.REOPENED)
        self.assertEqual(complaint.reopened_count, 1)
        self.assertIsNotNone(complaint.sla_due_at)

    def test_staff_can_view_analytics_and_export_report(self):
        Complaint.objects.create(
            reporter=self.student, category=self.category, title="Analytics item", description="Needs review.",
            location_description="Library",
        )
        self.client.force_login(self.staff_member)
        response = self.client.get("/analytics/?days=30")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maintenance analytics")
        response = self.client.get("/reports/complaints.csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertContains(response, "Analytics item")

    def test_student_cannot_view_analytics(self):
        self.client.force_login(self.student)
        response = self.client.get("/analytics/")
        self.assertRedirects(response, "/dashboard/")

    def test_ai_auto_assigns_it_staff_for_network_issue(self):
        """Network issue in Sir Syed Hall is automatically assigned to Sir Syed IT attendant."""
        it_cat = ComplaintCategory.objects.create(name="IT Network & Connectivity", department=self.department)
        it_staff = User.objects.create_user("itinf_sirsye_1", "itinf_sirsye_1@example.edu", "Strong-pass-123")
        it_staff.profile.role = UserProfile.Role.STAFF
        it_staff.profile.save()

        response = self.client.post(
            "/complaints/new/",
            {
                "reporter_name": "Tariq Ali",
                "reporter_enrollment_number": "GQ0101",
                "title": "Wi-Fi router down in corridor",
                "category": it_cat.id,
                "location_description": "Sir Syed Hall North Block Room 14",
                "description": "Internet connection drops every few minutes.",
            },
        )
        complaint = Complaint.objects.get(reporter_enrollment_number="GQ0101")
        self.assertRedirects(response, f"/track/{complaint.tracking_token}/")
        self.assertEqual(complaint.assigned_to, it_staff)
        self.assertEqual(complaint.status, Complaint.Status.ASSIGNED)
        self.assertIsNotNone(complaint.assigned_at)
        self.assertTrue(ComplaintStatusHistory.objects.filter(
            complaint=complaint, status=Complaint.Status.ASSIGNED
        ).exists())

    def test_ai_auto_assigns_electrician_for_electrical_issue(self):
        """Electrical issue in Aftab Hall is auto-assigned to Aftab Hall Electrician."""
        elec_cat = ComplaintCategory.objects.create(name="Estate Electrical Maintenance", department=self.department)
        elec_staff = User.objects.create_user("elec_aftabh_1", "elec_aftabh_1@example.edu", "Strong-pass-123")
        elec_staff.profile.role = UserProfile.Role.STAFF
        elec_staff.profile.save()

        response = self.client.post(
            "/complaints/new/",
            {
                "reporter_name": "Zubair Khan",
                "reporter_enrollment_number": "GQ0102",
                "title": "Sparking switch board",
                "category": elec_cat.id,
                "location_description": "Aftab Hall 2nd Floor Common Room",
                "description": "Short circuit and sparking when turning on switch.",
            },
        )
        complaint = Complaint.objects.get(reporter_enrollment_number="GQ0102")
        self.assertEqual(complaint.assigned_to, elec_staff)
        self.assertEqual(complaint.status, Complaint.Status.ASSIGNED)
        self.assertEqual(complaint.priority, Complaint.Priority.URGENT)

    def test_analyze_urgency_api_returns_suggested_staff(self):
        """API returns suggested technician from official staff roster."""
        import json
        response = self.client.post(
            "/api/analyze-urgency/",
            data=json.dumps({
                "title": "Wi-Fi dead",
                "description": "No internet connection",
                "category": "Network & Connectivity",
                "location": "Sir Syed Hall",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("suggested_staff", data)
        self.assertIsNotNone(data["suggested_staff"])
        self.assertEqual(data["suggested_staff"]["dept"], "IT & AV (ITINF)")
        self.assertIn("Sir Syed Hall", data["suggested_staff"]["location"])
        self.assertEqual(data["suggested_staff"]["name"], "Mohammad Shadab")

    def test_homepage_filter_by_status(self):
        """Homepage correctly filters public complaints when ?status= is provided."""
        c_open = Complaint.objects.create(
            category=self.category, title="Open Issue", description="details",
            location_description="Library", status=Complaint.Status.OPEN, is_public=True,
        )
        c_closed = Complaint.objects.create(
            category=self.category, title="Closed Issue", description="details",
            location_description="Library", status=Complaint.Status.CLOSED, is_public=True,
        )
        response = self.client.get("/?status=open")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open Issue")
        self.assertNotContains(response, "Closed Issue")

    def test_anonymous_student_can_verify_resolution_with_token(self):
        """Anonymous student can verify resolution on their complaint using tracking token."""
        complaint = Complaint.objects.create(
            category=self.category, title="Leaking faucet", description="details",
            location_description="Library", status=Complaint.Status.RESOLVED,
            resolved_at=timezone.now(),
        )
        response = self.client.post(
            f"/complaints/{complaint.reference}/verify-resolution/",
            {"decision": Complaint.ResolutionVerification.VERIFIED, "note": "Fixed.", "tracking_token": complaint.tracking_token},
        )
        self.assertRedirects(response, f"/track/{complaint.tracking_token}/")
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.CLOSED)
        self.assertEqual(complaint.resolution_verification, Complaint.ResolutionVerification.VERIFIED)


    def _make_test_image_file(self, name="test_photo.png", size=(1800, 1400), mode="RGBA"):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile

        buf = io.BytesIO()
        img = Image.new(mode, size, (20, 120, 220, 255) if mode == "RGBA" else (20, 120, 220))
        img.save(buf, format="PNG")
        buf.seek(0)
        return SimpleUploadedFile(name, buf.read(), content_type="image/png")

    def test_phase1_compress_uploaded_image(self):
        """Phase 1: RGBA PNG larger than 1280px is transposed, converted to RGB JPEG <= 1280px."""
        from PIL import Image
        from core.utils import compress_uploaded_image

        raw_file = self._make_test_image_file(name="camera_rgba.png", size=(2000, 1500), mode="RGBA")
        compressed = compress_uploaded_image(raw_file, max_dimension=1280, quality=75)
        self.assertIsNotNone(compressed)
        self.assertEqual(compressed.content_type, "image/jpeg")
        self.assertTrue(compressed.name.endswith(".jpg"))
        opened = Image.open(compressed)
        self.assertEqual(opened.mode, "RGB")
        self.assertLessEqual(max(opened.size), 1280)

    def test_phase3_zero_login_technician_workflow_and_dwell_time(self):
        """Phase 3: Technician starts task via UUID token, 5-min dwell enforced, resolves with proof, cannot close."""
        complaint = Complaint.objects.create(
            category=self.category,
            assigned_to=self.staff_member,
            title="Broken corridor switch",
            description="Switch board needs repair.",
            location_description="Sir Syed Hall",
            status=Complaint.Status.ASSIGNED,
        )
        task_url = f"/task/{complaint.staff_task_token}/"

        # 1. Start task without login
        self.client.logout()
        res_start = self.client.post(task_url, {"action": "start"})
        self.assertRedirects(res_start, task_url)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.IN_PROGRESS)
        self.assertIsNotNone(complaint.in_progress_at)

        # 2. Attempt resolve immediately (< 5 minutes) -> blocked with 400
        proof1 = self._make_test_image_file("proof1.png", size=(800, 600))
        res_early = self.client.post(task_url, {"action": "resolve", "resolution_proof": proof1})
        self.assertEqual(res_early.status_code, 400)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.IN_PROGRESS)

        # 3. Attempt close -> blocked with 403
        res_close = self.client.post(task_url, {"action": "close"})
        self.assertEqual(res_close.status_code, 403)

        # 4. Backdate in_progress_at by 6 minutes and resolve with camera proof
        complaint.in_progress_at = timezone.now() - timedelta(minutes=6)
        complaint.save(update_fields=["in_progress_at"])
        proof2 = self._make_test_image_file("proof2.png", size=(1600, 1200))
        res_ok = self.client.post(
            task_url,
            {"action": "resolve", "resolution_proof": proof2, "resolution_note": "Switch replaced."},
        )
        self.assertRedirects(res_ok, task_url)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.RESOLVED)
        self.assertTrue(bool(complaint.resolution_proof))

    def test_phase4_student_confirm_closes_and_purges_media(self):
        """Phase 4: Student confirmation sets CLOSED, saves rating, and deletes attached media files from storage."""
        import os
        proof = self._make_test_image_file("to_purge.png", size=(800, 600))
        complaint = Complaint.objects.create(
            category=self.category,
            title="Leaking pipe",
            description="Water leak.",
            location_description="Aftab Hall",
            status=Complaint.Status.RESOLVED,
            resolution_proof=proof,
        )
        file_path = complaint.resolution_proof.path
        self.assertTrue(os.path.exists(file_path))

        res = self.client.post(
            f"/complaints/{complaint.tracking_token}/confirm/",
            {"rating": 5, "comment": "Great job!"},
        )
        self.assertRedirects(res, f"/track/{complaint.tracking_token}/")
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.CLOSED)
        self.assertEqual(complaint.feedback.rating, 5)
        self.assertFalse(bool(complaint.resolution_proof))
        self.assertFalse(os.path.exists(file_path))

    def test_phase4_student_reopen_bumps_urgent_and_deducts_score(self):
        """Phase 4: Student reopen requires >=10 chars and photo proof, sets REOPENED, bumps urgent, deducts 15 pts."""
        self.staff_member.profile.accountability_score = 100
        self.staff_member.profile.save()
        complaint = Complaint.objects.create(
            category=self.category,
            assigned_to=self.staff_member,
            title="Tap still dripping",
            description="Water dripping.",
            location_description="Aftab Hall",
            status=Complaint.Status.RESOLVED,
            priority=Complaint.Priority.NORMAL,
        )
        reopen_url = f"/complaints/{complaint.tracking_token}/reopen/"

        # Short reason rejected
        res_short = self.client.post(reopen_url, {"reopen_reason": "short"})
        self.assertEqual(res_short.status_code, 400)

        # Valid explanation + photo proof
        reopen_img = self._make_test_image_file("reopen_evidence.png", size=(1000, 800))
        res_reopen = self.client.post(
            reopen_url,
            {
                "reopen_reason": "The pipe is still leaking heavily after repair.",
                "reopen_proof": reopen_img,
            },
        )
        self.assertRedirects(res_reopen, f"/track/{complaint.tracking_token}/")
        complaint.refresh_from_db()
        self.staff_member.profile.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.REOPENED)
        self.assertEqual(complaint.priority, Complaint.Priority.URGENT)
        self.assertEqual(complaint.reopen_count, 1)
        self.assertEqual(self.staff_member.profile.accountability_score, 85)

    def test_phase5_multi_tenant_scoping(self):
        """Phase 5: Registrar sees all, Provost sees managed_building, HOD sees managed_department."""
        from core.utils import get_scoped_complaints

        campus = Campus.objects.create(name="Main Campus", code="MAIN")
        other_dept = Department.objects.create(name="Physics Dept", code="PHYS")
        main_building = Building.objects.create(
            campus=campus, name="Sir Syed Hall", code="SSH", department=self.department
        )
        main_floor = Floor.objects.create(building=main_building, number=1)
        main_room = Room.objects.create(floor=main_floor, number="101")

        other_building = Building.objects.create(
            campus=campus, name="Physics Block", code="PHYB", department=other_dept
        )
        other_floor = Floor.objects.create(building=other_building, number=1)
        other_room = Room.objects.create(floor=other_floor, number="201")

        c1 = Complaint.objects.create(
            category=self.category, room=main_room, title="C1 in B1", description="Desc 1"
        )
        c2 = Complaint.objects.create(
            category=self.category, room=other_room, title="C2 in B2", description="Desc 2"
        )

        registrar = User.objects.create_user("reg_test", "reg@example.edu", "Strong-pass-123")
        registrar.profile.role = UserProfile.Role.REGISTRAR
        registrar.profile.save()

        provost = User.objects.create_user("prov_test", "prov@example.edu", "Strong-pass-123")
        provost.profile.role = UserProfile.Role.PROVOST
        provost.profile.managed_building = main_building
        provost.profile.save()

        hod = User.objects.create_user("hod_test", "hod@example.edu", "Strong-pass-123")
        hod.profile.role = UserProfile.Role.HOD
        hod.profile.managed_department = other_dept
        hod.profile.save()

        self.assertEqual(set(get_scoped_complaints(registrar)), {c1, c2})
        self.assertEqual(list(get_scoped_complaints(provost)), [c1])
        self.assertEqual(list(get_scoped_complaints(hod)), [c2])

    def test_student_enrollment_and_name_validation(self):
        """Test strict validation on student name and enrollment number (2 letters + 4 digits)."""
        req_err = "Both Name and Enrollment Number are required."
        fmt_err = "Invalid Enrollment Number. It must be exactly 6 characters: 2 letters followed by 4 digits (e.g., gq1234 or AA0001)."

        base_payload = {
            "title": "Broken fan",
            "description": "Fan not working in room.",
            "category": self.category.id,
            "location_description": "Hostel 1 Room 101",
        }

        # 1. Blank student name
        p1 = dict(base_payload, reporter_name="", reporter_enrollment_number="gq1234")
        r1 = self.client.post("/complaints/new/", p1)
        self.assertEqual(r1.status_code, 200)
        self.assertContains(r1, req_err)

        # 2. Whitespace-only student name
        p2 = dict(base_payload, reporter_name="   ", reporter_enrollment_number="gq1234")
        r2 = self.client.post("/complaints/new/", p2)
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, req_err)

        # 3. Blank enrollment number
        p3 = dict(base_payload, reporter_name="Mohd Asif", reporter_enrollment_number="")
        r3 = self.client.post("/complaints/new/", p3)
        self.assertEqual(r3.status_code, 200)
        self.assertContains(r3, req_err)

        # 4. Whitespace-only enrollment number
        p4 = dict(base_payload, reporter_name="Mohd Asif", reporter_enrollment_number="   ")
        r4 = self.client.post("/complaints/new/", p4)
        self.assertEqual(r4.status_code, 200)
        self.assertContains(r4, req_err)

        # 5. Valid 2 letters + 4 digits combinations across various prefixes
        valid_cases = ["aa0001", "ba0001", "gn0234", "gr0234", "hq1234", "ar0001", "za9999", "gq0234", "GQ9583"]
        for enroll_val in valid_cases:
            payload = dict(base_payload, reporter_name="Mohd Asif", reporter_enrollment_number=enroll_val)
            resp = self.client.post("/complaints/new/", payload)
            self.assertEqual(resp.status_code, 302, f"Failed for valid enrollment: {enroll_val}")
            self.assertTrue(
                Complaint.objects.filter(reporter_enrollment_number=enroll_val.upper()).exists(),
                f"Complaint with enrollment {enroll_val.upper()} not found"
            )

        # 6. Invalid formats
        invalid_cases = [
            "gq123",    # 5 chars (too short)
            "gq12345",  # 7 chars (too long)
            "12gq34",   # digits at start
            "abc123",   # 3 letters, 3 digits
            "ab123c",   # letter in last 4 chars
            "!@1234",   # special characters
            "123456",   # only digits
            "abcdef",   # only letters
        ]
        for bad_val in invalid_cases:
            payload = dict(base_payload, reporter_name="Mohd Asif", reporter_enrollment_number=bad_val)
            resp = self.client.post("/complaints/new/", payload)
            self.assertEqual(resp.status_code, 200, f"Failed to reject invalid enrollment: {bad_val}")
            self.assertContains(resp, fmt_err)

    def test_campus_heatmap_access_and_api(self):
        """Test that the campus heatmap and its API are strictly accessible only to SuperUser and Registrar."""
        # 1. Anonymous user blocked
        r_anon = self.client.get("/dashboard/heatmap/")
        self.assertEqual(r_anon.status_code, 302)
        self.assertIn("/login/", r_anon.url)

        r_api_anon = self.client.get("/api/heatmap-data/")
        self.assertEqual(r_api_anon.status_code, 302)

        # 2. Student user blocked
        self.client.force_login(self.student)
        r_stud = self.client.get("/dashboard/heatmap/")
        self.assertEqual(r_stud.status_code, 302)
        r_api_stud = self.client.get("/api/heatmap-data/")
        self.assertEqual(r_api_stud.status_code, 302)

        # 3. Staff user blocked
        self.client.force_login(self.staff_member)
        r_staff = self.client.get("/dashboard/heatmap/")
        self.assertEqual(r_staff.status_code, 302)

        # 4. Provost blocked
        provost = User.objects.create_user(username="provost_test", password="password")
        provost.profile.role = UserProfile.Role.PROVOST
        provost.profile.save()
        self.client.force_login(provost)
        r_prov = self.client.get("/dashboard/heatmap/")
        self.assertEqual(r_prov.status_code, 302)

        # 5. Registrar Office allowed
        registrar = User.objects.create_user(username="reg_test", password="password")
        registrar.profile.role = UserProfile.Role.REGISTRAR
        registrar.profile.save()
        self.client.force_login(registrar)
        r_reg = self.client.get("/dashboard/heatmap/")
        self.assertEqual(r_reg.status_code, 200)
        self.assertContains(r_reg, "Campus Complaint Heatmap")

        r_api_reg = self.client.get("/api/heatmap-data/")
        self.assertEqual(r_api_reg.status_code, 200)
        data_reg = r_api_reg.json()
        self.assertIn("points", data_reg)
        self.assertIn("buildings", data_reg)
        self.assertIn("total_complaints", data_reg)

        # 6. Superuser allowed
        superuser = User.objects.create_superuser(username="admin_super", email="admin@amu.edu", password="password")
        self.client.force_login(superuser)
        r_sup = self.client.get("/dashboard/heatmap/")
        self.assertEqual(r_sup.status_code, 200)

        r_api_sup = self.client.get("/api/heatmap-data/?status=active")
        self.assertEqual(r_api_sup.status_code, 200)
        data_sup = r_api_sup.json()
        self.assertIsInstance(data_sup["points"], list)


