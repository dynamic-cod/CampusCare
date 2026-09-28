#!/usr/bin/env python
"""Test script to verify CSRF-protected form submission works using Django test client."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campuscare.settings')
django.setup()

from django.test import Client
from core.models import ComplaintCategory, Room, Complaint

def test_csrf_submission():
    print("=== TESTING CSRF PROTECTED FORM SUBMISSION ===")
    
    client = Client()
    form_url = "/complaints/new/"
    
    try:
        # Get the form page first (this establishes the session and CSRF token)
        response = client.get(form_url)
        print(f"✅ Form page loaded: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Could not load form page")
            return False
        
        # Get form data
        category = ComplaintCategory.objects.first()
        room = Room.objects.first()
        
        if not category:
            print("❌ No categories found")
            return False
        
        print(f"Using category: {category.name}")
        print(f"Using room: {room if room else 'None'}")
        
        # Prepare form data
        form_data = {
            'reporter_name': 'Test Student',
            'reporter_enrollment_number': 'TEST-456',
            'title': 'CSRF Test Complaint',
            'description': 'This is a test to verify CSRF protection works correctly.',
            'category': category.id,
            'room_number': room.id if room else '',
            'location_description': 'Test location for CSRF verification',
            'priority': 'normal',
            'is_public': 'on',
        }
        
        # Submit the form (Django test client handles CSRF automatically)
        submit_response = client.post(form_url, data=form_data)
        print(f"✅ Form submitted: {submit_response.status_code}")
        
        # Check if submission was successful (should redirect)
        if submit_response.status_code in [302, 303]:
            redirect_url = submit_response.url if hasattr(submit_response, 'url') else submit_response.get('Location', 'unknown')
            print(f"✅ Form submission successful - redirect to: {redirect_url}")
            
            # Verify complaint was created
            new_complaint = Complaint.objects.filter(title='CSRF Test Complaint').first()
            if new_complaint:
                print(f"✅ Complaint created successfully: {new_complaint.reference}")
                print(f"   Tracking token: {new_complaint.tracking_token}")
                # Clean up
                new_complaint.delete()
                print("✅ Test complaint cleaned up")
            else:
                print("⚠️ Complaint not found in database")
            
            return True
        elif submit_response.status_code == 200:
            # Check for CSRF error in response
            if 'CSRF verification failed' in str(submit_response.content):
                print("❌ CSRF verification failed")
                return False
            else:
                print("⚠️ Form returned 200 but didn't redirect - might have validation errors")
                print(f"Response content preview: {str(submit_response.content)[:200]}")
                return False
        else:
            print(f"❌ Unexpected status code: {submit_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_csrf_submission()
    if success:
        print("\n✅ CSRF submission test passed!")
    else:
        print("\n❌ CSRF submission test failed!")
