"""
Administrative, executive, provost, HOD, registrar consoles, analytics, and dispatch sheets.
"""

import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from core.analytics import analytics_snapshot
from core.decorators import staff_or_admin_required, superuser_or_registrar_required
from core.models import (
    Building, Campus, Complaint, ComplaintCategory, ComplaintStatusHistory,
    Department, Floor, Room, UserProfile,
)
from core.permissions import get_scoped_complaints_for_user


@login_required
def dashboard(request):
    profile = getattr(request.user, "profile", None)
    if not profile and request.user.is_authenticated:
        role = UserProfile.Role.ADMIN if request.user.is_superuser else UserProfile.Role.STUDENT
        profile, _ = UserProfile.objects.get_or_create(user=request.user, defaults={"role": role})
    role_upper = str(getattr(profile, "role", "")).upper()
    context = {"profile": profile, "role_upper": role_upper}

    admin_roles = {"ADMIN", "REGISTRAR", "PROVOST", "HOD"}
    is_hall_caretaker = bool(profile and profile.managed_building)
    if request.user.is_superuser or role_upper in admin_roles or is_hall_caretaker:
        scoped_qs = get_scoped_complaints_for_user(request.user).select_related(
            "room__floor__building__parent",
            "category__department",
            "assigned_to__profile__department",
        )
        now = timezone.now()

        # Console header identity, role badge & jurisdiction
        if role_upper == "PROVOST" and profile.managed_building:
            console_title = f"Provost Console: {profile.managed_building.name}"
            role_badge_text = f"Provost - {profile.managed_building.name}"
            jurisdiction_label = f"Hall / Building Code: {profile.managed_building.code}"
            tenant_mode = "provost"
            active_template = "core/provost_dashboard.html"
        elif is_hall_caretaker and role_upper != "HOD":
            console_title = f"Caretaker Console: {profile.managed_building.name}"
            role_badge_text = f"Caretaker - {profile.managed_building.name}"
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

        # Compute KPI card counts in a single consolidated SQL aggregation
        kpi_metrics = scoped_qs.aggregate(
            total_scoped=Count("id"),
            open_only=Count("id", filter=Q(status=Complaint.Status.OPEN)),
            assigned_only=Count("id", filter=Q(status=Complaint.Status.ASSIGNED)),
            in_progress=Count("id", filter=Q(status=Complaint.Status.IN_PROGRESS)),
            pending_verification=Count("id", filter=Q(status=Complaint.Status.RESOLVED)),
            closed_count=Count("id", filter=Q(status=Complaint.Status.CLOSED)),
            reopened_disputed=Count("id", filter=Q(status=Complaint.Status.REOPENED)),
            sla_breach_count=Count(
                "id",
                filter=~Q(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]) & Q(sla_due_at__lt=now),
            ),
        )
        total_scoped = kpi_metrics["total_scoped"] or 0
        open_only_count = kpi_metrics["open_only"] or 0
        assigned_only_count = kpi_metrics["assigned_only"] or 0
        pending_assigned = open_only_count + assigned_only_count
        in_progress = kpi_metrics["in_progress"] or 0
        pending_verification = kpi_metrics["pending_verification"] or 0
        closed_count = kpi_metrics["closed_count"] or 0
        reopened_disputed = kpi_metrics["reopened_disputed"] or 0
        sla_breach_count = kpi_metrics["sla_breach_count"] or 0

        # Compute average staff accountability score strictly for personnel mapped to building/department
        staff_profiles_qs = UserProfile.objects.filter(role=UserProfile.Role.STAFF)
        if tenant_mode == "provost" and profile.managed_building:
            b = profile.managed_building
            mapped_staff_profiles = staff_profiles_qs.filter(
                Q(hall_location__icontains=b.name)
                | Q(managed_building=b)
                | Q(user__assigned_complaints__room__floor__building=b)
                | Q(user__assigned_complaints__room__floor__building__parent=b)
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
                | Q(user__assigned_complaints__room__floor__building__parent=inspected_building)
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
        # Dining Incharge KPIs — populated only in provost tenant_mode
        dining_incharge = None
        dining_pending  = 0
        dining_resolved = 0

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
                        | Q(profile__managed_building=b)
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
            # ── Dining Incharge KPIs for this hall ───────────────────────────
            dining_incharge_profile = UserProfile.objects.select_related("user", "department").filter(
                role=UserProfile.Role.STAFF,
                managed_building=b,
                managed_department__code="MESS",
            ).first()
            dining_incharge = dining_incharge_profile.user if dining_incharge_profile else None
            dining_qs = scoped_qs.filter(category__department__code="MESS")
            dining_counts = dining_qs.aggregate(
                pending=Count("id", filter=~Q(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED])),
                resolved=Count("id", filter=Q(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED])),
            )
            dining_pending  = dining_counts["pending"] or 0
            dining_resolved = dining_counts["resolved"] or 0
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
                # Dining Incharge KPIs (provost mode)
                "dining_incharge": dining_incharge if tenant_mode == "provost" else None,
                "dining_pending":  dining_pending  if tenant_mode == "provost" else 0,
                "dining_resolved": dining_resolved if tenant_mode == "provost" else 0,
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


