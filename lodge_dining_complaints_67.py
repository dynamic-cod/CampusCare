"""
lodge_dining_complaints_67.py
==============================
Permanently lodge 67 realistic food/dining complaints into the live DB.
- All 20 residential halls covered at least 3 times.
- All 4 MESS categories used.
- Each complaint dispatched via the MESS fast-path to the hall's Dining Incharge.
- No cleanup — data persists for dashboard inspection.

Run:
    ./.venv/bin/python manage.py shell -c "exec(open('lodge_dining_complaints_67.py').read())"
"""

import random
from django.db.models import Q
from django.utils import timezone
from core.models import (
    Building, UserProfile, Complaint, ComplaintCategory,
    Department, ComplaintStatusHistory
)
from core.dispatcher import auto_dispatch_complaint

random.seed(2026)

# ─── 67 varied realistic food/dining scenarios ────────────────────────────────
SCENARIOS = [
    # Food Quality & Preparation (18)
    ("Raw and undercooked roti served at dinner",
     "The rotis served tonight were completely uncooked from inside. Students could not eat them."),
    ("Stale and sour dal at lunch mess",
     "The dal served at today's lunch was clearly stale and had a sour fermented smell."),
    ("Cockroach found inside rice bowl",
     "A live cockroach was found inside a student's rice bowl at dinner. Urgent pest control needed."),
    ("Worm discovered in vegetable curry",
     "A worm was found in the vegetable curry by two students at dinner. Immediate action required."),
    ("Biryani served was completely cold and stale",
     "The biryani served on Friday was cold and clearly leftover from the previous meal."),
    ("Undercooked chicken in non-veg curry",
     "Raw and undercooked chicken pieces were served in the non-veg curry at dinner tonight."),
    ("Oil used in food is rancid and smells bad",
     "The food has been tasting rancid for several days. Substandard cooking oil is suspected."),
    ("Expired milk served at breakfast",
     "The milk served this morning was curdled and had an expired smell. Students avoided it."),
    ("Tasteless and unseasoned food all week",
     "Meals this entire week have been bland and completely unseasoned. No salt or spices."),
    ("Food quality drastically declined",
     "The overall food quality has dropped significantly. Meals are often cold, unseasoned, or stale."),
    ("Sand and grit found in rice",
     "Students found sand and grit in the rice served at dinner. It appears unwashed."),
    ("Insect found in chapati",
     "An insect was found baked inside a chapati at dinner. Serious food safety concern."),
    ("Sabzi served raw and uncooked",
     "The vegetable sabzi served tonight was raw and crunchy — clearly not properly cooked."),
    ("Caterer serving leftover food from previous day",
     "Leftover food from the previous day is being reheated and served to students without disclosure."),
    ("Non-veg smell in vegetarian food",
     "Vegetarian students have complained of non-vegetarian smell in their vegetable curry."),
    ("Food poisoning suspected after dinner",
     "Over 12 students fell ill after having dinner tonight. Vomiting and stomach pain reported."),
    ("Hair found repeatedly in food",
     "Multiple students have found hair strands in their food over the past week."),
    ("Raw eggs served at breakfast",
     "The boiled eggs served at breakfast were completely raw inside. A food safety violation."),

    # Dining Hall Maintenance & Hygiene (18)
    ("Dining hall tables not cleaned between meals",
     "Tables in the dining hall are filthy with leftover food from previous meals. No cleaning done."),
    ("Flies and mosquitoes infesting the dining area",
     "The dining hall has a severe mosquito and fly problem. No pest control treatment done."),
    ("Washroom near mess in very dirty condition",
     "The washrooms adjacent to the mess are extremely dirty and not being cleaned regularly."),
    ("Utensils served with food residue on them",
     "Plates, spoons, and glasses are being handed out without proper washing. Residue is visible."),
    ("Serving area floor covered in slippery grease",
     "The floor near the food serving counters is covered in grease. It is a slip and fall hazard."),
    ("Garbage bins overflowing inside dining hall",
     "Dustbins inside the dining hall are overflowing and not being emptied. Unbearable smell."),
    ("Rats spotted inside the dining hall kitchen",
     "Students and kitchen staff have spotted rats near the kitchen and food storage area."),
    ("Serving staff not wearing gloves or masks",
     "Staff serving food are not using gloves or face masks. This is a basic hygiene violation."),
    ("Dining tables have broken glass pieces",
     "Broken glass pieces were found on two dining tables during dinner. Safety risk for students."),
    ("Pest infestation in food storage area",
     "A cockroach and ant infestation has been observed near the food storage and pantry area."),
    ("Open drainage smell entering dining hall",
     "There is a strong drainage odor entering the dining hall from an open nearby drain."),
    ("No handwash soap at any sink in dining area",
     "All handwash stations in the dining area have been empty of soap for over a week."),
    ("Food serving counter is visibly dirty",
     "The food serving counter and surrounding surfaces are caked with old food stains."),
    ("Student sitting area not mopped or cleaned",
     "The student seating area is dirty with spilled food on floors that have not been mopped."),
    ("Wet floor with no warning sign in mess",
     "The mess floor is wet after mopping with no warning sign placed. Students are slipping."),
    ("Stray dogs entered the dining hall compound",
     "Stray dogs were seen entering the dining hall compound. The boundary is not secured."),
    ("Kitchen walls have fungal growth",
     "Black mold and fungal growth is visible on the kitchen walls near the cooking area."),
    ("Serving staff touching food with bare hands",
     "Kitchen staff are handling cooked food directly with bare hands without gloves."),

    # Mess Timings & Ration Supply (16)
    ("Mess closed 40 minutes before official time",
     "The mess was shut down at 8:20 PM instead of the announced 9:00 PM closure time."),
    ("Breakfast serving starts very late every day",
     "Breakfast does not begin until 8:30 AM instead of 7:30 AM causing students to miss morning classes."),
    ("Food quantity insufficient for dinner",
     "The quantity of food served at dinner is far too little. Students leave the mess hungry."),
    ("No vegetarian option served at lunch",
     "No vegetarian main dish was available at today's lunch despite being listed in the menu."),
    ("Mess menu not followed for 2 weeks",
     "The printed mess menu has not been followed for 14 consecutive days. Items differ completely."),
    ("Diet registration portal not working",
     "The online diet token registration system has not been functional for the new semester."),
    ("Insufficient rotis served per student",
     "Each student is being given only two rotis regardless of how many they ask for."),
    ("Late night snack not provided as promised",
     "The late-night snack between 10 PM and 11 PM that was promised in the mess charter is missing."),
    ("Special diet for sick students not arranged",
     "Students admitted to the dispensary have not received the prescribed special diet from the mess."),
    ("Sunday special menu cancelled without notice",
     "The Sunday special meal was cancelled without any prior notice or announcement."),
    ("Ramadan Sehri and Iftar timings not adjusted",
     "The mess has not adjusted its timings for Ramadan despite multiple requests from students."),
    ("Mess open during exam but schedule not updated",
     "During exam week, mess timings have not been adjusted to suit students studying late."),
    ("Insufficient bread at breakfast",
     "Bread runs out within 15 minutes of breakfast opening. Latecomers find nothing to eat."),
    ("Condiments and sugar not replenished",
     "Sugar, salt, and other condiments on dining tables have not been refilled for over a week."),
    ("Extra meal not provided during annual function",
     "During the hall annual function, the caterer failed to provide the extra meal that was committed."),
    ("Students charged extra without prior notice",
     "The caterer is charging students extra for meals that were supposed to be covered by the mess fee."),

    # Dining Hall Water & Utilities (15)
    ("Water cooler in dining hall not working",
     "The only water cooler in the dining hall has been non-functional for 3 days. No cold water available."),
    ("Geyser in utensil washing area broken",
     "The geyser used for hot water in the utensil washing area has stopped working. Cold washing is unhygienic."),
    ("Drinking water tastes foul and smells bad",
     "The water served in the dining hall has a strong foul smell. Students suspect pipeline contamination."),
    ("Water supply to mess kitchen cut off",
     "The mess kitchen had no running water this morning causing breakfast to be delayed significantly."),
    ("Water cooler leaking on dining hall floor",
     "The water cooler near the entrance is leaking continuously creating a slip hazard."),
    ("Hot water tap in handwash area not working",
     "The hot water tap at the student handwash station near the dining area has stopped functioning."),
    ("Overhead water tank above kitchen not cleaned",
     "The overhead water storage tank above the kitchen has reportedly not been cleaned in months."),
    ("Water cooler RO filter not replaced",
     "The RO filter in the dining hall water cooler has not been replaced in months. Water quality is poor."),
    ("Electric connection to mess kitchen tripping",
     "The electrical supply to the kitchen is frequently tripping affecting cooking gas burners and lights."),
    ("Mess exhaust fan not working in kitchen",
     "The kitchen exhaust fan is broken causing smoke accumulation inside the cooking area."),
    ("Lights in dining hall not working properly",
     "Several tube lights in the dining hall are not functioning. The area is very dim at dinner time."),
    ("Cold water tap broken at handwash area",
     "The cold water tap at the student handwash station has been broken for over a week."),
    ("Water stagnation near dining hall entrance",
     "Water is stagnating near the main entrance of the dining hall creating a breeding ground for mosquitoes."),
    ("Mess gas pipeline making hissing sound",
     "Students and staff have reported a hissing sound from the gas pipeline near the kitchen. Safety risk."),
    ("Water cooler dispensing warm water only",
     "The water cooler is dispensing only warm water. The cooling compressor appears to have failed."),
]

