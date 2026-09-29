"""Explainable heuristics for category suggestion and priority/SLA scoring."""
from difflib import SequenceMatcher
import re

from .faculty_directory import detect_department, detect_faculty
from .models import Complaint

SPECIFIC_KEYWORD_WEIGHTS = {
    # Tech / IT (weight 25)
    "wifi": 25, "wi-fi": 25, "internet": 25, "router": 25, "network": 20, "lan": 20, "broadband": 20,
    "computer": 20, "desktop": 20, "laptop": 20, "software": 20, "portal": 20, "projector": 25,
    # Electrical (weight 25)
    "spark": 25, "sparking": 25, "shock": 25, "short circuit": 25, "bulb": 20, "light": 15, "fan": 20,
    "wiring": 20, "electric": 20, "electrical": 25, "switch": 20, "socket": 20, "power": 15,
    # Plumbing (weight 25)
    "leak": 25, "leaking": 25, "pipe": 25, "tap": 25, "faucet": 25, "water": 15, "drain": 20, "drainage": 25, "sewer": 25, "flush": 20,
    # Civil / Carpentry (weight 20)
    "door": 20, "window": 20, "lock": 25, "latches": 20, "carpentry": 25, "carpenter": 25, "furniture": 20, "masonry": 25, "plaster": 20,
    # Sanitation (weight 25)
    "garbage": 25, "trash": 25, "waste": 20, "dirty": 20, "toilet": 25, "washroom": 20, "cleaning": 25, "sanitation": 25, "dustbin": 25,
    # Mess / Dining (weight 25) — maps to 'Food Quality & Hygiene' and related categories
    "food": 25, "mess": 25, "dining": 25, "dining hall": 25, "cafeteria": 25, "canteen": 25,
    "roti": 25, "rice": 20, "daal": 20, "dal": 20, "sabzi": 20, "biryani": 20,
    "lunch": 20, "dinner": 20, "breakfast": 20, "meal": 20, "tiffin": 20,
    "tasteless": 25, "stale": 25, "undercooked": 25, "raw": 20, "uncooked": 25,
    "insect in food": 30, "insect": 25, "worm": 30, "cockroach": 30,
    "caterer": 25, "diet": 20, "ration": 20, "portion": 20, "quantity": 20,
    "food poisoning": 30, "contamination": 30, "contaminated": 30,
    "ill after eating": 30, "sick after food": 30, "vomiting after": 30,
    "water cooler": 25, "mess timing": 25, "menu": 20,
}

URGENT_KEYWORDS = (
    "fire", "smoke", "spark", "electric shock", "flood", "gas", "unsafe", "injury",
    "emergency", "theft", "security",
    # Dining emergencies
    "food poisoning", "contamination", "contaminated", "insect in food",
    "cockroach", "worm", "ill after eating", "sick after food", "vomiting after",
)
HIGH_KEYWORDS = (
    "leak", "broken", "no power", "not working", "overflow", "security", "dark",
    "accident", "lost", "stolen",
    # Dining quality issues
    "stale", "undercooked", "uncooked", "insect", "tasteless", "raw",
)

# Mess/Dining specific category triggers — matched against lowercased combined text
MESS_KEYWORDS = {
    "food", "mess", "dining", "dining hall", "cafeteria", "canteen", "roti", "rice",
    "daal", "dal", "sabzi", "lunch", "dinner", "breakfast", "meal", "tiffin",
    "tasteless", "stale", "undercooked", "raw", "uncooked", "insect", "worm",
    "cockroach", "caterer", "diet", "ration", "portion", "quantity", "menu",
    "food poisoning", "contaminated", "water cooler", "mess timing",
}


ACADEMIC_FACULTY_CODES = {
    "AGRI", "ARTS", "COMM", "ENGG", "INTL", "LAW", "LIFE", "MGMT", "SCI", "SOC", "THEO", "MED", "UNANI"
}


