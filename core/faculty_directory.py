"""
Canonical Directory of AMU Faculties, Teaching Departments, Residential Halls, and Hostels.
Provides validation and cross-referencing to ensure strict hierarchical integrity:
1. Every teaching department belongs to its designated Faculty.
2. Every constituent hostel belongs to its designated Residential Hall.
"""

import re
from typing import Dict, List, Optional, Tuple

# =============================================================================
# 1. CANONICAL AMU FACULTIES (13 ACADEMIC DIVISIONS)
# =============================================================================
FACULTIES: Dict[str, dict] = {
    "AGRI": {
        "code": "AGRI",
        "name": "Faculty of Agricultural Sciences",
        "building_code": "AGRI",
        "aliases": [
            "faculty of agricultural sciences", "agricultural sciences", "faculty of agriculture",
            "agriculture faculty", "agri faculty"
        ],
    },
    "ARTS": {
        "code": "ARTS",
        "name": "Faculty of Arts",
        "building_code": "ARTS",
        "aliases": [
            "faculty of arts", "arts & humanities", "arts and humanities", "faculty of arts and humanities"
        ],
    },
    "COMM": {
        "code": "COMM",
        "name": "Faculty of Commerce",
        "building_code": "COMM",
        "aliases": [
            "faculty of commerce", "commerce faculty"
        ],
    },
    "ENGG": {
        "code": "ENGG",
        "name": "Zakir Husain College of Engineering & Technology",
        "building_code": "ENGG",
        "aliases": [
            "zakir husain college of engineering & technology",
            "zakir husain college of engineering and technology",
            "faculty of engineering & technology", "faculty of engineering and technology",
            "engineering college", "engineering faculty", "zhcet", "zakir husain college"
        ],
    },
    "INTL": {
        "code": "INTL",
        "name": "Faculty of International Studies",
        "building_code": "INTL",
        "aliases": [
            "faculty of international studies", "international studies"
        ],
    },
    "LAW": {
        "code": "LAW",
        "name": "Faculty of Law",
        "building_code": "LAW",
        "aliases": [
            "faculty of law", "law faculty"
        ],
    },
    "LIFE": {
        "code": "LIFE",
        "name": "Faculty of Life Sciences",
        "building_code": "LIFE",
        "aliases": [
            "faculty of life sciences", "life sciences faculty", "life sciences"
        ],
    },
    "MGMT": {
        "code": "MGMT",
        "name": "Faculty of Management Studies & Research",
        "building_code": "MGMT",
        "aliases": [
            "faculty of management studies & research",
            "faculty of management studies and research",
            "faculty of management studies", "management studies", "fmsr"
        ],
    },
    "SCI": {
        "code": "SCI",
        "name": "Faculty of Science",
        "building_code": "SCI",
        "aliases": [
            "faculty of science", "science faculty"
        ],
    },
    "SOC": {
        "code": "SOC",
        "name": "Faculty of Social Sciences",
        "building_code": "SOC",
        "aliases": [
            "faculty of social sciences", "social sciences faculty", "social sciences"
        ],
    },
    "THEO": {
        "code": "THEO",
        "name": "Faculty of Theology",
        "building_code": "THEO",
        "aliases": [
            "faculty of theology", "theology faculty"
        ],
    },
    "MED": {
        "code": "MED",
        "name": "Jawaharlal Nehru Medical College",
        "building_code": "MED",
        "aliases": [
            "jawaharlal nehru medical college", "jnmc", "faculty of medicine",
            "medical college", "dr. ziauddin ahmad dental college", "dental college"
        ],
    },
    "UNANI": {
        "code": "UNANI",
        "name": "Ajmal Khan Tibbiya College",
        "building_code": "UNANI",
        "aliases": [
            "ajmal khan tibbiya college", "tibbiya college", "faculty of unani medicine",
            "unani medicine", "tibbiya"
        ],
    },
}

