"""
Complaint lifecycle management views: creation, listing, detail, tracking, status updates,
resolution, student verification, reopening, and feedback.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme


def _safe_redirect_target(request, next_url, fallback="core:home"):
    """Validate next_url to prevent open redirect (CWE-601) to external malicious hosts."""
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return fallback

from core.accountability import set_sla_due_date
from core.ai_triage import bind_complaint_spatial_origin
from core.decorators import admin_only_required
from core.dispatcher import auto_dispatch_complaint, record_staff_assignment
from core.forms import (
    AdminResolutionForm, ComplaintAssignmentForm, ComplaintFeedbackForm, ComplaintReopenForm,
    ComplaintStatusForm, ComplaintSubmissionForm, ResolutionVerificationForm,
)
from core.models import (
    Building, Complaint, ComplaintFeedback, ComplaintStatusHistory,
    ComplaintSupport, Room, UserProfile,
)
from core.permissions import get_scoped_complaints_for_user
from core.smart import find_potential_duplicate
from core.staff_matcher import suggest_staff
from core.utils import compress_uploaded_image, get_scoped_complaints
from .helpers import _can_student_modify_complaint, is_rate_limited


def complaint_create(request):
    if request.method == "POST":
        if is_rate_limited(request, key_prefix="complaint_submit", max_requests=60, window_seconds=60):
            messages.error(request, "Too many complaint submissions. Please wait a minute before lodging another issue.")
            form = ComplaintSubmissionForm(request.POST, request.FILES)
            return render(
                request,
                "core/complaint_form.html",
                {
                    "form": form,
                    "active_halls": Building.objects.filter(is_active=True, parent__isnull=True, building_type="hall").prefetch_related("hostels").order_by("name"),
                    "active_hostels": Building.objects.filter(is_active=True, parent__isnull=False).select_related("parent").order_by("parent__name", "short_name"),
                },
                status=429,
            )
        form = ComplaintSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.is_public = form.cleaned_data.get("is_public", True)
            complaint.category_detected_automatically = form.category_detected_automatically
            complaint.category_detection_confidence = form.category_detection_confidence
            complaint.priority_score = form.priority_score
            complaint.priority_reason = form.priority_reason
            complaint.priority = form.recommended_priority
            qr_room_param = request.GET.get("room") or request.POST.get("qr_room")
            if qr_room_param and not complaint.room_id:
                matched_qr_room = Room.objects.filter(
                    Q(qr_code_token=qr_room_param) | Q(id__iexact=str(qr_room_param))
                ).first() if str(qr_room_param).isdigit() else Room.objects.filter(qr_code_token=qr_room_param).first()
                if matched_qr_room:
                    complaint.room = matched_qr_room
            bind_complaint_spatial_origin(complaint)
            set_sla_due_date(complaint)

            # ── AI Staff Auto-Assignment ──────────────────────────────────────
            category_name = complaint.category.name if complaint.category_id else ""
            dept_code = complaint.category.department.code if (complaint.category_id and complaint.category.department_id) else ""

            # For MESS / Dining categories: always use the hall's Dining Incharge
            # directly from the DB — never fall through to the JSON roster matcher.
            if dept_code in ("MESS", "DINING"):
                auto_dispatch_complaint(complaint, save=False)
            else:
                location_text = complaint.location_description or ""
                staff_matches = suggest_staff(
                    category_name=category_name,
                    location_description=location_text,
                    title=complaint.title or "",
                    description=complaint.description or "",
                    n=1,
                )
                if staff_matches:
                    best_match = staff_matches[0]
                    try:
                        assigned_user = User.objects.get(username=best_match["username"])
                        complaint.assigned_to = assigned_user
                        complaint.assigned_at = timezone.now()
                        complaint.status = Complaint.Status.ASSIGNED
                        record_staff_assignment(assigned_user.id)
                    except User.DoesNotExist:
                        pass  # Staff user not in DB yet — fallback to dispatcher
                if not complaint.assigned_to_id:
                    auto_dispatch_complaint(complaint, save=False)
            # ─────────────────────────────────────────────────────────────────

            if request.FILES.get("evidence"):
                complaint.evidence = compress_uploaded_image(request.FILES["evidence"])
            try:
                complaint.full_clean()
            except DjangoValidationError as exc:
                form.add_error(None, exc)
                return render(
                    request,
                    "core/complaint_form.html",
                    {
                        "form": form,
                        "active_halls": Building.objects.filter(is_active=True, parent__isnull=True, building_type="hall").prefetch_related("hostels").order_by("name"),
                        "active_hostels": Building.objects.filter(is_active=True, parent__isnull=False).select_related("parent").order_by("parent__name", "short_name"),
                    },
                )
            complaint.save()
            duplicate = find_potential_duplicate(complaint)
            if duplicate:
                complaint.duplicate_of = duplicate
                complaint.save(update_fields=["duplicate_of", "updated_at"])

            ComplaintStatusHistory.objects.create(
                complaint=complaint, status=Complaint.Status.OPEN, note="Complaint submitted."
            )
            if complaint.assigned_to:
                ComplaintStatusHistory.objects.create(
                    complaint=complaint,
                    status=complaint.status,
                    note=f"Auto-assigned to {complaint.assigned_to.get_full_name() or complaint.assigned_to.username} based on category and location.",
                )
            if duplicate:
                messages.success(request, f"Complaint {complaint.reference} submitted. A similar report ({duplicate.reference}) was found.")
            elif complaint.assigned_to:
                messages.success(request, f"Complaint {complaint.reference} submitted and assigned to {complaint.assigned_to.get_full_name()}. Tracking token: {complaint.tracking_token}")
            else:
                messages.success(request, f"Complaint {complaint.reference} has been submitted. Your tracking token is: {complaint.tracking_token}")
            return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
    else:
        form = ComplaintSubmissionForm()
    return render(
        request,
        "core/complaint_form.html",
        {
            "form": form,
            "active_halls": Building.objects.filter(is_active=True, parent__isnull=True, building_type="hall").prefetch_related("hostels").order_by("name"),
            "active_hostels": Building.objects.filter(is_active=True, parent__isnull=False).select_related("parent").order_by("parent__name", "short_name"),
        },
    )


@login_required
def complaint_list(request):
    role = getattr(getattr(request.user, "profile", None), "role", None)
    admin_roles = {
        UserProfile.Role.ADMIN,
        UserProfile.Role.REGISTRAR,
        UserProfile.Role.PROVOST,
        UserProfile.Role.HOD,
    }
    if request.user.is_superuser or role in admin_roles:
        complaints = get_scoped_complaints(request.user).select_related(
            "category", "reporter", "assigned_to", "room__floor__building__campus"
        )
    elif request.user.is_staff or role == UserProfile.Role.STAFF:
        complaints = Complaint.objects.select_related(
            "category", "reporter", "assigned_to", "room__floor__building__campus"
        )
    else:
        complaints = Complaint.objects.filter(Q(reporter=request.user) | Q(is_public=True)).select_related(
            "category", "assigned_to", "room__floor__building__campus"
        )
    
    # Default to showing all complaints (including auto-assigned) when no filter is chosen
    status = request.GET.get("status", "")
    if status in Complaint.Status.values:
        complaints = complaints.filter(status=status)
    
    # Annotate with support count and user's support status
    complaints = complaints.annotate(support_count=Count("supports"))
    
    # For authenticated users, mark which complaints they've supported
    user_supported_ids = set()
    if request.user.is_authenticated:
        user_supported_ids = set(
            ComplaintSupport.objects.filter(user=request.user, complaint__in=complaints).values_list("complaint_id", flat=True)
        )
    
    return render(
        request,
        "core/complaint_list.html",
        {
            "complaints": complaints, 
            "selected_status": status, 
            "status_choices": Complaint.Status.choices,
            "user_supported_ids": user_supported_ids,
        },
    )


def complaint_detail(request, reference):
    # Allow direct zero-login access via tracking_token for students
    complaint_by_token = Complaint.objects.filter(tracking_token=reference).first()
    if complaint_by_token:
        return complaint_tracking(request, tracking_token=complaint_by_token.tracking_token)

    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())

    complaint = get_object_or_404(
        Complaint.objects.select_related(
            "reporter", "category__department", "room__floor__building__parent", "assigned_to__profile", "assigned_by"
        ).annotate(
            support_count=Count("supports")
        ),
        reference=reference,
    )
    profile = getattr(request.user, "profile", None)
    role = getattr(profile, "role", None)
    admin_roles = {
        UserProfile.Role.ADMIN,
        UserProfile.Role.REGISTRAR,
        UserProfile.Role.PROVOST,
        UserProfile.Role.HOD,
    }
    can_manage = request.user.is_staff or role in ({UserProfile.Role.STAFF} | admin_roles)
    can_assign_and_update_status = request.user.is_superuser or (role in admin_roles)
    is_hall_caretaker = bool(
        profile
        and profile.managed_building
        and complaint.room
        and complaint.room.floor
        and (
            complaint.room.floor.building == profile.managed_building
            or complaint.room.floor.building.parent == profile.managed_building
        )
    )
    can_resolve = bool(
        can_assign_and_update_status
        or is_hall_caretaker
        or (complaint.assigned_to_id == request.user.id)
    )
    
    if (role in {UserProfile.Role.PROVOST, UserProfile.Role.HOD} or (profile and profile.managed_building)) and not request.user.is_superuser:
        if not get_scoped_complaints_for_user(request.user).filter(pk=complaint.pk).exists():
            messages.error(request, "Access denied: This complaint belongs to another Hall or Department jurisdiction.")
            return redirect("core:dashboard")
    if complaint.reporter_id != request.user.id and not complaint.is_public and not can_manage:
        messages.error(request, "You do not have permission to view that complaint.")
        return redirect("core:complaint_list")
    return render(
        request,
        "core/complaint_detail.html",
        {
            "complaint": complaint,
            "can_manage": can_manage,
            "can_assign_and_update_status": can_assign_and_update_status,  # New flag for admin-only operations
            "can_resolve": can_resolve,
            "is_tracking_view": False,
            "is_student_view": False,
            "admin_resolution_form": AdminResolutionForm(),
            "assignment_form": ComplaintAssignmentForm(instance=complaint) if can_assign_and_update_status else None,
            "status_form": ComplaintStatusForm(initial={"status": complaint.status}) if can_assign_and_update_status else None,
            "has_supported": ComplaintSupport.objects.filter(complaint=complaint, user=request.user).exists(),
            "verification_form": None,  # NEVER leak student verification form into administrative detail view
            "reopen_form": None,        # NEVER leak student reopen form into administrative detail view
            "feedback_form": None,
            "has_feedback": hasattr(complaint, "feedback"),
        },
    )


def admin_complaint_detail_by_id(request, complaint_id):
    complaint = get_object_or_404(Complaint, pk=complaint_id)
    return complaint_detail(request, reference=complaint.reference)


def tracking_form(request):
    """Form page for users to enter their tracking token."""
    if request.method == "POST":
        if is_rate_limited(request, key_prefix="track_lookup", max_requests=35, window_seconds=60):
            messages.error(request, "Too many lookup attempts. Please wait a moment before trying again.")
            return render(request, "core/tracking_form.html", status=429)
        tracking_token = request.POST.get("tracking_token", "").strip()
        if tracking_token:
            complaint = Complaint.objects.filter(tracking_token=tracking_token).first()
            if complaint:
                return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
            else:
                messages.error(request, "No complaint found with that tracking token. Please double check and try again.")
        else:
            messages.error(request, "Please enter your tracking token.")
    return render(request, "core/tracking_form.html")


def complaint_tracking(request, tracking_token):
    """Private no-account tracking page reached from the student's submission receipt."""
    complaint = get_object_or_404(
        Complaint.objects.select_related(
            "category__department", "room__floor__building__parent", "assigned_to__profile", "assigned_by"
        ).annotate(support_count=Count("supports")),
        tracking_token=tracking_token,
    )

    if request.GET.get("format") == "json" or request.headers.get("Accept") == "application/json":
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
            "closed_at": complaint.closed_at.strftime("%d %b %Y, %H:%M") if complaint.closed_at else None,
            "closed_at_iso": complaint.closed_at.isoformat() if complaint.closed_at else None,
            "resolved_at": complaint.resolved_at.strftime("%d %b %Y, %H:%M") if complaint.resolved_at else None,
            "updated_at": complaint.updated_at.isoformat() if complaint.updated_at else None,
            "history_count": len(history_items),
            "history": history_items,
            "feedback_rating": complaint.feedback.rating if hasattr(complaint, "feedback") and complaint.feedback else (complaint.feedback_rating or None),
            "feedback_comment": complaint.feedback.comment if hasattr(complaint, "feedback") and complaint.feedback else (complaint.feedback_comments or ""),
        })

    if request.method == "POST":
        action = request.POST.get("action") or request.POST.get("submit_action")
        if action == "reopen" or "reopen_reason" in request.POST:
            return student_reopen_complaint(request, complaint.tracking_token)
        else:
            return student_confirm_resolution(request, complaint.tracking_token)

    can_verify = complaint.status == Complaint.Status.RESOLVED
    can_reopen = complaint.status in {Complaint.Status.RESOLVED, Complaint.Status.CLOSED}
    can_feedback = (
        complaint.resolution_verification == Complaint.ResolutionVerification.VERIFIED
        and not hasattr(complaint, "feedback")
    )
    return render(
        request,
        "core/complaint_detail.html",
        {
            "complaint": complaint,
            "can_manage": False,
            "can_assign_and_update_status": False,
            "can_resolve": False,
            "is_tracking_view": True,
            "is_student_view": True,
            "has_supported": False,
            "verification_form": ResolutionVerificationForm() if can_verify else None,
            "reopen_form": ComplaintReopenForm() if can_reopen else None,
            "feedback_form": ComplaintFeedbackForm() if can_feedback else None,
            "has_feedback": hasattr(complaint, "feedback"),
        },
    )


