#!/usr/bin/env python3
"""
Idempotent Ingestion & Synchronization Script for University Departments & Residential Halls
CampusCare Multi-Tenant Directory Sync

Rules:
- Non-destructive: No flush, no drop, preserves existing IDs, FKs, tickets, and user accounts.
- Preserves legacy maintenance codes: ELEC, PLUMB, CIVIL, ITINF, CLEAN.
- Idempotent execution using update_or_create and get_or_create exclusively.
- Provisions/refreshes HOD sub-admin accounts (hod_<dept_code>) with password 'CampusAdmin@2026'.
- Verifies complaint scoping and foreign key integrity.
"""

import csv
import os
import re
import sys
from pathlib import Path

# Setup Django environment if run standalone
if __name__ == "__main__" or "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
    import django
    django.setup()

from django.contrib.auth import get_user_model
from django.db import models, transaction
from core.models import Building, Campus, Complaint, ComplaintCategory, Department, UserProfile

DEFAULT_ADMIN_PASSWORD = "CampusAdmin@2026"

# Core legacy maintenance trades that MUST NEVER be overwritten or removed
PROTECTED_TRADE_CODES = {"ELEC", "PLUMB", "CIVIL", "ITINF", "CLEAN"}

# Canonical structured directory of AMU teaching departments:
# Mapping of official clean name -> (unique code <= 12 chars, parent faculty/building code)
STRUCTURED_TEACHING_DEPARTMENTS = [
    # Faculty of Agricultural Sciences (AGRI)
    {"name": "Agricultural Eco. & Business Mngt.", "code": "AGRI_ECON", "faculty": "AGRI", "building": "AGRI"},
    {"name": "Agricultural Microbiology", "code": "AGRI_MICRO", "faculty": "AGRI", "building": "AGRI"},
    {"name": "Home Sciences", "code": "AGRI_HOMESC", "faculty": "AGRI", "building": "AGRI"},
    {"name": "Plant Protection", "code": "AGRI_PLANT", "faculty": "AGRI", "building": "AGRI"},
    {"name": "Post Harvest Engineering And Technology", "code": "AGRI_POSTHV", "faculty": "AGRI", "building": "AGRI"},

    # Faculty of Arts (ARTS)
    {"name": "Arabic", "code": "ARTS_ARABIC", "faculty": "ARTS", "building": "ARTS"},
    {"name": "English", "code": "ARTS_ENGL", "faculty": "ARTS", "building": "ARTS"},
    {"name": "Fine Arts", "code": "ARTS_FINE", "faculty": "ARTS", "building": "ARTS"},
    {"name": "Foreign Languages", "code": "ARTS_FORLANG", "faculty": "ARTS", "building": "ARTS"},
    {"name": "Hindi", "code": "ARTS_HINDI", "faculty": "ARTS", "building": "ARTS"},
    {"name": "Linguistics", "code": "ARTS_LING", "faculty": "ARTS", "building": "ARTS"},
    {"name": "Modern Indian Languages", "code": "ARTS_MIL", "faculty": "ARTS", "building": "ARTS"},
    {"name": "Persian", "code": "ARTS_PERSIAN", "faculty": "ARTS", "building": "ARTS"},
    {"name": "Philosophy", "code": "ARTS_PHIL", "faculty": "ARTS", "building": "ARTS"},
    {"name": "Sanskrit", "code": "ARTS_SANSKR", "faculty": "ARTS", "building": "ARTS"},
    {"name": "Urdu", "code": "ARTS_URDU", "faculty": "ARTS", "building": "ARTS"},

    # Faculty of Commerce (COMM) - maps cleanly to existing COMM department
    {"name": "Commerce", "code": "COMM", "faculty": "COMM", "building": "COMM"},

    # Zakir Husain College of Engineering & Technology (ENGG)
    {"name": "Applied Chemistry", "code": "ENGG_APPCHM", "faculty": "ENGG", "building": "ENGG"},
    {"name": "Applied Mathematics", "code": "ENGG_APPMTH", "faculty": "ENGG", "building": "ENGG"},
    {"name": "Applied Physics", "code": "ENGG_APPPHY", "faculty": "ENGG", "building": "ENGG"},
    {"name": "Architecture", "code": "ENGG_ARCH", "faculty": "ENGG", "building": "ENGG"},
    {"name": "Chemical Engineering", "code": "ENGG_CHEM", "faculty": "ENGG", "building": "ENGG"},
    {"name": "Civil Engineering", "code": "ENGG_CIVIL", "faculty": "ENGG", "building": "ENGG"},
    {"name": "Computer Engineering", "code": "ENGG_COMP", "faculty": "ENGG", "building": "ENGG"},
    {"name": "Electrical Engineering", "code": "ENGG_ELEC", "faculty": "ENGG", "building": "ENGG"},
    {"name": "Electronics Engineering", "code": "ENGG_ELX", "faculty": "ENGG", "building": "ENGG"},
    {"name": "Mechanical Engineering", "code": "ENGG_MECH", "faculty": "ENGG", "building": "ENGG"},
    {"name": "Petroleum Studies", "code": "ENGG_PETRO", "faculty": "ENGG", "building": "ENGG"},

    # Faculty of International Studies (INTL)
    {"name": "South African & Brazilian Studies", "code": "INTL_SABS", "faculty": "INTL", "building": "INTL"},
    {"name": "West Asian Studies And North African Studies", "code": "INTL_WASNAS", "faculty": "INTL", "building": "INTL"},

    # Faculty of Law (LAW) - maps cleanly to existing LAW department
    {"name": "Law", "code": "LAW", "faculty": "LAW", "building": "LAW"},
    {"name": "Law - Malappuram", "code": "LAW_MALAP", "faculty": "LAW", "building": "LAW"},
    {"name": "Law - Murshidabad", "code": "LAW_MURSH", "faculty": "LAW", "building": "LAW"},

    # Faculty of Life Sciences (LIFE)
    {"name": "Bio-Chemistry (Life Sciences)", "code": "LIFE_BIOCHM", "faculty": "LIFE", "building": "LIFE"},
    {"name": "Botany", "code": "LIFE_BOTANY", "faculty": "LIFE", "building": "LIFE"},
    {"name": "Interdisciplinary Biotechnology Unit", "code": "LIFE_IBU", "faculty": "LIFE", "building": "LIFE"},
    {"name": "Wildlife Sciences", "code": "LIFE_WILDLF", "faculty": "LIFE", "building": "LIFE"},
    {"name": "Zoology", "code": "LIFE_ZOOLOGY", "faculty": "LIFE", "building": "LIFE"},

    # Faculty of Management Studies & Research (MGMT)
    {"name": "Business Administration", "code": "MGMT_BA", "faculty": "MGMT", "building": "MGMT"},
    {"name": "Business Administration - Malappuram", "code": "MGMT_BAMAL", "faculty": "MGMT", "building": "MGMT"},
    {"name": "Business Administration - Murshidabad", "code": "MGMT_BAMUR", "faculty": "MGMT", "building": "MGMT"},

    # Faculty of Science (SCI)
    {"name": "Physics", "code": "DEPT_PHYS", "faculty": "SCI", "building": "SCI"},
    {"name": "Chemistry", "code": "DEPT_CHEM", "faculty": "SCI", "building": "SCI"},
    {"name": "Computer Science", "code": "SCI_CS", "faculty": "SCI", "building": "SCI"},
    {"name": "Geography", "code": "SCI_GEOG", "faculty": "SCI", "building": "SCI"},
    {"name": "Geology", "code": "SCI_GEOL", "faculty": "SCI", "building": "SCI"},
    {"name": "Industrial Chemistry", "code": "SCI_INDCHM", "faculty": "SCI", "building": "SCI"},
    {"name": "Interdisciplinary Department Of Remote Sensing And GIS Applications", "code": "SCI_RSGIS", "faculty": "SCI", "building": "SCI"},
    {"name": "Mathematics", "code": "SCI_MATH", "faculty": "SCI", "building": "SCI"},
    {"name": "Statistics And Operations Research", "code": "SCI_STATS", "faculty": "SCI", "building": "SCI"},

    # Faculty of Social Sciences (SOC)
    {"name": "Advanced Centre For Women's Studies", "code": "SOC_CWS", "faculty": "SOC", "building": "SOC"},
    {"name": "Economics", "code": "SOC_ECON", "faculty": "SOC", "building": "SOC"},
    {"name": "Education", "code": "SOC_EDU", "faculty": "SOC", "building": "SOC"},
    {"name": "Education - Malappuram", "code": "SOC_EDUMAL", "faculty": "SOC", "building": "SOC"},
    {"name": "Education - Murshidabad", "code": "SOC_EDUMUR", "faculty": "SOC", "building": "SOC"},
    {"name": "History", "code": "SOC_HIST", "faculty": "SOC", "building": "SOC"},
    {"name": "Islamic Studies", "code": "SOC_ISLAM", "faculty": "SOC", "building": "SOC"},
    {"name": "Library And Information Science", "code": "SOC_LIS", "faculty": "SOC", "building": "SOC"},
    {"name": "Mass Communication", "code": "SOC_MASSCOMM", "faculty": "SOC", "building": "SOC"},
    {"name": "Museology", "code": "SOC_MUSEOL", "faculty": "SOC", "building": "SOC"},
    {"name": "Physical Education", "code": "SOC_PHYEDU", "faculty": "SOC", "building": "SOC"},
    {"name": "Political Science", "code": "SOC_POLSCI", "faculty": "SOC", "building": "SOC"},
    {"name": "Psychology", "code": "SOC_PSYCH", "faculty": "SOC", "building": "SOC"},
    {"name": "Social Work", "code": "SOC_SOCWORK", "faculty": "SOC", "building": "SOC"},
    {"name": "Sociology", "code": "SOC_SOCIOL", "faculty": "SOC", "building": "SOC"},
    {"name": "Strategic & Security Studies", "code": "SOC_STRAT", "faculty": "SOC", "building": "SOC"},
    {"name": "Women's College", "code": "SOC_WOMENCOL", "faculty": "SOC", "building": "SOC"},

    # Faculty of Theology (THEO)
    {"name": "Shia Theology", "code": "THEO_SHIA", "faculty": "THEO", "building": "THEO"},
    {"name": "Sunni Theology", "code": "THEO_SUNNI", "faculty": "THEO", "building": "THEO"},
    {"name": "K. A. Nizami Centre For Quranic Studies", "code": "THEO_KANQS", "faculty": "THEO", "building": "THEO"},

    # Jawaharlal Nehru Medical College & Dental College (MED)
    {"name": "Anaesthesiology", "code": "MED_ANAESTH", "faculty": "MED", "building": "MED"},
    {"name": "Anatomy", "code": "MED_ANATOMY", "faculty": "MED", "building": "MED"},
    {"name": "Bio-Chemistry (JNMC)", "code": "MED_BIOCHM", "faculty": "MED", "building": "MED"},
    {"name": "Cardiology", "code": "MED_CARDIO", "faculty": "MED", "building": "MED"},
    {"name": "Cardiothoracic Surgery", "code": "MED_CTSURG", "faculty": "MED", "building": "MED"},
    {"name": "Community Medicine", "code": "MED_COMMED", "faculty": "MED", "building": "MED"},
    {"name": "Conservative Dentistry & Endodontics", "code": "MED_DENTCONS", "faculty": "MED", "building": "MED"},
    {"name": "Dermatology", "code": "MED_DERMAT", "faculty": "MED", "building": "MED"},
    {"name": "Forensic Medicine", "code": "MED_FORENS", "faculty": "MED", "building": "MED"},
    {"name": "Medicine", "code": "MED_MEDICIN", "faculty": "MED", "building": "MED"},
    {"name": "Microbiology", "code": "MED_MICRO", "faculty": "MED", "building": "MED"},
    {"name": "Neuro Surgery", "code": "MED_NEUROS", "faculty": "MED", "building": "MED"},
    {"name": "Obstetrics And Gynaecology", "code": "MED_OBSGYN", "faculty": "MED", "building": "MED"},
    {"name": "Ophthalmology", "code": "MED_OPHTHAL", "faculty": "MED", "building": "MED"},
    {"name": "Oral & Maxillofacial Surgery", "code": "MED_OMFS", "faculty": "MED", "building": "MED"},
    {"name": "Oral Medicine And Radiology", "code": "MED_OMRAD", "faculty": "MED", "building": "MED"},
    {"name": "Oral Pathology And Microbiology", "code": "MED_OPATH", "faculty": "MED", "building": "MED"},
    {"name": "Orthodontics And Dentofacial Orthopedics And Dental Anatomy", "code": "MED_ORTHOD", "faculty": "MED", "building": "MED"},
    {"name": "Orthopaedic Surgery", "code": "MED_ORTHOP", "faculty": "MED", "building": "MED"},
    {"name": "OTO-Rhino-Laryngology (E.N.T.)", "code": "MED_ENT", "faculty": "MED", "building": "MED"},
    {"name": "Paediatric Surgery", "code": "MED_PAEDSRG", "faculty": "MED", "building": "MED"},
    {"name": "Paediatrics", "code": "MED_PAEDIAT", "faculty": "MED", "building": "MED"},
    {"name": "Paediatrics & Preventive Dentistry", "code": "MED_PAEDENT", "faculty": "MED", "building": "MED"},
    {"name": "Pathology", "code": "MED_PATHOL", "faculty": "MED", "building": "MED"},
    {"name": "Periodontology", "code": "MED_PERIOD", "faculty": "MED", "building": "MED"},
    {"name": "Pharmacology", "code": "MED_PHARMA", "faculty": "MED", "building": "MED"},
    {"name": "Physiology", "code": "MED_PHYSIOL", "faculty": "MED", "building": "MED"},
    {"name": "Plastic Surgery", "code": "MED_PLASTSRG", "faculty": "MED", "building": "MED"},
    {"name": "Prosthodontics/Dental Material", "code": "MED_PROSTH", "faculty": "MED", "building": "MED"},
    {"name": "Psychiatry", "code": "MED_PSYCH", "faculty": "MED", "building": "MED"},
    {"name": "Public Health Dentistry", "code": "MED_PUBDENT", "faculty": "MED", "building": "MED"},
    {"name": "Radio-Diagnosis", "code": "MED_RADIOD", "faculty": "MED", "building": "MED"},
    {"name": "Radiotherapy", "code": "MED_RADIOTH", "faculty": "MED", "building": "MED"},
    {"name": "Surgery", "code": "MED_SURGERY", "faculty": "MED", "building": "MED"},
    {"name": "TB And Chest Diseases", "code": "MED_TBCHEST", "faculty": "MED", "building": "MED"},

    # Ajmal Khan Tibbiya College (UNANI)
    {"name": "Amraze Jild Wa Zohrawiya", "code": "UNN_JILD", "faculty": "UNANI", "building": "UNANI"},
    {"name": "Ilaj-Bit-Tadbeer", "code": "UNN_ILAJ", "faculty": "UNANI", "building": "UNANI"},
    {"name": "Ilmul Advia", "code": "UNN_ADVIA", "faculty": "UNANI", "building": "UNANI"},
    {"name": "Ilmul Amraz", "code": "UNN_AMRAZ", "faculty": "UNANI", "building": "UNANI"},
    {"name": "Ilmul Atfal", "code": "UNN_ATFAL", "faculty": "UNANI", "building": "UNANI"},
    {"name": "Jarahat", "code": "UNN_JARAHAT", "faculty": "UNANI", "building": "UNANI"},
    {"name": "Kulliyat", "code": "UNN_KULLIYAT", "faculty": "UNANI", "building": "UNANI"},
    {"name": "Moalajat (Medicine)", "code": "UNN_MOALAJ", "faculty": "UNANI", "building": "UNANI"},
    {"name": "Niswan Wa Qabalat", "code": "UNN_NISWAN", "faculty": "UNANI", "building": "UNANI"},
    {"name": "Saidla", "code": "UNN_SAIDLA", "faculty": "UNANI", "building": "UNANI"},
    {"name": "Tahaffuzi-Wa-Samaji-Tib", "code": "UNN_TAHAFF", "faculty": "UNANI", "building": "UNANI"},
    {"name": "Tashreeh Wa Munafeul Aza", "code": "UNN_TASHMUN", "faculty": "UNANI", "building": "UNANI"},
    {"name": "Tashreehul Badan", "code": "UNN_TASHBAD", "faculty": "UNANI", "building": "UNANI"},
]

