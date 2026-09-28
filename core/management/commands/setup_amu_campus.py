from django.core.management.base import BaseCommand
from core.models import Campus, Building, Floor, Room, Department, ComplaintCategory


class Command(BaseCommand):
    help = 'Setup Aligarh Muslim University campus structure and departments'

    def handle(self, *args, **options):
        # Create AMU Campus
        campus, created = Campus.objects.get_or_create(
            code='AMU',
            defaults={
                'name': 'Aligarh Muslim University',
                'address': 'Aligarh, Uttar Pradesh - 202002, India'
            }
        )
        if created:
            self.stdout.write(f'✓ Created campus: {campus.name}')
        else:
            self.stdout.write(f'⟳ Campus already exists: {campus.name}')

        # AMU Residential Halls (19 halls + NRSC)
        halls_data = [
            {'code': 'SSN', 'name': 'Sir Syed Hall (North)', 'type': 'Boys'},
            {'code': 'SSS', 'name': 'Sir Syed Hall (South)', 'type': 'Boys'},
            {'code': 'AFT', 'name': 'Aftab Hall', 'type': 'Boys'},
            {'code': 'VMH', 'name': 'Viqarul Mulk Hall', 'type': 'Boys'},
            {'code': 'MMH', 'name': 'Mohsinul Mulk Hall', 'type': 'Boys'},
            {'code': 'SSH', 'name': 'Sir Shah Sulaiman Hall', 'type': 'Boys'},
            {'code': 'SZH', 'name': 'Sir Ziauddin Hall', 'type': 'Boys'},
            {'code': 'RMH', 'name': 'Ross Masood Hall', 'type': 'Boys'},
            {'code': 'HHH', 'name': 'Hadi Hasan Hall', 'type': 'Boys'},
            {'code': 'MHH', 'name': 'Mohammad Habib Hall', 'type': 'Boys'},
            {'code': 'NTH', 'name': 'Nadeem Tarin Hall', 'type': 'Boys'},
            {'code': 'BRA', 'name': 'Dr. B.R. Ambedkar Hall', 'type': 'Boys'},
            {'code': 'AIB', 'name': 'Allama Iqbal Boarding House', 'type': 'Boys'},
            {'code': 'ABH', 'name': 'Abdullah Hall', 'type': 'Girls'},
            {'code': 'SNH', 'name': 'Sarojini Naidu Hall', 'type': 'Girls'},
            {'code': 'IGH', 'name': 'Indira Gandhi Hall', 'type': 'Girls'},
            {'code': 'BSJ', 'name': 'Begum Sultan Jahan Hall', 'type': 'Girls'},
            {'code': 'BFH', 'name': 'Bibi Fatima Hall', 'type': 'Girls'},
            {'code': 'BAN', 'name': 'Begum Azeezun Nisa Hall', 'type': 'Girls'},
            {'code': 'NRSC', 'name': 'Non-Resident Students Centre', 'type': 'Co-Ed'},
        ]

        for hall_data in halls_data:
            building, created = Building.objects.get_or_create(
                campus=campus,
                code=hall_data['code'],
                defaults={'name': hall_data['name']}
            )
            if created:
                self.stdout.write(f'  ✓ Created building: {building.name} ({hall_data["type"]})')
                
                # Create floors for each hall (typically 2-3 floors)
                for floor_num in range(1, 4):  # Floors 1-3
                    floor, created = Floor.objects.get_or_create(
                        building=building,
                        number=floor_num,
                        defaults={'label': f'Floor {floor_num}'}
                    )
                    if created:
                        self.stdout.write(f'    ✓ Created floor: {floor.label}')

                        # Create rooms for each floor (150 rooms: 50 per floor, numbered 001 to 150)
                        rooms_per_floor = 50
                        for room_num in range(1, rooms_per_floor + 1):
                            global_room_idx = ((floor_num - 1) * rooms_per_floor) + room_num
                            room_number = f'{global_room_idx:03d}'
                            room, created = Room.objects.get_or_create(
                                floor=floor,
                                number=room_number,
                                defaults={
                                    'name': f'{hall_data["name"]} · Room {room_number}',
                                    'qr_code_token': f'QR-{hall_data["code"]}-{room_number}'
                                }
                            )
                            if created:
                                self.stdout.write(f'      ✓ Created room: {room.number}')
            else:
                self.stdout.write(f'  ⟳ Building already exists: {building.name}')

        # Academic Buildings (Major Faculties)
        academic_buildings = [
            {'code': 'AGRI', 'name': 'Faculty of Agricultural Sciences'},
            {'code': 'ARTS', 'name': 'Faculty of Arts'},
            {'code': 'COMM', 'name': 'Faculty of Commerce'},
            {'code': 'ENGG', 'name': 'Zakir Husain College of Engineering & Technology'},
            {'code': 'INTL', 'name': 'Faculty of International Studies'},
            {'code': 'LAW', 'name': 'Faculty of Law'},
            {'code': 'LIFE', 'name': 'Faculty of Life Sciences'},
            {'code': 'MGMT', 'name': 'Faculty of Management Studies & Research'},
            {'code': 'MED', 'name': 'Jawaharlal Nehru Medical College'},
            {'code': 'SCI', 'name': 'Faculty of Science'},
            {'code': 'SOC', 'name': 'Faculty of Social Sciences'},
            {'code': 'THEO', 'name': 'Faculty of Theology'},
            {'code': 'UNANI', 'name': 'Ajmal Khan Tibbiya College'},
        ]

        for building_data in academic_buildings:
            building, created = Building.objects.get_or_create(
                campus=campus,
                code=building_data['code'],
                defaults={'name': building_data['name']}
            )
            if created:
                self.stdout.write(f'  ✓ Created academic building: {building.name}')
                
                # Create floors for academic buildings
                for floor_num in range(0, 4):  # Ground floor + 3 floors
                    floor_label = 'Ground Floor' if floor_num == 0 else f'Floor {floor_num}'
                    floor, created = Floor.objects.get_or_create(
                        building=building,
                        number=floor_num,
                        defaults={'label': floor_label}
                    )
                    if created:
                        self.stdout.write(f'    ✓ Created floor: {floor_label}')

                        # Create rooms/departments
                        rooms_per_floor = 8
                        for room_num in range(1, rooms_per_floor + 1):
                            room_number = f'{floor_num}0{room_num}' if floor_num > 0 else f'G{room_num:02d}'
                            room, created = Room.objects.get_or_create(
                                floor=floor,
                                number=room_number,
                                defaults={
                                    'name': f'{building_data["name"]} - Room {room_number}',
                                    'qr_code_token': f'QR-{building_data["code"]}-{room_number}'
                                }
                            )
                            if created:
                                self.stdout.write(f'      ✓ Created room: {room.number}')
            else:
                self.stdout.write(f'  ⟳ Academic building already exists: {building.name}')

        # Setup AMU Departments based on the 13 faculties
        departments_data = [
            {
                'code': 'AGRI', 'name': 'Agricultural Sciences', 
                'categories': [
                    {'name': 'Agricultural Infrastructure', 'sla': 48},
                    {'name': 'Farm Equipment', 'sla': 24},
                    {'name': 'Irrigation Systems', 'sla': 12},
                ]
            },
            {
                'code': 'ARTS', 'name': 'Arts & Humanities',
                'categories': [
                    {'name': 'Arts Classroom Furniture', 'sla': 24},
                    {'name': 'Arts Audio-Visual Equipment', 'sla': 8},
                    {'name': 'Arts Departmental Office', 'sla': 48},
                ]
            },
            {
                'code': 'COMM', 'name': 'Commerce',
                'categories': [
                    {'name': 'Commerce Computer Lab Equipment', 'sla': 8},
                    {'name': 'Commerce Classroom Maintenance', 'sla': 24},
                    {'name': 'Commerce Office Equipment', 'sla': 48},
                ]
            },
            {
                'code': 'ENGG', 'name': 'Engineering & Technology',
                'categories': [
                    {'name': 'Engineering Laboratory Equipment', 'sla': 4},
                    {'name': 'Engineering Workshop Machinery', 'sla': 8},
                    {'name': 'Engineering Computer Systems', 'sla': 4},
                    {'name': 'Engineering Electrical Systems', 'sla': 2},
                ]
            },
            {
                'code': 'INTL', 'name': 'International Studies',
                'categories': [
                    {'name': 'International Language Lab Equipment', 'sla': 8},
                    {'name': 'International Office Maintenance', 'sla': 48},
                ]
            },
            {
                'code': 'LAW', 'name': 'Law',
                'categories': [
                    {'name': 'Law Library Resources', 'sla': 24},
                    {'name': 'Law Classroom Maintenance', 'sla': 24},
                    {'name': 'Law Computer Lab', 'sla': 8},
                ]
            },
            {
                'code': 'LIFE', 'name': 'Life Sciences',
                'categories': [
                    {'name': 'Life Sciences Laboratory Equipment', 'sla': 4},
                    {'name': 'Life Sciences Chemical Safety', 'sla': 2},
                    {'name': 'Life Sciences Microscope Maintenance', 'sla': 8},
                ]
            },
            {
                'code': 'MGMT', 'name': 'Management Studies',
                'categories': [
                    {'name': 'Management Computer Lab', 'sla': 8},
                    {'name': 'Management Projector Equipment', 'sla': 4},
                    {'name': 'Management Office Maintenance', 'sla': 48},
                ]
            },
            {
                'code': 'MED', 'name': 'Medical College (JNMC)',
                'categories': [
                    {'name': 'JNMC Medical Equipment', 'sla': 1},
                    {'name': 'JNMC Hospital Infrastructure', 'sla': 2},
                    {'name': 'JNMC Laboratory Equipment', 'sla': 2},
                ]
            },
            {
                'code': 'SCI', 'name': 'Science',
                'categories': [
                    {'name': 'Science Laboratory Equipment', 'sla': 4},
                    {'name': 'Science Chemical Safety', 'sla': 2},
                    {'name': 'Science Computer Systems', 'sla': 4},
                ]
            },
            {
                'code': 'SOC', 'name': 'Social Sciences',
                'categories': [
                    {'name': 'Social Classroom Maintenance', 'sla': 24},
                    {'name': 'Social Computer Lab', 'sla': 8},
                    {'name': 'Social Office Equipment', 'sla': 48},
                ]
            },
            {
                'code': 'THEO', 'name': 'Theology',
                'categories': [
                    {'name': 'Theology Classroom Maintenance', 'sla': 24},
                    {'name': 'Theology Library Resources', 'sla': 48},
                ]
            },
            {
                'code': 'UNANI', 'name': 'Unani Medicine',
                'categories': [
                    {'name': 'Unani Medical Equipment', 'sla': 2},
                    {'name': 'Unani Herbal Garden Maintenance', 'sla': 48},
                    {'name': 'Unani Laboratory Equipment', 'sla': 4},
                ]
            },
            # Central Services
            {
                'code': 'ESTATE', 'name': 'Estate Office',
                'categories': [
                    {'name': 'Estate Civil Works', 'sla': 48},
                    {'name': 'Estate Electrical Maintenance', 'sla': 4},
                    {'name': 'Estate Plumbing', 'sla': 6},
                    {'name': 'Estate Carpentry', 'sla': 24},
                ]
            },
            {
                'code': 'SECURITY', 'name': 'Campus Security',
                'categories': [
                    {'name': 'Campus Security', 'sla': 1},
                    {'name': 'Gate Maintenance', 'sla': 12},
                ]
            },
            {
                'code': 'HOSTEL', 'name': 'Hostel Maintenance',
                'categories': [
                    {'name': 'Hostel Room Maintenance', 'sla': 24},
                    {'name': 'Hostel Common Area Maintenance', 'sla': 12},
                    {'name': 'Hostel Sanitation', 'sla': 6},
                    {'name': 'Hostel Water Supply', 'sla': 2},
                ]
            },
            {
                'code': 'IT', 'name': 'IT Services',
                'categories': [
                    {'name': 'IT Network & Connectivity', 'sla': 4},
                    {'name': 'IT Software & Portals', 'sla': 8},
                    {'name': 'IT Server Maintenance', 'sla': 2},
                ]
            },
            {
                'code': 'LIB', 'name': 'Central Library',
                'categories': [
                    {'name': 'Central Library Services', 'sla': 24},
                    {'name': 'Central Library Reading Room Maintenance', 'sla': 12},
                ]
            },
        ]

        for dept_data in departments_data:
            department, created = Department.objects.get_or_create(
                code=dept_data['code'],
                defaults={'name': dept_data['name']}
            )
            if created:
                self.stdout.write(f'✓ Created department: {department.name}')
            else:
                self.stdout.write(f'⟳ Department already exists: {department.name}')

            for cat_data in dept_data['categories']:
                category, created = ComplaintCategory.objects.get_or_create(
                    name=cat_data['name'],
                    department=department,
                    defaults={
                        'description': f'Maintenance issues related to {cat_data["name"]} at {dept_data["name"]}',
                        'default_sla_hours': cat_data['sla']
                    }
                )
                if created:
                    self.stdout.write(f'  ✓ Created category: {category.name} (SLA: {cat_data["sla"]}h)')
                else:
                    self.stdout.write(f'  ⟳ Category already exists: {category.name}')

        self.stdout.write(self.style.SUCCESS('✓ AMU campus setup complete!'))
        self.stdout.write(f'  Campus: {campus.name}')
        self.stdout.write(f'  Buildings: {campus.buildings.count()}')
        self.stdout.write(f'  Departments: {Department.objects.count()}')
        self.stdout.write(f'  Categories: {ComplaintCategory.objects.count()}')