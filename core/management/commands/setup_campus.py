from django.core.management.base import BaseCommand
from core.models import Campus, Building, Floor, Room


class Command(BaseCommand):
    help = 'Create sample campus structure for testing'

    def handle(self, *args, **options):
        # Create main campus
        campus, created = Campus.objects.get_or_create(
            code='MAIN',
            defaults={
                'name': 'Main Campus',
                'address': '123 University Avenue, Campus City'
            }
        )
        if created:
            self.stdout.write(f'✓ Created campus: {campus.name}')
        else:
            self.stdout.write(f'⟳ Campus already exists: {campus.name}')

        # Create buildings
        buildings_data = [
            {'code': 'ACAD', 'name': 'Academic Block'},
            {'code': 'LIBR', 'name': 'Library Building'},
            {'code': 'HOST', 'name': 'Hostel Block A'},
            {'code': 'ADMN', 'name': 'Administration Building'},
        ]

        for building_data in buildings_data:
            building, created = Building.objects.get_or_create(
                campus=campus,
                code=building_data['code'],
                defaults={'name': building_data['name']}
            )
            if created:
                self.stdout.write(f'  ✓ Created building: {building.name}')
            else:
                self.stdout.write(f'  ⟳ Building already exists: {building.name}')

            # Create floors for each building
            for floor_num in range(1, 4):  # Floors 1-3
                floor, created = Floor.objects.get_or_create(
                    building=building,
                    number=floor_num,
                    defaults={'label': f'Floor {floor_num}'}
                )
                if created:
                    self.stdout.write(f'    ✓ Created floor: {floor.label}')

                # Create rooms for each floor
                for room_num in range(1, 6):  # Rooms 101-105, 201-205, etc.
                    room_number = f'{floor_num}0{room_num}'
                    room, created = Room.objects.get_or_create(
                        floor=floor,
                        number=room_number,
                        defaults={
                            'name': f'Room {room_number}',
                            'qr_code_token': f'QR-{building.code}-{room_number}'
                        }
                    )
                    if created:
                        self.stdout.write(f'      ✓ Created room: {room.number}')

        self.stdout.write(self.style.SUCCESS('✓ Campus structure setup complete!'))
