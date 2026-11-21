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
    "EMERG": "Campus Safety & Emergency Response (EMERG)",
    "ELEC": "Electrical (ELEC)",
    "PLUMB": "Plumbing (PLUMB)",
    "CIVIL": "Civil (CIVIL)",
    "ITINF": "IT & AV (ITINF)",
    "CLEAN": "Sanitation (CLEAN)",
}

# Dedicated 10-person Campus Emergency Response Team for life-safety assistance
EMERGENCY_ROSTER = [
    {
        "location": "Central Campus Works",
        "name": "Tariq Hussain",
        "role": "Wildlife & Snake Rescue Lead",
        "dept": "Campus Safety & Emergency Response (EMERG)",
        "username": "emerg_centra_1",
        "contact": "+91 94121 00001",
        "keywords": ["snake", "saamp", "cobra", "viper", "python", "reptile", "slithering"],
    },
    {
        "location": "Central Campus Works",
        "name": "Javed Ansari",
        "role": "Venomous Reptile Rescue Specialist",
        "dept": "Campus Safety & Emergency Response (EMERG)",
        "username": "emerg_centra_2",
        "contact": "+91 94121 00002",
        "keywords": ["snake", "saamp", "cobra", "viper", "python", "reptile", "krait"],
    },
    {
        "location": "Central Campus Works",
        "name": "Salman Qureshi",
        "role": "Wildlife & Reptile Rescue Handler",
        "dept": "Campus Safety & Emergency Response (EMERG)",
        "username": "emerg_centra_7",
        "contact": "+91 94121 00007",
        "keywords": ["snake", "saamp", "reptile", "scorpion", "bichhu"],
    },
    {
        "location": "Central Campus Works",
        "name": "Farrukh Siddiqui",
        "role": "Campus Fire & Gas Safety Officer",
        "dept": "Campus Safety & Emergency Response (EMERG)",
        "username": "emerg_centra_3",
        "contact": "+91 94121 00003",
        "keywords": ["fire", "smoke", "gas leak", "cylinder leak", "lpg", "flames", "burning smell", "explosion"],
    },
    {
        "location": "Central Campus Works",
        "name": "Waseem Akram",
        "role": "Aggressive Animal & Canine Squad Officer",
        "dept": "Campus Safety & Emergency Response (EMERG)",
        "username": "emerg_centra_8",
        "contact": "+91 94121 00008",
        "keywords": ["monkey", "monkeys", "dog bite", "dogbite", "rabid", "rabies", "animal attack", "wild animal"],
    },
    {
        "location": "Central Campus Works",
        "name": "Rashid Mehmood",
        "role": "Beehive, Wasp & Toxic Pest Controller",
        "dept": "Campus Safety & Emergency Response (EMERG)",
        "username": "emerg_centra_9",
        "contact": "+91 94121 00009",
        "keywords": ["beehive", "bee hive", "hornet", "hornets", "wasp", "wasps", "bee swarm", "bees"],
    },
    {
        "location": "Central Campus Works",
        "name": "Imran Zaidi",
        "role": "Disaster & Structural Evacuation Officer",
        "dept": "Campus Safety & Emergency Response (EMERG)",
        "username": "emerg_centra_10",
        "contact": "+91 94121 00010",
        "keywords": ["collapse", "ceiling collapse", "wall collapse", "electrocution", "live wire", "disaster"],
    },
    {
        "location": "Central Campus Works",
        "name": "Mohd Irfan",
        "role": "Proctorial Rapid Response Guard",
        "dept": "Campus Safety & Emergency Response (EMERG)",
        "username": "emerg_centra_4",
        "contact": "+91 94121 00004",
        "keywords": ["proctorial", "security threat", "guard", "emergency"],
    },
    {
        "location": "Central Campus Works",
        "name": "Shahnawaz Khan",
        "role": "Proctorial Rapid Response Guard",
        "dept": "Campus Safety & Emergency Response (EMERG)",
        "username": "emerg_centra_5",
        "contact": "+91 94121 00005",
        "keywords": ["proctorial", "security threat", "guard", "emergency"],
    },
    {
        "location": "Central Campus Works",
        "name": "Abdul Rauf",
        "role": "Night Shift Emergency Coordinator",
        "dept": "Campus Safety & Emergency Response (EMERG)",
        "username": "emerg_centra_6",
        "contact": "+91 94121 00006",
        "keywords": ["night shift", "emergency coordinator", "sos"],
    },
]

# Regex patterns for high-precision department categorization
DEPT_PATTERNS = {
    "EMERG": [
        r"\b(?:snake|saanp|saap|saamp|cobra|viper|python|reptile|reptiles|slithering|slithered|serpent|scorpion|bichhu)\b",
        r"\b(?:beehive|bee\s*hive|hornet|hornets|wasp|wasps|bee\s*swarm|bees\s*attack|yellow\s*jacket)\b",
        r"\b(?:fire|flames|flame|blaze|smoke|gas\s*leak|cylinder\s*leak|lpg\s*leak|gas\s*smell|burning\s*smell|explosion)\b",
        r"\b(?:dog\s*bite|dogbite|rabid|rabies|monkey|monkeys|wild\s*animal|aggressive\s*animal)\b",
        r"\b(?:electrocution|electric\s*shock|live\s*wire|ceiling\s*collapse|wall\s*collapse|roof\s*collapse)\b",
    ],
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
    For emergency life-safety complaints, ONLY assigns from the dedicated 10-person Emergency Response Team.
    """
    # Combine all complaint signals
    combined_signal = f"{category_name} {title} {description} {location_description}"
    dept_code = detect_department_code(combined_signal)

    # 0. EMERGENCY / LIFE-SAFETY FAST-PATH
    # If the issue is an emergency (snake, reptile, fire, gas, beehive, animal attack, etc.),
    # ONLY assign from the 10-person Emergency Response Team! Never normal trade staff.
    is_emergency = dept_code == "EMERG" or any(
        kw in combined_signal.lower()
        for kw in (
            "snake", "saamp", "saap", "cobra", "viper", "python", "reptile", "slithering",
            "beehive", "hornet", "wasp", "bee swarm", "fire", "gas leak", "cylinder leak",
            "dog bite", "monkey", "rabid", "animal attack", "electrocution"
        )
    ) or any(
        cat_kw in (category_name or "").lower()
        for cat_kw in ("snake", "reptile", "beehive", "hazard", "fire", "gas leak", "safety threat")
    )

    if is_emergency:
        lower_signal = combined_signal.lower()
        scored_emerg = []
        for member in EMERGENCY_ROSTER:
            score = 1.0
            # Boost based on exact emergency specialty match
            keywords = member.get("keywords", [])
            for kw in keywords:
                if kw in lower_signal:
                    score += 2.0
            scored_emerg.append((score, member))
        scored_emerg.sort(key=lambda item: -item[0])

        results = []
        for score, member in scored_emerg[:n]:
            results.append({
                "location": member["location"],
                "name": member["name"],
                "role": member["role"],
                "dept": member["dept"],
                "username": member["username"],
                "contact": member["contact"],
                "dept_code": "EMERG",
                "match_score": score,
                "match_reason": "🚨 Dedicated Campus Emergency Response Team",
            })
        return results

    staff_roster = _load_staff()
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
