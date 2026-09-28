import time
from django.conf import settings
from django.core.cache import cache

from core.decorators import admin_only_required, staff_or_admin_required, superuser_or_registrar_required
from core.permissions import get_scoped_complaints_for_user
from core.utils import compress_uploaded_image, get_scoped_complaints


def _can_student_modify_complaint(request, complaint):
    """Check if the requesting student or session has permission to modify the complaint."""
    if request.user.is_authenticated and complaint.reporter_id == request.user.id:
        return True
    token = request.POST.get("tracking_token") or request.GET.get("tracking_token")
    if token and complaint.tracking_token == token:
        return True
    return False


def is_rate_limited(request, key_prefix="rate_limit", max_requests=60, window_seconds=60):
    """
    Check if a client IP or session is exceeding max_requests within window_seconds.
    Uses Django's configured cache (LocMemCache in memory).
    Returns True if rate limited (exceeded), False otherwise.
    """
    if getattr(settings, "RATE_LIMITING_DISABLED", False) or getattr(settings, "TESTING", False):
        return False

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.META.get("REMOTE_ADDR", "127.0.0.1")

    client_id = f"user:{request.user.id}" if getattr(request, "user", None) and request.user.is_authenticated else f"ip:{client_ip}"
    cache_key = f"{key_prefix}:{client_id}"
    current_time = time.time()

    request_history = cache.get(cache_key, [])
    request_history = [t for t in request_history if current_time - t < window_seconds]

    if len(request_history) >= max_requests:
        return True

    request_history.append(current_time)
    cache.set(cache_key, request_history, window_seconds)
    return False

