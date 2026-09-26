import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import core.models


def assign_tracking_tokens(apps, schema_editor):
    Complaint = apps.get_model("core", "Complaint")
    for complaint in Complaint.objects.filter(tracking_token__isnull=True):
        complaint.tracking_token = uuid.uuid4().hex
        complaint.save(update_fields=["tracking_token"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_complaint_escalated_at_complaint_escalation_level_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="complaint",
            name="reporter_name",
            field=models.CharField(default="Unknown", max_length=150),
        ),
        migrations.AddField(
            model_name="complaint",
            name="reporter_enrollment_number",
            field=models.CharField(db_index=True, default="LEGACY", max_length=40),
        ),
        migrations.AlterField(
            model_name="complaint",
            name="reporter",
            field=models.ForeignKey(blank=True, help_text="Used for legacy or staff-submitted complaints; students report without an account.", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="complaints", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="complaint",
            name="tracking_token",
            field=models.CharField(max_length=32, null=True, unique=True),
        ),
        migrations.RunPython(assign_tracking_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="complaint",
            name="tracking_token",
            field=models.CharField(default=core.models.generate_tracking_token, editable=False, max_length=32, unique=True),
        ),
    ]
