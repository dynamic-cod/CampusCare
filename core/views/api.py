"""
JSON and AJAX endpoints: category suggestions, live polling, urgency analysis,
room lookups, and geospatial heatmap data.
"""

from datetime import timedelta
import hashlib
import json
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from django.views.decorators.csrf import csrf_exempt

from core.ai_triage import extract_building_and_department
from core.decorators import superuser_or_registrar_required
from core.models import Building, Complaint, ComplaintCategory, Department, Floor, Room, UserProfile
from core.smart import is_mess_complaint, score_priority, suggest_categories, suggest_category
from core.staff_matcher import suggest_staff


@csrf_exempt
def suggest_category_api(request):
    """API endpoint for real-time category suggestions based on complaint text and optional location."""
    location = ""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            text = data.get("text", "").strip()
            location = data.get("location", "").strip()
        except (json.JSONDecodeError, ValueError):
            text = request.POST.get("text", "").strip()
            location = request.POST.get("location", "").strip()
    else:
        text = request.GET.get("text", "").strip()
        location = request.GET.get("location", "").strip()
    
    if not text or len(text) < 3:
        return JsonResponse({"suggestions": []})
    
    active_categories = ComplaintCategory.objects.filter(is_active=True).select_related("department")
    suggestions_data = suggest_categories(text, active_categories, location=location, limit=3)
    
    if suggestions_data:
        return JsonResponse({
            "suggestions": [
                {
                    "id": cat.id,
                    "name": cat.name,
                    "description": cat.description,
                    "confidence": conf,
                    "department": cat.department.name if cat.department else "",
                }
                for cat, conf in suggestions_data
            ]
        })
    
    return JsonResponse({"suggestions": []})


def complaint_status_poll_api(request, tracking_token):
    """Dedicated lightweight JSON polling endpoint for live status updates on tracking pages."""
    complaint = get_object_or_404(
        Complaint.objects.select_related("category"),
        tracking_token=tracking_token,
    )

    history_items = [
        {
            "status": h.status,
            "status_display": h.get_status_display(),
            "note": h.note,
            "changed_by": h.changed_by.get_full_name() or h.changed_by.username if h.changed_by else "System / Student",
            "created_at": h.created_at.strftime("%d %b %Y, %H:%M"),
            "iso_time": h.created_at.isoformat(),
        }
        for h in complaint.status_history.all().order_by("-created_at")
    ]
    return JsonResponse({
        "reference": complaint.reference,
        "status": complaint.status,
        "status_display": complaint.get_status_display(),
        "resolution_verification": complaint.resolution_verification,
        "can_verify": complaint.status == Complaint.Status.RESOLVED,
        "closed_at": complaint.closed_at.strftime("%d %b %Y, %H:%M") if complaint.closed_at else None,
        "closed_at_iso": complaint.closed_at.isoformat() if complaint.closed_at else None,
        "resolved_at": complaint.resolved_at.strftime("%d %b %Y, %H:%M") if complaint.resolved_at else None,
        "updated_at": complaint.updated_at.isoformat() if complaint.updated_at else None,
        "history_count": len(history_items),
        "history": history_items,
        "resolution_note": complaint.resolution_note or "",
        "feedback_rating": complaint.feedback.rating if hasattr(complaint, "feedback") and complaint.feedback else (complaint.feedback_rating or None),
        "feedback_comment": complaint.feedback.comment if hasattr(complaint, "feedback") and complaint.feedback else (complaint.feedback_comments or ""),
    })


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

    # Detect mess/dining category — look up Dining Incharge from DB for the given hall
    mess_dept = Department.objects.filter(code="MESS").first()
    category_is_mess = (
        mess_dept
        and any(mess_kw in category_name.lower() for mess_kw in ("dining", "mess", "food", "ration", "water & utilities"))
    ) or is_mess_complaint(title + " " + description)

    if category_is_mess and mess_dept:
        # Try to resolve the hall from the location string
        building, _ = extract_building_and_department(
            location_text=location, title=title, description=description
        )
        dining_profile = None
        if building:
            target_buildings = [building]
            if building.parent:
                target_buildings.append(building.parent)
            dining_profile = (
                UserProfile.objects.select_related("user", "managed_building")
                .filter(
                    role=UserProfile.Role.STAFF,
                    managed_building__in=target_buildings,
                    managed_department=mess_dept,
                )
                .first()
            )
        if not dining_profile:
            # Fallback: any Dining Incharge (campus-wide)
            dining_profile = (
                UserProfile.objects.select_related("user", "managed_building")
                .filter(role=UserProfile.Role.STAFF, managed_department=mess_dept)
                .first()
            )
        if dining_profile:
            hall_name = dining_profile.managed_building.name if dining_profile.managed_building else "Residential Hall"
            suggested_staff = {
                "name": dining_profile.user.get_full_name() or dining_profile.user.username,
                "role": "Dining Incharge",
                "dept": "Dining & Mess Services",
                "location": hall_name,
                "contact": dining_profile.phone or "+91-571-2700920",
                "reason": f"Hall Dining Incharge for {hall_name} — auto-routed for food/mess complaint",
            }
    elif staff_matches:
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
        if not matched_room and q.isdigit():
            # Support unpadded input matching 3-digit zero-padded room (e.g., '1' -> '001')
            matched_room = rooms_qs.filter(number__iexact=f"{int(q):03d}").first()
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


