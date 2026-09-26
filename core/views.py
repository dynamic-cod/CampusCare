from django.db.models import Avg
from .dispatcher import auto_dispatch_complaint
from .permissions import get_scoped_complaints_for_user
from .ai_triage import bind_complaint_spatial_origin
from .utils import compress_uploaded_image, get_scoped_complaints
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
import json

from .decorators import staff_or_admin_required, admin_only_required
from .accountability import set_sla_due_date
from .analytics import analytics_snapshot
from .forms import (
    ComplaintAssignmentForm, ComplaintFeedbackForm, ComplaintReopenForm, ComplaintStatusForm,
    ComplaintSubmissionForm, ResolutionVerificationForm,
)
from .models import Building, Campus, Complaint, ComplaintCategory, ComplaintFeedback, ComplaintStatusHistory, ComplaintSupport, Department, Floor, Room, UserProfile
from .smart import find_potential_duplicate, get_ai_sla_hours, score_priority, suggest_category
from .staff_matcher import suggest_staff


def home(request):
    """Public homepage — shows the community complaint dashboard to everyone."""
    from django.db.models import Count
    total = Complaint.objects.count()
    count_open = Complaint.objects.filter(status=Complaint.Status.OPEN).count()
    count_assigned = Complaint.objects.filter(status=Complaint.Status.ASSIGNED).count()
    count_in_progress = Complaint.objects.filter(status=Complaint.Status.IN_PROGRESS).count()
    count_resolved = Complaint.objects.filter(status=Complaint.Status.RESOLVED).count()
    count_closed = Complaint.objects.filter(status=Complaint.Status.CLOSED).count()
    count_reopened = Complaint.objects.filter(status=Complaint.Status.REOPENED).count()
    count_active = count_open + count_assigned + count_in_progress + count_reopened

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key or ""

    status_filter = request.GET.get("status", "").strip().lower()
    complaints_qs = Complaint.objects.filter(is_public=True)
    if status_filter == "active":
        complaints_qs = complaints_qs.filter(status__in=[
            Complaint.Status.OPEN, Complaint.Status.ASSIGNED,
            Complaint.Status.IN_PROGRESS, Complaint.Status.REOPENED,
        ])
    elif status_filter in Complaint.Status.values:
        complaints_qs = complaints_qs.filter(status=status_filter)

    recent_complaints = (
        complaints_qs
        .select_related("category")
        .annotate(support_count=Count("supports"))
        .order_by("-created_at")[:50]
    )

    if request.user.is_authenticated:
        supported_ids = set(
            ComplaintSupport.objects.filter(user=request.user, complaint__in=recent_complaints)
            .values_list("complaint_id", flat=True)
        )
    elif session_key:
        supported_ids = set(
            ComplaintSupport.objects.filter(session_key=session_key, complaint__in=recent_complaints)
            .values_list("complaint_id", flat=True)
        )
    else:
        supported_ids = set()

    context = {
        "total": total,
        "count_active": count_active,
        "count_open": count_open,
        "count_assigned": count_assigned,
        "count_in_progress": count_in_progress,
        "count_resolved": count_resolved,
        "count_closed": count_closed,
        "count_reopened": count_reopened,
        "recent_complaints": recent_complaints,
        "supported_ids": supported_ids,
        "selected_status": status_filter,
    }
    return render(request, "core/home.html", context)