def complaint_toggle_support(request, reference):
    """Allow both logged-in and anonymous visitors to support a complaint."""
    if request.method != "POST":
        next_url = request.GET.get("next")
        return redirect(_safe_redirect_target(request, next_url, fallback="core:home"))
    complaint = get_object_or_404(Complaint, reference=reference)
    if request.user.is_authenticated:
        support, created = ComplaintSupport.objects.get_or_create(
            complaint=complaint, user=request.user, defaults={"session_key": ""}
        )
        if created:
            messages.success(request, "Your support has been added.")
        else:
            support.delete()
            messages.info(request, "Your support was removed.")
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key or ""
        if session_key:
            support, created = ComplaintSupport.objects.get_or_create(
                complaint=complaint, session_key=session_key, defaults={"user": None}
            )
            if created:
                messages.success(request, "Your support has been added.")
            else:
                support.delete()
                messages.info(request, "Your support was removed.")
    next_url = request.POST.get("next") or request.GET.get("next")
    return redirect(_safe_redirect_target(request, next_url, fallback="core:home"))


@admin_only_required
def complaint_assign(request, reference):
    complaint = get_object_or_404(Complaint, reference=reference)
    profile = getattr(request.user, "profile", None)
    role = getattr(profile, "role", None)
    if (role in {UserProfile.Role.PROVOST, UserProfile.Role.HOD} or (profile and profile.managed_building)) and not request.user.is_superuser:
        if not get_scoped_complaints_for_user(request.user).filter(pk=complaint.pk).exists():
            messages.error(request, "Access denied: This complaint belongs to another Hall or Department jurisdiction.")
            return redirect("core:dashboard")
    if request.method != "POST":
        return redirect("core:complaint_detail", reference=reference)
    form = ComplaintAssignmentForm(request.POST, instance=complaint)
    if form.is_valid():
        updated = form.save(commit=False)
        updated.assigned_by = request.user
        updated.assigned_at = timezone.now()
        if updated.status == Complaint.Status.OPEN:
            updated.status = Complaint.Status.ASSIGNED
        try:
            updated.full_clean()
            updated.save()
            ComplaintStatusHistory.objects.create(
                complaint=updated, status=updated.status, note=f"Assigned to {updated.assigned_to.get_full_name() or updated.assigned_to.username}.", changed_by=request.user
            )
            messages.success(request, "Maintenance staff member assigned.")
        except Exception as exc:
            messages.error(request, f"Assignment could not be saved: {exc}")
    else:
        messages.error(request, "The assignment could not be saved.")
    return redirect("core:complaint_detail", reference=reference)


