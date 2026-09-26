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
}

URGENT_KEYWORDS = ("fire", "smoke", "spark", "electric shock", "flood", "gas", "unsafe", "injury", "emergency", "theft", "security")
HIGH_KEYWORDS = ("leak", "broken", "no power", "not working", "overflow", "security", "dark", "accident", "lost", "stolen")


def suggest_category(text, categories):
    """Return the strongest matching active category and a confidence percentage."""
    normalized = text.lower()
    best_cat, best_score = None, 0
    for cat in categories:
        cat_lower = cat.name.lower()
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
    elif any(term in category_name.lower() for term in ("electrical", "plumbing", "sanitation", "network", "water", "security")):
        priority = Complaint.Priority.NORMAL
        reason = f"Essential facilities category '{category_name}' requires timely attention."
        score = 55
    else:
        priority = Complaint.Priority.LOW
        reason = "No urgent service or safety indicators detected."
        score = 30
    sla_hours = get_ai_sla_hours(priority)
    return score, priority, reason, sla_hours


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

    source = f"{complaint.title} {complaint.description}".lower()
    best_match, best_score = None, 0
    for candidate in candidates[:100]:
        target = f"{candidate.title} {candidate.description}".lower()
        score = SequenceMatcher(None, source, target).ratio()
        if score > best_score:
            best_match, best_score = candidate, score
    return best_match if best_score >= 0.58 else None
