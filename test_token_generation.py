#!/usr/bin/env python
"""Test script to verify token generation for new complaints."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campuscare.settings')
django.setup()

from core.models import Complaint, ComplaintCategory, Room
from django.core.exceptions import ValidationError

def test_token_generation():
    print("=== TESTING TOKEN GENERATION FOR NEW COMPLAINTS ===")
    
    # Get a category and room for testing
    category = ComplaintCategory.objects.first()
    room = Room.objects.first()
    
    if not category:
        print("ERROR: No categories found. Please run populate_categories first.")
        return
    
    print(f"Using category: {category.name}")
    print(f"Using room: {room if room else 'None (location description only)'}")
    print()
    
    # Create a new complaint
    try:
        complaint = Complaint.objects.create(
            reporter_name="Test Student",
            reporter_enrollment_number="TEST123",
            title="Test complaint for token generation",
            description="This is a test complaint to verify token generation works.",
            category=category,
            room=room,
            location_description="Test location",
            priority="normal"
        )
        
        print(f"✅ NEW COMPLAINT CREATED")
        print(f"Reference: {complaint.reference}")
        print(f"Tracking Token: {complaint.tracking_token}")
        print(f"Token Length: {len(complaint.tracking_token)} characters")
        print(f"Token Generated: {'YES' if complaint.tracking_token else 'NO'}")
        
        # Verify uniqueness
        is_unique = Complaint.objects.filter(tracking_token=complaint.tracking_token).count() == 1
        print(f"Token Unique: {'YES' if is_unique else 'NO'}")
        
        # Test tracking URL
        tracking_url = f"/track/{complaint.tracking_token}/"
        print(f"Tracking URL: {tracking_url}")
        
        # Clean up
        complaint.delete()
        print()
        print("✅ Test complaint cleaned up")
        
        if complaint.tracking_token and is_unique:
            print("✅ TOKEN GENERATION WORKING CORRECTLY")
            return True
        else:
            print("❌ TOKEN GENERATION FAILED")
            return False
            
    except Exception as e:
        print(f"❌ ERROR creating test complaint: {e}")
        return False

if __name__ == "__main__":
    success = test_token_generation()
    if success:
        print("\n✅ All token generation tests passed!")
    else:
        print("\n❌ Token generation tests failed!")