assert len(SCENARIOS) == 67, f"Expected 67 scenarios, got {len(SCENARIOS)}"

# ─── Setup ────────────────────────────────────────────────────────────────────
halls     = list(Building.objects.filter(building_type__in=["hall", "residential"]).order_by("code"))
mess_dept = Department.objects.get(code="MESS")
cats      = {c.name: c for c in ComplaintCategory.objects.filter(department=mess_dept, is_active=True)}

cat_quality  = cats.get("Food Quality & Preparation")
cat_hygiene  = cats.get("Dining Hall Maintenance & Hygiene")
cat_timing   = cats.get("Mess Timings & Ration Supply")
cat_water    = cats.get("Dining Hall Water & Utilities")

# Category index ranges matching SCENARIOS order above
CATEGORY_MAP = (
    [(0, 18,  cat_quality),
     (18, 36, cat_hygiene),
     (36, 52, cat_timing),
     (52, 67, cat_water)]
)

def get_category_for_index(i):
    for start, end, cat in CATEGORY_MAP:
        if start <= i < end:
            return cat
    return cat_quality

# Hall pool: 20 halls × 3 = 60, then 7 random extras
hall_pool  = halls * 3           # 60 entries, each hall 3×
extras     = random.choices(halls, k=7)
all_halls  = hall_pool + extras  # 67 total
random.shuffle(all_halls)