# =============================================================================
# 2. CANONICAL AMU TEACHING DEPARTMENTS (118 DEPARTMENTS)
# =============================================================================
STRUCTURED_TEACHING_DEPARTMENTS: List[dict] = [
    # Faculty of Agricultural Sciences (AGRI)
    {"name": "Agricultural Eco. & Business Mngt.", "code": "AGRI_ECON", "faculty": "AGRI", "building": "AGRI", "aliases": ["agricultural economics", "agricultural eco", "agricultural eco & business mngt"]},
    {"name": "Agricultural Microbiology", "code": "AGRI_MICRO", "faculty": "AGRI", "building": "AGRI", "aliases": ["agri microbiology"]},
    {"name": "Home Sciences", "code": "AGRI_HOMESC", "faculty": "AGRI", "building": "AGRI", "aliases": ["home science"]},
    {"name": "Plant Protection", "code": "AGRI_PLANT", "faculty": "AGRI", "building": "AGRI", "aliases": []},
    {"name": "Post Harvest Engineering And Technology", "code": "AGRI_POSTHV", "faculty": "AGRI", "building": "AGRI", "aliases": ["post harvest engineering"]},

    # Faculty of Arts (ARTS)
    {"name": "Arabic", "code": "ARTS_ARABIC", "faculty": "ARTS", "building": "ARTS", "aliases": ["department of arabic"]},
    {"name": "English", "code": "ARTS_ENGL", "faculty": "ARTS", "building": "ARTS", "aliases": ["department of english"]},
    {"name": "Fine Arts", "code": "ARTS_FINE", "faculty": "ARTS", "building": "ARTS", "aliases": ["department of fine arts"]},
    {"name": "Foreign Languages", "code": "ARTS_FORLANG", "faculty": "ARTS", "building": "ARTS", "aliases": ["department of foreign languages"]},
    {"name": "Hindi", "code": "ARTS_HINDI", "faculty": "ARTS", "building": "ARTS", "aliases": ["department of hindi"]},
    {"name": "Linguistics", "code": "ARTS_LING", "faculty": "ARTS", "building": "ARTS", "aliases": ["department of linguistics"]},
    {"name": "Modern Indian Languages", "code": "ARTS_MIL", "faculty": "ARTS", "building": "ARTS", "aliases": ["department of modern indian languages"]},
    {"name": "Persian", "code": "ARTS_PERSIAN", "faculty": "ARTS", "building": "ARTS", "aliases": ["department of persian"]},
    {"name": "Philosophy", "code": "ARTS_PHIL", "faculty": "ARTS", "building": "ARTS", "aliases": ["department of philosophy"]},
    {"name": "Sanskrit", "code": "ARTS_SANSKR", "faculty": "ARTS", "building": "ARTS", "aliases": ["department of sanskrit"]},
    {"name": "Urdu", "code": "ARTS_URDU", "faculty": "ARTS", "building": "ARTS", "aliases": ["department of urdu"]},

    # Faculty of Commerce (COMM)
    {"name": "Commerce", "code": "COMM", "faculty": "COMM", "building": "COMM", "aliases": ["department of commerce"]},

    # Zakir Husain College of Engineering & Technology (ENGG)
    {"name": "Applied Chemistry", "code": "ENGG_APPCHM", "faculty": "ENGG", "building": "ENGG", "aliases": ["department of applied chemistry"]},
    {"name": "Applied Mathematics", "code": "ENGG_APPMTH", "faculty": "ENGG", "building": "ENGG", "aliases": ["department of applied mathematics"]},
    {"name": "Applied Physics", "code": "ENGG_APPPHY", "faculty": "ENGG", "building": "ENGG", "aliases": ["department of applied physics"]},
    {"name": "Architecture", "code": "ENGG_ARCH", "faculty": "ENGG", "building": "ENGG", "aliases": ["department of architecture", "architecture engineering"]},
    {"name": "Chemical Engineering", "code": "ENGG_CHEM", "faculty": "ENGG", "building": "ENGG", "aliases": ["department of chemical engineering"]},
    {"name": "Civil Engineering", "code": "ENGG_CIVIL", "faculty": "ENGG", "building": "ENGG", "aliases": ["department of civil engineering"]},
    {"name": "Computer Engineering", "code": "ENGG_COMP", "faculty": "ENGG", "building": "ENGG", "aliases": ["department of computer engineering"]},
    {"name": "Electrical Engineering", "code": "ENGG_ELEC", "faculty": "ENGG", "building": "ENGG", "aliases": ["department of electrical engineering"]},
    {"name": "Electronics Engineering", "code": "ENGG_ELX", "faculty": "ENGG", "building": "ENGG", "aliases": ["department of electronics engineering"]},
    {"name": "Mechanical Engineering", "code": "ENGG_MECH", "faculty": "ENGG", "building": "ENGG", "aliases": ["department of mechanical engineering"]},
    {"name": "Petroleum Studies", "code": "ENGG_PETRO", "faculty": "ENGG", "building": "ENGG", "aliases": ["department of petroleum studies"]},

    # Faculty of International Studies (INTL)
    {"name": "South African & Brazilian Studies", "code": "INTL_SABS", "faculty": "INTL", "building": "INTL", "aliases": ["centre for south african & brazilian studies"]},
    {"name": "West Asian Studies And North African Studies", "code": "INTL_WASNAS", "faculty": "INTL", "building": "INTL", "aliases": ["west asian studies", "department of west asian studies"]},

    # Faculty of Law (LAW)
    {"name": "Law", "code": "LAW", "faculty": "LAW", "building": "LAW", "aliases": ["department of law"]},
    {"name": "Law - Malappuram", "code": "LAW_MALAP", "faculty": "LAW", "building": "LAW", "aliases": []},
    {"name": "Law - Murshidabad", "code": "LAW_MURSH", "faculty": "LAW", "building": "LAW", "aliases": []},

    # Faculty of Life Sciences (LIFE)
    {"name": "Bio-Chemistry (Life Sciences)", "code": "LIFE_BIOCHM", "faculty": "LIFE", "building": "LIFE", "aliases": ["biochemistry (life sciences)", "life sciences biochemistry"]},
    {"name": "Botany", "code": "LIFE_BOTANY", "faculty": "LIFE", "building": "LIFE", "aliases": ["department of botany"]},
    {"name": "Interdisciplinary Biotechnology Unit", "code": "LIFE_IBU", "faculty": "LIFE", "building": "LIFE", "aliases": ["biotechnology unit", "ibu"]},
    {"name": "Wildlife Sciences", "code": "LIFE_WILDLF", "faculty": "LIFE", "building": "LIFE", "aliases": ["department of wildlife sciences", "wildlife science"]},
    {"name": "Zoology", "code": "LIFE_ZOOLOGY", "faculty": "LIFE", "building": "LIFE", "aliases": ["department of zoology"]},

    # Faculty of Management Studies & Research (MGMT)
    {"name": "Business Administration", "code": "MGMT_BA", "faculty": "MGMT", "building": "MGMT", "aliases": ["department of business administration", "mba department"]},
    {"name": "Business Administration - Malappuram", "code": "MGMT_BAMAL", "faculty": "MGMT", "building": "MGMT", "aliases": []},
    {"name": "Business Administration - Murshidabad", "code": "MGMT_BAMUR", "faculty": "MGMT", "building": "MGMT", "aliases": []},

    # Faculty of Science (SCI)
    {"name": "Physics", "code": "DEPT_PHYS", "faculty": "SCI", "building": "SCI", "aliases": ["department of physics"]},
    {"name": "Chemistry", "code": "DEPT_CHEM", "faculty": "SCI", "building": "SCI", "aliases": ["department of chemistry"]},
    {"name": "Computer Science", "code": "SCI_CS", "faculty": "SCI", "building": "SCI", "aliases": ["department of computer science", "comp science", "dept of computer science"]},
    {"name": "Geography", "code": "SCI_GEOG", "faculty": "SCI", "building": "SCI", "aliases": ["department of geography"]},
    {"name": "Geology", "code": "SCI_GEOL", "faculty": "SCI", "building": "SCI", "aliases": ["department of geology"]},
    {"name": "Industrial Chemistry", "code": "SCI_INDCHM", "faculty": "SCI", "building": "SCI", "aliases": ["department of industrial chemistry"]},
    {"name": "Interdisciplinary Department Of Remote Sensing And GIS Applications", "code": "SCI_RSGIS", "faculty": "SCI", "building": "SCI", "aliases": ["remote sensing and gis", "remote sensing", "gis applications"]},
    {"name": "Mathematics", "code": "SCI_MATH", "faculty": "SCI", "building": "SCI", "aliases": ["department of mathematics"]},
    {"name": "Statistics And Operations Research", "code": "SCI_STATS", "faculty": "SCI", "building": "SCI", "aliases": ["department of statistics", "statistics & operations research", "statistics and operations research"]},

    # Faculty of Social Sciences (SOC)
    {"name": "Advanced Centre For Women's Studies", "code": "SOC_CWS", "faculty": "SOC", "building": "SOC", "aliases": ["women's studies", "centre for women's studies"]},
    {"name": "Economics", "code": "SOC_ECON", "faculty": "SOC", "building": "SOC", "aliases": ["department of economics"]},
    {"name": "Education", "code": "SOC_EDU", "faculty": "SOC", "building": "SOC", "aliases": ["department of education"]},
    {"name": "Education - Malappuram", "code": "SOC_EDUMAL", "faculty": "SOC", "building": "SOC", "aliases": []},
    {"name": "Education - Murshidabad", "code": "SOC_EDUMUR", "faculty": "SOC", "building": "SOC", "aliases": []},
    {"name": "History", "code": "SOC_HIST", "faculty": "SOC", "building": "SOC", "aliases": ["department of history"]},
    {"name": "Islamic Studies", "code": "SOC_ISLAM", "faculty": "SOC", "building": "SOC", "aliases": ["department of islamic studies"]},
    {"name": "Library And Information Science", "code": "SOC_LIS", "faculty": "SOC", "building": "SOC", "aliases": ["library & information science", "department of library and information science"]},
    {"name": "Mass Communication", "code": "SOC_MASSCOMM", "faculty": "SOC", "building": "SOC", "aliases": ["department of mass communication", "mass comm"]},
    {"name": "Museology", "code": "SOC_MUSEOL", "faculty": "SOC", "building": "SOC", "aliases": ["department of museology"]},
    {"name": "Physical Education", "code": "SOC_PHYEDU", "faculty": "SOC", "building": "SOC", "aliases": ["department of physical education"]},
    {"name": "Political Science", "code": "SOC_POLSCI", "faculty": "SOC", "building": "SOC", "aliases": ["department of political science", "pol science"]},
    {"name": "Psychology", "code": "SOC_PSYCH", "faculty": "SOC", "building": "SOC", "aliases": ["department of psychology"]},
    {"name": "Social Work", "code": "SOC_SOCWORK", "faculty": "SOC", "building": "SOC", "aliases": ["department of social work"]},
    {"name": "Sociology", "code": "SOC_SOCIOL", "faculty": "SOC", "building": "SOC", "aliases": ["department of sociology"]},
    {"name": "Strategic & Security Studies", "code": "SOC_STRAT", "faculty": "SOC", "building": "SOC", "aliases": ["strategic and security studies", "department of strategic & security studies"]},
    {"name": "Women's College", "code": "SOC_WOMENCOL", "faculty": "SOC", "building": "SOC", "aliases": ["women's college amu"]},

    # Faculty of Theology (THEO)
    {"name": "Shia Theology", "code": "THEO_SHIA", "faculty": "THEO", "building": "THEO", "aliases": ["department of shia theology"]},
    {"name": "Sunni Theology", "code": "THEO_SUNNI", "faculty": "THEO", "building": "THEO", "aliases": ["department of sunni theology"]},
    {"name": "K. A. Nizami Centre For Quranic Studies", "code": "THEO_KANQS", "faculty": "THEO", "building": "THEO", "aliases": ["quranic studies", "nizami centre for quranic studies"]},

    # Jawaharlal Nehru Medical College & Dental College (MED)
    {"name": "Anaesthesiology", "code": "MED_ANAESTH", "faculty": "MED", "building": "MED", "aliases": ["department of anaesthesiology", "anesthesia"]},
    {"name": "Anatomy", "code": "MED_ANATOMY", "faculty": "MED", "building": "MED", "aliases": ["department of anatomy"]},
    {"name": "Bio-Chemistry (JNMC)", "code": "MED_BIOCHM", "faculty": "MED", "building": "MED", "aliases": ["biochemistry (jnmc)", "medical biochemistry"]},
    {"name": "Cardiology", "code": "MED_CARDIO", "faculty": "MED", "building": "MED", "aliases": ["department of cardiology"]},
    {"name": "Cardiothoracic Surgery", "code": "MED_CTSURG", "faculty": "MED", "building": "MED", "aliases": ["department of cardiothoracic surgery", "ct surgery"]},
    {"name": "Community Medicine", "code": "MED_COMMED", "faculty": "MED", "building": "MED", "aliases": ["department of community medicine"]},
    {"name": "Conservative Dentistry & Endodontics", "code": "MED_DENTCONS", "faculty": "MED", "building": "MED", "aliases": ["conservative dentistry"]},
    {"name": "Dermatology", "code": "MED_DERMAT", "faculty": "MED", "building": "MED", "aliases": ["department of dermatology"]},
    {"name": "Forensic Medicine", "code": "MED_FORENS", "faculty": "MED", "building": "MED", "aliases": ["department of forensic medicine"]},
    {"name": "Medicine", "code": "MED_MEDICIN", "faculty": "MED", "building": "MED", "aliases": ["department of medicine"]},
    {"name": "Microbiology", "code": "MED_MICRO", "faculty": "MED", "building": "MED", "aliases": ["department of microbiology (medical)"]},
    {"name": "Neuro Surgery", "code": "MED_NEUROS", "faculty": "MED", "building": "MED", "aliases": ["department of neuro surgery", "neurosurgery"]},
    {"name": "Obstetrics And Gynaecology", "code": "MED_OBSGYN", "faculty": "MED", "building": "MED", "aliases": ["obstetrics & gynaecology", "obs & gynae", "gynecology"]},
    {"name": "Ophthalmology", "code": "MED_OPHTHAL", "faculty": "MED", "building": "MED", "aliases": ["department of ophthalmology", "eye department"]},
    {"name": "Oral & Maxillofacial Surgery", "code": "MED_OMFS", "faculty": "MED", "building": "MED", "aliases": ["maxillofacial surgery", "omfs"]},
    {"name": "Oral Medicine And Radiology", "code": "MED_OMRAD", "faculty": "MED", "building": "MED", "aliases": ["oral medicine & radiology"]},
    {"name": "Oral Pathology And Microbiology", "code": "MED_OPATH", "faculty": "MED", "building": "MED", "aliases": ["oral pathology"]},
    {"name": "Orthodontics And Dentofacial Orthopedics And Dental Anatomy", "code": "MED_ORTHOD", "faculty": "MED", "building": "MED", "aliases": ["orthodontics"]},
    {"name": "Orthopaedic Surgery", "code": "MED_ORTHOP", "faculty": "MED", "building": "MED", "aliases": ["orthopaedics", "orthopedics", "department of orthopaedic surgery"]},
    {"name": "OTO-Rhino-Laryngology (E.N.T.)", "code": "MED_ENT", "faculty": "MED", "building": "MED", "aliases": ["ent department", "oto-rhino-laryngology", "ent"]},
    {"name": "Paediatric Surgery", "code": "MED_PAEDSRG", "faculty": "MED", "building": "MED", "aliases": ["pediatric surgery"]},
    {"name": "Paediatrics", "code": "MED_PAEDIAT", "faculty": "MED", "building": "MED", "aliases": ["pediatrics", "department of paediatrics"]},
    {"name": "Paediatrics & Preventive Dentistry", "code": "MED_PAEDENT", "faculty": "MED", "building": "MED", "aliases": ["pediatric dentistry"]},
    {"name": "Pathology", "code": "MED_PATHOL", "faculty": "MED", "building": "MED", "aliases": ["department of pathology"]},
    {"name": "Periodontology", "code": "MED_PERIOD", "faculty": "MED", "building": "MED", "aliases": ["department of periodontology"]},
    {"name": "Pharmacology", "code": "MED_PHARMA", "faculty": "MED", "building": "MED", "aliases": ["department of pharmacology"]},
    {"name": "Physiology", "code": "MED_PHYSIOL", "faculty": "MED", "building": "MED", "aliases": ["department of physiology"]},
    {"name": "Plastic Surgery", "code": "MED_PLASTSRG", "faculty": "MED", "building": "MED", "aliases": ["department of plastic surgery"]},
    {"name": "Prosthodontics/Dental Material", "code": "MED_PROSTH", "faculty": "MED", "building": "MED", "aliases": ["prosthodontics"]},
    {"name": "Psychiatry", "code": "MED_PSYCH", "faculty": "MED", "building": "MED", "aliases": ["department of psychiatry"]},
    {"name": "Public Health Dentistry", "code": "MED_PUBDENT", "faculty": "MED", "building": "MED", "aliases": ["community dentistry"]},
    {"name": "Radio-Diagnosis", "code": "MED_RADIOD", "faculty": "MED", "building": "MED", "aliases": ["radiology", "department of radio-diagnosis"]},
    {"name": "Radiotherapy", "code": "MED_RADIOTH", "faculty": "MED", "building": "MED", "aliases": ["department of radiotherapy"]},
    {"name": "Surgery", "code": "MED_SURGERY", "faculty": "MED", "building": "MED", "aliases": ["department of surgery", "general surgery"]},
    {"name": "TB And Chest Diseases", "code": "MED_TBCHEST", "faculty": "MED", "building": "MED", "aliases": ["tb & chest diseases", "chest diseases", "pulmonary medicine"]},

    # Ajmal Khan Tibbiya College (UNANI)
    {"name": "Amraze Jild Wa Zohrawiya", "code": "UNN_JILD", "faculty": "UNANI", "building": "UNANI", "aliases": ["amraze jild"]},
    {"name": "Ilaj-Bit-Tadbeer", "code": "UNN_ILAJ", "faculty": "UNANI", "building": "UNANI", "aliases": ["ilaj bit tadbeer"]},
    {"name": "Ilmul Advia", "code": "UNN_ADVIA", "faculty": "UNANI", "building": "UNANI", "aliases": ["ilmul advia"]},
    {"name": "Ilmul Amraz", "code": "UNN_AMRAZ", "faculty": "UNANI", "building": "UNANI", "aliases": ["ilmul amraz"]},
    {"name": "Ilmul Atfal", "code": "UNN_ATFAL", "faculty": "UNANI", "building": "UNANI", "aliases": ["ilmul atfal"]},
    {"name": "Jarahat", "code": "UNN_JARAHAT", "faculty": "UNANI", "building": "UNANI", "aliases": ["unani jarahat", "department of jarahat"]},
    {"name": "Kulliyat", "code": "UNN_KULLIYAT", "faculty": "UNANI", "building": "UNANI", "aliases": ["department of kulliyat"]},
    {"name": "Moalajat (Medicine)", "code": "UNN_MOALAJ", "faculty": "UNANI", "building": "UNANI", "aliases": ["moalajat", "department of moalajat"]},
    {"name": "Niswan Wa Qabalat", "code": "UNN_NISWAN", "faculty": "UNANI", "building": "UNANI", "aliases": ["niswan wa qabalat"]},
    {"name": "Saidla", "code": "UNN_SAIDLA", "faculty": "UNANI", "building": "UNANI", "aliases": ["department of saidla"]},
    {"name": "Tahaffuzi-Wa-Samaji-Tib", "code": "UNN_TAHAFF", "faculty": "UNANI", "building": "UNANI", "aliases": ["tahaffuzi wa samaji tib", "tahaffuzi"]},
    {"name": "Tashreeh Wa Munafeul Aza", "code": "UNN_TASHMUN", "faculty": "UNANI", "building": "UNANI", "aliases": ["tashreeh wa munafeul aza", "tashreeh"]},
    {"name": "Tashreehul Badan", "code": "UNN_TASHBAD", "faculty": "UNANI", "building": "UNANI", "aliases": ["tashreehul badan"]},
]