def suggest_category_api(request):
    """API endpoint for real-time category suggestions based on complaint text."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            text = data.get("text", "").strip()
        except (json.JSONDecodeError, ValueError):
            text = request.POST.get("text", "").strip()
    else:
        text = request.GET.get("text", "").strip()
    
    if not text or len(text) < 3:
        return JsonResponse({"suggestions": []})
    
    active_categories = ComplaintCategory.objects.filter(is_active=True)
    suggested_category, confidence = suggest_category(text, active_categories)
    
    if suggested_category:
        return JsonResponse({
            "suggestions": [
                {
                    "id": suggested_category.id,
                    "name": suggested_category.name,
                    "description": suggested_category.description,
                    "confidence": confidence,
                    "department": suggested_category.department.name,
                }
            ]
        })
    
    return JsonResponse({"suggestions": []})


def register(request):
    messages.info(request, "Students do not need an account. Submit a complaint using your enrollment number.")
    return redirect("core:complaint_create")


@login_required
def dashboard(request):
    profile = request.user.profile
    role_upper = str(getattr(profile, "role", "")).upper()
    context = {"profile": profile, "role_upper": role_upper}

    admin_roles = {"ADMIN", "REGISTRAR", "PROVOST", "HOD"}
    if request.user.is_superuser or role_upper in admin_roles:
        scoped_qs = get_scoped_complaints_for_user(request.user)
        now = timezone.now()

        # Console header identity, role badge & jurisdiction
        if role_upper == "PROVOST" and profile.managed_building:
            console_title = f"Provost Console: {profile.managed_building.name}"
            role_badge_text = f"Provost - {profile.managed_building.name}"
            jurisdiction_label = f"Hall / Building Code: {profile.managed_building.code}"
            tenant_mode = "provost"
            active_template = "core/provost_dashboard.html"
        elif role_upper == "HOD" and profile.managed_department:
            console_title = f"HOD Console: {profile.managed_department.name}"
            role_badge_text = f"HOD - {profile.managed_department.name}"
            jurisdiction_label = f"Department Code: {profile.managed_department.code}"
            tenant_mode = "hod"
            active_template = "core/hod_dashboard.html"
        else:
            console_title = "Registrar Master Console"
            role_badge_text = "Registrar"
            jurisdiction_label = "Global University-Wide Jurisdiction (All Halls & Departments)"
            tenant_mode = "registrar"
            active_template = "core/dashboard.html"

        # Optional Registrar / Superuser drill-down filter by Hall (Building) or Department
        selected_building_code = request.GET.get("building", "").strip()
        selected_department_code = request.GET.get("department", "").strip()
        inspected_building = None
        inspected_department = None

        if tenant_mode == "registrar":
            if selected_building_code:
                inspected_building = Building.objects.filter(code__iexact=selected_building_code).first()
                if inspected_building:
                    scoped_qs = scoped_qs.filter(
                        Q(room__floor__building=inspected_building)
                        | Q(room__floor__building__parent=inspected_building)
                    )
            if selected_department_code:
                inspected_department = Department.objects.filter(code__iexact=selected_department_code).first()
                if inspected_department:
                    scoped_qs = scoped_qs.filter(
                        Q(category__department=inspected_department)
                        | Q(room__floor__building__code__iexact=inspected_department.code)
                        | Q(room__floor__building__department=inspected_department)
                    ).distinct()

        # BUG 1: Compute KPI card counts directly from scoped_qs using ORM aggregations
        open_only_count = scoped_qs.filter(status=Complaint.Status.OPEN).count()
        assigned_only_count = scoped_qs.filter(status=Complaint.Status.ASSIGNED).count()
        pending_assigned = open_only_count + assigned_only_count
        in_progress = scoped_qs.filter(status=Complaint.Status.IN_PROGRESS).count()
        pending_verification = scoped_qs.filter(status=Complaint.Status.RESOLVED).count()
        closed_count = scoped_qs.filter(status=Complaint.Status.CLOSED).count()
        reopened_disputed = scoped_qs.filter(status=Complaint.Status.REOPENED).count()
        total_scoped = scoped_qs.count()
        sla_breach_count = scoped_qs.exclude(
            status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]
        ).filter(sla_due_at__lt=now).count()

        # BUG 1: Compute average staff accountability score strictly for personnel mapped to building/department
        staff_profiles_qs = UserProfile.objects.filter(role=UserProfile.Role.STAFF)
        if tenant_mode == "provost" and profile.managed_building:
            b = profile.managed_building
            mapped_staff_profiles = staff_profiles_qs.filter(
                Q(hall_location__icontains=b.name)
                | Q(managed_building=b)
                | Q(user__assigned_complaints__room__floor__building=b)
            ).distinct()
        elif tenant_mode == "hod" and profile.managed_department:
            d = profile.managed_department
            mapped_staff_profiles = staff_profiles_qs.filter(
                Q(department=d)
                | Q(managed_department=d)
                | Q(user__assigned_complaints__category__department=d)
            ).distinct()
        elif inspected_building:
            mapped_staff_profiles = staff_profiles_qs.filter(
                Q(hall_location__icontains=inspected_building.name)
                | Q(user__assigned_complaints__room__floor__building=inspected_building)
            ).distinct()
        elif inspected_department:
            mapped_staff_profiles = staff_profiles_qs.filter(
                Q(department=inspected_department)
                | Q(user__assigned_complaints__category__department=inspected_department)
            ).distinct()
        else:
            mapped_staff_profiles = staff_profiles_qs

        raw_avg_score = mapped_staff_profiles.aggregate(avg_score=Avg("accountability_score"))["avg_score"]
        avg_accountability_score = round(float(raw_avg_score), 1) if raw_avg_score is not None else 100.0

        # Role-specific breakdowns
        hall_room_breakdown = []
        hostel_breakdown = []
        hall_technicians = []
        dept_category_breakdown = []
        dept_room_breakdown = []
        dept_technicians = []
        all_buildings = []
        all_departments = []

        if tenant_mode == "provost" and profile.managed_building:
            b = profile.managed_building
            hall_room_breakdown = list(
                scoped_qs.values(
                    "room__floor__number",
                    "room__floor__label",
                    "room__number",
                    "room__name",
                )
                .annotate(
                    total=Count("id"),
                    open_count=Count(
                        "id",
                        filter=~Q(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]),
                    ),
                )
                .order_by("-total", "room__number")
            )
            # Constituent hostel / block breakdown for this residential hall
            constituent_hostels = list(b.hostels.filter(is_active=True).order_by("short_name"))
            hostel_map = {
                h.id: {
                    "id": h.id,
                    "name": h.short_name or h.name,
                    "code": h.code,
                    "wing": h.wing_detail or "—",
                    "capacity": h.capacity_detail or "—",
                    "total": 0,
                    "open_count": 0,
                }
                for h in constituent_hostels
            }
            direct_hall_total = 0
            direct_hall_open = 0
            for c in scoped_qs:
                bldg = c.room.floor.building if (c.room and c.room.floor) else None
                if bldg:
                    if bldg.id in hostel_map:
                        hostel_map[bldg.id]["total"] += 1
                        if c.status not in [Complaint.Status.RESOLVED, Complaint.Status.CLOSED]:
                            hostel_map[bldg.id]["open_count"] += 1
                    elif bldg.id == b.id:
                        direct_hall_total += 1
                        if c.status not in [Complaint.Status.RESOLVED, Complaint.Status.CLOSED]:
                            direct_hall_open += 1
            hostel_breakdown = list(hostel_map.values())
            if direct_hall_total > 0:
                hostel_breakdown.insert(0, {
                    "id": b.id,
                    "name": f"{b.name} (Main Complex)",
                    "code": b.code,
                    "wing": "Central / Common Facilities",
                    "capacity": b.capacity_detail or "—",
                    "total": direct_hall_total,
                    "open_count": direct_hall_open,
                })
            hall_technicians = list(
                User.objects.select_related("profile", "profile__department")
                .filter(
                    Q(profile__role=UserProfile.Role.STAFF)
                    & (
                        Q(profile__hall_location__icontains=b.name)
                        | Q(assigned_complaints__room__floor__building=b)
                        | Q(assigned_complaints__room__floor__building__parent=b)
                    )
                )
                .distinct()
                .annotate(
                    active_tasks=Count(
                        "assigned_complaints",
                        filter=(
                            Q(assigned_complaints__room__floor__building=b)
                            | Q(assigned_complaints__room__floor__building__parent=b)
                        )
                        & ~Q(assigned_complaints__status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]),
                    )
                )
            )
        elif tenant_mode == "hod" and profile.managed_department:
            d = profile.managed_department
            dept_category_breakdown = list(
                scoped_qs.values("category__name")
                .annotate(
                    total=Count("id"),
                    active=Count(
                        "id",
                        filter=~Q(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]),
                    ),
                )
                .order_by("-total")
            )
            dept_room_breakdown = list(
                scoped_qs.values(
                    "room__floor__building__name",
                    "room__number",
                    "room__name",
                )
                .annotate(total=Count("id"))
                .order_by("-total")
            )
            dept_technicians = list(
                User.objects.select_related("profile", "profile__department")
                .filter(profile__role=UserProfile.Role.STAFF, profile__department=d)
                .annotate(
                    active_tasks=Count(
                        "assigned_complaints",
                        filter=~Q(assigned_complaints__status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]),
                    )
                )
            )
        else:
            all_buildings = list(Building.objects.filter(is_active=True, parent__isnull=True).order_by("name"))
            all_departments = list(Department.objects.filter(is_active=True).order_by("name"))

        # Exact same scoped_qs rendered in the table so list counts == top-level KPI badges
        scoped_complaints_list = list(scoped_qs.order_by("-created_at"))

        context.update(
            {
                "dashboard_type": "administrator",
                "tenant_mode": tenant_mode,
                "console_title": console_title,
                "role_badge_text": role_badge_text,
                "jurisdiction_label": jurisdiction_label,
                "total_scoped_complaints": total_scoped,
                "pending_assigned_count": pending_assigned,
                "in_progress_count": in_progress,
                "pending_verification_count": pending_verification,
                "closed_count": closed_count,
                "reopened_disputed_count": reopened_disputed,
                "sla_breach_count": sla_breach_count,
                "avg_accountability_score": avg_accountability_score,
                "open_complaints": pending_assigned + in_progress + reopened_disputed,
                "resolved_complaints": pending_verification + closed_count,
                "campus_count": Campus.objects.filter(is_active=True).count(),
                "building_count": Building.objects.filter(is_active=True).count(),
                "room_count": Room.objects.filter(is_active=True).count(),
                "category_count": ComplaintCategory.objects.filter(is_active=True).count(),
                "recent_complaints": scoped_complaints_list,
                "complaints": scoped_complaints_list,
                "hall_room_breakdown": hall_room_breakdown,
                "hostel_breakdown": hostel_breakdown,
                "hall_technicians": hall_technicians,
                "dept_category_breakdown": dept_category_breakdown,
                "dept_room_breakdown": dept_room_breakdown,
                "dept_technicians": dept_technicians,
                "all_buildings": all_buildings,
                "all_departments": all_departments,
                "selected_building_code": selected_building_code,
                "selected_department_code": selected_department_code,
                "inspected_building": inspected_building,
                "inspected_department": inspected_department,
            }
        )
        return render(request, active_template, context)
    elif profile.role == UserProfile.Role.STAFF:
        context.update(
            {
                "dashboard_type": "staff",
                "console_title": f"Technician Portal: {request.user.get_full_name() or request.user.username}",
                "role_badge_text": f"Staff - {profile.department.name if profile.department else 'Maintenance'}",
                "department": profile.department,
                "category_count": ComplaintCategory.objects.filter(department=profile.department, is_active=True).count()
                if profile.department
                else 0,
                "assigned_complaints": Complaint.objects.filter(assigned_to=request.user).exclude(status=Complaint.Status.CLOSED).count(),
                "recent_complaints": Complaint.objects.filter(assigned_to=request.user).select_related("category", "reporter"),
            }
        )
    else:
        context.update(
            {
                "dashboard_type": "student",
                "console_title": "Student Dashboard",
                "role_badge_text": "Student",
                "my_open_complaints": Complaint.objects.filter(reporter=request.user).exclude(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]).count(),
                "my_resolved_complaints": Complaint.objects.filter(reporter=request.user, status=Complaint.Status.RESOLVED).count(),
                "recent_complaints": Complaint.objects.filter(reporter=request.user).select_related("category"),
            }
        )

    return render(request, "core/dashboard.html", context)


admin_dashboard = dashboard
dashboard_view = dashboard


def complaint_create(request):
    if request.method == "POST":
        form = ComplaintSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.category_detected_automatically = form.category_detected_automatically
            complaint.category_detection_confidence = form.category_detection_confidence
            complaint.priority_score = form.priority_score
            complaint.priority_reason = form.priority_reason
            complaint.priority = form.recommended_priority
            qr_room_param = request.GET.get("room") or request.POST.get("qr_room")
            if qr_room_param and not complaint.room_id:
                matched_qr_room = Room.objects.filter(
                    Q(qr_code_token=qr_room_param) | Q(id__iexact=str(qr_room_param))
                ).first() if str(qr_room_param).isdigit() else Room.objects.filter(qr_code_token=qr_room_param).first()
                if matched_qr_room:
                    complaint.room = matched_qr_room
            bind_complaint_spatial_origin(complaint)
            set_sla_due_date(complaint)

            # ── AI Staff Auto-Assignment ─────────────────────────────────────
            category_name = complaint.category.name if complaint.category_id else ""
            location_text = complaint.location_description or ""
            staff_matches = suggest_staff(
                category_name=category_name,
                location_description=location_text,
                title=complaint.title or "",
                description=complaint.description or "",
                n=1,
            )
            if staff_matches:
                best_match = staff_matches[0]
                try:
                    assigned_user = User.objects.get(username=best_match["username"])
                    complaint.assigned_to = assigned_user
                    complaint.assigned_at = timezone.now()
                    complaint.status = Complaint.Status.ASSIGNED
                except User.DoesNotExist:
                    pass  # Staff user not in DB yet — fallback to dispatcher
            if not complaint.assigned_to_id:
                auto_dispatch_complaint(complaint, save=False)
            # ────────────────────────────────────────────────────────────────

            if request.FILES.get("evidence"):
                complaint.evidence = compress_uploaded_image(request.FILES["evidence"])
            from django.core.exceptions import ValidationError as DjangoValidationError
            try:
                complaint.full_clean()
            except DjangoValidationError as exc:
                form.add_error(None, exc)
                return render(
                    request,
                    "core/complaint_form.html",
                    {
                        "form": form,
                        "active_halls": Building.objects.filter(is_active=True, parent__isnull=True, building_type="hall").prefetch_related("hostels").order_by("name"),
                        "active_hostels": Building.objects.filter(is_active=True, parent__isnull=False).select_related("parent").order_by("parent__name", "short_name"),
                    },
                )
            complaint.save()
            duplicate = find_potential_duplicate(complaint)
            if duplicate:
                complaint.duplicate_of = duplicate
                complaint.save(update_fields=["duplicate_of", "updated_at"])

            ComplaintStatusHistory.objects.create(
                complaint=complaint, status=Complaint.Status.OPEN, note="Complaint submitted."
            )
            if complaint.assigned_to:
                ComplaintStatusHistory.objects.create(
                    complaint=complaint,
                    status=complaint.status,
                    note=f"Auto-assigned to {complaint.assigned_to.get_full_name() or complaint.assigned_to.username} based on category and location.",
                )
            if duplicate:
                messages.success(request, f"Complaint {complaint.reference} submitted. A similar report ({duplicate.reference}) was found.")
            elif complaint.assigned_to:
                messages.success(request, f"Complaint {complaint.reference} submitted and assigned to {complaint.assigned_to.get_full_name()}. Tracking token: {complaint.tracking_token}")
            else:
                messages.success(request, f"Complaint {complaint.reference} has been submitted. Your tracking token is: {complaint.tracking_token}")
            return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
    else:
        form = ComplaintSubmissionForm()
    return render(
        request,
        "core/complaint_form.html",
        {
            "form": form,
            "active_halls": Building.objects.filter(is_active=True, parent__isnull=True, building_type="hall").prefetch_related("hostels").order_by("name"),
            "active_hostels": Building.objects.filter(is_active=True, parent__isnull=False).select_related("parent").order_by("parent__name", "short_name"),
        },
    )


@login_required
def complaint_list(request):
    role = getattr(getattr(request.user, "profile", None), "role", None)
    admin_roles = {
        UserProfile.Role.ADMIN,
        UserProfile.Role.REGISTRAR,
        UserProfile.Role.PROVOST,
        UserProfile.Role.HOD,
    }
    if request.user.is_superuser or role in admin_roles:
        complaints = get_scoped_complaints(request.user).select_related("category", "reporter", "assigned_to")
    elif request.user.is_staff or role == UserProfile.Role.STAFF:
        complaints = Complaint.objects.select_related("category", "reporter", "assigned_to")
    else:
        complaints = Complaint.objects.filter(Q(reporter=request.user) | Q(is_public=True)).select_related("category", "assigned_to")
    
    # Default to showing all complaints (including auto-assigned) when no filter is chosen
    status = request.GET.get("status", "")
    if status in Complaint.Status.values:
        complaints = complaints.filter(status=status)
    
    # Annotate with support count and user's support status
    complaints = complaints.annotate(support_count=Count("supports"))
    
    # For authenticated users, mark which complaints they've supported
    user_supported_ids = set()
    if request.user.is_authenticated:
        user_supported_ids = set(
            ComplaintSupport.objects.filter(user=request.user, complaint__in=complaints).values_list("complaint_id", flat=True)
        )
    
    return render(
        request,
        "core/complaint_list.html",
        {
            "complaints": complaints, 
            "selected_status": status, 
            "status_choices": Complaint.Status.choices,
            "user_supported_ids": user_supported_ids,
        },
    )


def complaint_detail(request, reference):
    # Allow direct access via tracking_token for students
    if len(reference) == 32 and Complaint.objects.filter(tracking_token=reference).exists():
        return complaint_tracking(request, tracking_token=reference)

    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())

    complaint = get_object_or_404(
        Complaint.objects.select_related("reporter", "category", "room", "assigned_to", "assigned_by").annotate(
            support_count=Count("supports")
        ),
        reference=reference,
    )
    role = getattr(getattr(request.user, "profile", None), "role", None)
    admin_roles = {
        UserProfile.Role.ADMIN,
        UserProfile.Role.REGISTRAR,
        UserProfile.Role.PROVOST,
        UserProfile.Role.HOD,
    }
    can_manage = request.user.is_staff or role in ({UserProfile.Role.STAFF} | admin_roles)
    can_assign_and_update_status = request.user.is_superuser or (role in admin_roles)
    
    if role in {UserProfile.Role.PROVOST, UserProfile.Role.HOD} and not request.user.is_superuser:
        if not get_scoped_complaints_for_user(request.user).filter(pk=complaint.pk).exists():
            messages.error(request, "Access denied: This complaint belongs to another Hall or Department jurisdiction.")
            return redirect("core:dashboard")
    if complaint.reporter_id != request.user.id and not complaint.is_public and not can_manage:
        messages.error(request, "You do not have permission to view that complaint.")
        return redirect("core:complaint_list")
    return render(
        request,
        "core/complaint_detail.html",
        {
            "complaint": complaint,
            "can_manage": can_manage,
            "can_assign_and_update_status": can_assign_and_update_status,  # New flag for admin-only operations
            "assignment_form": ComplaintAssignmentForm(instance=complaint) if can_assign_and_update_status else None,
            "status_form": ComplaintStatusForm(initial={"status": complaint.status}) if can_assign_and_update_status else None,
            "has_supported": ComplaintSupport.objects.filter(complaint=complaint, user=request.user).exists(),
            "verification_form": ResolutionVerificationForm() if complaint.reporter_id == request.user.id and complaint.status == Complaint.Status.RESOLVED else None,
            "reopen_form": ComplaintReopenForm() if complaint.reporter_id == request.user.id and complaint.status in {Complaint.Status.RESOLVED, Complaint.Status.CLOSED} else None,
            "feedback_form": ComplaintFeedbackForm() if complaint.reporter_id == request.user.id and complaint.resolution_verification == Complaint.ResolutionVerification.VERIFIED and not hasattr(complaint, "feedback") else None,
            "has_feedback": hasattr(complaint, "feedback"),
        },
    )


def tracking_form(request):
    """Form page for users to enter their tracking token."""
    if request.method == "POST":
        tracking_token = request.POST.get("tracking_token", "").strip()
        if tracking_token:
            return redirect("core:complaint_tracking", tracking_token=tracking_token)
        else:
            messages.error(request, "Please enter a tracking token.")
    return render(request, "core/tracking_form.html")


def _can_student_modify_complaint(request, complaint):
    if request.user.is_authenticated and complaint.reporter_id == request.user.id:
        return True
    token = request.POST.get("tracking_token") or request.GET.get("tracking_token")
    if token and complaint.tracking_token == token:
        return True
    return False


def complaint_tracking(request, tracking_token):
    """Private no-account tracking page reached from the student's submission receipt."""
    complaint = get_object_or_404(
        Complaint.objects.select_related("category", "room", "assigned_to", "assigned_by").annotate(
            support_count=Count("supports")
        ),
        tracking_token=tracking_token,
    )
    can_verify = complaint.status == Complaint.Status.RESOLVED
    can_reopen = complaint.status in {Complaint.Status.RESOLVED, Complaint.Status.CLOSED}
    can_feedback = (
        complaint.resolution_verification == Complaint.ResolutionVerification.VERIFIED
        and not hasattr(complaint, "feedback")
    )
    return render(
        request,
        "core/complaint_detail.html",
        {
            "complaint": complaint,
            "can_manage": False,
            "is_tracking_view": True,
            "has_supported": False,
            "verification_form": ResolutionVerificationForm() if can_verify else None,
            "reopen_form": ComplaintReopenForm() if can_reopen else None,
            "feedback_form": ComplaintFeedbackForm() if can_feedback else None,
            "has_feedback": hasattr(complaint, "feedback"),
        },
    )


