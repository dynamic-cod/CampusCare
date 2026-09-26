from django.core.management.base import BaseCommand

from core.accountability import escalate_overdue_complaints


class Command(BaseCommand):
    help = "Escalate unresolved complaints that have passed their SLA deadline."

    def handle(self, *args, **options):
        escalated = escalate_overdue_complaints()
        self.stdout.write(self.style.SUCCESS(f"Escalated {len(escalated)} overdue complaint(s)."))
