# Auto-dispatch engine for CampusCare complaints (156-person staff roster + campus reserve fallback).
import uuid
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from .models import Complaint, ComplaintStatusHistory, UserProfile
from .staff_matcher import suggest_staff

def select_best_technician(complaint: Complaint):
    """
    Match complaint category.department and room.floor.building against the 156-person
    staff roster, selecting the least-loaded technician, with fallback to campus reserve.
    """
    active_filter = ~Q(assigned_complaints__status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED])
    staff_qs = (
        User.objects.filter(is_active=True, profile__role=UserProfile.Role.STAFF)
        .annotate(active_load=Count("assigned_complaints", filter=active_filter))
    )

    building = complaint.room.floor.building if (complaint.room_id and complaint.room) else None
    dept = complaint.category.department if (complaint.category_id and complaint.category) else None
    category_name = complaint.category.name if (complaint.category_id and complaint.category) else ""
    b_name = building.name if building else ""
    loc_text = f"{b_name} {complaint.location_description or str()}".strip()

    # 1. Try AI/Roster matcher (staff_matcher.suggest_staff) among candidates with low load
    matches = suggest_staff(
        category_name=category_name,
        location_description=loc_text,
        title=complaint.title or "",
        description=complaint.description or "",
        n=5,
    )
    if matches:
        usernames = [m["username"] for m in matches if m.get("username")]
        matched_users = list(staff_qs.filter(username__in=usernames).order_by("active_load", "id"))
        if matched_users:
            return matched_users[0]

    # 2. Match building + department directly in DB
    if building and dept:
        b_dept_staff = staff_qs.filter(
            Q(profile__hall_location__icontains=building.name) | Q(profile__managed_building=building),
            profile__department=dept,
        ).order_by("active_load", "id").first()
        if b_dept_staff:
            return b_dept_staff

    # 3. Match building staff
    if building:
        b_staff = staff_qs.filter(
            Q(profile__hall_location__icontains=building.name) | Q(profile__managed_building=building)
        ).order_by("active_load", "id").first()
        if b_staff:
            return b_staff

    # 4. Match department staff
    if dept:
        d_staff = staff_qs.filter(profile__department=dept).order_by("active_load", "id").first()
        if d_staff:
            return d_staff

    # 5. Fallback to Campus Reserve (least-loaded active technician across the university)
    return staff_qs.order_by("active_load", "id").first()

def auto_dispatch_complaint(complaint: Complaint, save: bool = True) -> Complaint:
    """
    Ensure complaint has a staff_task_token, an assigned technician (assigned_to),
    and transitions from open -> assigned.
    """
    if not complaint.staff_task_token:
        complaint.staff_task_token = uuid.uuid4()
    if not complaint.assigned_to_id:
        tech = select_best_technician(complaint)
        if tech:
            complaint.assigned_to = tech
            complaint.assigned_at = timezone.now()
            if complaint.status == Complaint.Status.OPEN:
                complaint.status = Complaint.Status.ASSIGNED
            if save and complaint.pk:
                complaint.save(update_fields=["assigned_to", "assigned_at", "status", "staff_task_token", "updated_at"])
    return complaint

def backfill_unassigned_complaints() -> int:
    """
    Find all complaints with assigned_to__isnull=True, assign them to the least-loaded
    matching technician, generate staff_task_token if missing, and transition status to assigned.
    """
    unassigned = list(Complaint.objects.select_related("room__floor__building", "category__department").filter(assigned_to__isnull=True))
    updated_count = 0
    for c in unassigned:
        auto_dispatch_complaint(c, save=True)
        if c.assigned_to_id:
            ComplaintStatusHistory.objects.create(
                complaint=c,
                status=c.status,
                note=f"Auto-dispatched to {c.assigned_to.get_full_name() or c.assigned_to.username}.",
            )
            updated_count += 1
    return updated_count