# Fast lookup mappings
DEPT_BY_CODE = {item["code"].upper(): item for item in STRUCTURED_TEACHING_DEPARTMENTS}
DEPT_BY_NAME = {item["name"].lower(): item for item in STRUCTURED_TEACHING_DEPARTMENTS}


def detect_faculty(text: str) -> Optional[dict]:
    """
    Identifies if an AMU faculty/academic division is explicitly mentioned in the text.
    """
    if not text:
        return None
    raw_lower = text.lower()

    # 1. Match by official name and aliases (longest first)
    for code, fac in sorted(FACULTIES.items(), key=lambda x: len(x[1]["name"]), reverse=True):
        pattern = r"\b" + re.escape(fac["name"].lower()) + r"\b"
        if re.search(pattern, raw_lower):
            return fac
        for alias in sorted(fac["aliases"], key=len, reverse=True):
            if len(alias) >= 4:
                alias_pattern = r"\b" + re.escape(alias) + r"\b"
                if re.search(alias_pattern, raw_lower):
                    return fac

    # 2. Match by faculty code as a bracketed or bounded word
    for code, fac in FACULTIES.items():
        pattern = r"(?:faculty\s*(?:of)?\s*|\[|\()(?:\b" + re.escape(code.lower()) + r"\b)(?:\]|\))?"
        if re.search(pattern, raw_lower):
            return fac

    return None