@superuser_or_registrar_required
def heatmap_data_api(request):
    """
    GeoJSON / JSON Endpoint providing weighted coordinate points and building metrics
    for the real-time Leaflet heatmap.
    """
    status_param = request.GET.get("status", "active").strip().lower()
    category_id = request.GET.get("category", "").strip()
    priority_param = request.GET.get("priority", "all").strip().lower()
    timeframe = request.GET.get("timeframe", "all").strip().lower()

    qs = Complaint.objects.select_related(
        "room__floor__building__parent",
        "category__department",
    ).all()

    if status_param == "active":
        qs = qs.filter(status__in=[
            Complaint.Status.OPEN, Complaint.Status.ASSIGNED,
            Complaint.Status.IN_PROGRESS, Complaint.Status.REOPENED,
        ])
    elif status_param == "resolved":
        qs = qs.filter(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED])
    elif status_param in Complaint.Status.values:
        qs = qs.filter(status=status_param)

    if category_id:
        qs = qs.filter(category_id=category_id)

    if priority_param in Complaint.Priority.values:
        qs = qs.filter(priority=priority_param)

    if timeframe == "7days":
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=7))
    elif timeframe == "30days":
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=30))
    elif timeframe == "90days":
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=90))

    priority_weights = {
        Complaint.Priority.URGENT: 3.5,
        Complaint.Priority.HIGH: 2.2,
        Complaint.Priority.NORMAL: 1.2,
        Complaint.Priority.LOW: 0.8,
    }

    buildings_with_coords = list(Building.objects.filter(latitude__isnull=False, longitude__isnull=False))
    buildings_by_code = {b.code.lower(): b for b in buildings_with_coords}
    buildings_by_name = {b.name.lower(): b for b in buildings_with_coords}

    points = []
    building_stats = {}

    for complaint in qs:
        building = None
        if complaint.room and complaint.room.floor and complaint.room.floor.building:
            building = complaint.room.floor.building
            if building.parent and (not building.latitude or not building.longitude):
                building = building.parent

        if not building or not building.latitude or not building.longitude:
            desc = (complaint.location_description or "").lower()
            for name, b in buildings_by_name.items():
                if name in desc:
                    building = b
                    break
            if not building:
                for code, b in buildings_by_code.items():
                    if code in desc:
                        building = b
                        break

        if building and building.latitude and building.longitude:
            lat = float(building.latitude)
            lng = float(building.longitude)
            weight = priority_weights.get(complaint.priority, 1.0)

            # Jitter so multiple complaints at the same building spread out naturally on the canvas
            jitter_seed = int(hashlib.md5(f"{complaint.id}".encode()).hexdigest()[:6], 16)
            jitter_lat = ((jitter_seed % 100) - 50) * 0.00004
            jitter_lng = (((jitter_seed // 100) % 100) - 50) * 0.00004

            points.append([lat + jitter_lat, lng + jitter_lng, weight])

            b_key = building.id
            if b_key not in building_stats:
                building_stats[b_key] = {
                    "id": building.id,
                    "name": building.name,
                    "code": building.code,
                    "lat": lat,
                    "lng": lng,
                    "total": 0,
                    "active": 0,
                    "urgent": 0,
                    "categories": {},
                    "recent": [],
                }

            b_stat = building_stats[b_key]
            b_stat["total"] += 1
            if complaint.status in [Complaint.Status.OPEN, Complaint.Status.ASSIGNED, Complaint.Status.IN_PROGRESS, Complaint.Status.REOPENED]:
                b_stat["active"] += 1
            if complaint.priority == Complaint.Priority.URGENT:
                b_stat["urgent"] += 1

            cat_name = complaint.category.name if complaint.category else "General"
            b_stat["categories"][cat_name] = b_stat["categories"].get(cat_name, 0) + 1

            if len(b_stat["recent"]) < 3:
                b_stat["recent"].append({
                    "ref": complaint.reference,
                    "title": complaint.title,
                    "priority": complaint.priority,
                    "status": complaint.status,
                })

    return JsonResponse({
        "points": points,
        "buildings": list(building_stats.values()),
        "total_complaints": qs.count(),
        "hotspot_count": len(building_stats),
    })


def latest_public_complaints_api(request):
    """
    Lightweight JSON endpoint providing real-time board updates:
    stats, latest complaint ID, and newly lodged public complaints for auto-refresh.
    """
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

    since_id = request.GET.get("since_id")
    status_filter = request.GET.get("status", "").strip().lower()

    complaints_qs = Complaint.objects.filter(is_public=True)
    if status_filter == "active":
        complaints_qs = complaints_qs.filter(status__in=[
            Complaint.Status.OPEN, Complaint.Status.ASSIGNED,
            Complaint.Status.IN_PROGRESS, Complaint.Status.REOPENED,
        ])
    elif status_filter in Complaint.Status.values:
        complaints_qs = complaints_qs.filter(status=status_filter)

    latest_complaint = complaints_qs.order_by("-id").first()
    latest_id = latest_complaint.id if latest_complaint else 0

    if since_id and str(since_id).isdigit():
        new_complaints_qs = complaints_qs.filter(id__gt=int(since_id)).select_related(
            "category", "room__floor__building"
        ).annotate(support_count=Count("supports")).order_by("-id")[:20]
    else:
        new_complaints_qs = complaints_qs.select_related(
            "category", "room__floor__building"
        ).annotate(support_count=Count("supports")).order_by("-created_at")[:50]

    complaints_data = []
    for c in new_complaints_qs:
        loc_str = str(c.room) if c.room else (c.location_description or "")
        complaints_data.append({
            "id": c.id,
            "reference": c.reference,
            "title": c.title,
            "priority": c.priority,
            "priority_display": c.get_priority_display(),
            "status": c.status,
            "status_display": "Pending Student Verification" if c.status == Complaint.Status.RESOLVED else c.get_status_display(),
            "category": c.category.name if c.category else "General",
            "location": loc_str,
            "support_count": c.support_count,
            "created_at_display": c.created_at.strftime("%d %b, %H:%M"),
            "sla_due_at": c.sla_due_at.strftime("%d %b, %H:%M") if c.sla_due_at else None,
            "closed_at": c.closed_at.strftime("%d %b") if c.closed_at else None,
            "detail_url": f"/complaints/{c.reference}/",
        })

    return JsonResponse({
        "success": True,
        "latest_id": latest_id,
        "stats": {
            "total": total,
            "count_active": count_active,
            "count_open": count_open,
            "count_assigned": count_assigned,
            "count_in_progress": count_in_progress,
            "count_resolved": count_resolved,
            "count_closed": count_closed,
            "count_reopened": count_reopened,
        },
        "has_new": len(complaints_data) > 0 and since_id is not None,
        "new_count": len(complaints_data) if (since_id and str(since_id).isdigit()) else 0,
        "complaints": complaints_data,
    })

