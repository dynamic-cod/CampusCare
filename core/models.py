import uuid

from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    """Shared audit fields for editable campus reference data."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserProfile(TimestampedModel):
    """Campus-specific role and contact details for a Django user account."""

    class Role(models.TextChoices):
        REGISTRAR = "registrar", "Registrar"
        PROVOST = "provost", "Provost"
        HOD = "hod", "Head of Department"
        STAFF = "staff", "Maintenance staff"
        STUDENT = "student", "Student"
        ADMIN = "admin", "Administrator"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    department = models.ForeignKey(
        "Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="staff_profiles"
    )
    managed_building = models.ForeignKey(
        "Building", on_delete=models.SET_NULL, null=True, blank=True, related_name="managing_provosts"
    )
    managed_department = models.ForeignKey(
        "Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="managing_hods"
    )
    accountability_score = models.IntegerField(default=100)
    phone = models.CharField(max_length=20, blank=True)
    hall_location = models.CharField(max_length=200, blank=True, help_text="Assigned hall or facility (from staff roster).")

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} · {self.get_role_display()}"


class Department(TimestampedModel):
    """A campus unit responsible for handling a maintenance area."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=12, unique=True, help_text="Short unique code, e.g. ESTATE.")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Campus(TimestampedModel):
    """A physical campus or site managed by CampusCare."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=12, unique=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "campuses"

    def __str__(self):
        return self.name


class Building(TimestampedModel):
    """A named building or constituent hostel block within a campus."""

    campus = models.ForeignKey(Campus, on_delete=models.PROTECT, related_name="buildings")
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="buildings"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="hostels"
    )
    name = models.CharField(max_length=150)
    short_name = models.CharField(max_length=120, blank=True, help_text="Constituent hostel / block short name")
    code = models.CharField(max_length=20)
    gender = models.CharField(max_length=10, blank=True, help_text="e.g. Boys, Girls, Co-ed")
    building_type = models.CharField(max_length=50, default="hall", help_text="e.g. hall, hostel, academic, administrative")
    wing_detail = models.CharField(max_length=150, blank=True)
    capacity_detail = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["campus__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["campus", "name"], name="unique_building_name_per_campus"),
            models.UniqueConstraint(fields=["campus", "code"], name="unique_building_code_per_campus"),
        ]

    def __str__(self):
        return f"{self.campus.code} · {self.name}"


class Floor(TimestampedModel):
    """A floor within a campus building."""

    building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="floors")
    number = models.IntegerField(validators=[MinValueValidator(-5)])
    label = models.CharField(max_length=50, blank=True, help_text="Optional display name, e.g. Ground Floor.")

    class Meta:
        ordering = ["building__campus__name", "building__name", "number"]
        constraints = [models.UniqueConstraint(fields=["building", "number"], name="unique_floor_number_per_building")]

    def __str__(self):
        display = self.label or f"Floor {self.number}"
        return f"{self.building} · {display}"


class Room(TimestampedModel):
    """A reportable room, lab, office, or shared space."""

    floor = models.ForeignKey(Floor, on_delete=models.PROTECT, related_name="rooms")
    number = models.CharField(max_length=20)
    name = models.CharField(max_length=100, blank=True)
    qr_code_token = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["floor__building__name", "floor__number", "number"]
        constraints = [models.UniqueConstraint(fields=["floor", "number"], name="unique_room_number_per_floor")]

    def __str__(self):
        room_name = f" · {self.name}" if self.name else ""
        return f"{self.floor} · Room {self.number}{room_name}"


class ComplaintCategory(TimestampedModel):
    """A selectable maintenance category, owned by the relevant department."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="complaint_categories",
        help_text="The department normally responsible for this category.",
    )
    default_sla_hours = models.PositiveIntegerField(default=72, help_text="Default resolution target in hours.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "complaint categories"

    def __str__(self):
        return self.name


def generate_complaint_reference():
    return f"CC-{uuid.uuid4().hex[:8].upper()}"


def generate_tracking_token():
    return uuid.uuid4().hex


class Complaint(TimestampedModel):
    """A maintenance issue submitted by a campus user."""

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"
        REOPENED = "reopened", "Reopened"
        CLOSED = "closed", "Closed"

    class ResolutionVerification(models.TextChoices):
        PENDING = "pending", "Pending student verification"
        VERIFIED = "verified", "Verified by student"
        REJECTED = "rejected", "Rejected by student"

    reference = models.CharField(max_length=16, unique=True, default=generate_complaint_reference, editable=False)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="complaints", null=True, blank=True,
        help_text="Used for legacy or staff-submitted complaints; students report without an account.",
    )
    reporter_name = models.CharField(max_length=150, default="Unknown")
    reporter_enrollment_number = models.CharField(max_length=40, db_index=True, default="LEGACY")
    tracking_token = models.CharField(max_length=32, unique=True, default=generate_tracking_token, editable=False)
    category = models.ForeignKey(ComplaintCategory, on_delete=models.PROTECT, related_name="complaints")
    category_detected_automatically = models.BooleanField(default=False)
    category_detection_confidence = models.PositiveSmallIntegerField(default=0)
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="complaints", null=True, blank=True)
    location_description = models.CharField(max_length=160, blank=True)
    title = models.CharField(max_length=160)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    priority_score = models.PositiveSmallIntegerField(default=50, help_text="Rule-based urgency score from 0 to 100.")
    priority_reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    evidence = models.ImageField(
        upload_to="complaint_evidence/%Y/%m/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
        help_text="Optional JPG, PNG, or WEBP image evidence.",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_complaints"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assignments_made"
    )
    staff_task_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    assigned_at = models.DateTimeField(null=True, blank=True)
    in_progress_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    reopened_at = models.DateTimeField(null=True, blank=True)
    sla_due_at = models.DateTimeField(null=True, blank=True, help_text="Resolution target calculated from the category SLA.")
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalation_level = models.PositiveSmallIntegerField(default=0)
    resolution_verification = models.CharField(
        max_length=12, choices=ResolutionVerification.choices, default=ResolutionVerification.PENDING
    )
    resolution_verified_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)
    resolution_proof = models.ImageField(upload_to="resolution_proofs/", null=True, blank=True)
    reopen_proof = models.ImageField(upload_to="reopen_proofs/", null=True, blank=True)
    reopen_reason = models.TextField(blank=True, default="")
    reopen_count = models.PositiveSmallIntegerField(default=0)
    reopened_count = models.PositiveSmallIntegerField(default=0)
    is_public = models.BooleanField(
        default=True,
        help_text="Allow other campus users to find and support this issue without seeing reporter details.",
    )
    duplicate_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="duplicate_reports",
        help_text="A likely pre-existing complaint covering the same issue.",
    )

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.room and not self.location_description:
            raise ValidationError("Provide either a campus room or a location description.")
        if self.assigned_to and not (self.assigned_to.is_staff or self.assigned_to.profile.role == UserProfile.Role.STAFF):
            raise ValidationError({"assigned_to": "Complaints can only be assigned to maintenance staff."})

    def save(self, *args, **kwargs):
        if not kwargs.get("update_fields") and not self.room_id:
            try:
                from .ai_triage import bind_complaint_spatial_origin
                bind_complaint_spatial_origin(self)
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} · {self.title}"

    @property
    def reporter_display(self):
        if self.reporter_name and self.reporter_name != "Unknown":
            return self.reporter_name
        if self.reporter:
            return self.reporter.get_full_name() or self.reporter.username
        return "Unknown"

    @property
    def is_sla_breached(self):
        from django.utils import timezone

        return bool(
            self.sla_due_at
            and self.status not in {self.Status.RESOLVED, self.Status.CLOSED}
            and self.sla_due_at < timezone.now()
        )

    def purge_attached_media(self):
        """Delete attached image files from disk storage when complaint is closed."""
        updated_fields = []
        for field_name in ("evidence", "resolution_proof", "reopen_proof"):
            field_file = getattr(self, field_name, None)
            if field_file and getattr(field_file, "name", None):
                try:
                    storage, path_name = field_file.storage, field_file.name
                    field_file.delete(save=False)
                    if storage.exists(path_name):
                        storage.delete(path_name)
                except Exception:
                    pass
                setattr(self, field_name, None if field_name != "evidence" else "")
                updated_fields.append(field_name)
        if updated_fields and self.pk:
            self.save(update_fields=updated_fields)