def detect_department(text: str) -> Optional[dict]:
    """
    Identifies if a specific AMU teaching department is explicitly mentioned in the text.
    Avoids false matches from faculty titles (e.g. 'Faculty of Law' should not be matched as Dept of Law).
    """
    if not text:
        return None
    raw_lower = text.lower()

    # 1. Check for explicit bracketed code e.g. [SCI_CS] or (UNN_TASHBAD) or dept: SCI_CS
    for code, dept in DEPT_BY_CODE.items():
        if len(code) > 4:
            pattern = r"(?<![A-Za-z0-9_])" + re.escape(code.lower()) + r"(?![A-Za-z0-9_])"
            if re.search(pattern, raw_lower):
                return dept

    # 2. Check for "department of <name>" or "dept of <name>" or full department name
    # Sort by longest name first to match "Computer Science" before "Science"
    sorted_depts = sorted(STRUCTURED_TEACHING_DEPARTMENTS, key=lambda x: len(x["name"]), reverse=True)
    
    # Priority A: Check explicit "Department of X"
    for dept in sorted_depts:
        name_lower = dept["name"].lower()
        dept_pattern = r"\b(?:department|dept)\s+of\s+" + re.escape(name_lower) + r"\b"
        if re.search(dept_pattern, raw_lower):
            return dept

    # Priority B: Check department name and aliases (longest first)
    # Exclude base discipline matches if part of a compound department (e.g. bio-chemistry, applied chemistry)
    COMPOUND_PREFIXES = {
        "chemistry": [r"bio-", r"biochemical\s*", r"applied\s+", r"industrial\s+"],
        "physics": [r"applied\s+"],
        "mathematics": [r"applied\s+"],
        "microbiology": [r"agricultural\s+", r"agri\s+"],
        "biotechnology": [r"interdisciplinary\s+"],
    }

    for dept in sorted_depts:
        name_lower = dept["name"].lower()
        if len(name_lower) >= 4:
            pattern = r"\b" + re.escape(name_lower) + r"\b"
            for match in re.finditer(pattern, raw_lower):
                start = match.start()
                preceding = raw_lower[max(0, start - 25):start]
                # If preceded by "faculty of ", this is a faculty reference, not department
                if "faculty of" in preceding or "faculty" in preceding:
                    continue
                # If base discipline is preceded by compound prefix, skip base match
                prec_strip = preceding.rstrip()
                if name_lower == "chemistry" and any(prec_strip.endswith(p) for p in ["bio-", "applied", "industrial"]):
                    continue
                if name_lower == "physics" and prec_strip.endswith("applied"):
                    continue
                if name_lower == "mathematics" and prec_strip.endswith("applied"):
                    continue
                if name_lower == "microbiology" and any(prec_strip.endswith(p) for p in ["agricultural", "agri"]):
                    continue
                return dept

        for alias in sorted(dept.get("aliases", []), key=len, reverse=True):
            if len(alias) >= 4:
                alias_pattern = r"\b" + re.escape(alias) + r"\b"
                for match in re.finditer(alias_pattern, raw_lower):
                    start = match.start()
                    preceding = raw_lower[max(0, start - 15):start]
                    if "faculty of" in preceding:
                        continue
                    return dept

    # Priority C: Short codes e.g. [LAW] or [COMM] when explicitly in brackets or following 'dept:'
    for code in ["COMM", "LAW"]:
        if code in DEPT_BY_CODE:
            pattern = r"(?:\[|\(|dept:?\s*)" + re.escape(code.lower()) + r"(?:\]|\))?"
            if re.search(pattern, raw_lower):
                return DEPT_BY_CODE[code]

    return None