@admin_only_required
def complaint_update_status(request, reference):
    complaint = get_object_or_404(Complaint, reference=reference)
    profile = getattr(request.user, "profile", None)
    role = getattr(profile, "role", None)
    if (role in {UserProfile.Role.PROVOST, UserProfile.Role.HOD} or (profile and profile.managed_building)) and not request.user.is_superuser:
        if not get_scoped_complaints_for_user(request.user).filter(pk=complaint.pk).exists():
            messages.error(request, "Access denied: This complaint belongs to another Hall or Department jurisdiction.")
            return redirect("core:dashboard")
    if request.method != "POST":
        return redirect("core:complaint_detail", reference=reference)
    form = ComplaintStatusForm(request.POST, request.FILES)
    if form.is_valid():
        new_status = form.cleaned_data["status"]
        complaint.status = new_status
        fields_to_update = ["status", "updated_at"]
        if new_status == Complaint.Status.RESOLVED:
            now = timezone.now()
            complaint.resolved_at = now
            complaint.resolution_verification = Complaint.ResolutionVerification.PENDING
            complaint.resolution_note = form.cleaned_data["note"] or "Resolved via Caretaker Office inspection."
            fields_to_update.extend(["resolved_at", "resolution_verification", "resolution_note"])
            proof_file = request.FILES.get("resolution_proof")
            if proof_file:
                complaint.resolution_proof = compress_uploaded_image(proof_file)
                fields_to_update.append("resolution_proof")
        elif new_status == Complaint.Status.IN_PROGRESS and not complaint.in_progress_at:
            complaint.in_progress_at = timezone.now()
            fields_to_update.append("in_progress_at")
        complaint.save(update_fields=fields_to_update)
        ComplaintStatusHistory.objects.create(
            complaint=complaint,
            status=new_status,
            note=form.cleaned_data["note"] or f"Status set to {new_status} by {request.user.get_full_name() or request.user.username} (Caretaker/Admin proxy update).",
            changed_by=request.user,
        )
        if new_status == Complaint.Status.RESOLVED:
            messages.success(request, f"Complaint #{complaint.reference} marked as resolved. Pending student confirmation.")
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect("core:complaint_detail", reference=reference)
        else:
            messages.success(request, f"Complaint status updated to {complaint.get_status_display()}.")
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect("core:complaint_detail", reference=reference)