def complaint_toggle_support(request, reference):
    """Allow both logged-in and anonymous visitors to support a complaint."""
    if request.method != "POST":
        next_url = request.GET.get("next", "/")
        return redirect(next_url)
    complaint = get_object_or_404(Complaint, reference=reference)
    if request.user.is_authenticated:
        support, created = ComplaintSupport.objects.get_or_create(
            complaint=complaint, user=request.user, defaults={"session_key": ""}
        )
        if created:
            messages.success(request, "Your support has been added.")
        else:
            support.delete()
            messages.info(request, "Your support was removed.")
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key or ""
        if session_key:
            support, created = ComplaintSupport.objects.get_or_create(
                complaint=complaint, session_key=session_key, defaults={"user": None}
            )
            if created:
                messages.success(request, "Your support has been added.")
            else:
                support.delete()
                messages.info(request, "Your support was removed.")
    next_url = request.POST.get("next") or request.GET.get("next") or "/"
    return redirect(next_url)


@admin_only_required
def complaint_assign(request, reference):
    complaint = get_object_or_404(Complaint, reference=reference)
    if request.method != "POST":
        return redirect("core:complaint_detail", reference=reference)
    form = ComplaintAssignmentForm(request.POST, instance=complaint)
    if form.is_valid():
        updated = form.save(commit=False)
        updated.assigned_by = request.user
        updated.assigned_at = timezone.now()
        if updated.status == Complaint.Status.OPEN:
            updated.status = Complaint.Status.ASSIGNED
        try:
            updated.full_clean()
            updated.save()
            ComplaintStatusHistory.objects.create(
                complaint=updated, status=updated.status, note=f"Assigned to {updated.assigned_to.get_full_name() or updated.assigned_to.username}.", changed_by=request.user
            )
            messages.success(request, "Maintenance staff member assigned.")
        except Exception as exc:
            messages.error(request, f"Assignment could not be saved: {exc}")
    else:
        messages.error(request, "The assignment could not be saved.")
    return redirect("core:complaint_detail", reference=reference)


