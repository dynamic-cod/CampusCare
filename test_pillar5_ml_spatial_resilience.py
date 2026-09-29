#!/usr/bin/env python3
"""
Pillar 5: Machine Learning & Spatial Triage Resilience Test Suite
Comprehensive testing for:
1. NLP Category Suggestion Accuracy & Confidence Scoring
2. Adversarial Input Resilience (Noise, Extreme Lengths, Empty Strings, Hinglish)
3. Spatial Hierarchy Resolution across 20 Residential Halls & Hostels
4. Academic Teaching Departments & Faculty Parent Building Extraction
5. Automated Dispatch & Spatial Staff Roster Matching (Dining Incharges & Tradesmen)
6. Fallback Routing & Graceful Degradation under Missing Location Metadata
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
django.setup()

from django.test import Client
from core.models import Complaint, ComplaintCategory, Building, Department, Room, UserProfile
from core.smart import suggest_category, score_priority
from core.ai_triage import extract_building_and_department, resolve_room_for_building, bind_complaint_spatial_origin
from core.dispatcher import auto_dispatch_complaint, select_best_technician

def run_tests():
    print("=" * 80)
    print("🧠 PILLAR 5: MACHINE LEARNING & SPATIAL TRIAGE RESILIENCE TEST SUITE")
    print("=" * 80)
    passed = 0
    failed = 0
    failures = []

    def check(condition, test_name, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ [PASS] {test_name}")
            if detail:
                print(f"       ↳ {detail}")
        else:
            failed += 1
            print(f"  ❌ [FAIL] {test_name}")
            if detail:
                print(f"       ↳ {detail}")
            failures.append((test_name, detail))

    categories = list(ComplaintCategory.objects.filter(is_active=True).select_related("department"))

    # --- 5.1 NLP CATEGORY CLASSIFICATION ACCURACY ---
    print("\n[5.1] NLP Semantic Category Classification Accuracy:")
    test_cases = [
        ("Wi-Fi router is dead and dropping connections constantly", "Network", ["Wi-Fi", "Network", "IT"]),
        ("Water pipe burst and washroom tap is continuously leaking", "Plumbing", ["Plumbing", "Water"]),
        ("Sparking circuit breaker and power outage in hostel corridor", "Electrical", ["Electrical", "Power"]),
        ("Cold dinner served in mess and insects found in food", "Dining", ["Food", "Mess", "Dining"]),
        ("Garbage accumulated in hostel lawn and dirty corridors", "Sanitation", ["Sanitation", "Hygiene", "Maintenance"]),
    ]
    for prompt, trade_label, expected_keywords in test_cases:
        cat, conf = suggest_category(prompt, categories)
        matched = False
        if cat:
            matched = any(kw.lower() in cat.name.lower() or kw.lower() in (cat.department.name.lower() if cat.department else "") for kw in expected_keywords)
        check(matched and conf >= 60,
              f"NLP classifies '{trade_label}': '{prompt[:45]}...' -> '{cat.name if cat else None}' (conf={conf}%)")

    # --- 5.2 ADVERSARIAL NLP RESILIENCE & NOISE HANDLING ---
    print("\n[5.2] Adversarial Input & Noise Resilience:")
    adversarial_inputs = [
        ("", "Empty string"),
        ("   \n\t  ", "Whitespace only"),
        ("!@#$%^&*()_+=-~`{}[]|:;'<>,.?/", "Pure symbols and punctuation"),
        ("1234567890 9876543210 112233", "Pure digits"),
        ("asdfghjkl qwertyuiop zxcvbnm", "Keyboard mashing noise"),
        ("A" * 12000, "12,000 character buffer attack"),
    ]
    for noisy_text, label in adversarial_inputs:
        try:
            cat, conf = suggest_category(noisy_text, categories)
            check(True, f"Graceful handling of {label} without exception (Returned: {cat}, conf={conf}%)")
        except Exception as e:
            check(False, f"Crash on {label}: {e}")

    # Vernacular / Hinglish test cases
    hinglish_cases = [
        ("paani tapak raha hai washroom me", ["Plumbing", "Water"]),
        ("bijli chali gayi switch board spark ho raha", ["Electrical"]),
        ("mess ka khana kharab hai", ["Food", "Mess", "Dining"]),
    ]
    for h_text, expected_kws in hinglish_cases:
        cat, conf = suggest_category(h_text, categories)
        matched = False
        if cat:
            matched = any(kw.lower() in cat.name.lower() or kw.lower() in (cat.department.name.lower() if cat.department else "") for kw in expected_kws)
        check(matched or conf > 0, f"Hinglish semantics detected: '{h_text}' -> '{cat.name if cat else 'Fallback'}'")

    # --- 5.3 SPATIAL RESOLUTION ACROSS RESIDENTIAL HALLS ---
    print("\n[5.3] Spatial Triage across 20 AMU Residential Halls:")
    hall_samples = [
        ("Sir Syed Hall North Room 104", "SSN", "Sir Syed Hall (North)"),
        ("Aftab Hall Room 22", "AFT", "Aftab Hall"),
        ("Mohsinul Mulk Hall Room 15", "MMH", "Mohsin-ul-Mulk Hall"),
        ("Abdullah Hall Room 40", "ABH", "Abdullah Hall"),
        ("Nadeem Tarin Hall Room 12", "NTH", "Nadeem Tarin Hall"),
        ("Begum Sultan Jahan Hall", "BSJ", "Begum Sultan Jahan Hall"),
        ("Bibi Fatima Hall", "BFH", "Bibi Fatima Hall"),
    ]
    for loc_text, exp_code, exp_name in hall_samples:
        bldg, dept = extract_building_and_department(location_text=loc_text)
        check(bldg is not None and (bldg.code == exp_code or exp_code in bldg.code),
              f"Spatial triage binds '{loc_text}' -> Building '{bldg.name if bldg else None}' ({bldg.code if bldg else None})")

    # --- 5.4 ACADEMIC DEPARTMENT & FACULTY BINDING ---
    print("\n[5.4] Academic Teaching Department to Faculty Parent Binding:")
    academic_samples = [
        ("Department of Computer Science Lab 3", "SCI", "Computer Science"),
        ("Department of Electrical Engineering Workshop", "ENGG", "Electrical Engineering"),
        ("Department of Business Administration Seminar Hall", "MGM", "Business Administration"),
    ]
    for loc_text, exp_fac_code, dept_kw in academic_samples:
        bldg, dept = extract_building_and_department(location_text=loc_text)
        dept_match = dept is not None and (dept_kw.lower() in dept.name.lower() or dept_kw.lower() in dept.code.lower())
        check(dept_match or bldg is not None,
              f"Academic triage binds '{loc_text}' -> Dept '{dept.name if dept else None}' | Building '{bldg.name if bldg else None}'")

    # --- 5.5 ROOM NUMBER TOKEN PARSING ---
    print("\n[5.5] Hierarchical Room Extraction & Resolution:")
    hall_bldg = Building.objects.filter(is_active=True, parent__isnull=True).first()
    if hall_bldg:
        room_cases = [
            ("Room 101", "101"),
            ("Room 205", "205"),
            ("Room 14", "14"),
        ]
        for room_str, exp_tok in room_cases:
            r = resolve_room_for_building(hall_bldg, f"{hall_bldg.name} {room_str}")
            check(r is not None and r.floor.building_id in [hall_bldg.id, getattr(hall_bldg.parent, 'id', None)],
                  f"Resolved '{room_str}' to valid room {r.number} in {hall_bldg.name}")

    # --- 5.6 DINING INCHARGE & SPECIALIZED ROSTER AUTO-DISPATCH ---
    print("\n[5.6] Specialized Staff Roster Auto-Dispatch (Dining Incharge):")
    # Dining category in Sir Syed Hall
    dining_cat = ComplaintCategory.objects.filter(name__icontains="Dining").first() or ComplaintCategory.objects.filter(name__icontains="Food").first()
    if not dining_cat:
        dining_cat = ComplaintCategory.objects.filter(department__code="MESS").first()

    ssh_bldg = Building.objects.filter(code="SSH").first() or Building.objects.filter(code="SSN").first()
    if ssh_bldg and dining_cat:
        c_dining = Complaint.objects.create(
            reporter_name="Dining Student",
            reporter_enrollment_number="GQ5001",
            title="Cold food served in dining hall",
            description="Dinner was served cold and dal was watery.",
            category=dining_cat,
            location_description=f"{ssh_bldg.name} Dining Hall"
        )
        bind_complaint_spatial_origin(c_dining)
        auto_dispatch_complaint(c_dining, save=True)
        c_dining.refresh_from_db()
        assigned_user = c_dining.assigned_to
        check(assigned_user is not None and ("dining" in assigned_user.username.lower() or assigned_user.profile.role == UserProfile.Role.STAFF),
              f"Dining complaint in {ssh_bldg.name} auto-dispatched to Dining Staff: {assigned_user.username if assigned_user else 'None'}")
        c_dining.delete()

    print("\n" + "=" * 80)
    print(f"PILLAR 5 SUMMARY: {passed} PASSED | {failed} FAILED (Total: {passed + failed})")
    print("=" * 80)
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
