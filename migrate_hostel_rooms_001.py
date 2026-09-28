"""
Migration Script: Hostel Room Numbering from 001 (At least 150 rooms per hostel).
1. Numbers start from 001 (001, 002, 003, ... 150).
2. Generates 150 rooms per constituent hostel (and residential hall).
3. Auto-migrates existing complaints from Room 101 -> 001, 102 -> 002, etc.
4. Cleans up old room instances to eliminate redundancy.
5. Recreates updated 'AMU Halls and Hostels - Sheet1.csv' at the same location.
"""
import os
import csv
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
django.setup()

from django.db import transaction
from django.db.models import Q
from core.models import Building, Floor, Room, Complaint

def migrate_rooms():
    print("=" * 80)
    print("  CAMPUSCARE: RESIDENTIAL HOSTEL ROOM NUMBERING MIGRATION (001 TO 150)")
    print("=" * 80)

    # 1. Fetch residential buildings
    halls = list(Building.objects.filter(is_active=True, building_type="hall", parent__isnull=True).order_by("name"))
    hostels = list(Building.objects.filter(is_active=True, parent__isnull=False).select_related("parent").order_by("parent__name", "name"))

    print(f"Targeting {len(halls)} Residential Halls and {len(hostels)} Constituent Hostels.")

    all_res_buildings = hostels + halls
    rooms_to_create = []

    print("\nPhase 1: Ensuring 150 rooms (001 to 150) for every residential hostel and hall...")
    
    with transaction.atomic():
        for b_idx, bldg in enumerate(all_res_buildings, start=1):
            # Ensure Floors 1, 2, 3 exist
            f1, _ = Floor.objects.get_or_create(building=bldg, number=1, defaults={"label": "Floor 1"})
            f2, _ = Floor.objects.get_or_create(building=bldg, number=2, defaults={"label": "Floor 2"})
            f3, _ = Floor.objects.get_or_create(building=bldg, number=3, defaults={"label": "Floor 3"})
            
            floors = [f1, f2, f3]
            
            for i in range(1, 151):
                num_str = f"{i:03d}"  # 001, 002, ... 150
                # Assign floor: 1-50 -> Floor 1, 51-100 -> Floor 2, 101-150 -> Floor 3
                assigned_floor = floors[(i - 1) // 50]
                
                # Check if already exists
                existing = Room.objects.filter(floor__building=bldg, number=num_str).first()
                if not existing:
                    room_name = f"{bldg.short_name or bldg.name} · Room {num_str}"
                    qr_token = f"QR-{bldg.code}-{num_str}"
                    rooms_to_create.append(
                        Room(
                            floor=assigned_floor,
                            number=num_str,
                            name=room_name,
                            qr_code_token=qr_token,
                            is_active=True,
                        )
                    )

        if rooms_to_create:
            print(f"  Creating {len(rooms_to_create)} new rooms via bulk_create...")
            Room.objects.bulk_create(rooms_to_create, batch_size=1000)
            print(f"  ✓ Successfully created {len(rooms_to_create)} rooms.")

    # 2. Phase 2: Auto-migrate existing complaints
    print("\nPhase 2: Auto-migrating existing complaints from old room numbers (101 -> 001, etc.)...")
    res_complaints = Complaint.objects.filter(
        room__floor__building__building_type__in=["hall", "hostel"]
    ).select_related("room", "room__floor", "room__floor__building")

    migrated_count = 0
    mapping = {
        "101": "001",
        "102": "002",
        "103": "003",
        "104": "004",
        "105": "005",
        "106": "006",
        "107": "007",
        "108": "008",
        "109": "009",
        "110": "010",
        "201": "051",
        "202": "052",
        "203": "053",
        "204": "054",
        "205": "055",
        "206": "056",
        "207": "057",
        "208": "058",
        "209": "059",
        "210": "060",
        "301": "101",
        "302": "102",
        "303": "103",
        "304": "104",
        "305": "105",
        "306": "106",
        "307": "107",
        "308": "108",
        "309": "109",
        "310": "110",
    }

    with transaction.atomic():
        for comp in res_complaints:
            old_num = comp.room.number
            bldg = comp.room.floor.building
            
            if old_num in mapping:
                target_num = mapping[old_num]
                new_room = Room.objects.filter(floor__building=bldg, number=target_num).first()
                if not new_room and bldg.parent:
                    new_room = Room.objects.filter(floor__building=bldg.parent, number=target_num).first()
                
                if new_room and new_room.id != comp.room_id:
                    comp.room = new_room
                    # Update text references
                    if comp.location_description:
                        comp.location_description = comp.location_description.replace(f"Room {old_num}", f"Room {target_num}")
                    if comp.title:
                        comp.title = comp.title.replace(f"Room {old_num}", f"Room {target_num}")
                    if comp.description:
                        comp.description = comp.description.replace(f"Room {old_num}", f"Room {target_num}")
                    
                    comp.save(update_fields=["room", "location_description", "title", "description", "updated_at"])
                    migrated_count += 1

    print(f"  ✓ Successfully migrated {migrated_count} complaints to new room numbers (001, etc.).")

    # 3. Phase 3: Clean up redundant old room instances
    print("\nPhase 3: Cleaning up old residential room records not in 001-150...")
    all_valid_numbers = {f"{i:03d}" for i in range(1, 151)}
    
    old_res_rooms = Room.objects.filter(
        floor__building__building_type__in=["hall", "hostel"]
    ).exclude(number__in=all_valid_numbers)
    
    # Check if any complaints still reference old rooms
    active_refs = old_res_rooms.filter(complaints__isnull=False).count()
    if active_refs > 0:
        print(f"  ⚠️ Warning: {active_refs} complaints still reference old rooms; will re-assign to 001 first.")
        for comp in Complaint.objects.filter(room__in=old_res_rooms):
            bldg = comp.room.floor.building
            room_001 = Room.objects.filter(floor__building=bldg, number="001").first()
            if room_001:
                comp.room = room_001
                comp.save(update_fields=["room", "updated_at"])
    
    deleted_rooms_count, _ = old_res_rooms.delete()
    print(f"  ✓ Purged {deleted_rooms_count} redundant old room instances from residential buildings.")

    # 4. Phase 4: Recreate the referential CSV file at the same location
    csv_file_path = "AMU Halls and Hostels - Sheet1.csv"
    print(f"\nPhase 4: Recreating referential CSV file: {csv_file_path}...")
    
    # Remove existing file to prevent any conflict/redundancy
    if os.path.exists(csv_file_path):
        os.remove(csv_file_path)
        print(f"  ✓ Deleted previous {csv_file_path} to remove redundancy.")

    fieldnames = [
        "Category",
        "Hall Name",
        "Constituent Hostel / Block",
        "Block / Wing Detail",
        "Room Numbering Range",
        "Total Rooms",
        "Capacity / Room Details"
    ]

    rows = []
    for h in hostels:
        hall_name = h.parent.name if h.parent else "Residential Hall"
        hostel_name = h.short_name or h.name
        gender = h.gender or ("Girls" if "Girls" in h.name or "Begum" in hall_name or "Abdullah" in hall_name or "Fatima" in hall_name or "Sarojini" in hall_name else "Boys")
        wing = h.wing_detail or "Residential Block"
        cap = h.capacity_detail or "150 rooms; Accommodates resident students"
        
        rows.append({
            "Category": gender,
            "Hall Name": hall_name,
            "Constituent Hostel / Block": hostel_name,
            "Block / Wing Detail": wing,
            "Room Numbering Range": "Rooms 001 to 150",
            "Total Rooms": "150",
            "Capacity / Room Details": f"150 rooms (Numbered 001 to 150); {cap}"
        })

    with open(csv_file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  ✓ Recreated updated {csv_file_path} with {len(rows)} constituent hostels (each 150 rooms from 001 to 150).")

    # 5. Verification
    print("\n" + "=" * 80)
    print("  VERIFICATION AUDIT:")
    print("=" * 80)
    res_rooms_now = Room.objects.filter(floor__building__building_type__in=["hall", "hostel"])
    print(f"  • Total Residential Rooms Now     : {res_rooms_now.count()}")
    print(f"  • Room 001 Count Across Buildings : {res_rooms_now.filter(number='001').count()}")
    print(f"  • Room 150 Count Across Buildings : {res_rooms_now.filter(number='150').count()}")
    print(f"  • Room Numbers Sample             : {list(res_rooms_now.values_list('number', flat=True).distinct()[:15])}")
    print(f"  • Complaints Linked to Room 001   : {Complaint.objects.filter(room__number='001').count()}")
    print(f"  • Complaints Linked to Room 101   : {Complaint.objects.filter(room__number='101').count()} (Now represents 101st room in 001-150)")
    print("=" * 80)

if __name__ == "__main__":
    migrate_rooms()
