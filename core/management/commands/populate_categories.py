from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import ComplaintCategory, Department


class Command(BaseCommand):
    help = "Populate complaint categories from the hierarchical structure"

    @transaction.atomic
    def handle(self, *args, **options):
        # Define categories with their descriptions and SLA hours
        categories_data = [
            # IT & Digital Infrastructure (assume "IT Services" department)
            {
                "name": "Network & Connectivity",
                "description": "WiFi, internet connectivity, network issues, bandwidth problems",
                "department_code": "IT",
                "default_sla_hours": 4,
            },
            {
                "name": "Software & Portals",
                "description": "Portal access, application issues, software bugs, login problems",
                "department_code": "IT",
                "default_sla_hours": 8,
            },
            {
                "name": "Lab Equipment",
                "description": "Lab computers, printers, scanners, and other lab devices",
                "department_code": "IT",
                "default_sla_hours": 24,
            },
            # Campus Facilities & Maintenance (assume "Facilities" department)
            {
                "name": "Classroom Amenities",
                "description": "Projectors, screens, boards, lighting, AC, furniture in classrooms",
                "department_code": "FACILITIES",
                "default_sla_hours": 24,
            },
            {
                "name": "Sanitation & Hygiene",
                "description": "Cleaning, garbage disposal, hygiene, restroom and bathroom maintenance",
                "department_code": "FACILITIES",
                "default_sla_hours": 6,
            },
            {
                "name": "Civil & Electrical",
                "description": "Electrical systems, plumbing, construction, painting, structural issues",
                "department_code": "FACILITIES",
                "default_sla_hours": 48,
            },
            # Hostel & Residential Services (assume "Hostel Services" department)
            {
                "name": "Room Maintenance",
                "description": "Hostel room repairs, furniture, doors, windows, paint, leaks",
                "department_code": "HOSTEL",
                "default_sla_hours": 24,
            },
            {
                "name": "Dining & Mess",
                "description": "Mess quality, food issues, dining facility problems",
                "department_code": "HOSTEL",
                "default_sla_hours": 12,
            },
            {
                "name": "Living Environment",
                "description": "Hostel living conditions, water, electricity, ventilation, temperature",
                "department_code": "HOSTEL",
                "default_sla_hours": 24,
            },
            # Administration & Finance (assume "Administration" department)
            {
                "name": "Fees & Accounts",
                "description": "Fee payment issues, refunds, billing problems, financial queries",
                "department_code": "ADMIN",
                "default_sla_hours": 48,
            },
            {
                "name": "Documentation",
                "description": "Certificate requests, document issues, form problems, records",
                "department_code": "ADMIN",
                "default_sla_hours": 72,
            },
            {
                "name": "Library Services",
                "description": "Library access, book issues, member card, database problems",
                "department_code": "LIBRARY",
                "default_sla_hours": 24,
            },
            # Safety, Health & Student Welfare (assume "Health & Safety" department)
            {
                "name": "Campus Security",
                "description": "Security concerns, theft, lost items, safety emergencies",
                "department_code": "SECURITY",
                "default_sla_hours": 2,
            },
            {
                "name": "Medical Services",
                "description": "Medical emergencies, health center access, healthcare issues",
                "department_code": "HEALTH",
                "default_sla_hours": 1,
            },
            {
                "name": "Grievance & Ethics",
                "description": "Grievances, harassment, misconduct, ethical concerns",
                "department_code": "ADMIN",
                "default_sla_hours": 72,
            },
        ]

        # Create or get departments
        department_map = {}
        department_names = {
            "IT": "IT Services",
            "FACILITIES": "Facilities & Maintenance",
            "HOSTEL": "Hostel Services",
            "ADMIN": "Administration",
            "LIBRARY": "Library",
            "SECURITY": "Campus Security",
            "HEALTH": "Health & Medical Services",
        }

        for code, name in department_names.items():
            dept, created = Department.objects.get_or_create(
                code=code, defaults={"name": name, "is_active": True}
            )
            department_map[code] = dept
            if created:
                self.stdout.write(self.style.SUCCESS(f"✓ Created department: {name}"))

        # Create or update categories
        created_count = 0
        updated_count = 0

        for category_data in categories_data:
            dept_code = category_data.pop("department_code")
            department = department_map[dept_code]

            category, created = ComplaintCategory.objects.update_or_create(
                name=category_data["name"],
                defaults={
                    **category_data,
                    "department": department,
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created category: {category.name}")
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"⟳ Updated category: {category.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Process complete! Created: {created_count}, Updated: {updated_count}"
            )
        )
