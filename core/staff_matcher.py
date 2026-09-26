"""
AI Staff Matcher — selects the best available staff member for a complaint
based on complaint category/department, issue description, and location (hall/faculty/block).

Data source: core/staff_data.json (generated from "staff list.xlsx" covering 156 personnel across AMU)
"""
import json
import os
import re

_STAFF_DATA = None  # module-level cache


def _load_staff():
    global _STAFF_DATA
    if _STAFF_DATA is None:
        data_path = os.path.join(os.path.dirname(__file__), "staff_data.json")
        with open(data_path, "r", encoding="utf-8") as f:
            _STAFF_DATA = json.load(f)
    return _STAFF_DATA


DEPT_FULL_NAMES = {
    "ELEC": "Electrical (ELEC)",
    "PLUMB": "Plumbing (PLUMB)",
    "CIVIL": "Civil (CIVIL)",
    "ITINF": "IT & AV (ITINF)",
    "CLEAN": "Sanitation (CLEAN)",
}

# Regex patterns for high-precision department categorization
DEPT_PATTERNS = {
    "ITINF": [
        r"\b(?:wi-?fi|internet|network|lan|router|broadband|connectivity)\b",
        r"\b(?:it|audio-?visual|av|projector|computer|software|portal|server)\b",
        r"\b(?:desktop|laptop|printer|scanner|fiber|smart\s*class)\b",
    ],
    "ELEC": [
        r"\b(?:electric(?:al)?|power|light|bulb|fan|switch|socket|wiring|short\s*circuit)\b",
        r"\b(?:generator|transformer|substation|voltage|spark|breaker|ac|air\s*condition(?:ing)?)\b",
    ],
    "PLUMB": [
        r"\b(?:plumb(?:ing)?|water|pipe|leak|tap|faucet|drain|drainage|sewer|sewage|flush|pump|tank|tube-?well)\b",
    ],
    "CIVIL": [
        r"\b(?:civil|carpenter|carpentry|door|window|lock|furniture|desk|chair|table|bed|masonry)\b",
        r"\b(?:glass|glazier|wall|ceiling|floor|tile|paint|plaster|welder|welding|iron|almirah|chiller)\b",
        r"\b(?:room\s*maintenance|classroom\s*maintenance|common\s*area)\b",
    ],
    "CLEAN": [
        r"\b(?:clean(?:ing)?|sanitat(?:ion)?|hygiene|garbage|trash|waste|dustbin|toilet|washroom|restroom|sweeper|housekeeping)\b",
    ],
}

LOCATION_CANONICAL = {
    "Sir Syed Hall (North & South Blocks)": ["sir syed", "ss hall", "ss north", "ss south", "sirsye"],
    "Aftab Hall": ["aftab"],
    "Mohsin-ul-Mulk Hall": ["mohsin", "mm hall", "mum hall"],
    "Viqar-ul-Mulk Hall": ["viqar", "vm hall"],
    "Sulaiman Hall": ["sulaiman", "sh hall"],
    "Nadeem Tarin Hall": ["nadeem tarin", "tarin", "nt hall"],
    "Sarojini Naidu Hall": ["sarojini", "naidu", "sn hall"],
    "Abdullah Hall (Women's Complex)": ["abdullah", "women", "girls"],
    "Faculty of Engineering & Technology (Z.H. College of Engg)": ["engineering", "z.h", "zhcet", "engg", "polytechnic"],
    "Faculty of Science": ["faculty of science", "science faculty", "dept of physics", "dept of chemistry", "dept of computer science"],
    "Faculty of Arts & Humanities": ["arts", "humanities", "english", "urdu", "history"],
    "Faculty of Commerce & Management": ["commerce", "management", "business", "mba"],
    "Faculty of Life Sciences": ["life sciences", "botany", "zoology", "biochemistry"],
    "Administrative & Examination Block": ["admin", "administrative", "examination", "exam block", "controller", "registrar"],
    "Central Mobile & Heavy Equipment Reserve": ["central", "reserve", "campus-wide", "substation"],
}


def detect_department_code(text):
    """Detect the most appropriate department code (ELEC, PLUMB, CIVIL, ITINF, CLEAN) from text."""
    text_lower = text.lower()
    scores = {d: 0 for d in DEPT_PATTERNS}
    for dept, patterns in DEPT_PATTERNS.items():
        for pat in patterns:
            matches = re.findall(pat, text_lower)
            scores[dept] += len(matches)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "CIVIL"


def match_canonical_location(text):
    """Match text against known AMU Halls, Faculties, and Administrative facilities."""
    q = text.lower()
    best_loc, best_score = None, 0
    for loc, aliases in LOCATION_CANONICAL.items():
        for alias in aliases:
            if alias in q and len(alias) > best_score:
                best_score = len(alias)
                best_loc = loc
    return best_loc


def suggest_staff(category_name, location_description="", title="", description="", n=3):
    """
    Return up to n staff members ranked by department expertise and location proximity.
    Each item is a dict with staff details from the official roster.
    """
    staff_roster = _load_staff()

    # Combine all complaint signals
    combined_signal = f"{category_name} {title} {description} {location_description}"
    dept_code = detect_department_code(combined_signal)
    target_location = match_canonical_location(f"{location_description} {title} {description}")

    dept_full = DEPT_FULL_NAMES.get(dept_code, "Civil (CIVIL)")
    candidates = [s for s in staff_roster if s["dept"] == dept_full]
    if not candidates:
        candidates = staff_roster

    # Rank candidates: exact location match first, then central reserve, then others
    scored = []
    for member in candidates:
        score = 0.5
        reason = f"Department match ({dept_full})"
        if target_location and member["location"] == target_location:
            score = 1.0
            reason = f"Location & Department match ({member['location']})"
        elif "Central" in member["location"] or "Administrative" in member["location"]:
            score = 0.7
            reason = f"Central facility specialist ({member['location']})"
        scored.append((score, reason, member))

    scored.sort(key=lambda item: -item[0])

    results = []
    for score, reason, member in scored[:n]:
        results.append({
            **member,
            "dept_code": dept_code,
            "match_score": score,
            "match_reason": reason,
        })
    return results


def best_staff_username(category_name, location_description="", title="", description=""):
    """Return the username of the single best-matched staff member, or None."""
    results = suggest_staff(
        category_name=category_name,
        location_description=location_description,
        title=title,
        description=description,
        n=1,
    )
    return results[0]["username"] if results else None