# Quick lookup by department name
NAME_TO_STRUCTURED = {item["name"]: item for item in STRUCTURED_TEACHING_DEPARTMENTS}


def normalize_code_fallback(name, existing_codes):
    """
    Generate a clean, unique uppercase identifier <= 12 characters
    if a department is not present in STRUCTURED_TEACHING_DEPARTMENTS.
    """
    cleaned = re.sub(r"[^A-Za-z0-9\s]", "", name).upper()
    words = [w for w in cleaned.split() if w not in {"DEPARTMENT", "OF", "AND", "FOR", "CENTRE", "THE", "IN"}]
    if len(words) == 1:
        base = f"DEPT_{words[0][:7]}"
    elif len(words) == 2:
        base = f"{words[0][:5]}_{words[1][:5]}"
    else:
        acronym = "".join(w[0] for w in words[:6])
        base = f"DEPT_{acronym}"
    
    code = base[:12]
    counter = 1
    while code in existing_codes:
        suffix = f"_{counter}"
        code = f"{base[:12 - len(suffix)]}{suffix}"
        counter += 1
    return code


def ingest_department_directory(csv_path=None):
    """
    Step 1: Ingest updated department directory.
    Accepts CSV path or falls back to STRUCTURED_TEACHING_DEPARTMENTS.
    Returns list of parsed department dictionaries:
    [{'name': ..., 'code': ..., 'faculty': ..., 'building': ...}, ...]
    """
    entries = []
    used_codes = {d.code.upper() for d in Department.objects.all()}
    
    # Try loading from CSV if file is provided or standard default exists
    resolved_csv = None
    if csv_path and Path(csv_path).exists():
        resolved_csv = Path(csv_path)
    else:
        default_csv = Path("updated AMU - Departments and Residential Halls Data - Teaching Departments.csv")
        if default_csv.exists():
            resolved_csv = default_csv

    if resolved_csv:
        print(f"📥 Loading department data from CSV: {resolved_csv}")
        with open(resolved_csv, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if not row or len(row) < 2 or row[0].strip().lower() == "total":
                    continue
                name = row[1].strip()
                if not name:
                    continue
                
                # Check pre-mapped definitions first
                if name in NAME_TO_STRUCTURED:
                    entry = dict(NAME_TO_STRUCTURED[name])
                else:
                    # Dynamically generate safe, normalized code
                    code = normalize_code_fallback(name, used_codes)
                    entry = {"name": name, "code": code, "faculty": None, "building": None}
                entries.append(entry)
                used_codes.add(entry["code"].upper())
    else:
        print("📋 Using built-in structured dictionary definitions (118 teaching departments).")
        entries = [dict(item) for item in STRUCTURED_TEACHING_DEPARTMENTS]

    return entries


@transaction.atomic
def sync_departments(entries):
    """
    Step 1 & 2: Safe model mapping with update_or_create.
    Preserves primary keys, existing trades, and relations.
    """
    print("\n🔄 Synchronizing Department records...")
    synced_depts = []
    created_count = 0
    updated_count = 0
    preserved_legacy_count = 0

    dept_field_names = {f.name for f in Department._meta.fields}

    for entry in entries:
        name = entry["name"]
        code = entry["code"].upper()
        parent_ref = entry.get("building") or entry.get("faculty")

        # Check existing department by code first
        existing_dept = Department.objects.filter(code=code).first()

        # Handle parental foreign key safely if the Department model supports it
        parent_building = None
        if parent_ref:
            parent_building = Building.objects.filter(code__iexact=parent_ref).first()

        defaults = {
            "name": name,
            "is_active": True,
        }

        # Safe dynamic model mapping: assign FK only if field exists
        if "building" in dept_field_names and parent_building:
            defaults["building"] = parent_building
        if "faculty" in dept_field_names and parent_building:
            defaults["faculty"] = parent_building

        if existing_dept:
            # Preserve existing legacy code / primary key relations
            if code in PROTECTED_TRADE_CODES:
                preserved_legacy_count += 1
                print(f"  🔒 Preserving protected maintenance trade: {existing_dept.name} [{code}] (id={existing_dept.pk})")
                synced_depts.append(existing_dept)
                continue
            
            # Check name uniqueness collision with other departments
            clash = Department.objects.filter(name=name).exclude(pk=existing_dept.pk).first()
            if clash:
                print(f"  ⚠️ Name '{name}' matches department [{clash.code}], updating existing department record...")
                dept = clash
                updated_count += 1
            else:
                dept, _ = Department.objects.update_or_create(code=code, defaults=defaults)
                updated_count += 1
        else:
            # Check if department with this exact name already exists under a legacy code
            existing_by_name = Department.objects.filter(name=name).first()
            if existing_by_name:
                print(f"  ℹ️ Department '{name}' already exists with code [{existing_by_name.code}], preserving id={existing_by_name.pk}")
                dept = existing_by_name
                updated_count += 1
            else:
                dept, created = Department.objects.update_or_create(code=code, defaults=defaults)
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        synced_depts.append(dept)

    # Reverse lookup & residential hall linkage
    # Ensure buildings matching departments or residential halls are safely linked
    hostel_dept = Department.objects.filter(code="HOSTEL").first()
    for bldg in Building.objects.filter(is_active=True):
        b_code = bldg.code.upper()
        matching_dept = Department.objects.filter(code=b_code).first()
        if matching_dept and bldg.department_id != matching_dept.id:
            bldg.department = matching_dept
            bldg.save(update_fields=["department", "updated_at"])
        elif not bldg.department_id and hostel_dept and "hall" in bldg.name.lower():
            bldg.department = hostel_dept
            bldg.save(update_fields=["department", "updated_at"])

    print(f"✅ Department sync complete: {created_count} created, {updated_count} updated, {preserved_legacy_count} protected legacy preserved.")
    return synced_depts


@transaction.atomic
def sync_subadmin_profiles():
    """
    Step 2: Synchronize HOD sub-admin profiles.
    Provisions or refreshes HOD access for all active departments.
    Maintains existing Provost accounts and core trade HODs intact.
    """
    print("\n👤 Synchronizing HOD administrative profiles...")
    User = get_user_model()
    provisioned_hods = []

    for dept in Department.objects.filter(is_active=True):
        dept_code_clean = dept.code.lower()
        username = f"hod_{dept_code_clean}"

        user, user_created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": "HOD",
                "last_name": dept.name[:120],
                "email": f"{username}@amucare.edu.in",
                "is_staff": True,
            },
        )
        user.is_staff = True
        user.set_password(DEFAULT_ADMIN_PASSWORD)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.Role.HOD
        profile.managed_department = dept
        profile.department = dept
        profile.save()

        provisioned_hods.append(username)

    # Verify existing Provosts are intact
    provost_count = UserProfile.objects.filter(role=UserProfile.Role.PROVOST).count()
    print(f"✅ HOD profile sync complete: {len(provisioned_hods)} HOD profiles active.")
    print(f"ℹ️ Active Provost profiles preserved: {provost_count}")
    return provisioned_hods


