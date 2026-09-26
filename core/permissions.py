# Row-level multi-tenant ORM scoping utilities for CampusCare sub-admins.
from django.db import models
from .models import Complaint, UserProfile

def get_scoped_complaints_for_user(user):
    """
    Strictly scope Complaint queryset according to the user administrative jurisdiction:
    - Superuser / REGISTRAR / ADMIN -> All complaints
    - PROVOST -> Only complaints in user.profile.managed_building
    - HOD -> Only complaints in user.profile.managed_department (via category.department or building)
    - Else -> Complaint.objects.none()
    """
    if not user or not getattr(user, "is_authenticated", False):
        return Complaint.objects.none()

    profile = getattr(user, "profile", None)
    role_raw = getattr(profile, "role", "") or ""
    role_upper = str(role_raw).upper()

    base_qs = Complaint.objects.select_related(
        "room__floor__building", "category", "category__department", "assigned_to", "reporter"
    )

    if getattr(user, "is_superuser", False) or role_upper in ("REGISTRAR", "ADMIN"):
        return base_qs.all()

    if role_upper == "PROVOST":
        if profile and profile.managed_building_id:
            return base_qs.filter(
                models.Q(room__floor__building=profile.managed_building)
                | models.Q(room__floor__building__parent=profile.managed_building)
            ).distinct()
        return Complaint.objects.none()

    if role_upper == "HOD":
        if profile and profile.managed_department_id:
            dept = profile.managed_department
            return base_qs.filter(
                models.Q(category__department=dept)
                | models.Q(room__floor__building__code__iexact=dept.code)
                | models.Q(room__floor__building__department=dept)
            ).distinct()
        return Complaint.objects.none()

    return Complaint.objects.none()