@staff_or_admin_required
def analytics_dashboard(request):
    try:
        days = int(request.GET.get("days", 30))
    except ValueError:
        days = 30
    days = days if days in {7, 30, 90} else 30
    return render(request, "core/analytics_dashboard.html", analytics_snapshot(days))


def _sanitize_csv_cell(value):
    """Sanitize CSV cell against spreadsheet formula injection (CWE-1236)."""
    if value is None:
        return ""
    str_val = str(value)
    if str_val and str_val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{str_val}"
    return str_val


@staff_or_admin_required
def complaint_report_csv(request):
    """Export the filtered maintenance register for department review or archival."""
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
        rating_val = complaint.feedback.rating if hasattr(complaint, "feedback") else ""
        writer.writerow([
            _sanitize_csv_cell(complaint.reference),
            _sanitize_csv_cell(complaint.title),
            _sanitize_csv_cell(complaint.category.name if complaint.category else ""),
            _sanitize_csv_cell(complaint.category.department.name if (complaint.category and complaint.category.department) else ""),
            _sanitize_csv_cell(complaint.get_status_display()),
            _sanitize_csv_cell(complaint.get_priority_display()),
            _sanitize_csv_cell(complaint.priority_score),
            _sanitize_csv_cell(location),
            _sanitize_csv_cell(complaint.created_at.isoformat() if complaint.created_at else ""),
            _sanitize_csv_cell(complaint.sla_due_at.isoformat() if complaint.sla_due_at else ""),
            _sanitize_csv_cell(complaint.resolved_at.isoformat() if complaint.resolved_at else ""),
            _sanitize_csv_cell(complaint.escalation_level),
            _sanitize_csv_cell(complaint.supports.count()),
            _sanitize_csv_cell(rating_val),
        ])
    return response


@login_required
def daily_dispatch_sheet(request):
    """
    Printable Daily Maintenance & Mess Dispatch Sheet for Hall Caretakers / Supervisors.
    Generates paper-ready job order tickets with checkboxes and student verification
    signature lines so staff who do not use smartphones or know English can be dispatched.
    """
    profile = getattr(request.user, "profile", None)
    role_upper = str(getattr(profile, "role", "")).upper()
    admin_roles = {"ADMIN", "REGISTRAR", "PROVOST", "HOD"}
    is_hall_caretaker = bool(profile and profile.managed_building)
    if not (request.user.is_superuser or role_upper in admin_roles or is_hall_caretaker):
        messages.error(request, "Access restricted to administrators, provosts, and hall caretakers.")
        return redirect("core:home")

    scoped_qs = get_scoped_complaints_for_user(request.user)

    if request.method == "POST":
        # Handle manual form POST or print logging
        newly_dispatched = list(
            scoped_qs.filter(
                status__in=[Complaint.Status.ASSIGNED, Complaint.Status.OPEN]
            ).select_related("assigned_to", "room__floor__building", "category")
        )
        now = timezone.now()
        actor_name = request.user.get_full_name() or request.user.username
        role_display = profile.get_role_display() if profile else "Administrator"
        for c in newly_dispatched:
            c.status = Complaint.Status.IN_PROGRESS
            if not c.in_progress_at:
                c.in_progress_at = now
            c.save(update_fields=["status", "in_progress_at", "updated_at"])
            tech_str = f" Assigned technician: {c.assigned_to.get_full_name() or c.assigned_to.username}." if c.assigned_to else ""
            ComplaintStatusHistory.objects.create(
                complaint=c,
                status=Complaint.Status.IN_PROGRESS,
                note=f"Daily Dispatch Slip printed by {actor_name} ({role_display}). Physical work order slip issued to ground staff; status updated to In Progress.{tech_str}",
                changed_by=request.user,
            )
        messages.success(request, f"Daily dispatch recorded: {len(newly_dispatched)} complaint(s) transitioned to In Progress.")

    active_complaints = scoped_qs.filter(
        status__in=[
            Complaint.Status.OPEN,
            Complaint.Status.ASSIGNED,
            Complaint.Status.IN_PROGRESS,
            Complaint.Status.REOPENED,
        ]
    ).select_related(
        "category",
        "category__department",
        "room",
        "room__floor",
        "room__floor__building",
        "assigned_to",
        "assigned_to__profile",
    ).order_by("-priority_score", "-created_at")

    hall_name = "Campus Maintenance & Services"
    hall_code = ""
    if role_upper == "PROVOST" and profile and profile.managed_building:
        hall_name = f"{profile.managed_building.name} (Provost / Caretaker Office)"
        hall_code = profile.managed_building.code
    elif role_upper == "HOD" and profile and profile.managed_department:
        hall_name = f"{profile.managed_department.name} Maintenance Depot"
        hall_code = profile.managed_department.code
    elif profile and profile.hall_location:
        hall_name = f"{profile.hall_location} (Caretaker Office)"

    return render(
        request,
        "core/daily_dispatch_sheet.html",
        {
            "complaints": active_complaints,
            "hall_name": hall_name,
            "hall_code": hall_code,
            "today": timezone.now(),
            "total_count": active_complaints.count(),
            "role_upper": role_upper,
        },
    )