@admin_only_required
def complaint_update_status(request, reference):
    complaint = get_object_or_404(Complaint, reference=reference)
    if request.method != "POST":
        return redirect("core:complaint_detail", reference=reference)
    form = ComplaintStatusForm(request.POST)
    if form.is_valid():
        new_status = form.cleaned_data["status"]
        complaint.status = new_status
        if new_status == Complaint.Status.RESOLVED:
            complaint.resolved_at = timezone.now()
            complaint.resolution_verification = Complaint.ResolutionVerification.PENDING
            complaint.resolution_note = form.cleaned_data["note"]
        complaint.save(update_fields=["status", "resolved_at", "resolution_verification", "resolution_note", "updated_at"])
        ComplaintStatusHistory.objects.create(
            complaint=complaint, status=new_status, note=form.cleaned_data["note"], changed_by=request.user
        )
        messages.success(request, "Complaint status updated.")
    return redirect("core:complaint_detail", reference=reference)


def complaint_verify_resolution(request, reference):
    complaint = get_object_or_404(Complaint, reference=reference)
    if not _can_student_modify_complaint(request, complaint):
        messages.error(request, "You do not have permission to verify this complaint.")
        return redirect("core:home")
    if request.method != "POST" or complaint.status != Complaint.Status.RESOLVED:
        if complaint.tracking_token and not request.user.is_authenticated:
            return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
        return redirect("core:complaint_detail", reference=reference)
    form = ResolutionVerificationForm(request.POST)
    if form.is_valid():
        decision = form.cleaned_data["decision"]
        complaint.resolution_verification = decision
        complaint.resolution_verified_at = timezone.now()
        if decision == Complaint.ResolutionVerification.VERIFIED:
            complaint.status = Complaint.Status.CLOSED
            complaint.closed_at = timezone.now()
            complaint.purge_attached_media()
            note = "Student verified that the resolution is complete."
        else:
            complaint.status = Complaint.Status.REOPENED
            complaint.reopened_count += 1
            set_sla_due_date(complaint)
            note = "Student rejected the resolution and reopened the complaint."
        if form.cleaned_data["note"]:
            note = f"{note} {form.cleaned_data['note']}"
        complaint.save(update_fields=["status", "resolution_verification", "resolution_verified_at", "reopened_count", "sla_due_at", "updated_at"])
        changer = request.user if request.user.is_authenticated else None
        ComplaintStatusHistory.objects.create(complaint=complaint, status=complaint.status, note=note, changed_by=changer)
        messages.success(request, "Your resolution response has been recorded.")
    if complaint.tracking_token and not request.user.is_authenticated:
        return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
    return redirect("core:complaint_detail", reference=reference)


