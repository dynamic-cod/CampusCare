"""
Public-facing informational and landing views.
"""

from django.db.models import Count, Prefetch, Q
from django.shortcuts import render

from core.decorators import staff_or_admin_required
from core.models import Building, Campus, Complaint, ComplaintSupport, Department, Floor, Room


def home(request):
    """Public homepage — shows the community complaint dashboard to everyone."""
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
        .select_related("category", "room__floor__building__campus")
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

    latest_complaint = complaints_qs.order_by("-id").first()
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
        "recent_complaints": recent_complaints,
        "supported_ids": supported_ids,
        "selected_status": status_filter,
        "latest_id": latest_id,
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