def suggest_categories(text, categories, location="", limit=3):
    """
    Return top matching active categories with calibrated confidence percentages.
    
    Fine-tuned AI routing features:
    - Academic Faculty & Department context binding:
      Strictly avoids cross-faculty classification errors (e.g. suggesting
      'Management Projector Equipment' for 'Department of Computer Science').
    - Comprehensive domain & semantic keyword mapping across IT, AV, Electrical,
      Plumbing, Civil, Sanitation, Dining, Labs, Libraries, and Security.
    - Calibrated confidence scoring (50% - 95%).
    """
    combined_raw = f"{text or ''} {location or ''}".strip()
    if not combined_raw or len(combined_raw) < 3:
        return []

    normalized = combined_raw.lower()

    # Detect academic context
    detected_dept = detect_department(combined_raw)
    detected_fac = detect_faculty(combined_raw)
    detected_fac_code = None
    if detected_dept:
        detected_fac_code = detected_dept.get("faculty", "").upper()
    elif detected_fac:
        detected_fac_code = detected_fac.get("code", "").upper()

    # Is dining / mess complaint? (Use word boundaries to avoid false positives like 'ration' in 'administration')
    is_dining = bool(re.search(
        r"\b(dining|mess|canteen|cafeteria|food|kitchen|ration|rations|cook|meal|meals|"
        r"tiffin|roti|rotis|rice|daal|dal|sabzi|biryani|breakfast|lunch|dinner)\b",
        normalized
    ))

    scored_categories = []

    for cat in categories:
        cat_lower = cat.name.lower()
        dept_code = (cat.department.code or "").upper() if (cat.department and cat.department.code) else ""

        # 1. STRICT CROSS-FACULTY ISOLATION:
        # If an academic faculty is identified (e.g. SCI for Computer Science),
        # any category from an incompatible academic faculty (e.g. MGMT, ARTS, ENGG, etc.) is strictly filtered out.
        if detected_fac_code and dept_code in ACADEMIC_FACULTY_CODES and dept_code != detected_fac_code:
            continue

        # 2. If it's NOT a dining complaint, do not suggest dining/mess categories
        if not is_dining and (dept_code == "MESS" or "dining" in cat_lower or "mess" in cat_lower):
            continue

        score = 0

        # Faculty affinity boost
        if detected_fac_code and dept_code == detected_fac_code:
            score += 15

        # --- A. PROJECTOR / AUDIO-VISUAL / SMART CLASS ---
        if re.search(r"\b(projector|smart class|smart board|audio visual|av equipment|podium|display screen|overhead projector)\b", normalized):
            if detected_fac_code == "SCI":
                if cat.name == "Science Computer Systems":
                    score += 45
                elif cat.name == "Science Laboratory Equipment":
                    score += 30
            elif detected_fac_code == "ENGG":
                if cat.name == "Engineering Computer Systems":
                    score += 45
                elif cat.name == "Engineering Laboratory Equipment":
                    score += 30
            elif detected_fac_code == "ARTS":
                if cat.name == "Arts Audio-Visual Equipment":
                    score += 50
            elif detected_fac_code == "MGMT":
                if cat.name == "Management Projector Equipment":
                    score += 50
            elif detected_fac_code == "COMM":
                if cat.name == "Commerce Computer Lab Equipment":
                    score += 45
                elif cat.name == "Commerce Classroom Maintenance":
                    score += 35
            elif detected_fac_code == "SOC":
                if cat.name == "Social Computer Lab":
                    score += 45
                elif cat.name == "Social Classroom Maintenance":
                    score += 35
            elif detected_fac_code == "LAW":
                if cat.name == "Law Classroom Maintenance":
                    score += 45
                elif cat.name == "Law Computer Lab":
                    score += 35
            else:
                if cat.name in ("Arts Audio-Visual Equipment", "IT Services", "IT Software & Portals", "Campus Wi-Fi & Network Services"):
                    score += 30
                elif cat.name == "Electrical & Wiring Maintenance":
                    score += 20

        # --- B. WI-FI & NETWORK ---
        if re.search(r"\b(wifi|wi-fi|internet|router|broadband|lan|ethernet|network|connectivity|signal|hotspot|modem)\b", normalized):
            if cat.name == "Campus Wi-Fi & Network Services":
                score += 50
            elif cat.name == "IT Network & Connectivity":
                score += 45
            elif cat.name == "IT Server Maintenance":
                score += 25

        # --- C. COMPUTERS, LAB HARDWARE & SOFTWARE ---
        if re.search(r"\b(computer|pc|desktop|laptop|cpu|monitor|mouse|keyboard|printer|scanner|ups|hard disk|ram|motherboard|software|portal|erp|login|crash|server)\b", normalized):
            if detected_fac_code == "SCI" and cat.name == "Science Computer Systems":
                score += 45
            elif detected_fac_code == "ENGG" and cat.name == "Engineering Computer Systems":
                score += 45
            elif detected_fac_code == "COMM" and cat.name == "Commerce Computer Lab Equipment":
                score += 45
            elif detected_fac_code == "MGMT" and cat.name == "Management Computer Lab":
                score += 45
            elif detected_fac_code == "SOC" and cat.name == "Social Computer Lab":
                score += 45
            elif detected_fac_code == "LAW" and cat.name == "Law Computer Lab":
                score += 45
            elif detected_fac_code == "INTL" and cat.name == "International Language Lab Equipment":
                score += 45
            elif cat.name in ("IT Server Maintenance", "IT Software & Portals"):
                score += 40
            elif cat.name == "IT Network & Connectivity":
                score += 30

        # --- D. ELECTRICAL & WIRING ---
        if re.search(r"\b(spark|sparking|shock|electric shock|short circuit|mcb|fuse|bulb|tube light|light|fan|wiring|electric|electrical|switch|switchboard|socket|power|blackout|voltage|ac|air conditioner|cooler|geyser|heater|inverter)\b", normalized):
            if detected_fac_code == "ENGG" and cat.name == "Engineering Electrical Systems":
                score += 45
            elif cat.name == "Electrical & Wiring Maintenance":
                score += 45
            elif cat.name == "Estate Electrical Maintenance":
                score += 35
            elif ("hostel" in normalized or "hall" in normalized) and cat.name == "Hostel Room Maintenance":
                score += 30

        # --- E. PLUMBING & WATER ---
        if re.search(r"\b(leak|leaking|pipe|pipeline|tap|faucet|water|drain|drainage|sewer|sewage|flush|cistern|tank|submersible|motor|clogged|choked|overflow)\b", normalized):
            if is_dining and cat.name in ("Dining Hall Water & Utilities", "Water Cooler & Dining Hall Maintenance"):
                score += 50
            elif cat.name == "Estate Plumbing":
                score += 60 if re.search(r"\b(pipe|pipeline|leak|leaking|tap|faucet|plumb|plumbing|drain|drainage|sewer|sewage|flush)\b", normalized) else 45
            elif ("hostel" in normalized or "hall" in normalized) and cat.name == "Hostel Water Supply":
                score += 40
            elif cat.name == "Hostel Water Supply":
                score += 35

        # --- F. CIVIL & CARPENTRY & FURNITURE ---
        if re.search(r"\b(door|window|lock|latches|hinges|carpentry|carpenter|furniture|desk|bench|chair|table|masonry|plaster|wall|ceiling|roof|tile|paint|seepage|dampness|cracked wall|broken glass|window pane|cupboard|almirah)\b", normalized):
            if detected_fac_code == "ARTS" and cat.name == "Arts Classroom Furniture":
                score += 45
            elif detected_fac_code == "COMM" and cat.name == "Commerce Classroom Maintenance":
                score += 45
            elif detected_fac_code == "SOC" and cat.name == "Social Classroom Maintenance":
                score += 45
            elif detected_fac_code == "LAW" and cat.name == "Law Classroom Maintenance":
                score += 45
            elif detected_fac_code == "THEO" and cat.name == "Theology Classroom Maintenance":
                score += 45
            elif ("hostel" in normalized or "hall" in normalized) and cat.name in ("Hostel Room Maintenance", "Hostel Common Area Maintenance"):
                score += 40
            elif cat.name == "Civil & Carpentry Works":
                score += 45
            elif cat.name in ("Estate Civil Works", "Estate Carpentry"):
                score += 35

        # --- G. SANITATION & CLEANING ---
        if re.search(r"\b(garbage|trash|waste|dirty|toilet|washroom|bathroom|urinal|cleaning|sanitation|dustbin|sweeper|sweep|broom|mop|stink|foul smell|litter)\b", normalized):
            if is_dining and cat.name == "Dining Hall Maintenance & Hygiene":
                score += 45
            elif cat.name == "Hostel Sanitation":
                score += 45

        # --- H. MESS & DINING ---
        if is_dining:
            if re.search(r"\b(insect|worm|cockroach|contamination|contaminated|food poisoning|stale|tasteless|undercooked|raw|uncooked|ill after|sick after|vomiting|hygiene)\b", normalized):
                if cat.name == "Food Quality & Hygiene":
                    score += 50
                elif cat.name == "Food Quality & Preparation":
                    score += 45
            elif re.search(r"\b(timing|late|early|quantity|portion|ration|menu|caterer)\b", normalized):
                if cat.name == "Mess Timings & Quantity":
                    score += 50
                elif cat.name == "Mess Timings & Ration Supply":
                    score += 45
            elif re.search(r"\b(water cooler|drinking water|cooler)\b", normalized):
                if cat.name == "Water Cooler & Dining Hall Maintenance":
                    score += 50
                elif cat.name == "Dining Hall Water & Utilities":
                    score += 45
            else:
                if cat.name in ("Dining Hall Maintenance & Hygiene", "Food Quality & Hygiene"):
                    score += 40

        # --- I. LABORATORY APPARATUS & CHEMICAL SAFETY ---
        if re.search(r"\b(chemical|acid|reagent|hazard|spill|safety|fume hood)\b", normalized):
            if detected_fac_code == "SCI" and cat.name == "Science Chemical Safety":
                score += 50
            elif detected_fac_code == "LIFE" and cat.name == "Life Sciences Chemical Safety":
                score += 50
        if re.search(r"\b(microscope|specimen|slides|lens)\b", normalized):
            if detected_fac_code == "LIFE" and cat.name == "Life Sciences Microscope Maintenance":
                score += 50
        if re.search(r"\b(lab|laboratory|apparatus|centrifuge|autoclave|incubator|test tube|pipette)\b", normalized):
            if detected_fac_code == "SCI" and cat.name == "Science Laboratory Equipment":
                score += 45
            elif detected_fac_code == "ENGG" and cat.name == "Engineering Laboratory Equipment":
                score += 45
            elif detected_fac_code == "LIFE" and cat.name == "Life Sciences Laboratory Equipment":
                score += 45
            elif detected_fac_code == "MED" and cat.name == "JNMC Laboratory Equipment":
                score += 45
            elif detected_fac_code == "UNANI" and cat.name == "Unani Laboratory Equipment":
                score += 45

        # --- J. MEDICAL & HOSPITAL (JNMC & UNANI) ---
        if re.search(r"\b(hospital|patient|doctor|ward|bed|stretcher|ambulance|medical|stethoscope|ecg|x-ray)\b", normalized):
            if detected_fac_code == "MED" or "jnmc" in normalized:
                if cat.name == "JNMC Medical Equipment":
                    score += 50
                elif cat.name == "JNMC Hospital Infrastructure":
                    score += 45
            elif detected_fac_code == "UNANI" or "tibbiya" in normalized:
                if cat.name == "Unani Medical Equipment":
                    score += 50
        if re.search(r"\b(herbal|medicinal plant|herbal garden)\b", normalized):
            if cat.name == "Unani Herbal Garden Maintenance":
                score += 50

        # --- K. AGRICULTURE ---
        if re.search(r"\b(farm|tractor|plough|crop|irrigation|tubewell|sprinkler)\b", normalized):
            if cat.name == "Farm Equipment":
                score += 50
            elif cat.name == "Irrigation Systems":
                score += 50

        # --- L. LIBRARY ---
        if re.search(r"\b(library|maulana azad|book|journal|reading room|stack|circulation|catalog)\b", normalized):
            if cat.name == "Central Library Services":
                score += 45
            elif cat.name == "Central Library Reading Room Maintenance":
                score += 45

        # --- M. SECURITY ---
        if re.search(r"\b(security|guard|gate|entry|trespassing|stolen|theft|cycle|bike|cctv|camera)\b", normalized):
            if "gate" in normalized and cat.name == "Gate Maintenance":
                score += 50
            elif cat.name == "Campus Security":
                score += 45

        # Fallback keyword matching
        for kw, weight in SPECIFIC_KEYWORD_WEIGHTS.items():
            if re.search(r"\b" + re.escape(kw) + r"\b", normalized):
                if kw in cat_lower:
                    if not (detected_fac_code and dept_code in ACADEMIC_FACULTY_CODES and dept_code != detected_fac_code):
                        score += min(weight, 15)

        if score > 0:
            scored_categories.append((cat, score))

    scored_categories.sort(key=lambda x: x[1], reverse=True)

    results = []
    seen_ids = set()
    for cat, score in scored_categories:
        if cat.id in seen_ids:
            continue
        seen_ids.add(cat.id)
        conf = min(95, 50 + score) if score >= 15 else 0
        if conf > 0:
            results.append((cat, conf))
        if len(results) >= limit:
            break

    return results