def verify_department_and_faculty(text: str) -> Tuple[bool, Optional[str]]:
    """
    Verifies that if both a Department and a Faculty are referenced in the complaint text,
    the department belongs to that faculty.
    Returns:
        (True, None) if consistent or if only one/neither is mentioned.
        (False, error_message) if mismatched.
    """
    dept = detect_department(text)
    fac = detect_faculty(text)

    if dept and fac:
        expected_fac_code = dept["faculty"]
        if fac["code"].upper() != expected_fac_code.upper():
            expected_fac = FACULTIES.get(expected_fac_code, {})
            expected_name = expected_fac.get("name", expected_fac_code)
            detected_name = fac["name"]
            msg = (
                f"Mismatched Academic Hierarchy: Department '{dept['name']}' belongs to "
                f"'{expected_name}', not '{detected_name}'. Please verify the department and faculty."
            )
            return False, msg

    return True, None


def get_faculty_for_department(dept_code_or_name: str) -> Optional[dict]:
    """Returns faculty dictionary for a given department name or code."""
    if not dept_code_or_name:
        return None
    key = dept_code_or_name.strip()
    if key.upper() in DEPT_BY_CODE:
        fac_code = DEPT_BY_CODE[key.upper()]["faculty"]
        return FACULTIES.get(fac_code)
    if key.lower() in DEPT_BY_NAME:
        fac_code = DEPT_BY_NAME[key.lower()]["faculty"]
        return FACULTIES.get(fac_code)
    # Search aliases
    for dept in STRUCTURED_TEACHING_DEPARTMENTS:
        if any(a == key.lower() for a in dept.get("aliases", [])):
            return FACULTIES.get(dept["faculty"])
    return None


