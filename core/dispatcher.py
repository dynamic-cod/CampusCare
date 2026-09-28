import time
import uuid
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from .models import Complaint, ComplaintStatusHistory, UserProfile
from .staff_matcher import suggest_staff

# Department codes that route exclusively to the hall's Dining Incharge
MESS_DEPT_CODES = frozenset({"MESS", "DINING"})

_ACTIVE_LOAD_CACHE = None
_ACTIVE_LOAD_TIMESTAMP = 0.0


def get_active_staff_loads(force_refresh: bool = False) -> dict:
    """Return a dictionary of {staff_user_id: active_complaints_count} cached with 2-second TTL."""
    global _ACTIVE_LOAD_CACHE, _ACTIVE_LOAD_TIMESTAMP
    now = time.time()
    if force_refresh or _ACTIVE_LOAD_CACHE is None or (now - _ACTIVE_LOAD_TIMESTAMP) > 2.0:
        _ACTIVE_LOAD_CACHE = dict(
            Complaint.objects.exclude(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED])
            .filter(assigned_to__isnull=False)
            .values("assigned_to_id")
            .annotate(cnt=Count("id"))
            .values_list("assigned_to_id", "cnt")
        )
        _ACTIVE_LOAD_TIMESTAMP = now
    return _ACTIVE_LOAD_CACHE


def record_staff_assignment(user_id: int):
    """Increment local cached active count for immediate accurate least-load sorting."""
    global _ACTIVE_LOAD_CACHE
    if _ACTIVE_LOAD_CACHE is not None:
        _ACTIVE_LOAD_CACHE[user_id] = _ACTIVE_LOAD_CACHE.get(user_id, 0) + 1


def record_staff_release(user_id: int):
    """Decrement local cached active count when a complaint is resolved or closed."""
    global _ACTIVE_LOAD_CACHE
    if _ACTIVE_LOAD_CACHE is not None and user_id in _ACTIVE_LOAD_CACHE:
        _ACTIVE_LOAD_CACHE[user_id] = max(0, _ACTIVE_LOAD_CACHE[user_id] - 1)


def pick_least_loaded_staff(users):
    """Pick the least-loaded technician from an iterable or queryset of users."""
    user_list = list(users)
    if not user_list:
        return None
    if len(user_list) == 1:
        return user_list[0]
    loads = get_active_staff_loads()
    return min(user_list, key=lambda u: (loads.get(u.id, 0), u.id))


def select_best_technician(complaint: Complaint):
    """
    Match complaint category.department and room.floor.building against the 156-person
    staff roster, selecting the least-loaded technician, with fallback to campus reserve.

    For MESS / DINING complaints the hall's dedicated Dining Incharge is always preferred
    before the generic AI roster matcher is consulted.
    """
    staff_base = User.objects.filter(is_active=True, profile__role=UserProfile.Role.STAFF)

    building = complaint.room.floor.building if (complaint.room_id and complaint.room) else None
    dept = complaint.category.department if (complaint.category_id and complaint.category) else None
    category_name = complaint.category.name if (complaint.category_id and complaint.category) else ""
    b_name = building.name if building else ""
    loc_text = f"{b_name} {complaint.location_description or ''}".strip()

    # Build target buildings list including constituent hostel and its parent hall
    target_buildings = []
    if building:
        target_buildings.append(building)
        if building.parent and building.parent not in target_buildings:
            target_buildings.append(building.parent)
    else:
        try:
            from .ai_triage import extract_building_and_department
            extracted_bldg, _ = extract_building_and_department(
                location_text=loc_text, title=complaint.title or "", description=complaint.description or ""
            )
            if extracted_bldg:
                target_buildings.append(extracted_bldg)
                if extracted_bldg.parent and extracted_bldg.parent not in target_buildings:
                    target_buildings.append(extracted_bldg.parent)
        except Exception:
            pass

    # 0. MESS / DINING fast-path — route directly to the hall's Dining Incharge
    if dept and dept.code in MESS_DEPT_CODES:
        if target_buildings:
            dining_user = pick_least_loaded_staff(
                staff_base.filter(
                    profile__managed_building__in=target_buildings,
                    username__startswith="dining_",
                )
            )
            if dining_user:
                return dining_user
        # Hall not resolved — pick the least-loaded Dining Incharge across campus
        dining_any = pick_least_loaded_staff(staff_base.filter(username__startswith="dining_"))
        if dining_any:
            return dining_any

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
        matched_user = pick_least_loaded_staff(staff_base.filter(username__in=usernames))
        if matched_user:
            return matched_user

    # 2. Match building + department directly in DB (checking building, parent hall, and short_name)
    if target_buildings and dept:
        b_names_q = Q()
        for tb in target_buildings:
            b_names_q |= Q(profile__hall_location__icontains=tb.name)
            if tb.short_name:
                b_names_q |= Q(profile__hall_location__icontains=tb.short_name)
        b_dept_staff = pick_least_loaded_staff(
            staff_base.filter(
                (b_names_q | Q(profile__managed_building__in=target_buildings)),
                profile__department=dept,
            )
        )
        if b_dept_staff:
            return b_dept_staff

    # 3. Match building staff
    if target_buildings:
        b_names_q = Q()
        for tb in target_buildings:
            b_names_q |= Q(profile__hall_location__icontains=tb.name)
            if tb.short_name:
                b_names_q |= Q(profile__hall_location__icontains=tb.short_name)
        b_staff = pick_least_loaded_staff(
            staff_base.filter(b_names_q | Q(profile__managed_building__in=target_buildings))
        )
        if b_staff:
            return b_staff

    # 4. Match department staff
    if dept:
        d_staff = pick_least_loaded_staff(staff_base.filter(profile__department=dept))
        if d_staff:
            return d_staff

    # 5. Fallback — least-loaded active technician across the entire campus
    return pick_least_loaded_staff(staff_base)


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
            record_staff_assignment(tech.id)
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
