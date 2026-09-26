#!/usr/bin/env python
"""Script to clear existing data for fresh AMU setup."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campuscare.settings')
django.setup()

from core.models import Campus, Building, Floor, Room, Department, ComplaintCategory, Complaint

def clear_all_data():
    print("=== CLEARING EXISTING DATA ===")
    
    # Clear in correct order respecting foreign keys
    Complaint.objects.all().delete()
    print("✓ Cleared all complaints")
    
    ComplaintCategory.objects.all().delete()
    print("✓ Cleared all complaint categories")
    
    Department.objects.all().delete()
    print("✓ Cleared all departments")
    
    Room.objects.all().delete()
    print("✓ Cleared all rooms")
    
    Floor.objects.all().delete()
    print("✓ Cleared all floors")
    
    Building.objects.all().delete()
    print("✓ Cleared all buildings")
    
    Campus.objects.all().delete()
    print("✓ Cleared all campuses")
    
    print("\n=== DATA CLEARED SUCCESSFULLY ===")

if __name__ == "__main__":
    clear_all_data()