class ComplaintSupport(models.Model):
    """Community upvote - one per logged-in user OR one per anonymous browser session."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="supports")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="supported_complaints", null=True, blank=True
    )
    session_key = models.CharField(max_length=40, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["complaint", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_complaint_support_per_user",
            ),
            models.UniqueConstraint(
                fields=["complaint", "session_key"],
                condition=models.Q(session_key__gt=""),
                name="unique_complaint_support_per_session",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        identifier = self.user or f"session:{self.session_key[:8]}"
        return f"{identifier} supports {self.complaint.reference}"


class ComplaintFeedback(models.Model):
    """One student satisfaction response after a verified resolution."""

    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name="feedback")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if not 1 <= self.rating <= 5:
            raise ValidationError({"rating": "Choose a rating from 1 to 5."})
        if self.complaint_id and self.complaint.resolution_verification != Complaint.ResolutionVerification.VERIFIED:
            raise ValidationError("Feedback is available once the student verifies the resolution.")

    def __str__(self):
        return f"{self.complaint.reference} · {self.rating}/5"


class ComplaintStatusHistory(models.Model):
    """Immutable audit trail for every submitted or changed complaint status."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=16, choices=Complaint.Status.choices)
    note = models.TextField(blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "complaint status histories"

    def __str__(self):
        return f"{self.complaint.reference} · {self.get_status_display()}"