def suggest_category(text, categories, location=""):
    """Return the strongest matching active category and a confidence percentage."""
    results = suggest_categories(text, categories, location=location, limit=1)
    return results[0] if results else (None, 0)


def get_ai_sla_hours(priority):
    """Map a priority string to an SLA window in hours."""
    return {
        Complaint.Priority.URGENT: 2,
        Complaint.Priority.HIGH: 6,
        Complaint.Priority.NORMAL: 24,
        Complaint.Priority.LOW: 48,
    }.get(priority, 24)


def is_mess_complaint(text, title="", description="", category_name=""):
    """Return True if text signals a mess/dining issue."""
    combined = f"{title} {description} {text} {category_name}".lower()
    return any(re.search(r"\b" + re.escape(kw) + r"\b", combined) for kw in MESS_KEYWORDS)


def score_priority(text, title="", description="", category_name="", location=""):
    """Return (score, priority, reason, sla_hours) - all four values."""
    combined = f"{title} {description} {text} {category_name} {location}".lower()
    if any(kw in combined for kw in URGENT_KEYWORDS):
        priority = Complaint.Priority.URGENT
        reason = "Safety or emergency keywords detected in your report."
        score = 95
    elif any(kw in combined for kw in HIGH_KEYWORDS):
        priority = Complaint.Priority.HIGH
        reason = "Service-disruption language detected."
        score = 75
    elif any(term in category_name.lower() for term in (
        "electrical", "plumbing", "sanitation", "network", "water", "security",
        "food", "mess", "dining", "hygiene",
    )):
        priority = Complaint.Priority.NORMAL
        reason = f"Essential facilities category '{category_name}' requires timely attention."
        score = 55
    else:
        priority = Complaint.Priority.LOW
        reason = "No urgent service or safety indicators detected."
        score = 30
    sla_hours = get_ai_sla_hours(priority)
    return score, priority, reason, sla_hours


