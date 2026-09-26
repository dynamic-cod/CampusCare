from django.core.management.base import BaseCommand
from seed_subadmins import seed_subadmins


class Command(BaseCommand):
    help = "Seed Registrar, Provost, and HOD multi-tenant sub-admin accounts"

    def handle(self, *args, **options):
        seed_subadmins(stdout=self.stdout)