def complaint_reopen(request, reference):
    complaint = get_object_or_404(Complaint, reference=reference)
    if not _can_student_modify_complaint(request, complaint):
        messages.error(request, "You do not have permission to reopen this complaint.")
        return redirect("core:home")
    if request.method != "POST" or complaint.status not in {Complaint.Status.RESOLVED, Complaint.Status.CLOSED}:
        if complaint.tracking_token and not request.user.is_authenticated:
            return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
        return redirect("core:complaint_detail", reference=reference)
    form = ComplaintReopenForm(request.POST)
    if form.is_valid():
        complaint.status = Complaint.Status.REOPENED
        complaint.resolution_verification = Complaint.ResolutionVerification.REJECTED
        complaint.resolution_verified_at = timezone.now()
        complaint.reopened_count += 1
        set_sla_due_date(complaint)
        complaint.save(update_fields=["status", "resolution_verification", "resolution_verified_at", "reopened_count", "sla_due_at", "updated_at"])
        changer = request.user if request.user.is_authenticated else None
        ComplaintStatusHistory.objects.create(
            complaint=complaint, status=Complaint.Status.REOPENED, note=f"Reopened by student: {form.cleaned_data['note']}", changed_by=changer
        )
        messages.success(request, "The complaint has been reopened.")
    if complaint.tracking_token and not request.user.is_authenticated:
        return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
    return redirect("core:complaint_detail", reference=reference)


