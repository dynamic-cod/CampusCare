from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import UserProfile


def staff_or_admin_required(view_func):
    """Restrict operational reference data to maintenance staff and administrators."""

    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        role = getattr(getattr(request.user, "profile", None), "role", None)
        if request.user.is_staff or role in {UserProfile.Role.STAFF, UserProfile.Role.ADMIN, UserProfile.Role.REGISTRAR, UserProfile.Role.PROVOST, UserProfile.Role.HOD}:
            return view_func(request, *args, **kwargs)
        messages.error(request, "This area is available to maintenance staff and administrators only.")
        return redirect("core:dashboard")

    return wrapped


def admin_only_required(view_func):
    """Restrict sensitive operations to administrators only."""

    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        role = getattr(getattr(request.user, "profile", None), "role", None)
        admin_roles = {
            UserProfile.Role.ADMIN,
            UserProfile.Role.REGISTRAR,
            UserProfile.Role.PROVOST,
            UserProfile.Role.HOD,
        }
        if request.user.is_superuser or role in admin_roles:
            return view_func(request, *args, **kwargs)
        messages.error(request, "This action is available to administrators only.")
        reference = kwargs.get("reference")
        if reference:
            return redirect("core:complaint_detail", reference=reference)
        return redirect("core:dashboard")

    return wrapped


def superuser_or_registrar_required(view_func):
    """Restrict global campus heatmap to Superusers and the Registrar Office only."""

    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        role = getattr(getattr(request.user, "profile", None), "role", None)
        if request.user.is_superuser or role == UserProfile.Role.REGISTRAR:
            return view_func(request, *args, **kwargs)
        messages.error(request, "The Campus Heatmap is restricted to the Registrar Office and University Administrators only.")
        return redirect("core:dashboard")

    return wrapped

