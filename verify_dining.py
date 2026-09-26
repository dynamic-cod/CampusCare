from core.models import Building, UserProfile, Complaint, ComplaintCategory, Department
from core.dispatcher import auto_dispatch_complaint

halls = Building.objects.filter(code__in=["SSN", "SNH", "AFT", "IGH"])
print("Checking Dining Staff across sample halls...")
for h in halls:
    dining_staff = UserProfile.objects.filter(
        role=UserProfile.Role.STAFF,
        managed_building=h,
        user__username__startswith="dining_"
    ).first()
    name = dining_staff.user.username if dining_staff else "MISSING"
    print(f"  Hall: {h.code} -> Dining Staff: {name}")
    assert dining_staff is not None, f"Dining Incharge missing for {h.code}!"

# Test mock complaint dispatch
sample_hall = halls.first()
dept_mess = Department.objects.filter(code="MESS").first()
cat_food = ComplaintCategory.objects.filter(department=dept_mess).first()

print(f"\nSimulating Food Quality Complaint in {sample_hall.name} ...")
mock_room = sample_hall.floors.first().rooms.first()
test_complaint = Complaint.objects.create(
    title="Uncooked raw rotis served in dinner mess",
    description="The rotis served in dinner tonight are completely unbaked and undercooked.",
    room=mock_room,
    category=cat_food
)
auto_dispatch_complaint(test_complaint)
test_complaint.refresh_from_db()

assigned_username = test_complaint.assigned_to.username
print(f"  Assigned staff:    {assigned_username}")
print(f"  Task token:        {test_complaint.staff_task_token}")
assert assigned_username.startswith("dining_"), f"Expected dining_ staff, got {assigned_username}"
assert test_complaint.status == "assigned", f"Expected status=assigned, got {test_complaint.status}"
test_complaint.delete()
print("\nDining Incharge auto-dispatch test PASSED cleanly!")

# Final counts
total_staff = UserProfile.objects.filter(role=UserProfile.Role.STAFF).count()
dining_count = UserProfile.objects.filter(role=UserProfile.Role.STAFF, user__username__startswith="dining_").count()
cats = ComplaintCategory.objects.filter(department=dept_mess).count()
print("\n=== Final Counts ===")
print(f"  Total STAFF profiles : {total_staff}")
print(f"  Dining Incharges     : {dining_count}")
print(f"  MESS categories      : {cats}")
