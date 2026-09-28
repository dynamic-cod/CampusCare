from django.contrib.auth import get_user_model
from django.db.backends.signals import connection_created
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(connection_created)
def configure_sqlite_connection(sender, connection, **kwargs):
    """Enforce optimal SQLite WAL pragma settings and caching for high throughput."""
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA cache_size=-64000;")
            cursor.execute("PRAGMA busy_timeout=5000;")


@receiver(post_save, sender=get_user_model())
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """Ensure externally created users have a matching CampusCare role profile."""
    if created:
        role = UserProfile.Role.ADMIN if instance.is_superuser else UserProfile.Role.STUDENT
        UserProfile.objects.get_or_create(user=instance, defaults={"role": role})