def complaint_feedback(request, reference):
    complaint = get_object_or_404(Complaint, reference=reference)
    if not _can_student_modify_complaint(request, complaint):
        messages.error(request, "You do not have permission to leave feedback on this complaint.")
        return redirect("core:home")
    if request.method != "POST" or complaint.resolution_verification != Complaint.ResolutionVerification.VERIFIED:
        if complaint.tracking_token and not request.user.is_authenticated:
            return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
        return redirect("core:complaint_detail", reference=reference)
    if hasattr(complaint, "feedback"):
        messages.error(request, "Feedback has already been submitted for this complaint.")
        if complaint.tracking_token and not request.user.is_authenticated:
            return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
        return redirect("core:complaint_detail", reference=reference)
    form = ComplaintFeedbackForm(request.POST)
    if form.is_valid():
        feedback = form.save(commit=False)
        feedback.complaint = complaint
        try:
            feedback.full_clean()
            feedback.save()
            messages.success(request, "Thank you for your feedback.")
        except Exception as exc:
            messages.error(request, f"Feedback could not be saved: {exc}")
    if complaint.tracking_token and not request.user.is_authenticated:
        return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
    return redirect("core:complaint_detail", reference=reference)


@staff_or_admin_required
def analytics_dashboard(request):
    try:
        days = int(request.GET.get("days", 30))
    except ValueError:
        days = 30
    days = days if days in {7, 30, 90} else 30
    return render(request, "core/analytics_dashboard.html", analytics_snapshot(days))


@staff_or_admin_required
def complaint_report_csv(request):
    """Export the filtered maintenance register for department review or archival."""
    import csv

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="campuscare-complaint-report.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Reference", "Title", "Category", "Department", "Status", "Priority", "Priority score", "Location",
        "Reported at", "SLA deadline", "Resolved at", "Escalation level", "Support count", "Rating",
    ])
    role_upper = str(getattr(getattr(request.user, "profile", None), "role", "")).upper()
    if request.user.is_superuser or role_upper in {"REGISTRAR", "PROVOST", "HOD", "ADMIN"}:
        complaints = get_scoped_complaints_for_user(request.user).prefetch_related("supports", "feedback")
    else:
        complaints = Complaint.objects.select_related("category__department", "room").prefetch_related("supports", "feedback")
    for complaint in complaints:
        location = str(complaint.room) if complaint.room else complaint.location_description
        writer.writerow([
            complaint.reference, complaint.title, complaint.category.name, complaint.category.department.name,
            complaint.get_status_display(), complaint.get_priority_display(), complaint.priority_score, location,
            complaint.created_at.isoformat(), complaint.sla_due_at.isoformat() if complaint.sla_due_at else "",
            complaint.resolved_at.isoformat() if complaint.resolved_at else "", complaint.escalation_level,
            complaint.supports.count(), complaint.feedback.rating if hasattr(complaint, "feedback") else "",
        ])
    return response


@staff_or_admin_required
def campus_directory(request):
    """Read-only operational directory; editing stays protected in Django admin."""
    active_rooms = Room.objects.filter(is_active=True)
    active_floors = Floor.objects.prefetch_related(Prefetch("rooms", queryset=active_rooms))
    active_buildings = Building.objects.filter(is_active=True).prefetch_related(
        Prefetch("floors", queryset=active_floors)
    )
    campuses = Campus.objects.filter(is_active=True).prefetch_related(
        Prefetch("buildings", queryset=active_buildings)
    )
    return render(
        request,
        "core/campus_directory.html",
        {
            "campuses": campuses,
            "departments": Department.objects.filter(is_active=True).prefetch_related("complaint_categories"),
        },
    )


