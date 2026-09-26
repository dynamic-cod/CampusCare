from django import forms
from django.contrib.auth.models import User

from .models import Complaint, ComplaintCategory, ComplaintFeedback, Room, UserProfile
from .smart import score_priority, suggest_category


class ComplaintSubmissionForm(forms.ModelForm):
    # Override room field to be a text input instead of dropdown
    room_number = forms.CharField(
        max_length=20, 
        required=False,
        label="Room number (optional)",
        help_text="Enter the room number of your department or hostel (e.g., A205, Hostel-B-301). Leave blank if the issue is outside a specific room."
    )
    
    class Meta:
        model = Complaint
        fields = (
            "reporter_name", "reporter_enrollment_number", "title", "category", "location_description",
            "description", "is_public", "evidence",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "title": forms.TextInput(attrs={"placeholder": "e.g., WiFi not working in Room A205"}),
            "category": forms.Select(attrs={"class": "form-control"})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ComplaintCategory.objects.filter(is_active=True)
        self.fields["category"].required = True
        self.fields["category"].help_text = "Fill the category field"
        self.fields["reporter_name"].label = "Full name"
        self.fields["reporter_enrollment_number"].label = "University enrollment number"
        self.fields["reporter_enrollment_number"].help_text = "Use the number issued by your university."
        self.fields["title"].help_text = "Brief one-line summary of the issue (e.g., 'WiFi not working in Room A205')"
        # Set initial room_number from existing room if editing
        if self.instance and self.instance.room:
            self.fields["room_number"].initial = self.instance.room.number

    def clean(self):
        cleaned_data = super().clean()
        room_number = cleaned_data.get("room_number", "").strip()
        location_desc = cleaned_data.get("location_description", "").strip()
        
        # Store room_number in location_description if provided
        if room_number:
            if location_desc:
                cleaned_data["location_description"] = f"Room {room_number}: {location_desc}"
            else:
                cleaned_data["location_description"] = f"Room {room_number}"
        
        # At least one location info is required
        if not cleaned_data.get("location_description"):
            self.add_error("location_description", "Enter a room number or provide a location description.")
        
        category = cleaned_data.get("category")
        self.category_detected_automatically = False
        self.category_detection_confidence = 0

        title = cleaned_data.get("title", "")
        description = cleaned_data.get("description", "")
        location = cleaned_data.get("location_description", "")
        text = f"{title} {description}"

        if not category:
            self.add_error("category", "Please select a category for your complaint.")

        if category:
            active_cats = ComplaintCategory.objects.filter(is_active=True)
            suggested, conf = suggest_category(text, active_cats)
            if suggested and suggested.id == category.id:
                self.category_detected_automatically = True
                self.category_detection_confidence = conf

            self.priority_score, self.recommended_priority, self.priority_reason, _sla = score_priority(
                text, title=title, description=description,
                category_name=category.name, location=location,
            )
        else:
            self.priority_score = 30
            self.recommended_priority = "low"
            self.priority_reason = ""
        return cleaned_data


class ComplaintAssignmentForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ("assigned_to",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(profile__role=UserProfile.Role.STAFF).select_related("profile")
        self.fields["assigned_to"].label = "Assign to maintenance staff"


class ComplaintStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            (Complaint.Status.OPEN, "Open"), (Complaint.Status.ASSIGNED, "Assigned"),
            (Complaint.Status.IN_PROGRESS, "In progress"), (Complaint.Status.RESOLVED, "Resolved"),
        ]
    )
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}), max_length=1000)


class ResolutionVerificationForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[
            (Complaint.ResolutionVerification.VERIFIED, "Yes, the issue is resolved"),
            (Complaint.ResolutionVerification.REJECTED, "No, the issue remains"),
        ],
        widget=forms.RadioSelect,
    )
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}), max_length=1000)


class ComplaintFeedbackForm(forms.ModelForm):
    class Meta:
        model = ComplaintFeedback
        fields = ("rating", "comment")
        widgets = {"rating": forms.Select(choices=[(number, f"{number} / 5") for number in range(1, 6)]), "comment": forms.Textarea(attrs={"rows": 3})}


class ComplaintReopenForm(forms.Form):
    note = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), max_length=1000, label="Why does this complaint need to be reopened?")
