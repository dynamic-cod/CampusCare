#!/usr/bin/env python
"""Test script to verify system state and functionality."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campuscare.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile, Department, Campus, Building, Floor, Room, ComplaintCategory, Complaint

def test_users():
    print("=== USERS ===")
    users = User.objects.all()
    for user in users:
        print(f"Username: {user.username}, Email: {user.email}, Is Superuser: {user.is_superuser}, Is Staff: {user.is_staff}")
        try:
            profile = user.profile
            print(f"  Role: {profile.get_role_display()}, Department: {profile.department}")
        except UserProfile.DoesNotExist:
            print("  No profile")
    print(f"Total users: {users.count()}\n")

def test_campus_structure():
    print("=== CAMPUS STRUCTURE ===")
    campuses = Campus.objects.all()
    print(f"Campuses: {campuses.count()}")
    if campuses.count() == 0:
        print("WARNING: No campuses found in database!")
    for campus in campuses:
        print(f"  {campus.name} ({campus.code})")
        buildings = campus.buildings.filter(is_active=True)
        print(f"    Buildings: {buildings.count()}")
        for building in buildings:
            print(f"      {building.name} ({building.code})")
            floors = building.floors.all()
            print(f"        Floors: {floors.count()}")
            for floor in floors:
                rooms = floor.rooms.filter(is_active=True)
                print(f"          Floor {floor.number}: {rooms.count()} rooms")
    print()

def test_departments():
    print("=== DEPARTMENTS ===")
    departments = Department.objects.filter(is_active=True)
    print(f"Active departments: {departments.count()}")
    for dept in departments:
        print(f"  {dept.name} ({dept.code})")
        categories = dept.complaint_categories.filter(is_active=True)
        print(f"    Categories: {categories.count()}")
        for cat in categories:
            print(f"      - {cat.name} (SLA: {cat.default_sla_hours}h)")
    print()

def test_complaints():
    print("=== COMPLAINTS ===")
    complaints = Complaint.objects.all()
    print(f"Total complaints: {complaints.count()}")
    if complaints.count() == 0:
        print("WARNING: No complaints found in database!")
    for complaint in complaints[:5]:
        print(f"  {complaint.reference}: {complaint.title}")
        print(f"    Status: {complaint.get_status_display()}, Priority: {complaint.get_priority_display()}")
        print(f"    Category: {complaint.category.name}, Room: {complaint.room}")
    print()

if __name__ == "__main__":
    test_users()
    test_campus_structure()
    test_departments()
    test_complaints()
    print("Database state check complete!")