def verify_hostel_and_hall(text: str) -> Tuple[bool, Optional[str]]:
    """
    Verifies that if both a constituent Hostel and a Residential Hall are referenced,
    the hostel strictly belongs to that Hall.
    """
    if not text:
        return True, None
    raw_lower = text.lower()

    # Lazy import to avoid circular dependencies during Django startup
    from core.models import Building

    all_hostels = list(Building.objects.filter(building_type="hostel", parent__isnull=False).select_related("parent"))
    all_halls = list(Building.objects.filter(building_type="hall", parent__isnull=True))

    detected_hostel = None
    # Sort hostels by name length descending for most specific match
    for h in sorted(all_hostels, key=lambda x: len(x.name), reverse=True):
        h_name_low = h.name.lower()
        short_low = h.short_name.lower() if h.short_name else ""
        if h_name_low in raw_lower:
            detected_hostel = h
            break
        # Match short name if unique and >= 5 chars
        if short_low and len(short_low) >= 5 and short_low in raw_lower:
            detected_hostel = h
            break

    if not detected_hostel:
        return True, None

    detected_hall = None
    for hall in sorted(all_halls, key=lambda x: len(x.name), reverse=True):
        hall_name_low = hall.name.lower()
        short_low = hall.short_name.lower() if hall.short_name else ""
        code_low = hall.code.lower()
        if hall_name_low in raw_lower:
            detected_hall = hall
            break
        if short_low and len(short_low) >= 4 and short_low in raw_lower:
            detected_hall = hall
            break
        if re.search(r"\b" + re.escape(code_low) + r"\b", raw_lower):
            detected_hall = hall
            break

    if detected_hostel and detected_hall:
        if detected_hostel.parent_id != detected_hall.id:
            msg = (
                f"Mismatched Residential Hierarchy: Hostel '{detected_hostel.short_name or detected_hostel.name}' "
                f"belongs to '{detected_hostel.parent.name}', not '{detected_hall.name}'. "
                f"Please verify the residential hall and hostel."
            )
            return False, msg

    return True, None