def analyze_urgency_api(request):
    """API: POST JSON with title/description/category/location -> AI priority + SLA estimate."""
    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=400)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    category_name = data.get("category", "").strip()
    location = data.get("location", "").strip()
    text = f"{title} {description}"
    score, priority, reason, sla_hours = score_priority(
        text, title=title, description=description, category_name=category_name, location=location,
    )
    priority_display = {"urgent": "Urgent", "high": "High", "normal": "Normal", "low": "Low"}.get(priority, priority)
    if sla_hours <= 2:
        sla_display = f"{sla_hours}h (Emergency)"
    elif sla_hours <= 6:
        sla_display = f"{sla_hours}h (Same day)"
    elif sla_hours <= 24:
        sla_display = f"{sla_hours}h (Next business day)"
    else:
        sla_display = f"{sla_hours}h ({sla_hours // 24} days)"
    staff_matches = suggest_staff(
        category_name=category_name,
        location_description=location,
        title=title,
        description=description,
        n=1,
    )
    suggested_staff = None
    if staff_matches:
        s = staff_matches[0]
        suggested_staff = {
            "name": s["name"],
            "role": s["role"],
            "dept": s["dept"],
            "location": s["location"],
            "contact": s["contact"],
            "reason": s["match_reason"],
        }

    return JsonResponse({
        "priority": priority,
        "priority_display": priority_display,
        "priority_score": score,
        "sla_hours": sla_hours,
        "sla_display": sla_display,
        "reason": reason,
        "suggested_staff": suggested_staff,
    })


def room_lookup_api(request):
    """
    API endpoint: search and auto-identify Room, Hostel, and Hall from query.
    GET/POST params: q, query, room, hall, hostel, or token.
    """
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            q = body.get("q") or body.get("query") or body.get("room") or ""
            hall_param = body.get("hall", "")
            hostel_param = body.get("hostel", "")
        except (json.JSONDecodeError, ValueError):
            q = request.POST.get("q") or request.POST.get("query") or request.POST.get("room") or ""
            hall_param = request.POST.get("hall", "")
            hostel_param = request.POST.get("hostel", "")
    else:
        q = request.GET.get("q") or request.GET.get("query") or request.GET.get("room") or ""
        hall_param = request.GET.get("hall", "")
        hostel_param = request.GET.get("hostel", "")

    q = str(q).strip()
    hall_param = str(hall_param).strip()
    hostel_param = str(hostel_param).strip()

    rooms_qs = Room.objects.filter(is_active=True).select_related("floor__building", "floor__building__parent")

    if hostel_param:
        rooms_qs = rooms_qs.filter(
            Q(floor__building__code__iexact=hostel_param)
            | Q(floor__building__short_name__icontains=hostel_param)
            | Q(floor__building__name__icontains=hostel_param)
        )
    elif hall_param:
        rooms_qs = rooms_qs.filter(
            Q(floor__building__code__iexact=hall_param)
            | Q(floor__building__parent__code__iexact=hall_param)
            | Q(floor__building__parent__name__icontains=hall_param)
            | Q(floor__building__name__icontains=hall_param)
        )

    matched_room = None
    if q:
        # Check by qr_code_token
        matched_room = rooms_qs.filter(qr_code_token=q).first()
        if not matched_room:
            # Check by exact room number
            matched_room = rooms_qs.filter(number__iexact=q).first()
        if not matched_room:
            # Check by room name or partial match
            matched_room = rooms_qs.filter(Q(name__icontains=q) | Q(number__icontains=q)).first()
    else:
        matched_room = rooms_qs.first()

    if matched_room:
        bldg = matched_room.floor.building
        parent_hall = bldg.parent if bldg.parent else bldg
        hostel_name = bldg.short_name if bldg.parent else ""
        return JsonResponse({
            "found": True,
            "room_id": matched_room.id,
            "room_number": matched_room.number,
            "room_name": matched_room.name,
            "floor_number": matched_room.floor.number,
            "floor_label": matched_room.floor.label or f"Floor {matched_room.floor.number}",
            "building_id": bldg.id,
            "building_name": bldg.name,
            "building_code": bldg.code,
            "hostel_name": hostel_name,
            "hostel_code": bldg.code if bldg.parent else "",
            "hall_id": parent_hall.id,
            "hall_name": parent_hall.name,
            "hall_code": parent_hall.code,
            "display": f"{parent_hall.name} · {hostel_name + ' · ' if hostel_name else ''}Room {matched_room.number}",
        })

    return JsonResponse({
        "found": False,
        "message": f"No room matching '{q}' found.",
    })


def technician_task_view(request, task_token):
    """Zero-login technician task execution portal accessed via UUID staff_task_token."""
    complaint = get_object_or_404(Complaint, staff_task_token=task_token)
    error_message = None

    if request.method == "POST":
        action = request.POST.get("action", "").strip().lower()

        if action == "close" or request.POST.get("status", "").strip().lower() == Complaint.Status.CLOSED:
            error_message = "Technicians are not permitted to close complaints. Only students can confirm closure."
            return render(
                request,
                "core/technician_task.html",
                {"complaint": complaint, "error_message": error_message},
                status=403,
            )

        if action == "start":
            now = timezone.now()
            complaint.status = Complaint.Status.IN_PROGRESS
            complaint.in_progress_at = now
            complaint.save(update_fields=["status", "in_progress_at", "updated_at"])
            ComplaintStatusHistory.objects.create(
                complaint=complaint,
                status=Complaint.Status.IN_PROGRESS,
                note="Technician started working on task via token link.",
            )
            messages.success(request, "Task marked as In Progress. Dwell timer started.")
            return redirect("core:technician_task_view", task_token=complaint.staff_task_token)

        elif action == "resolve":
            now = timezone.now()
            if not complaint.in_progress_at:
                error_message = "Task must be started (In Progress) before it can be resolved."
                return render(
                    request,
                    "core/technician_task.html",
                    {"complaint": complaint, "error_message": error_message},
                    status=400,
                )

            elapsed_seconds = (now - complaint.in_progress_at).total_seconds()
            if elapsed_seconds < 300:
                remaining = int(300 - elapsed_seconds)
                error_message = f"Minimum 5-minute dwell-time required before resolving ({remaining}s remaining)."
                return render(
                    request,
                    "core/technician_task.html",
                    {"complaint": complaint, "error_message": error_message},
                    status=400,
                )

            proof_file = (
                request.FILES.get("resolution_proof")
                or request.FILES.get("proof")
                or request.FILES.get("evidence")
                or request.FILES.get("image")
            )
            if not proof_file:
                error_message = "Camera proof image is mandatory to mark a complaint as resolved."
                return render(
                    request,
                    "core/technician_task.html",
                    {"complaint": complaint, "error_message": error_message},
                    status=400,
                )

            compressed_proof = compress_uploaded_image(proof_file)
            complaint.resolution_proof = compressed_proof
            complaint.status = Complaint.Status.RESOLVED
            complaint.resolved_at = now
            complaint.resolution_verification = Complaint.ResolutionVerification.PENDING
            note_text = request.POST.get("resolution_note") or request.POST.get("note") or "Resolved by technician with camera proof."
            complaint.resolution_note = note_text
            complaint.save(
                update_fields=[
                    "resolution_proof",
                    "status",
                    "resolved_at",
                    "resolution_verification",
                    "resolution_note",
                    "updated_at",
                ]
            )
            ComplaintStatusHistory.objects.create(
                complaint=complaint,
                status=Complaint.Status.RESOLVED,
                note=note_text,
            )
            messages.success(request, "Task marked as Resolved and awaiting student verification.")
            return redirect("core:technician_task_view", task_token=complaint.staff_task_token)

    return render(
        request,
        "core/technician_task.html",
        {"complaint": complaint, "error_message": error_message},
    )