def admin_update_status_by_id(request, complaint_id):
    complaint = get_object_or_404(Complaint, pk=complaint_id)
    return complaint_update_status(request, reference=complaint.reference)


@login_required
def complaint_admin_resolve(request, reference):
    """
    Allow Provost, HOD, Caretaker, or Admin to mark a complaint resolved directly from
    the complaint detail view with mandatory proof upload (repair photo or signed slip).
    """
    complaint = get_object_or_404(Complaint, reference=reference)
    if request.method != "POST":
        return redirect("core:complaint_detail", reference=reference)

    profile = getattr(request.user, "profile", None)
    role = getattr(profile, "role", None)
    admin_roles = {
        UserProfile.Role.ADMIN,
        UserProfile.Role.REGISTRAR,
        UserProfile.Role.PROVOST,
        UserProfile.Role.HOD,
    }
    is_hall_caretaker = bool(
        profile
        and profile.managed_building
        and complaint.room
        and complaint.room.floor
        and (
            complaint.room.floor.building == profile.managed_building
            or complaint.room.floor.building.parent == profile.managed_building
        )
    )
    can_resolve = bool(
        request.user.is_superuser
        or (role in {UserProfile.Role.ADMIN, UserProfile.Role.REGISTRAR})
        or (role in {UserProfile.Role.PROVOST, UserProfile.Role.HOD} and get_scoped_complaints_for_user(request.user).filter(pk=complaint.pk).exists())
        or is_hall_caretaker
        or (complaint.assigned_to_id == request.user.id)
    )
    if not can_resolve:
        messages.error(request, "Permission denied: Only authorized administrators, provosts, HODs, caretakers, or assigned technicians can mark this complaint resolved.")
        return redirect("core:dashboard")

    proof_file = request.FILES.get("resolution_proof")
    note = (request.POST.get("resolution_note") or "").strip()

    if not proof_file:
        messages.error(request, "A resolution proof photo or signed paper dispatch slip is required to mark the complaint resolved.")
        return redirect("core:complaint_detail", reference=reference)

    compressed_proof = compress_uploaded_image(proof_file)
    if not compressed_proof:
        messages.error(request, "The uploaded file is not a valid image. Please upload a clear JPG, PNG, or WEBP photo.")
        return redirect("core:complaint_detail", reference=reference)

    now = timezone.now()
    complaint.status = Complaint.Status.RESOLVED
    complaint.resolved_at = now
    complaint.resolution_verification = Complaint.ResolutionVerification.PENDING
    complaint.resolution_note = note or "Resolved and inspected via Caretaker / Provost Office."
    complaint.resolution_proof = compressed_proof
    complaint.save(update_fields=["status", "resolved_at", "resolution_verification", "resolution_note", "resolution_proof", "updated_at"])

    role_display = profile.get_role_display() if profile else "Administrator"
    actor_name = request.user.get_full_name() or request.user.username

    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        status=Complaint.Status.RESOLVED,
        note=f"Marked as resolved by {actor_name} ({role_display}). Resolution proof / signed slip uploaded. Awaiting student verification.",
        changed_by=request.user,
    )
    messages.success(request, f"Complaint #{complaint.reference} marked as resolved. Pending student confirmation.")
    role_upper = str(getattr(profile, "role", "")).upper()
    if role_upper == "PROVOST" or is_hall_caretaker:
        return redirect("core:provost_dashboard")
    return redirect("core:admin_dashboard")


