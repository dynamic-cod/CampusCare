"""
Technician task views: magic UUID zero-login execution portal, dwell-time validation,
and completion photo verification.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.models import Complaint, ComplaintStatusHistory, UserProfile
from core.utils import compress_uploaded_image


def technician_task_view(request, task_token):
    """Technician task execution portal accessed via UUID staff_task_token."""
    complaint = get_object_or_404(Complaint, staff_task_token=task_token)
    error_message = None

    # Access Control: Students must NEVER have access to the technician portal
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        role = getattr(profile, "role", None)
        if role == UserProfile.Role.STUDENT or (complaint.reporter_id and request.user.id == complaint.reporter_id and not request.user.is_staff):
            error_message = (
                "Access Denied: Students are not permitted to access the technician task portal. "
                "This portal is strictly reserved for assigned maintenance technicians and authorized administrators."
            )
            return render(
                request,
                "core/technician_task.html",
                {"complaint": complaint, "error_message": error_message, "access_denied": True},
                status=403,
            )

    if request.method == "POST":
        action = request.POST.get("action", "").strip().lower()

        if complaint.status in [Complaint.Status.RESOLVED, Complaint.Status.CLOSED]:
            error_message = (
                f"This complaint has already been {complaint.get_status_display().lower()}. "
                "The technician task link is now read-only and no further actions can be taken."
            )
            return render(
                request,
                "core/technician_task.html",
                {"complaint": complaint, "error_message": error_message, "is_read_only": True},
                status=400,
            )

        if action == "close" or request.POST.get("status", "").strip().lower() == Complaint.Status.CLOSED:
            error_message = "Technicians are not permitted to close complaints. Only students can confirm closure."
            return render(
                request,
                "core/technician_task.html",
                {"complaint": complaint, "error_message": error_message},
                status=403,
            )

        if action == "start":
            now = timezone.now()
            complaint.status = Complaint.Status.IN_PROGRESS
            if not complaint.in_progress_at:
                complaint.in_progress_at = now
            complaint.save(update_fields=["status", "in_progress_at", "updated_at"])
            ComplaintStatusHistory.objects.create(
                complaint=complaint,
                status=Complaint.Status.IN_PROGRESS,
                note="Technician started working on task via token link.",
            )
            messages.success(request, "Task marked as In Progress. Dwell timer active.")
            return redirect("core:technician_task_view", task_token=complaint.staff_task_token)

        elif action == "resolve":
            now = timezone.now()
            if not complaint.in_progress_at:
                error_message = "Task must be started (In Progress) before it can be resolved."
                return render(
                    request,
                    "core/technician_task.html",
                    {"complaint": complaint, "error_message": error_message},
                    status=400,
                )

            elapsed_seconds = (now - complaint.in_progress_at).total_seconds()
            if elapsed_seconds < 300:
                remaining = int(300 - elapsed_seconds)
                error_message = f"Minimum 5-minute dwell-time required before resolving ({remaining}s remaining)."
                return render(
                    request,
                    "core/technician_task.html",
                    {"complaint": complaint, "error_message": error_message},
                    status=400,
                )

            proof_file = (
                request.FILES.get("resolution_proof")
                or request.FILES.get("proof")
                or request.FILES.get("evidence")
                or request.FILES.get("image")
            )
            if not proof_file:
                error_message = "Camera proof image is mandatory to mark a complaint as resolved."
                return render(
                    request,
                    "core/technician_task.html",
                    {"complaint": complaint, "error_message": error_message},
                    status=400,
                )

            compressed_proof = compress_uploaded_image(proof_file)
            if not compressed_proof:
                error_message = "The uploaded file is not a valid image. Please provide a clear camera photo (JPG, PNG, or WEBP)."
                return render(
                    request,
                    "core/technician_task.html",
                    {"complaint": complaint, "error_message": error_message},
                    status=400,
                )
            complaint.resolution_proof = compressed_proof
            complaint.status = Complaint.Status.RESOLVED
            complaint.resolved_at = now
            complaint.resolution_verification = Complaint.ResolutionVerification.PENDING
            note_text = request.POST.get("resolution_note") or request.POST.get("note") or "Resolved by technician with camera proof."
            complaint.resolution_note = note_text
            complaint.save(
                update_fields=[
                    "resolution_proof",
                    "status",
                    "resolved_at",
                    "resolution_verification",
                    "resolution_note",
                    "updated_at",
                ]
            )
            ComplaintStatusHistory.objects.create(
                complaint=complaint,
                status=Complaint.Status.RESOLVED,
                note=note_text,
            )
            messages.success(request, "Task marked as Resolved and awaiting student verification.")
            return redirect("core:technician_task_view", task_token=complaint.staff_task_token)

    is_read_only = complaint.status in [Complaint.Status.RESOLVED, Complaint.Status.CLOSED]
    return render(
        request,
        "core/technician_task.html",
        {"complaint": complaint, "error_message": error_message, "is_read_only": is_read_only},
    )
