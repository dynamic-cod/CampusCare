"""
Public-facing informational and landing views.
"""

from django.db.models import Count, Prefetch, Q
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.decorators import staff_or_admin_required
from core.models import Building, Campus, Complaint, ComplaintSupport, Department, Floor, Room


@ensure_csrf_cookie
def home(request):
    """Public homepage — minimal hero + collapsible active complaints panel."""
    stats = Complaint.objects.aggregate(
        total=Count("id"),
        count_open=Count("id", filter=Q(status=Complaint.Status.OPEN)),
        count_assigned=Count("id", filter=Q(status=Complaint.Status.ASSIGNED)),
        count_in_progress=Count("id", filter=Q(status=Complaint.Status.IN_PROGRESS)),
        count_resolved=Count("id", filter=Q(status=Complaint.Status.RESOLVED)),
        count_closed=Count("id", filter=Q(status=Complaint.Status.CLOSED)),
        count_reopened=Count("id", filter=Q(status=Complaint.Status.REOPENED)),
    )
    total = stats["total"] or 0
    count_open = stats["count_open"] or 0
    count_assigned = stats["count_assigned"] or 0
    count_in_progress = stats["count_in_progress"] or 0
    count_resolved = stats["count_resolved"] or 0
    count_closed = stats["count_closed"] or 0
    count_reopened = stats["count_reopened"] or 0
    count_active = count_open + count_assigned + count_in_progress + count_reopened

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key or ""

    # Active complaints only — sorted by urgency then support count
    ACTIVE_STATUSES = [
        Complaint.Status.OPEN,
        Complaint.Status.ASSIGNED,
        Complaint.Status.IN_PROGRESS,
        Complaint.Status.REOPENED,
    ]
    PRIORITY_ORDER = {"urgent": 0, "high": 1, "normal": 2, "low": 3}

    active_complaints_qs = (
        Complaint.objects.filter(is_public=True, status__in=ACTIVE_STATUSES)
        .select_related("category__department", "room__floor__building")
        .annotate(support_count=Count("supports"))
        .order_by("-created_at")[:80]
    )
    # Sort: urgent first, then by support count desc
    active_complaints = sorted(
        active_complaints_qs,
        key=lambda c: (PRIORITY_ORDER.get(c.priority, 9), -c.support_count),
    )

    # Department/category breakdown for the mini summary bar
    dept_breakdown = (
        Complaint.objects.filter(is_public=True, status__in=ACTIVE_STATUSES)
        .values("category__department__code", "category__department__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")[:8]
    )

    if request.user.is_authenticated:
        supported_ids = set(
            ComplaintSupport.objects.filter(user=request.user, complaint__in=active_complaints)
            .values_list("complaint_id", flat=True)
        )
    elif session_key:
        supported_ids = set(
            ComplaintSupport.objects.filter(session_key=session_key, complaint__in=active_complaints)
            .values_list("complaint_id", flat=True)
        )
    else:
        supported_ids = set()

    # Collect unique categories and buildings for the quick filter dropdowns
    filter_categories = sorted(set(
        c.category.name for c in active_complaints if c.category_id
    ))
    filter_buildings = sorted(set(
        c.room.floor.building.name
        for c in active_complaints
        if c.room_id and c.room and c.room.floor and c.room.floor.building
    ))

    latest_complaint = Complaint.objects.filter(is_public=True).order_by("-id").first()
    latest_id = latest_complaint.id if latest_complaint else 0

    context = {
        "total": total,
        "count_active": count_active,
        "count_open": count_open,
        "count_assigned": count_assigned,
        "count_in_progress": count_in_progress,
        "count_resolved": count_resolved,
        "count_closed": count_closed,
        "count_reopened": count_reopened,
        "active_complaints": active_complaints,
        "supported_ids": supported_ids,
        "dept_breakdown": dept_breakdown,
        "filter_categories": filter_categories,
        "filter_buildings": filter_buildings,
        "latest_id": latest_id,
        # keep for backward compat with live-poll JS
        "recent_complaints": active_complaints,
        "selected_status": "",
    }
    return render(request, "core/home.html", context)


from django.core.cache import cache


@staff_or_admin_required
def campus_directory(request):
    """Read-only operational directory; editing stays protected in Django admin."""
    cached_data = cache.get("campus_directory_data")
    if not cached_data:
        active_rooms = Room.objects.filter(is_active=True)
        active_floors = Floor.objects.prefetch_related(Prefetch("rooms", queryset=active_rooms))
        active_buildings = Building.objects.filter(is_active=True).prefetch_related(
            Prefetch("floors", queryset=active_floors)
        )
        campuses = list(Campus.objects.filter(is_active=True).prefetch_related(
            Prefetch("buildings", queryset=active_buildings)
        ))
        departments = list(Department.objects.filter(is_active=True).prefetch_related("complaint_categories"))
        cached_data = {"campuses": campuses, "departments": departments}
        cache.set("campus_directory_data", cached_data, 300)

    return render(
        request,
        "core/campus_directory.html",
        cached_data,
    )