def complaint_verify_resolution(request, reference):
    complaint = get_object_or_404(Complaint, reference=reference)
    if not _can_student_modify_complaint(request, complaint):
        messages.error(request, "You do not have permission to verify this complaint.")
        return redirect("core:home")
    if request.method != "POST" or complaint.status != Complaint.Status.RESOLVED:
        if complaint.tracking_token and not request.user.is_authenticated:
            return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
        return redirect("core:complaint_detail", reference=reference)
    form = ResolutionVerificationForm(request.POST)
    if form.is_valid():
        decision = form.cleaned_data["decision"]
        complaint.resolution_verification = decision
        complaint.resolution_verified_at = timezone.now()
        if decision == Complaint.ResolutionVerification.VERIFIED:
            complaint.status = Complaint.Status.CLOSED
            complaint.closed_at = timezone.now()
            complaint.purge_attached_media()
            note = "Student verified that the resolution is complete."
        else:
            complaint.status = Complaint.Status.REOPENED
            complaint.reopened_count += 1
            set_sla_due_date(complaint)
            note = "Student rejected the resolution and reopened the complaint."
        if form.cleaned_data["note"]:
            note = f"{note} {form.cleaned_data['note']}"
        complaint.save(update_fields=["status", "resolution_verification", "resolution_verified_at", "reopened_count", "sla_due_at", "updated_at"])
        changer = request.user if request.user.is_authenticated else None
        ComplaintStatusHistory.objects.create(complaint=complaint, status=complaint.status, note=note, changed_by=changer)
        messages.success(request, "Your resolution response has been recorded.")
    if complaint.tracking_token and not request.user.is_authenticated:
        return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
    return redirect("core:complaint_detail", reference=reference)


