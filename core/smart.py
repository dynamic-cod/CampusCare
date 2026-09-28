"""Explainable heuristics for category suggestion and priority/SLA scoring."""
from difflib import SequenceMatcher
import re

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


def suggest_category(text, categories):
    """Return the strongest matching active category and a confidence percentage."""
    normalized = text.lower()
    best_cat, best_score = None, 0
    for cat in categories:
        cat_lower = cat.name.lower()
        if ("dining" in cat_lower or "mess" in cat_lower) and not any(k in normalized for k in ("dining", "mess", "canteen", "cafeteria", "food", "kitchen", "ration", "cook", "meal", "tiffin")):
            continue
        score = 0
        for kw, weight in SPECIFIC_KEYWORD_WEIGHTS.items():
            if re.search(r"\b" + re.escape(kw) + r"\b", normalized):
                if kw in cat_lower or any(part in cat_lower for part in kw.split()):
                    score += weight
                elif "network" in cat_lower and kw in ("wifi", "wi-fi", "internet", "router", "lan", "broadband"):
                    score += weight
                elif "electrical" in cat_lower and kw in ("bulb", "light", "fan", "switch", "socket", "power", "spark", "sparking", "shock", "wiring"):
                    score += weight
                elif "plumbing" in cat_lower and kw in ("leak", "leaking", "pipe", "tap", "faucet", "water", "drain", "drainage", "sewer", "flush"):
                    score += weight
                elif "dining incharge" in cat_lower and kw in ("food poisoning", "contamination", "insect in food","food","roti","dal","sabzi","tasteless","stale","undercooked","raw","uncooked","insect","worm","cockroach","caterer","diet","ration","portion","food quantity","food menu","dining water cooler","mess timing","mess"):
                    score += weight
                elif "water" in cat_lower and kw in ("water", "tap", "pipe", "leak", "leaking"):
                    score += weight
                elif "sanitation" in cat_lower and kw in ("garbage", "trash", "waste", "dirty", "toilet", "washroom", "cleaning", "sanitation", "dustbin"):
                    score += weight
                elif ("carpentry" in cat_lower or "civil" in cat_lower) and kw in ("door", "window", "lock", "latches", "carpentry", "furniture", "masonry"):
                    score += weight
        if score > best_score:
            best_cat, best_score = cat, score
    conf = min(95, 50 + best_score * 2) if best_cat and best_score >= 15 else 0
    return (best_cat, conf) if conf > 0 else (None, 0)


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
    return any(kw in combined for kw in MESS_KEYWORDS)


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

