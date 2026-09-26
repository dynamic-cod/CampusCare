"""Query helpers that turn complaint history into operational analytics."""
from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from .models import Complaint, Department, Room


def analytics_snapshot(days=30):
    """Build a portable, database-agnostic analytics summary for the requested period."""
    cutoff = timezone.now() - timedelta(days=days)
    complaints = list(
        Complaint.objects.filter(created_at__gte=cutoff).select_related("category__department", "room").prefetch_related("feedback")
    )
    completed = [item for item in complaints if item.resolved_at]
    feedback = [item.feedback.rating for item in complaints if hasattr(item, "feedback")]
    department_rows = []
    for department in Department.objects.filter(is_active=True):
        items = [item for item in complaints if item.category.department_id == department.id]
        resolutions = [item for item in items if item.resolved_at]
        ratings = [item.feedback.rating for item in items if hasattr(item, "feedback")]
        average_hours = (
            round(sum((item.resolved_at - item.created_at).total_seconds() / 3600 for item in resolutions) / len(resolutions), 1)
            if resolutions else None
        )
        department_rows.append({
            "name": department.name, "total": len(items), "resolved": sum(item.status in {Complaint.Status.RESOLVED, Complaint.Status.CLOSED} for item in items),
            "overdue": sum(item.is_sla_breached for item in items), "average_hours": average_hours,
            "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        })

    trend_dates = [(timezone.localdate() - timedelta(days=offset)) for offset in range(days - 1, -1, -1)]
    reported = defaultdict(int)
    resolved = defaultdict(int)
    for item in complaints:
        reported[timezone.localtime(item.created_at).date()] += 1
        if item.resolved_at:
            resolved[timezone.localtime(item.resolved_at).date()] += 1
    trends = [{"date": day, "reported": reported[day], "resolved": resolved[day]} for day in trend_dates]
    max_trend_value = max([1] + [max(row["reported"], row["resolved"]) for row in trends])

    recurring = list(
        Complaint.objects.filter(created_at__gte=cutoff, room__isnull=False)
        .values("room__number", "room__name", "room__floor__building__name", "category__name")
        .annotate(total=Count("id"), open_total=Count("id", filter=~Q(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED])))
        .filter(total__gte=2).order_by("-total", "room__floor__building__name")[:10]
    )
    heatmap = list(
        Room.objects.filter(is_active=True)
        .values("number", "name", "floor__building__name", "floor__number")
        .annotate(total=Count("complaints", filter=Q(complaints__created_at__gte=cutoff)), open_total=Count("complaints", filter=Q(complaints__created_at__gte=cutoff) & ~Q(complaints__status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED])))
        .filter(total__gt=0).order_by("-total", "floor__building__name", "number")[:20]
    )
    max_heat = max([1] + [row["total"] for row in heatmap])
    history = Complaint.objects.filter(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]).select_related("category__department", "room").order_by("-resolved_at")[:20]

    return {
        "days": days, "period_complaints": len(complaints),
        "period_resolved": sum(item.status in {Complaint.Status.RESOLVED, Complaint.Status.CLOSED} for item in complaints),
        "currently_overdue": Complaint.objects.exclude(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]).filter(sla_due_at__lt=timezone.now()).count(),
        "average_resolution_hours": round(sum((item.resolved_at - item.created_at).total_seconds() / 3600 for item in completed) / len(completed), 1) if completed else None,
        "average_rating": round(sum(feedback) / len(feedback), 1) if feedback else None,
        "departments": department_rows, "trends": trends, "max_trend_value": max_trend_value,
        "recurring": recurring, "heatmap": heatmap, "max_heat": max_heat, "history": history,
    }