@login_required
def log_dispatch_print(request):
    """
    Called via AJAX/fetch when an admin prints the Daily Dispatch Slip.
    - Transitions newly assigned complaints (status=ASSIGNED or status=OPEN) to IN_PROGRESS.
    - Sets in_progress_at to current timestamp.
    - Records an audit log in ComplaintStatusHistory for each dispatched complaint.
    """
    profile = getattr(request.user, "profile", None)
    role_upper = str(getattr(profile, "role", "")).upper()
    admin_roles = {"ADMIN", "REGISTRAR", "PROVOST", "HOD"}
    is_hall_caretaker = bool(profile and profile.managed_building)
    if not (request.user.is_superuser or role_upper in admin_roles or is_hall_caretaker):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    scoped_qs = get_scoped_complaints_for_user(request.user)
    newly_dispatched = list(
        scoped_qs.filter(
            status__in=[Complaint.Status.ASSIGNED, Complaint.Status.OPEN]
        ).select_related("assigned_to", "room__floor__building", "category")
    )

    now = timezone.now()
    actor_name = request.user.get_full_name() or request.user.username
    role_display = profile.get_role_display() if profile else "Administrator"

    updated_refs = []
    for c in newly_dispatched:
        c.status = Complaint.Status.IN_PROGRESS
        if not c.in_progress_at:
            c.in_progress_at = now
        c.save(update_fields=["status", "in_progress_at", "updated_at"])

        tech_str = f" Assigned technician: {c.assigned_to.get_full_name() or c.assigned_to.username}." if c.assigned_to else ""
        ComplaintStatusHistory.objects.create(
            complaint=c,
            status=Complaint.Status.IN_PROGRESS,
            note=f"Daily Dispatch Slip printed by {actor_name} ({role_display}). Physical work order slip issued to ground staff; status updated to In Progress.{tech_str}",
            changed_by=request.user,
        )
        updated_refs.append(c.reference)

    return JsonResponse({
        "status": "ok",
        "updated_count": len(updated_refs),
        "updated_references": updated_refs,
        "message": f"Daily dispatch recorded. {len(updated_refs)} newly assigned complaint(s) updated to In Progress.",
    })


@superuser_or_registrar_required
def campus_heatmap_view(request):
    """
    Interactive Campus Complaint Heatmap & Hotspot Analysis.
    Strictly restricted to Superusers and the Registrar Office.
    """
    categories = ComplaintCategory.objects.filter(is_active=True).select_related("department").order_by("name")
    departments = Department.objects.filter(is_active=True).order_by("name")

    counts = Complaint.objects.aggregate(
        total=Count("id"),
        active=Count(
            "id",
            filter=Q(status__in=[Complaint.Status.OPEN, Complaint.Status.ASSIGNED, Complaint.Status.IN_PROGRESS, Complaint.Status.REOPENED]),
        ),
        urgent=Count(
            "id",
            filter=Q(
                status__in=[Complaint.Status.OPEN, Complaint.Status.ASSIGNED, Complaint.Status.IN_PROGRESS, Complaint.Status.REOPENED],
                priority=Complaint.Priority.URGENT,
            ),
        ),
    )
    total_complaints = counts["total"] or 0
    active_complaints = counts["active"] or 0
    urgent_complaints = counts["urgent"] or 0

    context = {
        "categories": categories,
        "departments": departments,
        "total_complaints": total_complaints,
        "active_complaints": active_complaints,
        "urgent_complaints": urgent_complaints,
        "is_registrar": request.user.is_superuser or (hasattr(request.user, "profile") and request.user.profile.role == UserProfile.Role.REGISTRAR),
    }
    return render(request, "core/campus_heatmap.html", context)


admin_dashboard = dashboard
provost_dashboard = dashboard
hod_dashboard = dashboard
dashboard_view = dashboard