def verify_sync():
    """
    Step 4: Verification & Regression Check.
    Asserts no broken foreign keys, critical trades present, and HOD bindings intact.
    """
    print("\n🔍 Running verification and regression checks...")

    total_depts = Department.objects.count()
    total_hods = UserProfile.objects.filter(role=UserProfile.Role.HOD).count()
    print(f"  Total Departments in DB: {total_depts}")
    print(f"  Total HOD Profiles: {total_hods}")

    # Assert no broken foreign keys on complaints
    broken_complaints = Complaint.objects.filter(category__department__isnull=True).count()
    print(f"  Complaints with unlinked departments: {broken_complaints}")
    assert broken_complaints == 0, "Regression: Unlinked complaint departments found!"

    # Verify legacy trades remain intact
    for trade in ["ELEC", "PLUMB", "CIVIL", "ITINF", "CLEAN"]:
        exists = Department.objects.filter(code=trade).exists()
        print(f"  Core trade {trade} present: {exists}")
        assert exists, f"Critical trade {trade} was removed or broken!"

    # Verify newly added key departments exist
    for code in ["DEPT_PHYS", "DEPT_CHEM", "ENGG_CIVIL"]:
        exists = Department.objects.filter(code=code).exists()
        print(f"  Teaching department {code} present: {exists}")
        assert exists, f"Teaching department {code} not found!"

    print("\n🎉 Sync verified successfully without regression.")


def main():
    csv_file = sys.argv[1] if len(sys.argv) > 1 else None
    entries = ingest_department_directory(csv_file)
    sync_departments(entries)
    sync_subadmin_profiles()
    verify_sync()


if __name__ == "__main__":
    main()
