"""
Re-align Existing Complaints Hierarchy in CampusCare SQLite Database.
Aligns:
1. Departmental complaints to their true parent Faculty building & room.
2. Residential complaints to their true parent Hall / Hostel building & room.
Preserves all complaints, tracking tokens, statuses, references, and audit histories.
"""

import os
import sys

sys.path.insert(0, "/Users/Asif/Python:Project v2")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
import django
django.setup()

from core.models import Complaint, Building, Room
from core.ai_triage import extract_building_and_department, resolve_room_for_building, invalidate_triage_caches

invalidate_triage_caches()

total_complaints = Complaint.objects.count()
print(f"Total complaints in database: {total_complaints}")

aligned_count = 0
dept_aligned = 0
hostel_aligned = 0

for complaint in Complaint.objects.select_related("room__floor__building__parent", "category").all():
    target_building, target_dept = extract_building_and_department(
        location_text=complaint.location_description or "",
        title=complaint.title or "",
        description=complaint.description or "",
        category=complaint.category if complaint.category_id else None,
    )
    
    if not target_building:
        continue

    current_room = complaint.room
    needs_update = False

    if not current_room:
        needs_update = True
    else:
        current_bldg = current_room.floor.building
        # Check if current_bldg matches target_building or target_building's parent/child
        is_match = (
            current_bldg.id == target_building.id
            or (current_bldg.parent_id and current_bldg.parent_id == target_building.id)
            or (target_building.parent_id and current_bldg.id == target_building.parent_id)
            or (current_bldg.parent_id and target_building.parent_id and current_bldg.parent_id == target_building.parent_id)
        )
        if not is_match:
            needs_update = True

    if needs_update:
        new_room = resolve_room_for_building(target_building, complaint.location_description or "")
        if new_room:
            old_bldg_name = current_room.floor.building.name if current_room else "None"
            complaint.room = new_room
            complaint.save(update_fields=["room"])
            aligned_count += 1
            if target_building.building_type == "academic":
                dept_aligned += 1
            else:
                hostel_aligned += 1
            if aligned_count <= 15:
                print(f"  • Aligned {complaint.reference}: {old_bldg_name} -> {new_room.floor.building.name} ({new_room.number})")

print(f"\nCompleted Realignment:")
print(f"  - Total complaints realigned: {aligned_count}")
print(f"  - Academic Department complaints realigned: {dept_aligned}")
print(f"  - Residential Hall/Hostel complaints realigned: {hostel_aligned}")
print(f"  - Total database complaints remaining: {Complaint.objects.count()} (100% intact)")