# ─── Lodge complaints ─────────────────────────────────────────────────────────
print("=" * 72)
print("  CampusCare — Lodging 67 Live Dining Complaints into Database")
print("=" * 72)
print(f"\n{'#':<4} {'Hall':<6} {'Category':<38} {'Assigned To':<26} Status")
print("-" * 95)

success = 0
skipped = 0
lodged_refs = []

for idx, (hall, (title, desc)) in enumerate(zip(all_halls, SCENARIOS), start=1):
    cat = get_category_for_index(idx - 1)

    # Get a usable room for this hall
    floor = hall.floors.first()
    if not floor:
        print(f"{idx:<4} {hall.code:<6} {'No floors — skipped':<38}")
        skipped += 1
        continue
    room = floor.rooms.first()
    if not room:
        print(f"{idx:<4} {hall.code:<6} {'No rooms — skipped':<38}")
        skipped += 1
        continue

    # Create the complaint
    complaint = Complaint.objects.create(
        title=title,
        description=desc,
        room=room,
        category=cat,
        reporter_name=f"Student Test {idx:02d}",
        reporter_enrollment_number=f"TEST-DIN-{2000 + idx}",
        location_description=f"{hall.name} — Dining Hall",
    )

    # Dispatch via MESS fast-path (mirrors fixed views.py logic)
    dept_code = complaint.category.department.code
    if dept_code in ("MESS", "DINING"):
        auto_dispatch_complaint(complaint, save=True)

    complaint.refresh_from_db()

    # Log status history entry
    if complaint.assigned_to:
        ComplaintStatusHistory.objects.get_or_create(
            complaint=complaint,
            status=complaint.status,
            defaults={"note": f"Auto-dispatched to {complaint.assigned_to.username} (test data)."},
        )

    assigned = complaint.assigned_to.username if complaint.assigned_to else "NONE"
    expected = f"dining_{hall.code.lower()}"
    ok_tag   = "✓" if assigned == expected else "✗"
    cat_short = cat.name[:36]

    print(f"{idx:<4} {hall.code:<6} {cat_short:<38} {assigned:<26} {ok_tag} {complaint.reference}")
    lodged_refs.append((complaint.reference, hall.code, assigned))
    success += 1

# ─── Final report ─────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print(f"  SUMMARY:  {success} complaints lodged  |  {skipped} skipped")
print("=" * 72)

# Coverage per hall
from collections import Counter
hall_cov = Counter(h.code for h, _ in zip(all_halls, SCENARIOS))
print(f"\n  Hall coverage (each should be ≥ 3):")
for h in sorted(halls, key=lambda x: x.code):
    count = hall_cov.get(h.code, 0)
    bar   = "█" * count
    mark  = "✓" if count >= 3 else "✗"
    print(f"    {mark} {h.code:<6} {bar} ({count}×)")

# Category breakdown
cat_cov = Counter()
for i in range(67):
    cat_cov[get_category_for_index(i).name] += 1
print(f"\n  Category breakdown:")
for name, cnt in cat_cov.items():
    print(f"    {cnt:>2}×  {name}")

print(f"\n  Data is LIVE in the database.")
print(f"  View on provost dashboards at: http://127.0.0.1:8000/dashboard/")
print("=" * 72)
