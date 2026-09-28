# Spatial location binding and AI routing for incoming CampusCare complaints.
import re
from typing import Optional, Tuple
from django.db.models import Q
from .faculty_directory import detect_department, detect_faculty
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
    "sir shah sulaiman hall": "SSH",
    "sir shah sulaiman": "SSH",
    "sulaiman hall": "SSH",
    "sulaiman": "SSH",
    "ssh": "SSH",
    "viqar-ul-mulk": "VMH",
    "viqarul mulk": "VMH",
    "vm hall": "VMH",
    "v.m. hall": "VMH",
    "mohsin-ul-mulk": "MMH",
    "mohsinul mulk": "MMH",
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

_BUILDINGS_CACHE = None
_DEPTS_CACHE = None


def get_cached_buildings():
    global _BUILDINGS_CACHE
    if _BUILDINGS_CACHE is None:
        _BUILDINGS_CACHE = list(Building.objects.select_related("department", "parent").filter(is_active=True))
    return _BUILDINGS_CACHE


def get_cached_departments():
    global _DEPTS_CACHE
    if _DEPTS_CACHE is None:
        _DEPTS_CACHE = list(Department.objects.filter(is_active=True))
    return _DEPTS_CACHE


def invalidate_triage_caches():
    global _BUILDINGS_CACHE, _DEPTS_CACHE
    _BUILDINGS_CACHE = None
    _DEPTS_CACHE = None


def extract_building_and_department(
    location_text: str,
    title: str = "",
    description: str = "",
    category: Optional[ComplaintCategory] = None,
) -> Tuple[Optional[Building], Optional[Department]]:
    combined_raw = " ".join([location_text or "", title or "", description or ""])
    combined = combined_raw.lower()
    matched_building: Optional[Building] = None
    matched_dept: Optional[Department] = None

    buildings = get_cached_buildings()
    depts = get_cached_departments()

    # 1. PRIORITY A: Academic Teaching Department -> Bind to its Parent Faculty Building
    dept_info = detect_department(combined_raw)
    if dept_info:
        for d in depts:
            if d.code.upper() == dept_info["code"].upper():
                matched_dept = d
                break
        fac_code = dept_info["faculty"].upper()
        for b in buildings:
            if b.building_type == "academic" and b.code.upper() == fac_code:
                matched_building = b
                break

    # 2. PRIORITY B: Check if a Residential Hall is explicitly named
    mentioned_hall = None
    for b in buildings:
        if b.building_type == "hall":
            h_name_low = b.name.lower()
            code_low = b.code.lower()
            if h_name_low in combined or re.search(r"\b" + re.escape(code_low) + r"\b", combined):
                mentioned_hall = b
                break

    # Constituent Hostel -> If a hall is mentioned, strictly match that hall's hostels
    if not matched_building:
        for b in buildings:
            if b.building_type == "hostel" and b.parent_id:
                h_name_low = b.name.lower()
                short_low = b.short_name.lower() if b.short_name else ""
                if mentioned_hall:
                    if b.parent_id == mentioned_hall.id and (h_name_low in combined or (short_low and len(short_low) >= 4 and short_low in combined)):
                        matched_building = b
                        break
                else:
                    if h_name_low in combined or (short_low and len(short_low) >= 5 and short_low in combined):
                        matched_building = b
                        break

    # If hall was mentioned and no constituent hostel matched, use the hall itself
    if not matched_building and mentioned_hall:
        matched_building = mentioned_hall

    # 3. PRIORITY C: Building Aliases (Residential Halls, Faculties, Libraries)
    if not matched_building:
        for phrase, b_code in sorted(BUILDING_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
            if phrase in combined:
                for b in buildings:
                    if b.code.upper() == b_code.upper():
                        matched_building = b
                        break
                if matched_building:
                    break

    # 4. PRIORITY D: General Building Full Name, Short Name, or Code Match
    if not matched_building:
        for b in buildings:
            b_name_low = b.name.lower()
            b_code_low = b.code.lower()
            short_low = b.short_name.lower() if b.short_name else ""
            if (
                (short_low and len(short_low) >= 4 and short_low in combined)
                or b_name_low in combined
                or (b_code_low in combined and re.search(r"\b" + re.escape(b_code_low) + r"\b", combined))
            ):
                matched_building = b
                break

    # Associate department from matched building if department not already found
    if matched_building and not matched_dept and matched_building.department_id:
        matched_dept = matched_building.department

    # Check for department text if still not found
    if not matched_dept:
        for d in depts:
            d_code_low = d.code.lower()
            if d.name.lower() in combined or (d_code_low in combined and re.search(r"\b" + re.escape(d_code_low) + r"\b", combined)):
                matched_dept = d
                break

    # Fallback to category department if still unassigned
    if not matched_dept and category and category.department_id:
        matched_dept = category.department

    # If building still unmatched, check if department corresponds to an academic building
    if not matched_building and matched_dept:
        for b in buildings:
            if b.code.upper() == matched_dept.code.upper() or (b.department_id and b.department_id == matched_dept.id):
                matched_building = b
                break

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
            if token.isdigit():
                padded_room = rooms_qs.filter(number__iexact=f"{int(token):03d}").first()
                if padded_room:
                    return padded_room
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

    # Extract verified building and department from text
    building, dept = extract_building_and_department(
        location_text=complaint.location_description or "",
        title=complaint.title or "",
        description=complaint.description or "",
        category=complaint.category if complaint.category_id else None,
    )

    # If building identified, verify and ensure room is within this building or its hierarchy
    if building:
        current_room = complaint.room if complaint.room_id else None
        needs_rebind = True
        if current_room:
            room_bldg = current_room.floor.building
            # Valid if room belongs to building or building's parent or building is parent of room
            if (
                room_bldg.id == building.id
                or (room_bldg.parent_id and room_bldg.parent_id == building.id)
                or (building.parent_id and room_bldg.id == building.parent_id)
            ):
                needs_rebind = False

        if needs_rebind:
            room = resolve_room_for_building(building, complaint.location_description or "")
            if room:
                complaint.room = room

        if not complaint.location_description and complaint.room:
            complaint.location_description = f"{building.name} - {complaint.room.number}"

    elif not complaint.room_id and not complaint.location_description:
        fallback_building = Building.objects.filter(is_active=True).order_by("id").first()
        if fallback_building:
            complaint.room = resolve_room_for_building(fallback_building, "")
            complaint.location_description = str(complaint.room)

    complaint._spatial_bound = True
    return complaint