def student_confirm_resolution(request, tracking_token):
    """Public token-authenticated endpoint for students to confirm resolution, rate, and purge media."""
    complaint = (
        Complaint.objects.filter(tracking_token=tracking_token).first()
        or get_object_or_404(Complaint, reference=tracking_token)
    )
    if request.method != "POST":
        return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)

    now = timezone.now()
    complaint.status = Complaint.Status.CLOSED
    complaint.closed_at = now
    complaint.resolution_verification = Complaint.ResolutionVerification.VERIFIED
    complaint.resolution_verified_at = now
    complaint.save(
        update_fields=[
            "status",
            "closed_at",
            "resolution_verification",
            "resolution_verified_at",
            "updated_at",
        ]
    )

    # Record student feedback rating
    raw_rating = request.POST.get("rating", "5")
    try:
        rating_val = max(1, min(5, int(raw_rating)))
    except (ValueError, TypeError):
        rating_val = 5
    comment_val = (request.POST.get("comment") or request.POST.get("note") or "").strip()
    ComplaintFeedback.objects.update_or_create(
        complaint=complaint,
        defaults={"rating": rating_val, "comment": comment_val},
    )

    # Purge attached images from disk now that complaint is closed
    complaint.purge_attached_media()

    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        status=Complaint.Status.CLOSED,
        note=f"Student confirmed resolution (Rating: {rating_val}/5). Media purged.",
    )
    messages.success(request, "Thank you! Complaint confirmed as Closed and media files cleaned up.")
    return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)


def student_reopen_complaint(request, tracking_token):
    """
    Public token-authenticated endpoint for students to dispute/reopen a resolved complaint.
    Requires explanation (>= 10 chars) and mandatory photo proof.
    Compresses proof, sets status to REOPENED, bumps priority to urgent,
    and deducts 15 points from assigned technician accountability_score.
    """
    complaint = (
        Complaint.objects.filter(tracking_token=tracking_token).first()
        or get_object_or_404(Complaint, reference=tracking_token)
    )
    if request.method != "POST":
        return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)

    explanation = (
        request.POST.get("reopen_reason")
        or request.POST.get("reason")
        or request.POST.get("note")
        or request.POST.get("explanation")
        or ""
    ).strip()

    proof_file = (
        request.FILES.get("reopen_proof")
        or request.FILES.get("proof")
        or request.FILES.get("evidence")
        or request.FILES.get("image")
    )

    # Legacy logged-in student reopen by reference without photo proof
    if (
        complaint.reference == tracking_token
        and not proof_file
        and request.user.is_authenticated
        and complaint.reporter_id == request.user.id
        and len(explanation) > 0
    ):
        return complaint_reopen(request, reference=complaint.reference)

    if len(explanation) < 10:
        messages.error(request, "Please provide a detailed explanation of at least 10 characters to reopen.")
        return HttpResponse(
            "Explanation must be at least 10 characters long.",
            status=400,
        )

    if not proof_file:
        messages.error(request, "Mandatory photo proof is required to reopen a complaint.")
        return HttpResponse(
            "Photo proof (reopen_proof) is required to reopen a complaint.",
            status=400,
        )

    now = timezone.now()
    compressed_proof = compress_uploaded_image(proof_file)
    complaint.reopen_proof = compressed_proof
    complaint.reopen_reason = explanation
    complaint.status = Complaint.Status.REOPENED
    complaint.reopened_at = now
    complaint.resolution_verification = Complaint.ResolutionVerification.REJECTED
    complaint.resolution_verified_at = now
    complaint.reopen_count = (complaint.reopen_count or 0) + 1
    complaint.reopened_count = (complaint.reopened_count or 0) + 1
    complaint.priority = Complaint.Priority.URGENT
    complaint.priority_score = max(complaint.priority_score or 0, 95)
    set_sla_due_date(complaint, from_time=now)
    complaint.save(
        update_fields=[
            "reopen_proof",
            "reopen_reason",
            "status",
            "reopened_at",
            "resolution_verification",
            "resolution_verified_at",
            "reopen_count",
            "reopened_count",
            "priority",
            "priority_score",
            "sla_due_at",
            "updated_at",
        ]
    )

    # Deduct 15 points from assigned technician accountability_score
    if complaint.assigned_to_id:
        profile, _ = UserProfile.objects.get_or_create(user_id=complaint.assigned_to_id)
        profile.accountability_score = (profile.accountability_score or 100) - 15
        profile.save(update_fields=["accountability_score", "updated_at"])

    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        status=Complaint.Status.REOPENED,
        note=f"Reopened by student with photo proof (Priority bumped to Urgent): {explanation}",
    )
    messages.success(request, "Complaint has been reopened and escalated to Urgent priority.")
    return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)


from django.contrib.auth.views import LoginView as DjangoLoginView
from django.urls import reverse

class SubAdminLoginView(DjangoLoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        return reverse("core:dashboard")