def suggest_mess_category(text, title="", description=""):
    """
    Return the best matching Mess/Dining category for a food-related complaint,
    or None if no food signals are detected.
    """
    from .models import ComplaintCategory, Department
    combined = f"{title} {description} {text}".lower()
    if not is_mess_complaint(combined):
        return None
    mess_dept = Department.objects.filter(code="MESS").first()
    if not mess_dept:
        return None
    # Tier 1: contamination/safety → Food Quality & Hygiene
    if any(kw in combined for kw in ("insect", "worm", "cockroach", "contaminated", "food poisoning", "ill after", "sick after", "vomiting")):
        cat = ComplaintCategory.objects.filter(department=mess_dept, name__icontains="Hygiene").first()
        if cat:
            return cat
    # Tier 2: timing/quantity
    if any(kw in combined for kw in ("timing", "late", "early", "quantity", "less food", "portion", "menu")):
        cat = ComplaintCategory.objects.filter(department=mess_dept, name__icontains="Timing").first()
        if cat:
            return cat
    # Tier 3: water cooler / infrastructure
    if any(kw in combined for kw in ("water cooler", "cooler", "dining hall maintenance", "infrastructure")):
        cat = ComplaintCategory.objects.filter(department=mess_dept, name__icontains="Water").first()
        if cat:
            return cat
    # Default to Food Quality & Hygiene
    return ComplaintCategory.objects.filter(department=mess_dept).first()


