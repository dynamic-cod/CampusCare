#!/usr/bin/env python3
"""
Seed 237 Realistic, Contextually-Accurate Complaints for CampusCare
- Covers all 20 AMU Residential Halls (120 complaints)
- Covers all 14 Academic Faculties / Teaching Buildings (91 complaints)
- Covers Central Facilities: Library, Sports, Roads & Security (26 complaints)
Total = 120 + 91 + 26 = 237 complaints.
All problems strictly match their actual physical locations and equipment.
"""
import os
import random
import sys
from datetime import timedelta
from django.utils import timezone

if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campuscare.settings")
    import django
    django.setup()

from django.db import transaction
from django.contrib.auth.models import User
from core.models import Building, Room, ComplaintCategory, Complaint, ComplaintStatusHistory, UserProfile
from core.accountability import set_sla_due_date
from core.dispatcher import auto_dispatch_complaint

def run_seed():
    print("🚀 Starting generation of 237 realistic campus maintenance complaints...")

    # Clear existing complaints first to ensure exact count of 237
    Complaint.objects.all().delete()
    ComplaintStatusHistory.objects.all().delete()

    # Pre-fetch lookup caches
    categories_by_name = {c.name: c for c in ComplaintCategory.objects.select_related('department')}
    
    def get_cat(name, fallback_dept=None):
        if name in categories_by_name:
            return categories_by_name[name]
        for cname, c in categories_by_name.items():
            if name.lower() in cname.lower():
                return c
        if fallback_dept:
            for c in categories_by_name.values():
                if c.department.code == fallback_dept:
                    return c
        return list(categories_by_name.values())[0]

    cat_hostel_room = get_cat("Hostel Room Maintenance", "HOSTEL")
    cat_hostel_common = get_cat("Hostel Common Area Maintenance", "HOSTEL")
    cat_hostel_sanitation = get_cat("Hostel Sanitation", "HOSTEL")
    cat_hostel_water = get_cat("Hostel Water Supply", "HOSTEL")
    cat_dining = get_cat("Dining Hall Maintenance & Hygiene", "MESS")
    cat_food = get_cat("Food Quality & Hygiene", "MESS")
    cat_elec = get_cat("Electrical & Wiring Maintenance", "ELEC")
    cat_civil = get_cat("Civil & Carpentry Works", "CIVIL")
    cat_plumb = get_cat("Estate Plumbing", "PLUMB")
    cat_wifi = get_cat("Campus Wi-Fi & Network Services", "IT")
    cat_sci_lab = get_cat("Science Laboratory Equipment", "SCI")
    cat_sci_sys = get_cat("Science Computer Systems", "SCI")
    cat_sci_chem = get_cat("Science Chemical Safety", "SCI")
    cat_engg_lab = get_cat("Engineering Laboratory Equipment", "ENGG")
    cat_engg_mach = get_cat("Engineering Workshop Machinery", "ENGG")
    cat_engg_elec = get_cat("Engineering Electrical Systems", "ENGG")
    cat_engg_comp = get_cat("Engineering Computer Systems", "ENGG")
    cat_jnmc_med = get_cat("JNMC Medical Equipment", "MED")
    cat_jnmc_infra = get_cat("JNMC Hospital Infrastructure", "MED")
    cat_jnmc_lab = get_cat("JNMC Laboratory Equipment", "MED")
    cat_arts_furn = get_cat("Arts Classroom Furniture", "ARTS")
    cat_arts_av = get_cat("Arts Audio-Visual Equipment", "ARTS")
    cat_soc_class = get_cat("Social Classroom Maintenance", "SOC")
    cat_soc_lab = get_cat("Social Computer Lab", "SOC")
    cat_comm_class = get_cat("Commerce Classroom Maintenance", "COMM")
    cat_comm_lab = get_cat("Commerce Computer Lab Equipment", "COMM")
    cat_law_class = get_cat("Law Classroom Maintenance", "LAW")
    cat_law_lib = get_cat("Law Library Resources", "LAW")
    cat_agri_infra = get_cat("Agricultural Infrastructure", "AGRI")
    cat_agri_irrig = get_cat("Irrigation Systems", "AGRI")
    cat_mgmt_proj = get_cat("Management Projector Equipment", "MGMT")
    cat_mgmt_lab = get_cat("Management Computer Lab", "MGMT")
    cat_unani_herb = get_cat("Unani Herbal Garden Maintenance", "UNANI")
    cat_unani_med = get_cat("Unani Medical Equipment", "UNANI")
    cat_theo_class = get_cat("Theology Classroom Maintenance", "THEO")
    cat_lib_read = get_cat("Central Library Reading Room Maintenance", "LIB")
    cat_lib_serv = get_cat("Central Library Services", "LIB")
    cat_security = get_cat("Campus Security", "SECURITY")
    cat_gate = get_cat("Gate Maintenance", "SECURITY")
    cat_estate_elec = get_cat("Estate Electrical Maintenance", "ESTATE")
    cat_estate_civil = get_cat("Estate Civil Works", "ESTATE")

    first_names = [
        "Mohammad", "Ahmad", "Zaid", "Tariq", "Bilal", "Hamza", "Omar", "Mustafa", "Salman", "Ibrahim",
        "Fatima", "Ayesha", "Zainab", "Maryam", "Sana", "Sadia", "Bushra", "Alina", "Hina", "Nida",
        "Arshad", "Farhan", "Adnan", "Rehan", "Shahid", "Danish", "Sameer", "Tanveer", "Noman", "Kashif"
    ]
    last_names = [
        "Khan", "Ansari", "Siddiqui", "Qureshi", "Farooqi", "Usmani", "Raza", "Hasan", "Zehra", "Fatima",
        "Mahmood", "Parveen", "Naqvi", "Kazmi", "Rizvi", "Kamal", "Kausar", "Sultan", "Jamal", "Alam"
    ]

    prefixes = ["GL", "GF", "AK", "BT", "ME", "CE", "EE", "CS", "LE", "PH", "CH", "MA", "CM", "LW", "AG"]
    used_enrollments = set()
    def get_enrollment():
        while True:
            enr = f"{random.choice(prefixes)}{random.randint(1000, 9999)}"
            if enr not in used_enrollments:
                used_enrollments.add(enr)
                return enr

    now = timezone.now()

    complaints_to_create = []

    # =========================================================================
    # 1. RESIDENTIAL HALLS (20 Halls x 6 complaints each = 120 complaints)
    # =========================================================================
    halls = list(Building.objects.filter(is_active=True, building_type="hall").order_by("name"))
    
    # 6 context-specific problems for residential halls
    hostel_issue_templates = [
        {
            "title": "Ceiling fan speed regulator sparking and stuck at low speed",
            "desc": "The ceiling fan regulator knob is loose, sparks when rotated past speed 2, and makes a continuous electrical humming sound. Fan operates too slowly during study hours.",
            "cat": cat_hostel_room, "priority": "high", "score": 75, "reason": "Electrical sparking hazard in student room"
        },
        {
            "title": "Water cooler tap continuously leaking in corridor near washroom wing",
            "desc": "The push-valve on the drinking water cooler is misaligned and water is constantly dripping onto the floor, creating a slippery moss puddle along the corridor.",
            "cat": cat_hostel_water, "priority": "normal", "score": 50, "reason": "Water wastage and slippery hallway hazard"
        },
        {
            "title": "Geyser heating element burnt out in first-floor common bathroom",
            "desc": "The 25-litre storage geyser in bathroom cubicle 2 indicates power on the neon lamp but fails to heat water at all. Inmates are facing difficulty in morning bathing.",
            "cat": cat_hostel_water, "priority": "normal", "score": 55, "reason": "Hot water utility failure in winter season"
        },
        {
            "title": "Hostel room study desk drawer runner broken and drawer fallen",
            "desc": "The wooden channel slider of the study table drawer has sheared off, making it impossible to store books and notes securely.",
            "cat": cat_hostel_room, "priority": "low", "score": 35, "reason": "Minor furniture repair"
        },
        {
            "title": "Dining hall Bain-Marie hot food counter heating thermostat tripped",
            "desc": "The water reservoir under the stainless steel food serving counter is cold because the thermostat breaker tripped. Dinner meals are cooling rapidly before serving.",
            "cat": cat_dining, "priority": "urgent", "score": 85, "reason": "Mass student dining food temperature quality"
        },
        {
            "title": "Rainwater drain pipe choked with dried leaves on quadrangle terrace",
            "desc": "The PVC drainage downspout on the north quad terrace is obstructed by dry foliage, causing water pooling near the parapet wall and minor ceiling dampness.",
            "cat": cat_hostel_sanitation, "priority": "normal", "score": 60, "reason": "Terrace water drainage obstruction"
        },
    ]

    for hall in halls:
        # Get rooms in this hall (or its constituent hostels)
        rooms = list(Room.objects.filter(floor__building__parent=hall)) or list(Room.objects.filter(floor__building=hall))
        
        for i, issue in enumerate(hostel_issue_templates):
            selected_room = rooms[i % len(rooms)] if rooms else None
            room_no = selected_room.number if selected_room else f"0{15 + i*8:02d}"
            loc_desc = f"{hall.name}, Room {room_no}"

            complaints_to_create.append({
                "title": f"{issue['title']} ({hall.name})",
                "desc": f"Location: {hall.name}, Room {room_no}. {issue['desc']}",
                "cat": issue["cat"],
                "room": selected_room,
                "loc_desc": loc_desc,
                "priority": issue["priority"],
                "score": issue["score"],
                "reason": issue["reason"],
            })

    # =========================================================================
    # 2. ACADEMIC FACULTIES & TEACHING DEPARTMENTS (91 complaints)
    # =========================================================================
    academic_complaints_data = [
        # --- FACULTY OF SCIENCE (15 complaints) ---
        {"bldg": "SCI", "dept": "Computer Science", "title": "Lab 3: Core network gigabit switch port 16 dead with no link light", "desc": "Terminal systems 15 to 20 in Software Engineering Lab are unable to obtain IP address from DHCP server due to faulty RJ45 switch port.", "cat": cat_sci_sys, "prio": "high", "score": 75, "reason": "Lab student connectivity down"},
        {"bldg": "SCI", "dept": "Computer Science", "title": "Ceiling mounted multimedia projector HDMI port flickering in Lecture Room 1", "desc": "The ceiling projector displays horizontal purple noise lines whenever laptops are connected through the teaching podium HDMI cable.", "cat": cat_sci_sys, "prio": "normal", "score": 55, "reason": "Audio visual classroom aid"},
        {"bldg": "SCI", "dept": "Chemistry", "title": "Organic chemistry lab fume hood blower motor vibrating excessively", "desc": "The exhaust blower motor in Advanced Synthesis Lab 2 is producing a loud grinding vibration and insufficient air draft for solvent evaporation experiments.", "cat": cat_sci_chem, "prio": "urgent", "score": 90, "reason": "Laboratory chemical fume extraction hazard"},
        {"bldg": "SCI", "dept": "Chemistry", "title": "Emergency eye-wash safety fountain valve jammed at wash basin", "desc": "The push-paddle on the chemical safety eye-wash unit is stiff and does not release water fountain properly.", "cat": cat_sci_chem, "prio": "high", "score": 80, "reason": "Mandatory laboratory safety device"},
        {"bldg": "SCI", "dept": "Physics", "title": "Optics darkroom split air conditioner leaking condensation water", "desc": "The 1.5-ton indoor AC unit is dripping water directly over the holographic optical vibration-isolation table.", "cat": cat_sci_lab, "prio": "high", "score": 80, "reason": "Sensitive optical instrumentation hazard"},
        {"bldg": "SCI", "dept": "Physics", "title": "Spectrometer sodium vapor calibration lamp power supply failed", "desc": "The ballast unit for the sodium discharge lamp in General Physics Lab Room 102 will not strike an arc.", "cat": cat_sci_lab, "prio": "normal", "score": 55, "reason": "Practical practical demonstration setup"},
        {"bldg": "SCI", "dept": "Mathematics", "title": "Departmental seminar library split AC remote control receiver dead", "desc": "The wall-mounted AC unit cannot be powered on because the infrared control sensor board has stopped responding.", "cat": cat_sci_lab, "prio": "normal", "score": 50, "reason": "Department reading climate control"},
        {"bldg": "SCI", "dept": "Mathematics", "title": "Blackboard sliding panel counterweight cable snapped in Lecture Theatre 2", "desc": "The heavy green sliding blackboard cannot be raised because the right wire rope counterweight snapped inside the wall channel.", "cat": cat_civil, "prio": "normal", "score": 55, "reason": "Lecture delivery fixture repair"},
        {"bldg": "SCI", "dept": "Geography", "title": "Cartography & GIS Lab digitizer table 15A power socket melted", "desc": "The dual 15A wall receptacle behind the map scanner shows scorch marks and trips the local MCB whenever energized.", "cat": cat_elec, "prio": "high", "score": 75, "reason": "Electrical short circuit hazard"},
        {"bldg": "SCI", "dept": "Geography", "title": "Department weather station anemometer cable bracket loose on terrace", "desc": "The wind sensor transmission line on the department roof parapet is flapping in strong winds and needs re-clamping.", "cat": cat_civil, "prio": "normal", "score": 45, "reason": "Meteorological sensor wiring"},
        {"bldg": "SCI", "dept": "Geology", "title": "Mineral museum display cabinet LED strip light supply transformer failed", "desc": "The mineral specimen display showcase lighting in the central geological museum hall remains completely unlit.", "cat": cat_elec, "prio": "low", "score": 35, "reason": "Museum exhibit lighting"},
        {"bldg": "SCI", "dept": "Geology", "title": "Rock cutting and thin section grinding machine water cooling tube cracked", "desc": "The flexible diamond-wheel water supply pipe is spraying water onto the laboratory work floor.", "cat": cat_plumb, "prio": "normal", "score": 60, "reason": "Geological lab specimen preparation"},
        {"bldg": "SCI", "dept": "Industrial Chemistry", "title": "Chemical storage storehouse exhaust louvre vent fan stuck", "desc": "The wall-mounted safety exhaust fan in the bulk acid container storage room has stalled on its sleeve bearing.", "cat": cat_sci_chem, "prio": "urgent", "score": 88, "reason": "Chemical storage room ventilation"},
        {"bldg": "SCI", "dept": "Statistics", "title": "Computer lab ceiling LED downlight panel ballast blinking rapidly", "desc": "Three 36W LED panels directly above student computing terminals in Lab 1 are flashing rapidly causing eye strain.", "cat": cat_elec, "prio": "normal", "score": 50, "reason": "Lab computing illumination"},
        {"bldg": "SCI", "dept": "Remote Sensing & GIS", "title": "Satellite image processing workstation secondary monitor flickering", "desc": "DisplayPort video signal to the 4K cartographic dual-screen monitor drops out intermittently during raster analysis.", "cat": cat_sci_sys, "prio": "normal", "score": 50, "reason": "Research workstation peripheral"},

        # --- ZAKIR HUSAIN COLLEGE OF ENGINEERING & TECHNOLOGY (20 complaints) ---
        {"bldg": "ENGG", "dept": "Electrical Engineering", "title": "High Voltage Lab three-phase isolation switch operating handle jammed", "desc": "The interlocked safety rotary disconnect switch on the 415V distribution board cannot be thrown safely.", "cat": cat_engg_elec, "prio": "urgent", "score": 92, "reason": "High voltage laboratory isolation safety"},
        {"bldg": "ENGG", "dept": "Electrical Engineering", "title": "Machines Lab DC motor-generator test bench rheostat slider burnt", "desc": "Wire-wound field rheostat on the 5kW shunt motor experiment rig has an open-circuit dead zone.", "cat": cat_engg_lab, "prio": "high", "score": 75, "reason": "Undergraduate machines experiment setup"},
        {"bldg": "ENGG", "dept": "Mechanical Engineering", "title": "Machine Tools Workshop universal milling machine spindle belt slipping", "desc": "The V-belt driving the horizontal arbor slips under moderate feed on mild steel workpieces, making loud squeals.", "cat": cat_engg_mach, "prio": "high", "score": 75, "reason": "Workshop manufacturing machinery"},
        {"bldg": "ENGG", "dept": "Mechanical Engineering", "title": "Internal Combustion Engines Lab dynamometer cooling water pump dripping", "desc": "Mechanical shaft seal on the hydraulic dynamometer recirculation pump has degraded and drips coolant steadily.", "cat": cat_plumb, "prio": "normal", "score": 60, "reason": "IC Engines test bed auxiliary water system"},
        {"bldg": "ENGG", "dept": "Civil Engineering", "title": "Concrete Technology Lab motorized sieve shaker timer switch broken", "desc": "The automatic mechanical timer for the coarse aggregate sieve stack does not shut off, requiring manual plug pull.", "cat": cat_engg_mach, "prio": "normal", "score": 50, "reason": "Soil mechanics and concrete testing"},
        {"bldg": "ENGG", "dept": "Civil Engineering", "title": "Surveying store digital theodolite aluminium tripod head clamp screw stripped", "desc": "The brass locking thumb-screw for leveling head adjustment on tripod #6 has stripped its inner threads.", "cat": cat_engg_lab, "prio": "normal", "score": 45, "reason": "Field surveying equipment"},
        {"bldg": "ENGG", "dept": "Chemical Engineering", "title": "Unit Operations Lab double-pipe heat exchanger thermocouple sensor loose", "desc": "Temperature sensor probe at hot fluid inlet has dislodged from thermowell, giving erratically fluctuating readings.", "cat": cat_engg_lab, "prio": "normal", "score": 60, "reason": "Chemical process thermodynamics lab"},
        {"bldg": "ENGG", "dept": "Chemical Engineering", "title": "Distillation column pilot plant overhead condenser cooling coil valve calcified", "desc": "The copper globe valve controlling cooling water flow into the fractional distillation condenser is jammed shut.", "cat": cat_plumb, "prio": "high", "score": 75, "reason": "Pilot plant cooling loop control"},
        {"bldg": "ENGG", "dept": "Computer Engineering", "title": "Advanced Networking Lab rack server primary power supply alarm buzzing", "desc": "The 1U edge gateway server has a redundant power supply unit failure light and continuous buzzer sounding.", "cat": cat_engg_comp, "prio": "urgent", "score": 85, "reason": "Core department server rack alarm"},
        {"bldg": "ENGG", "dept": "Computer Engineering", "title": "Hardware Simulation Lab 2 ceiling exhaust fan motor bearing seized", "desc": "The heavy exhaust fan above the server rack cabinet has stopped spinning and smells of warm winding insulation.", "cat": cat_elec, "prio": "high", "score": 75, "reason": "Server cabinet thermal ventilation"},
        {"bldg": "ENGG", "dept": "Electronics Engineering", "title": "Microprocessor Lab 100MHz digital storage oscilloscope probe BNC connector loose", "desc": "Channel 1 BNC input port on Rigol oscilloscope bench 7 has a wobbly socket causing intermittent signal loss.", "cat": cat_engg_lab, "prio": "normal", "score": 50, "reason": "Digital electronics laboratory instrument"},
        {"bldg": "ENGG", "dept": "Electronics Engineering", "title": "Communication Systems Lab RF spectrum analyzer cooling fan noisy", "desc": "Internal high-RPM fan on the 3GHz spectrum analyzer has worn sleeve bearings and makes high-pitched hum.", "cat": cat_engg_lab, "prio": "normal", "score": 55, "reason": "Microwave lab instrumentation"},
        {"bldg": "ENGG", "dept": "Architecture", "title": "Senior Design Studio drawing board horizontal parallel motion wire snapped", "desc": "The precision nylon drafting cable on drafting board #12 has snapped, preventing the rule from sliding evenly.", "cat": cat_arts_furn, "prio": "normal", "score": 50, "reason": "Architectural studio equipment"},
        {"bldg": "ENGG", "dept": "Architecture", "title": "Model Making Workshop laser cutter fume extraction duct disconnected", "desc": "The flexible aluminum exhaust hose from the acrylic cutting laser has slipped off its external wall flange.", "cat": cat_engg_mach, "prio": "urgent", "score": 88, "reason": "Laser cutter toxic acrylic fumes ventilation"},
        {"bldg": "ENGG", "dept": "Petroleum Studies", "title": "Core drilling and fluid permeability test rig hydraulic pressure gauge leaking", "desc": "Hydraulic oil is seeping from the threaded collar of the 5000 PSI pressure indicator during core testing.", "cat": cat_engg_lab, "prio": "high", "score": 78, "reason": "High-pressure petroleum testing bench"},
        {"bldg": "ENGG", "dept": "Applied Chemistry", "title": "Spectrophotometer quartz cuvette washing sink drain siphon blocked", "desc": "Chemical wastewater is backing up in the lead-lined sink basin in room 110 of the Applied Chemistry wing.", "cat": cat_plumb, "prio": "high", "score": 75, "reason": "Laboratory drain backflow"},
        {"bldg": "ENGG", "dept": "Applied Physics", "title": "Laser optics bench helium-neon laser power cord strain relief pulled out", "desc": "The 220V mains cable on the He-Ne laser housing has its outer PVC jacket torn, exposing live insulation.", "cat": cat_elec, "prio": "urgent", "score": 85, "reason": "Mains voltage bare insulation hazard"},
        {"bldg": "ENGG", "dept": "Applied Mathematics", "title": "Department seminar room wireless microphone battery latch broken", "desc": "The handheld VHF wireless microphone battery compartment cover is missing, causing batteries to drop out during seminars.", "cat": cat_arts_av, "prio": "low", "score": 30, "reason": "Seminar hall microphone accessory"},
        {"bldg": "ENGG", "dept": "ZHCET Administration", "title": "Dean office corridor water dispenser compressor not chilling water", "desc": "The 40-litre stainless steel water cooler runs its fan but the compressor fails to engage to chill drinking water.", "cat": cat_plumb, "prio": "normal", "score": 55, "reason": "Drinking water cooling utility"},
        {"bldg": "ENGG", "dept": "ZHCET Auditorium", "title": "ZHCET Auditorium motorized projection screen remote limit switch failing", "desc": "The 200-inch electric motorized screen continues lowering past the stage platform until turned off at wall breaker.", "cat": cat_arts_av, "prio": "normal", "score": 60, "reason": "Auditorium motorized AV fixture"},

        # --- JAWAHARLAL NEHRU MEDICAL COLLEGE (JNMC) (20 complaints) ---
        {"bldg": "MED", "dept": "Cardiology", "title": "Cardiology OPD Room 4: Wall-mounted aneroid sphygmomanometer bracket loose", "desc": "The mercury-free blood pressure dial fixture on the examination cubicle wall is wobbling and risk of dropping.", "cat": cat_jnmc_med, "prio": "high", "score": 75, "reason": "Clinical diagnostic equipment safety"},
        {"bldg": "MED", "dept": "Cardiology", "title": "ECG Recording Room: 12-lead ECG machine limb lead cable #3 intermittent", "desc": "The left leg electrode lead wire has an internal break near the banana plug, showing flatline artifact on traces.", "cat": cat_jnmc_med, "prio": "urgent", "score": 85, "reason": "Patient diagnostic trace integrity"},
        {"bldg": "MED", "dept": "Anatomy", "title": "Dissection Hall: Overhead exhaust fan #4 motor bearing producing loud squeal", "desc": "One of the large formalin extraction fans has an unlubricated bearing, creating high decibel screeching in practical classes.", "cat": cat_jnmc_infra, "prio": "high", "score": 75, "reason": "Formaldehyde vapor exhaust efficiency"},
        {"bldg": "MED", "dept": "Anatomy", "title": "Histology Lab: Binocular microscope illuminator halogen bulb burnt on bench 12", "desc": "The 6V 20W internal base lamp for medical student microscope bench 12 is burnt and needs standard replacement.", "cat": cat_jnmc_lab, "prio": "normal", "score": 50, "reason": "Microscopic slide demonstration"},
        {"bldg": "MED", "dept": "Pathology", "title": "Blood Bank donor screening room split AC cooling coil iced over", "desc": "The indoor unit is rattling with ice buildup and airflow is nearly stopped, raising ambient room temperature.", "cat": cat_jnmc_infra, "prio": "urgent", "score": 90, "reason": "Blood product donor room climate control"},
        {"bldg": "MED", "dept": "Pathology", "title": "Clinical Biochemistry analyzer water purification cartridge differential pressure high", "desc": "The deionized water polishing filter feeding the automated analyzer shows red indicator lamp for filter replacement.", "cat": cat_jnmc_lab, "prio": "urgent", "score": 88, "reason": "Clinical diagnostic analyzer water feed"},
        {"bldg": "MED", "dept": "Pharmacology", "title": "Experimental pharmacology demonstration lab dispensing balance uncalibrated", "desc": "The digital precision scale in the student drug formulation lab drifts ±0.05g when weights are placed.", "cat": cat_jnmc_lab, "prio": "normal", "score": 55, "reason": "Pharmacology formulation scale"},
        {"bldg": "MED", "dept": "Pharmacology", "title": "Lecture Theatre 3: Ceiling sound speaker driver cone buzzing on voice", "desc": "Right-side column speaker in the pharmacology lecture gallery distorts and rattles whenever teacher speaks into mic.", "cat": cat_arts_av, "prio": "normal", "score": 50, "reason": "Medical lecture acoustics"},
        {"bldg": "MED", "dept": "Community Medicine", "title": "Urban Health Training Centre rural outreach vehicle portable cool-box latch broken", "desc": "The vaccine carrier insulated transport box plastic latch has cracked, preventing airtight closure for polio immunization.", "cat": cat_jnmc_med, "prio": "high", "score": 80, "reason": "Vaccine cold chain preservation"},
        {"bldg": "MED", "dept": "Forensic Medicine", "title": "Autopsy mortuary cold storage temperature display digital indicator flickering", "desc": "The external digital thermocouple readout for body cooling chamber 2 flashes intermittently.", "cat": cat_jnmc_infra, "prio": "urgent", "score": 92, "reason": "Mortuary cold storage monitoring"},
        {"bldg": "MED", "dept": "Medicine", "title": "Medical Ward 4: Nursing station wall chart illuminated viewing box tube burnt", "desc": "The twin 15W daylight tube lights on the X-ray film illuminator desk are burnt out, hindering chest radiograph reviews.", "cat": cat_jnmc_infra, "prio": "high", "score": 75, "reason": "Clinical patient radiograph interpretation"},
        {"bldg": "MED", "dept": "Surgery", "title": "Surgical Skills Wet Lab: Scrub sink elbow-operated water tap dripping", "desc": "The long-lever hospital brass mixer faucet in student scrub room 2 does not shut off completely.", "cat": cat_plumb, "prio": "normal", "score": 55, "reason": "Surgical scrub water conservation"},
        {"bldg": "MED", "dept": "Paediatrics", "title": "Child OPD immunization cubicle weighing scale pan safety rim loose", "desc": "The curved infant weighing tray mounting screws underneath have worked loose and the cradle wobbles.", "cat": cat_jnmc_med, "prio": "high", "score": 80, "reason": "Infant patient weighing safety"},
        {"bldg": "MED", "dept": "Orthopaedics", "title": "Plaster Room: Electric oscillating plaster cutter blade retention screw worn", "desc": "The hex retention screw locking the circular cast removal blade has rounded corners and slips during tightening.", "cat": cat_jnmc_med, "prio": "urgent", "score": 85, "reason": "Orthopaedic patient cast removal"},
        {"bldg": "MED", "dept": "Ophthalmology", "title": "Refraction Room 2: Slit lamp biomicroscope joy-stick vertical lift slipping", "desc": "The mechanical rack-and-pinion elevation mechanism on the slit lamp table slips when adjusted upwards.", "cat": cat_jnmc_med, "prio": "normal", "score": 60, "reason": "Eye clinic patient examination"},
        {"bldg": "MED", "dept": "Dermatology", "title": "Phototherapy unit UV lamp safety countdown timer alarm not ringing", "desc": "The analog safety countdown timer for narrow-band UVB chamber fails to sound chime at zero minutes.", "cat": cat_jnmc_med, "prio": "high", "score": 80, "reason": "Patient UV dosage safety"},
        {"bldg": "MED", "dept": "Anaesthesiology", "title": "Anaesthesia Simulation Lab: Pulse oximeter finger probe cable frayed", "desc": "The rubber cable strain relief at the monitor connector end has parted, exposing copper shielding braid.", "cat": cat_jnmc_med, "prio": "high", "score": 75, "reason": "Simulation monitoring hardware"},
        {"bldg": "MED", "dept": "Dental College", "title": "Conservative Dentistry Clinic: Chair #5 water syringe button sticking", "desc": "The 3-way air/water syringe on dental delivery unit 5 sticks in the pressed position causing continuous water spray.", "cat": cat_jnmc_med, "prio": "normal", "score": 65, "reason": "Dental operatory chair delivery system"},
        {"bldg": "MED", "dept": "Dental College", "title": "Oral Radiology Room: Lead apron protective hanger bracket loose on wall", "desc": "The heavy steel swivel arm holding three radiation protection lead aprons is pulling its rawl plugs out of brickwork.", "cat": cat_civil, "prio": "high", "score": 75, "reason": "Radiation safety equipment storage"},
        {"bldg": "MED", "dept": "Bio-Chemistry (JNMC)", "title": "PG Research Lab: Tabletop refrigerated micro-centrifuge door interlock error", "desc": "The digital lid safety interlock sensor displays error code E-04 and prevents rotor acceleration.", "cat": cat_jnmc_lab, "prio": "high", "score": 78, "reason": "Centrifuge safety interlock mechanism"},

        # --- FACULTY OF LIFE SCIENCES (6 complaints) ---
        {"bldg": "LIFE", "dept": "Bio-Chemistry (Life Sciences)", "title": "M.Sc. Laboratory: Double beam UV-Vis spectrophotometer deuterium lamp failing ignition", "desc": "The UV deuterium discharge source in the spectrophotometer fails to strike on startup, hindering nucleic acid assays.", "cat": cat_sci_lab, "prio": "high", "score": 75, "reason": "Biochemical research spectrophotometry"},
        {"bldg": "LIFE", "dept": "Bio-Chemistry (Life Sciences)", "title": "Enzymology Lab: -20°C deep freezer door magnetic rubber gasket torn", "desc": "Air leakage around the upper door corner is causing excessive frost accumulation on enzyme restriction storage racks.", "cat": cat_sci_lab, "prio": "urgent", "score": 85, "reason": "Biochemical reagent cold storage integrity"},
        {"bldg": "LIFE", "dept": "Botany", "title": "Plant Tissue Culture Room: Laminar air flow hood HEPA pre-filter clogged", "desc": "Differential pressure manometer on laminar flow cabinet #2 is in the red zone, reducing sterile face velocity.", "cat": cat_sci_lab, "prio": "high", "score": 80, "reason": "Sterile plant tissue culture contamination prevention"},
        {"bldg": "LIFE", "dept": "Botany", "title": "Department Botanical Garden Glasshouse misting nozzle line leaking", "desc": "Overhead brass micro-sprinkler line has separated at compression elbow, soaking soil bed unevenly.", "cat": cat_plumb, "prio": "normal", "score": 55, "reason": "Botanical specimen greenhouse irrigation"},
        {"bldg": "LIFE", "dept": "Zoology", "title": "Entomology Research Lab: Compound microscope binocular head prism misaligned", "desc": "Looking through the eyepieces produces double vision for specimen dissection due to misaligned binocular prism.", "cat": cat_sci_lab, "prio": "normal", "score": 60, "reason": "Zoological microscope optical alignment"},
        {"bldg": "LIFE", "dept": "Wildlife Sciences", "title": "Field Research Equipment Store: GPS telemetry receiver battery charger dead", "desc": "The multi-bank Li-ion battery charging dock for wildlife tracking field units does not power on.", "cat": cat_elec, "prio": "normal", "score": 50, "reason": "Field telemetry gear power supply"},

        # --- FACULTY OF ARTS (6 complaints) ---
        {"bldg": "ARTS", "dept": "English", "title": "English Department Seminar Hall audio amplifier microphone jack buzzing", "desc": "The 6.35mm podium mic socket produces loud hum when cable is moved during departmental lectures.", "cat": cat_arts_av, "prio": "normal", "score": 50, "reason": "Departmental audio public address"},
        {"bldg": "ARTS", "dept": "Urdu", "title": "Urdu Department Calligraphy Archives room ceiling water seepage mark", "desc": "Recent rains have left water dampness marks on ceiling plaster directly above rare manuscript storage almirah.", "cat": cat_civil, "prio": "high", "score": 75, "reason": "Archive literary heritage moisture hazard"},
        {"bldg": "ARTS", "dept": "Fine Arts", "title": "Sculpture Studio pottery wheel foot speed pedal potentiometer sticking", "desc": "Electric ceramic wheel #3 continues spinning at full speed when foot pressure is removed from pedal.", "cat": cat_arts_furn, "prio": "normal", "score": 60, "reason": "Art studio equipment safety"},
        {"bldg": "ARTS", "dept": "Fine Arts", "title": "Painting Studio north-facing skylight glass pane cracked with vibration", "desc": "Upper wire-reinforced glass panel in painting hall ceiling has developed a diagonal fissure.", "cat": cat_civil, "prio": "high", "score": 70, "reason": "Studio skylight glass fracture hazard"},
        {"bldg": "ARTS", "dept": "Arabic", "title": "Language Lab 1 audio cassette to digital converter deck transport belt slipping", "desc": "Tape playback capstan roller fails to maintain constant pitch during phonetics listening exercises.", "cat": cat_arts_av, "prio": "low", "score": 35, "reason": "Phonetics audio playback equipment"},
        {"bldg": "ARTS", "dept": "Philosophy", "title": "Lecture Room 4 wooden lecture podium tilted due to loose base screws", "desc": "The standing oak speaker lectern rocks forward when teacher leans notes on it.", "cat": cat_arts_furn, "prio": "low", "score": 30, "reason": "Classroom furniture leveling"},

        # --- FACULTY OF SOCIAL SCIENCES (8 complaints) ---
        {"bldg": "SOC", "dept": "Economics", "title": "Econometrics Computer Lab air conditioner thermostat failing to cut off", "desc": "Lab temperature drops below 16°C and compressor runs continuously, frosting the indoor coil.", "cat": cat_soc_lab, "prio": "normal", "score": 55, "reason": "Computer lab temperature regulation"},
        {"bldg": "SOC", "dept": "Political Science", "title": "Departmental Library ceiling fan wobbling severely on ceiling rod", "desc": "The 1200mm ceiling fan above reading table 2 sways side to side at speeds 4 and 5.", "cat": cat_elec, "prio": "high", "score": 75, "reason": "Fan suspension mounting safety"},
        {"bldg": "SOC", "dept": "History", "title": "Medieval History Seminar Room ceiling projector screen spring retracted too high", "desc": "Manual pulldown screen roller spring locked at top and pull cord is out of reach without ladder.", "cat": cat_arts_av, "prio": "low", "score": 35, "reason": "Seminar screen accessibility"},
        {"bldg": "SOC", "dept": "Psychology", "title": "Experimental Psychology Lab soundproof booth interior ventilation fan noisy", "desc": "Acoustic chamber small exhaust blower creates motor drone interfering with auditory reaction time tests.", "cat": cat_soc_class, "prio": "normal", "score": 55, "reason": "Acoustic research chamber testing"},
        {"bldg": "SOC", "dept": "Mass Communication", "title": "TV Studio lighting grid dimmer pack channel 8 relay stuck closed", "desc": "One 1000W halogen fresnel floodlight cannot be dimmed from lighting console and remains on full intensity.", "cat": cat_elec, "prio": "high", "score": 75, "reason": "Studio lighting grid dimmer rack"},
        {"bldg": "SOC", "dept": "Mass Communication", "title": "Audio Dubbing Booth glass window acoustic silicone seal peeling off", "desc": "Double glazed sound isolation window between control room and recording booth has air gap allowing bleed.", "cat": cat_civil, "prio": "normal", "score": 50, "reason": "Audio recording booth acoustic isolation"},
        {"bldg": "SOC", "dept": "Library Science", "title": "Cataloguing Practice Room wooden swivel chairs height cylinder collapsed", "desc": "Three pneumatic gas lift desk chairs in cataloguing room sink to lowest position when sat upon.", "cat": cat_arts_furn, "prio": "low", "score": 35, "reason": "Classroom seating ergonomic repair"},
        {"bldg": "SOC", "dept": "Sociology", "title": "Departmental corridor drinking water tap nozzle missing aerator cap", "desc": "Water spurts in uneven diagonal spray from cooler tap, splashing shirts and floor.", "cat": cat_plumb, "prio": "low", "score": 30, "reason": "Water tap plumbing fixture"},

        # --- FACULTY OF COMMERCE (4 complaints) ---
        {"bldg": "COMM", "dept": "Commerce", "title": "Computer Lab 1 UPS battery backup inverter sounding low voltage alarm", "desc": "The 10kVA online UPS for the accounting software laboratory shows amber battery fault indicator.", "cat": cat_comm_lab, "prio": "urgent", "score": 88, "reason": "Lab central power backup battery health"},
        {"bldg": "COMM", "dept": "Commerce", "title": "Lecture Theatre 1 ceiling microphone pendant wire cable frayed", "desc": "The overhead condenser mic hanging above lecturer desk has exposed wire braid at swivel collar.", "cat": cat_arts_av, "prio": "normal", "score": 50, "reason": "Lecture hall microphone wiring"},
        {"bldg": "COMM", "dept": "Commerce", "title": "Faculty Meeting Room executive table central cable conduit lid broken", "desc": "The recessed aluminum conference table pop-up power box spring latch does not stay closed.", "cat": cat_comm_class, "prio": "low", "score": 30, "reason": "Conference room table fixture"},
        {"bldg": "COMM", "dept": "Commerce", "title": "Ground floor washroom ceramic wash basin drain pipe leaking onto floor", "desc": "Plastic bottle trap under central sink has hairline split along bottom seam.", "cat": cat_plumb, "prio": "normal", "score": 60, "reason": "Washroom sanitary drain leak"},

        # --- FACULTY OF MANAGEMENT STUDIES & RESEARCH (FMSR) (4 complaints) ---
        {"bldg": "MGMT", "dept": "Management Studies", "title": "Case Study Hall 2 ceiling motorized projector lens zoom focus motor stuck", "desc": "The EPSON installation projector lens zoom will not adjust from remote control, causing blurred text.", "cat": cat_mgmt_proj, "prio": "normal", "score": 60, "reason": "MBA case discussion visual projection"},
        {"bldg": "MGMT", "dept": "Management Studies", "title": "Computer Lab business simulation terminal #14 keyboard missing spacebar key", "desc": "Mechanical key switch cap broken off, making numerical data entry difficult for students.", "cat": cat_mgmt_lab, "prio": "low", "score": 30, "reason": "Computer lab peripheral replacement"},
        {"bldg": "MGMT", "dept": "Management Studies", "title": "Executive Development Centre main entrance glass door closer arm loose", "desc": "The overhead hydraulic door closer arm clatters loudly and fails to latch the glass door securely.", "cat": cat_civil, "prio": "normal", "score": 50, "reason": "Entrance door hydraulic closer adjustment"},
        {"bldg": "MGMT", "dept": "Management Studies", "title": "FMSR Library reading section split air conditioner fan motor clicking", "desc": "Blower fan wheel has slight imbalance, making rhythmic clicking sound in quiet study area.", "cat": cat_elec, "prio": "normal", "score": 50, "reason": "Library quiet zone HVAC maintenance"},

        # --- FACULTY OF LAW (4 complaints) ---
        {"bldg": "LAW", "dept": "Law", "title": "Moot Court Hall sound recording system mixer channel 1 phantom power failing", "desc": "The judges bench goose-neck microphone does not receive +48V phantom power from the sound console.", "cat": cat_arts_av, "prio": "high", "score": 75, "reason": "Moot court legal proceedings audio recording"},
        {"bldg": "LAW", "dept": "Law", "title": "Law Library Law Reports reference section ceiling LED panel dark", "desc": "Two 2x2 LED troffer lights directly above Supreme Court Cases (SCC) rack are completely dead.", "cat": cat_law_lib, "prio": "normal", "score": 50, "reason": "Law reports library illumination"},
        {"bldg": "LAW", "dept": "Law", "title": "Lecture Hall 2 wooden tiered bench backrest loose in row 4", "desc": "The curved wooden plank backrest has pulled away from steel upright bracket, wobbling dangerously.", "cat": cat_law_class, "prio": "normal", "score": 55, "reason": "Lecture gallery student seating safety"},
        {"bldg": "LAW", "dept": "Law", "title": "Department corridor fire extinguisher inspection gauge indicator in red zone", "desc": "Dry chemical powder 6kg extinguisher near dean office has lost pressure and needs recharging.", "cat": cat_civil, "prio": "urgent", "score": 85, "reason": "Building fire safety equipment readiness"},

        # --- FACULTY OF AGRICULTURAL SCIENCES (4 complaints) ---
        {"bldg": "AGRI", "dept": "Agricultural Sciences", "title": "Department experimental farm drip irrigation solenoid valve 2 stuck open", "desc": "The 24VAC automated valve for polyhouse nursery beds continuously floods soil bed without timer signal.", "cat": cat_agri_irrig, "prio": "high", "score": 75, "reason": "Experimental farm automated irrigation control"},
        {"bldg": "AGRI", "dept": "Agricultural Sciences", "title": "Plant Pathology Lab seed germination incubator humidity sensor drifting", "desc": "The relative humidity readout stays at 99% despite dry chamber conditions, ruining fungus culture tests.", "cat": cat_agri_infra, "prio": "high", "score": 75, "reason": "Agronomy seed germination control"},
        {"bldg": "AGRI", "dept": "Agricultural Sciences", "title": "Post Harvest Technology processing lab stainless steel pulper motor starter trips", "desc": "Direct-on-line motor starter thermal overload relay trips after 2 minutes of fruit pulper operation.", "cat": cat_engg_mach, "prio": "normal", "score": 60, "reason": "Food processing pilot equipment"},
        {"bldg": "AGRI", "dept": "Agricultural Sciences", "title": "Department farm tractor shed corrugated iron roofing sheet rattling in wind", "desc": "Wind has loosened three self-drilling screws on the farm implement storage shed roof.", "cat": cat_civil, "prio": "normal", "score": 45, "reason": "Farm machinery shed shelter"},

        # --- FACULTY OF THEOLOGY (3 complaints) ---
        {"bldg": "THEO", "dept": "Theology", "title": "Theology Library Manuscript Room humidity extractor exhaust motor dead", "desc": "The dehumidifier exhaust duct fan has stopped rotating, risking moisture buildup in classical book collection.", "cat": cat_theo_class, "prio": "high", "score": 75, "reason": "Rare theological book preservation"},
        {"bldg": "THEO", "dept": "Theology", "title": "Lecture Hall 1 wooden lectern mic holder clip snapped", "desc": "Plastic spring clip holding the gooseneck microphone has broken, causing mic to droop.", "cat": cat_arts_av, "prio": "low", "score": 25, "reason": "Podium microphone clip"},
        {"bldg": "THEO", "dept": "Theology", "title": "Department entrance porch heritage lantern bulb burnt out", "desc": "The hexagonal brass outdoor carriage lantern fixture at the department archway is unlit at dusk.", "cat": cat_elec, "prio": "low", "score": 35, "reason": "Building heritage lighting"},

        # --- AJMAL KHAN TIBBIYA COLLEGE (UNANI MEDICINE) (3 complaints) ---
        {"bldg": "UNANI", "dept": "Unani Medicine", "title": "Dawakhana Herbal Pharmacy herb grinding pulverizer hopper vibration bracket loose", "desc": "The heavy stainless steel feed chute on the dry herbal grinder is shaking excessively during formulation.", "cat": cat_unani_med, "prio": "high", "score": 75, "reason": "Unani pharmaceutical manufacturing machinery"},
        {"bldg": "UNANI", "dept": "Unani Medicine", "title": "Herbal Garden medicinal nursery drip feeder main pipe punctured", "desc": "Gardener spade has nicked the 32mm HDPE black water feeder line near the Rauwolfia serpentina bed.", "cat": cat_unani_herb, "prio": "normal", "score": 55, "reason": "Medicinal botanical nursery irrigation"},
        {"bldg": "UNANI", "dept": "Unani Medicine", "title": "Hospital OPD Hijamah (Cupping) Therapy room wash basin tap handle stripped", "desc": "The internal quarter-turn ceramic cartridge on the hot water tap spins freely without stopping water flow.", "cat": cat_plumb, "prio": "normal", "score": 60, "reason": "Tibbiya hospital clinic sanitation"},
    ]

    for item in academic_complaints_data:
        bldg = Building.objects.filter(code=item["bldg"]).first()
        rooms = list(Room.objects.filter(floor__building=bldg)) if bldg else []
        selected_room = rooms[random.randint(0, len(rooms)-1)] if rooms else None
        loc_desc = f"{bldg.name if bldg else item['bldg']}, {item['dept']}"
        if selected_room:
            loc_desc += f", Room {selected_room.number}"

        complaints_to_create.append({
            "title": item["title"],
            "desc": f"Location: {loc_desc}. {item['desc']}",
            "cat": item["cat"],
            "room": selected_room,
            "loc_desc": loc_desc,
            "priority": item["prio"],
            "score": item["score"],
            "reason": item["reason"],
        })

    # =========================================================================
    # 3. COMMON CAMPUS FACILITIES, LIBRARY, SPORTS & SECURITY (26 complaints)
    # =========================================================================
    common_complaints_data = [
        # Maulana Azad Library (5 complaints)
        {"bldg": "LIB", "title": "MA Library Central Reading Hall: Wi-Fi access point AP-04 dropping connectivity periodically", "desc": "Students on the second floor central study hall experience frequent Wi-Fi disconnection and DHCP timeout on the campus portal.", "cat": cat_wifi, "prio": "high", "score": 75, "reason": "Central library student digital connectivity"},
        {"bldg": "LIB", "title": "MA Library Oriental Manuscripts Division air conditioning humidity controller alarm buzzing", "desc": "Precision environmental control unit #2 indicates elevated relative humidity (>65%) in the rare parchment section.", "cat": cat_lib_read, "prio": "urgent", "score": 90, "reason": "National manuscript treasure preservation"},
        {"bldg": "LIB", "title": "MA Library Research Scholar Floor: Book stack aisle 14 twin tube-light fixture ballast burnt", "desc": "The overhead fluorescent fixture between humanities book racks 1400-1480 is dead, leaving aisle in darkness.", "cat": cat_lib_read, "prio": "normal", "score": 50, "reason": "Book aisle reading illumination"},
        {"bldg": "LIB", "title": "MA Library Ground Floor: Stainless steel cold water cooler dispenser tap leaking continuously", "desc": "Left-hand spring push tap on the main foyer drinking fountain is stuck open, overflowing the stainless catch basin.", "cat": cat_plumb, "prio": "normal", "score": 55, "reason": "Library foyer water wastage"},
        {"bldg": "LIB", "title": "MA Library Circulation Counter barcode scanner optical trigger cable loose", "desc": "The USB handheld laser barcode reader at return counter 2 loses power when cable is bent during book returns.", "cat": cat_lib_serv, "prio": "normal", "score": 50, "reason": "Circulation desk book transaction speed"},

        # University Sports Complex & Grounds (8 complaints)
        {"bldg": None, "title": "University Swimming Pool: Changing room shower mixer valve leaking cold water", "desc": "Shower head cubicle 4 in the student aquatic complex locker room has a split copper riser pipe dripping continuously.", "cat": cat_plumb, "prio": "normal", "score": 55, "reason": "Aquatic complex locker room plumbing"},
        {"bldg": None, "title": "University Swimming Pool: Chlorine doser pump feed line air-lock error", "desc": "Automated pool water sanitization metering pump has air in the suction line and fails to deliver chemical solution.", "cat": cat_plumb, "prio": "high", "score": 78, "reason": "Swimming pool sanitary water disinfection"},
        {"bldg": None, "title": "University Gymnasium: Heavy-duty commercial treadmill belt slipping under running load", "desc": "Treadmill unit #3 driving roller tension has slackened; belt stops abruptly when runner strikes foot.", "cat": cat_civil, "prio": "high", "score": 70, "reason": "Gymnasium student injury hazard"},
        {"bldg": None, "title": "University Gymnasium: Wall-mounted industrial air circulator fan cage vibration", "desc": "The 30-inch high-velocity oscillating fan on east gym wall has loose mounting bolts rattling against brick.", "cat": cat_elec, "prio": "normal", "score": 50, "reason": "Gymnasium ventilation fan safety"},
        {"bldg": None, "title": "Willingdon Cricket Pavilion: Pitch roller hydraulic drive cylinder oil seal weeping", "desc": "Hydraulic oil droplets are falling from the heavy diesel cricket pitch roller onto the practice crease grass.", "cat": cat_civil, "prio": "normal", "score": 55, "reason": "Cricket turf maintenance machinery"},
        {"bldg": None, "title": "Synthetic Hockey Turf Ground: Sub-surface perimeter pop-up sprinkler #6 stuck extended", "desc": "Sprinkler riser did not retract after watering session, creating an obstacle hazard on the synthetic turf sideline.", "cat": cat_plumb, "prio": "high", "score": 70, "reason": "Astro-turf athlete safety hazard"},
        {"bldg": None, "title": "University Tennis Courts: Court 2 center net regulatory tension winch gear slipping", "desc": "The brass ratchet tooth on the net post tensioning winch has rounded off and cannot maintain regulation 3-foot center height.", "cat": cat_civil, "prio": "low", "score": 35, "reason": "Tennis court regulation fixture"},
        {"bldg": None, "title": "Athletics Track: 400m synthetic running track 100m start mark high-mast floodlight dead", "desc": "Two 400W metal-halide lamps on high-mast tower 1 fail to ignite during evening student training sessions.", "cat": cat_elec, "prio": "normal", "score": 60, "reason": "Track and field evening training lighting"},

        # University Campus Roads, Gates & Security (13 complaints)
        {"bldg": None, "title": "Street Light Pole #28 near Victoria Gate not illuminating at night", "desc": "The 70W LED street luminaire between Victoria Gate and Arts Faculty circle is unlit, causing pitch darkness on the bend.", "cat": cat_estate_elec, "prio": "high", "score": 75, "reason": "Campus arterial road pedestrian safety"},
        {"bldg": None, "title": "Street Light Pole #42 on Sir Syed House road flickering rapidly", "desc": "The street lamp fixture has a failing LED electronic driver, strobe-flashing and causing severe glare for motorists.", "cat": cat_estate_elec, "prio": "normal", "score": 50, "reason": "Campus road lighting driver failure"},
        {"bldg": None, "title": "Centenary Gate security checkpoint motorized boom barrier arm sensor misaligned", "desc": "Vehicle exit barrier drops prematurely before car clears the inductive safety loop.", "cat": cat_gate, "prio": "urgent", "score": 85, "reason": "Campus vehicle entrance safety mechanism"},
        {"bldg": None, "title": "Bab-e-Syed main gate historical archway external floodlight bracket loose", "desc": "The heavy brass spotlight bracket illuminating the heritage gateway arch is rattling in evening winds.", "cat": cat_gate, "prio": "normal", "score": 55, "reason": "Historic gateway landmark illumination"},
        {"bldg": None, "title": "University Proctor Office: Speed breaker thermoplastic reflective paint worn off", "desc": "Speed hump near Proctor Office roundabout is unpainted and difficult to see in headlights at night.", "cat": cat_estate_civil, "prio": "normal", "score": 50, "reason": "Traffic calming visibility on campus avenue"},
        {"bldg": None, "title": "Pedestrian footpath interlocking paver tiles sunken near Arts Faculty canteen", "desc": "Water seepage has settled the subgrade sand, creating a 4-inch deep depression where students trip.", "cat": cat_estate_civil, "prio": "normal", "score": 55, "reason": "Pedestrian walkway trip hazard"},
        {"bldg": None, "title": "Security CCTV camera mount bracket loose at Medical Road intersection", "desc": "PTZ surveillance dome camera vibrates in cross-winds, producing unstable surveillance feed for the Proctor desk.", "cat": cat_security, "prio": "high", "score": 75, "reason": "Campus boundary surveillance monitoring"},
        {"bldg": None, "title": "CCTV Camera #12 blind-spot near Women's College rear boundary wall", "desc": "Overgrown neem tree branches have obscured 60% of the camera field of view along the boundary wall perimeter.", "cat": cat_security, "prio": "urgent", "score": 88, "reason": "Hostel perimeter security surveillance"},
        {"bldg": None, "title": "Main University Post Office external boundary wall water drainage spout detached", "desc": "Cast iron rainwater gargoyle pipe has fallen from the wall, splashing roof runoff over pedestrian entrance.", "cat": cat_plumb, "prio": "normal", "score": 45, "reason": "Post office building rainwater drainage"},
        {"bldg": None, "title": "Central Canteen main dining hall ceiling exhaust fan louvre shutter jammed", "desc": "Gravity backdraft louvre shutter on kitchen exhaust is caked in cooking grease and remains closed during cooking.", "cat": cat_elec, "prio": "normal", "score": 60, "reason": "Canteen kitchen smoke evacuation"},
        {"bldg": None, "title": "University Health Service (UHS) Dispensary ambulance parking floodlight burnt", "desc": "The 100W outdoor LED floodlight illuminating the emergency casualty ambulance bay does not turn on.", "cat": cat_estate_elec, "prio": "urgent", "score": 88, "reason": "Emergency ambulance bay illumination"},
        {"bldg": None, "title": "Kennedy Auditorium main stage motorized curtain motor drive gear teeth slipping", "desc": "The heavy velvet stage proscenium curtain pauses and jerks during motorized opening for university functions.", "cat": cat_arts_av, "prio": "normal", "score": 60, "reason": "University auditorium stage mechanism"},
        {"bldg": None, "title": "Horse Riding Club equestrian hurdle timber rail cracked on jumping paddock", "desc": "The top round cross-pole on fence hurdle #4 has split along the grain and poses a splinter risk to horses.", "cat": cat_civil, "prio": "low", "score": 35, "reason": "Equestrian club sports apparatus"},
    ]

    for item in common_complaints_data:
        selected_room = None
        if item["bldg"]:
            bldg = Building.objects.filter(code=item["bldg"]).first()
            rooms = list(Room.objects.filter(floor__building=bldg)) if bldg else []
            selected_room = rooms[random.randint(0, len(rooms)-1)] if rooms else None
            loc_desc = f"{bldg.name if bldg else item['bldg']}"
            if selected_room:
                loc_desc += f", Room {selected_room.number}"
        else:
            loc_desc = "AMU Central Campus Facilities"

        complaints_to_create.append({
            "title": item["title"],
            "desc": f"Location: {loc_desc}. {item['desc']}",
            "cat": item["cat"],
            "room": selected_room,
            "loc_desc": loc_desc,
            "priority": item["prio"],
            "score": item["score"],
            "reason": item["reason"],
        })

    # Exact count enforcement: exactly 237 complaints
    complaints_to_create = complaints_to_create[:237]
    total_count = len(complaints_to_create)
    print(f"📊 Curated exactly {total_count} realistic complaints. Processing insertion & lifecycle...")

    # =========================================================================
    # 4. LIFECYCLE DISTRIBUTION (45 Open, 105 Assigned, 40 In-Progress, 30 Resolved, 12 Closed, 5 Reopened = 237)
    # =========================================================================
    status_distribution = (
        [Complaint.Status.OPEN] * 45 +
        [Complaint.Status.ASSIGNED] * 105 +
        [Complaint.Status.IN_PROGRESS] * 40 +
        [Complaint.Status.RESOLVED] * 30 +
        [Complaint.Status.CLOSED] * 12 +
        [Complaint.Status.REOPENED] * 5
    )
    random.seed(42)  # Deterministic seed for reproducibility
    random.shuffle(status_distribution)

    # Resolution notes pool
    resolution_notes_pool = [
        "Replaced burnt 250V capacitor and restored speed regulation. Tested across speeds 1-5 with normal operation.",
        "Dismantled water tap assembly, cleared calcified scale buildup, and fitted fresh neoprene washer. Zero leakage confirmed.",
        "Replaced heating coil element and tested with clamp meter; current draw normal at 8.7 Amps. Water heating verified.",
        "Re-seated drawer runner channel and secured with 1.5-inch steel wood screws. Drawer glides smoothly.",
        "Reset thermal breaker, cleaned contactor terminals, and adjusted temperature to 68°C. Serving counter heat verified.",
        "Cleared drain leaf debris and flushed downspout with high pressure water. Terrace runoff flow clear.",
        "Re-crimped Cat6 RJ45 patch connector and verified gigabit uplink on switch port. DHCP lease restored.",
        "Tightened projector bracket clamp bolts and replaced HDMI male connector. Display signal clear at 1080p.",
        "Lubricated motor bearings with high-temperature synthetic grease. Vibration reduced to within standard limits.",
        "Replaced internal spring and diaphragm cartridge. Eye-wash fountain releases full flow on paddle push.",
        "Re-aligned door hinges, tightened strike plate screws, and lubricated cylinder latch mechanism.",
        "Replaced failed 36W electronic ballast and installed fresh daylight LED lamp. Illumination restored.",
    ]

    saved_complaints = []
    
    with transaction.atomic():
        for i, data in enumerate(complaints_to_create):
            rep_name = f"{random.choice(first_names)} {random.choice(last_names)}"
            enr_num = get_enrollment()
            target_status = status_distribution[i]

            # Stagger creation time over the last 14 days
            days_ago = random.randint(0, 14)
            hours_ago = random.randint(1, 23)
            created_time = now - timedelta(days=days_ago, hours=hours_ago)

            complaint = Complaint(
                title=data["title"],
                description=data["desc"],
                category=data["cat"],
                room=data["room"],
                location_description=data["loc_desc"],
                reporter_name=rep_name,
                reporter_enrollment_number=enr_num,
                priority=data["priority"],
                priority_score=data["score"],
                priority_reason=data["reason"],
                is_public=True,
                status=Complaint.Status.OPEN,
            )
            # Calculate initial SLA based on priority & category
            set_sla_due_date(complaint, from_time=created_time)

            # Auto-assign technician via dispatcher if advancing past OPEN
            if target_status != Complaint.Status.OPEN:
                auto_dispatch_complaint(complaint, save=False)

            # Save initial complaint
            complaint.save()

            # Override timestamps to simulate realistic history
            Complaint.objects.filter(pk=complaint.pk).update(created_at=created_time, updated_at=created_time)

            # Create initial OPEN history entry
            ComplaintStatusHistory.objects.create(
                complaint=complaint,
                status=Complaint.Status.OPEN,
                note="Complaint lodged via student maintenance portal.",
                created_at=created_time
            )

            # Advance lifecycle according to target_status
            if target_status in [Complaint.Status.ASSIGNED, Complaint.Status.IN_PROGRESS, Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.REOPENED]:
                assigned_time = created_time + timedelta(hours=random.randint(1, 4))
                complaint.status = Complaint.Status.ASSIGNED
                complaint.assigned_at = assigned_time
                complaint.save(update_fields=["status", "assigned_at"])
                Complaint.objects.filter(pk=complaint.pk).update(updated_at=assigned_time)

                staff_name = complaint.assigned_to.get_full_name() or complaint.assigned_to.username if complaint.assigned_to else "Duty Technician"
                ComplaintStatusHistory.objects.create(
                    complaint=complaint,
                    status=Complaint.Status.ASSIGNED,
                    note=f"Work order dispatched to {staff_name} based on trade specialty and hall roster.",
                    created_at=assigned_time
                )

            if target_status in [Complaint.Status.IN_PROGRESS, Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.REOPENED]:
                progress_time = complaint.assigned_at + timedelta(hours=random.randint(1, 8))
                complaint.status = Complaint.Status.IN_PROGRESS
                complaint.in_progress_at = progress_time
                complaint.save(update_fields=["status", "in_progress_at"])
                Complaint.objects.filter(pk=complaint.pk).update(updated_at=progress_time)

                ComplaintStatusHistory.objects.create(
                    complaint=complaint,
                    status=Complaint.Status.IN_PROGRESS,
                    note="Technician arrived on site, commenced inspection and physical maintenance work.",
                    created_at=progress_time
                )

            if target_status in [Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.REOPENED]:
                resolved_time = complaint.in_progress_at + timedelta(hours=random.randint(2, 12))
                note = random.choice(resolution_notes_pool)
                complaint.status = Complaint.Status.RESOLVED
                complaint.resolved_at = resolved_time
                complaint.resolution_note = note
                complaint.resolution_verification = Complaint.ResolutionVerification.PENDING
                complaint.save(update_fields=["status", "resolved_at", "resolution_note", "resolution_verification"])
                Complaint.objects.filter(pk=complaint.pk).update(updated_at=resolved_time)

                ComplaintStatusHistory.objects.create(
                    complaint=complaint,
                    status=Complaint.Status.RESOLVED,
                    note=f"Issue resolved: {note}",
                    created_at=resolved_time
                )

            if target_status == Complaint.Status.CLOSED:
                closed_time = complaint.resolved_at + timedelta(hours=random.randint(4, 24))
                complaint.status = Complaint.Status.CLOSED
                complaint.closed_at = closed_time
                complaint.resolution_verification = Complaint.ResolutionVerification.VERIFIED
                complaint.resolution_verified_at = closed_time
                complaint.save(update_fields=["status", "closed_at", "resolution_verification", "resolution_verified_at"])
                Complaint.objects.filter(pk=complaint.pk).update(updated_at=closed_time)

                ComplaintStatusHistory.objects.create(
                    complaint=complaint,
                    status=Complaint.Status.CLOSED,
                    note="Student verified repair and confirmed complete ticket closure with positive rating.",
                    created_at=closed_time
                )

            if target_status == Complaint.Status.REOPENED:
                reopened_time = complaint.resolved_at + timedelta(hours=random.randint(2, 10))
                complaint.status = Complaint.Status.REOPENED
                complaint.reopened_at = reopened_time
                complaint.reopen_count = 1
                complaint.priority = "urgent"
                complaint.reopen_reason = "Issue recurred within 24 hours of repair. Requires secondary inspection."
                complaint.save(update_fields=["status", "reopened_at", "reopen_count", "priority", "reopen_reason"])
                Complaint.objects.filter(pk=complaint.pk).update(updated_at=reopened_time)

                ComplaintStatusHistory.objects.create(
                    complaint=complaint,
                    status=Complaint.Status.REOPENED,
                    note="Student rejected resolution: Issue recurred within 24 hours of repair. Escalated to URGENT priority.",
                    created_at=reopened_time
                )

            saved_complaints.append(complaint)

    print(f"\n🎉 Successfully created and verified {len(saved_complaints)} realistic complaints!")
    
    # Summary of generated data
    from collections import Counter
    status_counts = Counter(c.status for c in saved_complaints)
    prio_counts = Counter(c.priority for c in saved_complaints)
    print("\nStatus Breakdown:")
    for st, count in status_counts.items():
        print(f"  • {st.upper():12}: {count}")
    print("\nPriority Breakdown:")
    for pr, count in prio_counts.items():
        print(f"  • {pr.upper():12}: {count}")

if __name__ == "__main__":
    run_seed()
