"""SLA and resolution workflow helpers for Phase 4."""
from datetime import timedelta

from django.utils import timezone

from .models import Complaint, ComplaintStatusHistory
from .smart import score_priority


def set_sla_due_date(complaint, from_time=None):
    """Set the SLA deadline using AI-determined priority rather than the category default."""
    text = f"{complaint.title} {complaint.description}"
    category_name = complaint.category.name if complaint.category_id else ""
    location = complaint.location_description or ""
    _score, _priority, _reason, sla_hours = score_priority(
        text, title=complaint.title, description=complaint.description,
        category_name=category_name, location=location,
    )
    complaint.sla_due_at = (from_time or timezone.now()) + timedelta(hours=sla_hours)


def escalate_overdue_complaints(now=None):
    """Record a single automatic escalation for each currently overdue unresolved complaint."""
    now = now or timezone.now()
    overdue = Complaint.objects.filter(sla_due_at__lt=now, escalated_at__isnull=True).exclude(
        status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]
    )
    escalated = []
    for complaint in overdue:
        complaint.escalation_level += 1
        complaint.escalated_at = now
        complaint.save(update_fields=["escalation_level", "escalated_at", "updated_at"])
        ComplaintStatusHistory.objects.create(
            complaint=complaint,
            status=complaint.status,
            note=f"Automatic SLA escalation triggered (level {complaint.escalation_level}).",
        )
        escalated.append(complaint)
    return escalated
