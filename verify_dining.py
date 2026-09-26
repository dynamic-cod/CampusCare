"""Full verification suite for Dining Incharge feature."""
from core.models import Building, UserProfile, Complaint, ComplaintCategory, Department
from core.dispatcher import auto_dispatch_complaint

# 1. Verify MESS department
dept = Department.objects.get(code="MESS")
print(f"[OK] MESS dept: {dept.name}")

# 2. Verify 4 active categories
cats = ComplaintCategory.objects.filter(department=dept, is_active=True)
cat_names = list(cats.values_list("name", flat=True))
print(f"[OK] Dining Categories ({cats.count()}): {cat_names}")
assert cats.count() >= 4, f"Expected >=4 categories, got {cats.count()}"

# 3. Verify all halls have a Dining Incharge
halls = Building.objects.filter(building_type__in=["hall", "residential"])
missing = []
for hall in halls:
    staff = UserProfile.objects.filter(
        role=UserProfile.Role.STAFF,
        managed_building=hall,
        managed_department=dept,
    ).first()
    if not staff:
        missing.append(hall.code)
if missing:
    print(f"[FAIL] Missing Dining Incharge for: {missing}")
else:
    print(f"[OK] All {halls.count()} halls have a resident Dining Incharge")

# 4. Test auto-dispatch for each sample hall
test_halls = Building.objects.filter(code__in=["SSN", "SNH", "AFT", "IGH", "ABH"])
for hall in test_halls:
    cat_food = cats.first()
    mock_room = hall.floors.first().rooms.first()
    c = Complaint.objects.create(
        title="Cleanliness issue in dining hall tables",
        description="The tables in the dining hall are not sanitized after dinner.",
        room=mock_room,
        category=cat_food,
    )
    auto_dispatch_complaint(c)
    c.refresh_from_db()
    assigned = c.assigned_to.username if c.assigned_to else "NONE"
    expected = f"dining_{hall.code.lower()}"
    status = "[OK]  " if assigned == expected else "[FAIL]"
    print(f"{status} Hall {hall.code}: assigned → {assigned} (expected: {expected})")
    c.delete()

# 5. Summary counts
total_staff  = UserProfile.objects.filter(role=UserProfile.Role.STAFF).count()
dining_count = UserProfile.objects.filter(role=UserProfile.Role.STAFF, user__username__startswith="dining_").count()
print(f"\n=== Final Counts ===")
print(f"  Total STAFF profiles : {total_staff}")
print(f"  Dining Incharges     : {dining_count}")
print(f"  Active MESS cats     : {cats.count()}")
print("\nDining Incharge feature verification COMPLETE.")