def complaint_reopen(request, reference):
    complaint = get_object_or_404(Complaint, reference=reference)
    if not _can_student_modify_complaint(request, complaint):
        messages.error(request, "You do not have permission to reopen this complaint.")
        return redirect("core:home")
    if request.method != "POST" or complaint.status not in {Complaint.Status.RESOLVED, Complaint.Status.CLOSED}:
        if complaint.tracking_token and not request.user.is_authenticated:
            return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
        return redirect("core:complaint_detail", reference=reference)
    form = ComplaintReopenForm(request.POST)
    if form.is_valid():
        complaint.status = Complaint.Status.REOPENED
        complaint.resolution_verification = Complaint.ResolutionVerification.REJECTED
        complaint.resolution_verified_at = timezone.now()
        complaint.reopened_count += 1
        set_sla_due_date(complaint)
        complaint.save(update_fields=["status", "resolution_verification", "resolution_verified_at", "reopened_count", "sla_due_at", "updated_at"])
        changer = request.user if request.user.is_authenticated else None
        ComplaintStatusHistory.objects.create(
            complaint=complaint, status=Complaint.Status.REOPENED, note=f"Reopened by student: {form.cleaned_data['note']}", changed_by=changer
        )
        messages.success(request, "The complaint has been reopened.")
    if complaint.tracking_token and not request.user.is_authenticated:
        return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
    return redirect("core:complaint_detail", reference=reference)


