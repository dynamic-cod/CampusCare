# Spatial location binding and AI routing for incoming CampusCare complaints.
import re
from typing import Optional, Tuple
from django.db.models import Q
from .models import Building, Complaint, ComplaintCategory, Department, Floor, Room

BUILDING_ALIASES = {
    "sir syed hall (north)": "SSN",
    "sir syed hall north": "SSN",
    "sir syed north": "SSN",
    "ss hall north": "SSN",
    "ss north": "SSN",
    "ssn": "SSN",
    "sir syed hall (south)": "SSS",
    "sir syed hall south": "SSS",
    "sir syed south": "SSS",
    "ss hall south": "SSS",
    "ss south": "SSS",
    "sss": "SSS",
    "aftab hall": "AFT",
    "aftab": "AFT",
    "abdullah hall": "ABH",
    "abdullah": "ABH",
    "sulaiman hall": "SUL",
    "sulaiman": "SUL",
    "viqar-ul-mulk": "VMH",
    "viqarul mulk": "VMH",
    "vm hall": "VMH",
    "v.m. hall": "VMH",
    "mohsin-ul-mulk": "MMH",
    "mm hall": "MMH",
    "m.m. hall": "MMH",
    "ross masood": "RMH",
    "rm hall": "RMH",
    "r.m. hall": "RMH",
    "hadi hasan": "HHH",
    "nadeem tarin": "NTH",
    "sir ziauddin": "SZH",
    "sz hall": "SZH",
    "bibi fatima": "BFH",
    "begum sultan jahan": "BSJ",
    "begum azeezun nisa": "BAN",
    "sarojini naidu": "SNH",
    "indira gandhi": "IGH",
    "ambedkar hall": "BRA",
    "allama iqbal": "AIB",
    "nrsc": "NRSC",
    "non-resident students": "NRSC",
    "tibbiya": "UNANI",
    "zakir husain": "ENGG",
    "zhcet": "ENGG",
    "engineering college": "ENGG",
    "maulana azad library": "LIB",
    "central library": "LIB",
}

def extract_building_and_department(
    location_text: str,
    title: str = "",
    description: str = "",
    category: Optional[ComplaintCategory] = None,
) -> Tuple[Optional[Building], Optional[Department]]:
    combined_raw = " ".join([location_text or "", title or "", description or ""])
    combined = combined_raw.lower()
    matched_building: Optional[Building] = None
    matched_dept: Optional[Department] = category.department if (category and category.department_id) else None

    for phrase, b_code in sorted(BUILDING_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if phrase in combined:
            matched_building = Building.objects.select_related("department").filter(code__iexact=b_code).first()
            if matched_building:
                break

    if not matched_building:
        for b in Building.objects.select_related("department", "parent").filter(is_active=True):
            b_name_low = b.name.lower()
            b_code_low = b.code.lower()
            short_low = b.short_name.lower() if b.short_name else ""
            if (
                (short_low and len(short_low) >= 3 and short_low in combined)
                or b_name_low in combined
                or re.search(r"\b" + re.escape(b_code_low) + r"\b", combined)
            ):
                matched_building = b
                break

    if not matched_dept:
        for d in Department.objects.filter(is_active=True):
            if d.name.lower() in combined or re.search(r"\b" + re.escape(d.code.lower()) + r"\b", combined):
                matched_dept = d
                break

    if matched_building and not matched_dept and matched_building.department_id:
        matched_dept = matched_building.department

    if not matched_building and matched_dept:
        matched_building = (
            Building.objects.filter(Q(code__iexact=matched_dept.code) | Q(department=matched_dept))
            .order_by("id")
            .first()
        )
    return matched_building, matched_dept

def resolve_room_for_building(building: Building, location_text: str = "") -> Optional[Room]:
    if not building:
        return None
    rooms_qs = Room.objects.select_related("floor__building").filter(
        Q(floor__building=building) | Q(floor__building__parent=building)
    )
    if location_text:
        tokens = re.findall(r"\b([A-Za-z]?\d{1,4}[A-Za-z]?)\b", location_text)
        for token in tokens:
            exact_room = rooms_qs.filter(Q(number__iexact=token) | Q(name__icontains=token)).first()
            if exact_room:
                return exact_room
    first_room = rooms_qs.first()
    if first_room:
        return first_room
    floor, _ = Floor.objects.get_or_create(building=building, number=0, defaults={"label": "Ground Floor"})
    room, _ = Room.objects.get_or_create(
        floor=floor,
        number="GEN-01",
        defaults={"name": f"{building.name} General Area", "is_active": True},
    )
    return room

def bind_complaint_spatial_origin(complaint: Complaint) -> Complaint:
    if complaint.category_id and complaint.category and not complaint.category.department_id:
        default_dept = Department.objects.filter(is_active=True).first()
        if default_dept:
            complaint.category.department = default_dept
            complaint.category.save(update_fields=["department", "updated_at"])

    if complaint.room_id and complaint.room:
        building = complaint.room.floor.building
        if not building.department_id and complaint.category_id and complaint.category.department_id:
            if building.code.upper() == complaint.category.department.code.upper():
                building.department = complaint.category.department
                building.save(update_fields=["department", "updated_at"])
        if not complaint.location_description:
            complaint.location_description = str(complaint.room)
        return complaint

    building, dept = extract_building_and_department(
        location_text=complaint.location_description or "",
        title=complaint.title or "",
        description=complaint.description or "",
        category=complaint.category if complaint.category_id else None,
    )
    if not building:
        building = Building.objects.filter(is_active=True).order_by("id").first()
    if building:
        room = resolve_room_for_building(building, complaint.location_description or "")
        if room:
            complaint.room = room
            if not complaint.location_description:
                complaint.location_description = f"{building.name} - {room.number}"
    return complaint