def find_potential_duplicate(complaint):
    """Find the closest open public complaint at the same location using text similarity."""
    candidates = Complaint.objects.filter(is_public=True).exclude(pk=complaint.pk).exclude(
        status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]
    )
    if complaint.room_id:
        candidates = candidates.filter(room=complaint.room)
    elif complaint.location_description:
        candidates = candidates.filter(location_description__iexact=complaint.location_description)
    else:
        return None

    # Focus on the most recent 15 open complaints at this specific location
    candidates = candidates.order_by("-created_at")[:15]

    source = f"{complaint.title} {complaint.description}".lower().strip()
    source_words = set(source.split())
    if not source_words:
        return None

    best_match, best_score = None, 0
    for candidate in candidates:
        target = f"{candidate.title} {candidate.description}".lower().strip()
        # Fast path 1: Exact match
        if target == source or (complaint.title and candidate.title and complaint.title.strip().lower() == candidate.title.strip().lower()):
            return candidate

        # Fast path 2: Require token intersection before executing Ratcliff/Obershelp SequenceMatcher
        target_words = set(target.split())
        shared_words = source_words & target_words
        if not shared_words or len(shared_words) / max(min(len(source_words), len(target_words)), 1) < 0.2:
            continue

        score = SequenceMatcher(None, source, target).ratio()
        if score > best_score:
            best_match, best_score = candidate, score
            if score >= 0.90:  # Confident duplicate found, early return
                return best_match
    return best_match if best_score >= 0.58 else None