def complaint_feedback(request, reference):
    complaint = get_object_or_404(Complaint, reference=reference)
    if not _can_student_modify_complaint(request, complaint):
        messages.error(request, "You do not have permission to leave feedback on this complaint.")
        return redirect("core:home")
    if request.method != "POST" or complaint.resolution_verification != Complaint.ResolutionVerification.VERIFIED:
        if complaint.tracking_token and not request.user.is_authenticated:
            return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
        return redirect("core:complaint_detail", reference=reference)
    if hasattr(complaint, "feedback"):
        messages.error(request, "Feedback has already been submitted for this complaint.")
        if complaint.tracking_token and not request.user.is_authenticated:
            return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
        return redirect("core:complaint_detail", reference=reference)
    form = ComplaintFeedbackForm(request.POST)
    if form.is_valid():
        feedback = form.save(commit=False)
        feedback.complaint = complaint
        try:
            feedback.full_clean()
            feedback.save()
            messages.success(request, "Thank you for your feedback.")
        except Exception as exc:
            messages.error(request, f"Feedback could not be saved: {exc}")
    if complaint.tracking_token and not request.user.is_authenticated:
        return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)
    return redirect("core:complaint_detail", reference=reference)


def student_confirm_resolution(request, tracking_token):
    """Public token-authenticated endpoint for students to confirm resolution, rate, and purge media."""
    complaint = get_object_or_404(Complaint, tracking_token=tracking_token)
    if request.method != "POST":
        return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)

    if complaint.status != Complaint.Status.RESOLVED:
        messages.error(request, "This complaint is not pending resolution verification.")
        return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)

    # Process optional feedback
    rating = request.POST.get("rating")
    feedback = (request.POST.get("feedback") or request.POST.get("comment") or request.POST.get("note") or "").strip()
    rating_val = None
    if rating:
        try:
            rating_val = max(1, min(5, int(rating)))
            complaint.feedback_rating = rating_val
        except (ValueError, TypeError):
            pass
    if feedback:
        complaint.feedback_comments = feedback

    # Update status
    now = timezone.now()
    complaint.status = Complaint.Status.CLOSED
    complaint.closed_at = now
    complaint.resolution_verification = Complaint.ResolutionVerification.VERIFIED
    complaint.resolution_verified_at = now
    complaint.save()

    # Save to ComplaintFeedback model
    if rating_val is not None or feedback:
        ComplaintFeedback.objects.update_or_create(
            complaint=complaint,
            defaults={
                "rating": rating_val or 5,
                "comment": feedback,
            },
        )

    # Automated disk cleanup
    if hasattr(complaint, "purge_attached_media"):
        complaint.purge_attached_media()

    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        status=Complaint.Status.CLOSED,
        note=f"Student confirmed resolution (Rating: {rating_val or 5}/5). Media purged.",
    )
    messages.success(request, "Thank you! Your complaint has been marked as resolved and closed.")
    return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)


def student_reopen_complaint(request, tracking_token):
    """
    Public token-authenticated endpoint for students to dispute/reopen a resolved complaint.
    Requires explanation (>= 10 chars) and mandatory photo proof.
    Compresses proof, sets status to REOPENED, bumps priority to urgent,
    and deducts 15 points from assigned technician accountability_score.
    """
    complaint = get_object_or_404(Complaint, tracking_token=tracking_token)
    if request.method != "POST":
        return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)

    explanation = (
        request.POST.get("reopen_reason")
        or request.POST.get("reason")
        or request.POST.get("note")
        or request.POST.get("explanation")
        or ""
    ).strip()

    proof_file = (
        request.FILES.get("reopen_proof")
        or request.FILES.get("proof")
        or request.FILES.get("evidence")
        or request.FILES.get("image")
    )

    if len(explanation) < 10:
        messages.error(request, "Please provide a detailed explanation of at least 10 characters to reopen.")
        return HttpResponse(
            "Explanation must be at least 10 characters long.",
            status=400,
        )

    if not proof_file:
        messages.error(request, "Mandatory photo proof is required to reopen a complaint.")
        return HttpResponse(
            "Photo proof (reopen_proof) is required to reopen a complaint.",
            status=400,
        )

    compressed_proof = compress_uploaded_image(proof_file)
    if not compressed_proof:
        messages.error(request, "The uploaded file is not a valid image. Please provide a clear photo (JPG, PNG, or WEBP).")
        return HttpResponse(
            "Photo proof must be a valid JPG, PNG, or WEBP image file.",
            status=400,
        )

    now = timezone.now()
    complaint.reopen_proof = compressed_proof
    complaint.reopen_reason = explanation
    complaint.status = Complaint.Status.REOPENED
    complaint.reopened_at = now
    complaint.resolution_verification = Complaint.ResolutionVerification.REJECTED
    complaint.resolution_verified_at = now
    complaint.reopen_count = (complaint.reopen_count or 0) + 1
    complaint.reopened_count = (complaint.reopened_count or 0) + 1
    complaint.priority = Complaint.Priority.URGENT
    complaint.priority_score = max(complaint.priority_score or 0, 95)
    set_sla_due_date(complaint, from_time=now)
    complaint.save(
        update_fields=[
            "reopen_proof",
            "reopen_reason",
            "status",
            "reopened_at",
            "resolution_verification",
            "resolution_verified_at",
            "reopen_count",
            "reopened_count",
            "priority",
            "priority_score",
            "sla_due_at",
            "updated_at",
        ]
    )

    # Deduct 15 points from assigned technician accountability_score
    if complaint.assigned_to_id:
        profile, _ = UserProfile.objects.get_or_create(user_id=complaint.assigned_to_id)
        profile.accountability_score = (profile.accountability_score or 100) - 15
        profile.save(update_fields=["accountability_score", "updated_at"])

    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        status=Complaint.Status.REOPENED,
        note=f"Reopened by student with photo proof (Priority bumped to Urgent): {explanation}",
    )
    messages.success(request, "Complaint has been reopened and escalated to Urgent priority.")
    return redirect("core:complaint_tracking", tracking_token=complaint.tracking_token)


track_complaint = complaint_tracking
admin_complaint_detail = complaint_detail
admin_update_status = complaint_update_status
