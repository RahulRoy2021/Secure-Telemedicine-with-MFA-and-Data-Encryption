# users/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
# --- Import necessary models ---
from .models import CustomUser, DoctorProfile, DoctorReview, AvailabilitySlot
from django.core.exceptions import ValidationError
from django.utils import timezone

class CustomUserCreationForm(UserCreationForm):
    phone_number = forms.CharField(max_length=15, required=True, help_text="Enter your phone number")
    ROLE_CHOICES = (
        ('PATIENT', 'Patient'),
        ('DOCTOR', 'Doctor'),
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        widget=forms.RadioSelect # Or forms.Select for a dropdown
    )
    class Meta:
        model = CustomUser
        fields = ["username", "email", "phone_number"]

class CustomUserAdminAddForm(forms.ModelForm):
    """
    A simpler form for creating users specifically in the admin add view.
    Inherits from ModelForm.
    """
    password = forms.CharField(widget=forms.PasswordInput)
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password'] # Fields needed for creation

    def save(self, commit=True):
        # Override save to hash the password correctly
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"]) # Hash the password
        if commit:
            user.save()
        return user
class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        # List fields doctor can edit (awards removed based on previous discussion)
        fields = [
            'specialization', 'profile_picture', 'degree', 'address',
            'consultation_charges',
            'experience_years', 'qualifications',
            'clinic_name', 'clinic_address',
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'qualifications': forms.Textarea(attrs={'rows': 4}),
            # 'awards': forms.Textarea(attrs={'rows': 3}), # Removed
            'clinic_address': forms.Textarea(attrs={'rows': 3}),
        }

    # Optional: Add __init__ to apply CSS classes if needed
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Example: Apply 'form-control' class to most fields
        # for field_name, field in self.fields.items():
        #     if not isinstance(field.widget, (forms.CheckboxInput, forms.FileInput)):
        #          field.widget.attrs.update({'class': 'form-control'})


# --- NEW FORM FOR DOCTOR REVIEWS ---
class DoctorReviewForm(forms.ModelForm):
    # Optionally customize the rating widget
    rating = forms.ChoiceField(
        choices=[(i, f'{i} Stars') for i in range(1, 6)], # Generate choices 1-5
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}), # Style radios if needed
        required=True
    )

    class Meta:
        model = DoctorReview
        fields = ['rating', 'comment'] # Fields the patient will fill
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Share your experience...'}),
            # Rating widget is defined above
        }
        labels = {
            'rating': 'Your Rating (1-5 Stars)',
            'comment': 'Your Review Comments (Optional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optional: Apply Bootstrap classes here too
        # self.fields['comment'].widget.attrs.update({'class': 'form-control'})
        # Note: RadioSelect styling often needs more custom CSS or Bootstrap wrappers in the template

# --- NEW FORM FOR AVAILABILITY SLOTS ---
# --- UPDATED FORM FOR AVAILABILITY SLOTS ---
class AvailabilitySlotForm(forms.ModelForm):
    # Explicitly define fields using SplitDateTimeField
    start_time = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={'type': 'date', 'class': 'form-control'}, # Add form-control class
            time_attrs={'type': 'time', 'class': 'form-control'} # Add form-control class
        ),
        label="Slot Start Time"
    )
    end_time = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={'type': 'date', 'class': 'form-control'}, # Add form-control class
            time_attrs={'type': 'time', 'class': 'form-control'} # Add form-control class
        ),
        label="Slot End Time"
    )

    class Meta:
        model = AvailabilitySlot
        # Fields from model used directly (doctor set in view, is_booked defaults)
        fields = ['start_time', 'end_time']
        # Widgets are defined on the fields above now, so this isn't strictly needed
        # but doesn't hurt to leave if you add more fields later.
        widgets = {
            'start_time': forms.SplitDateTimeWidget(),
            'end_time': forms.SplitDateTimeWidget(),
        }
        # Labels are defined on the fields above now


    def clean(self):
        """
        Add validation:
        1. End time must be after start time.
        2. Start time cannot be in the past.
        """
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time:
            if end_time <= start_time:
                # Raise validation error on the specific field if possible
                self.add_error('end_time', "End time must be after start time.")
                # Or raise a general form error: raise ValidationError("End time must be after start time.")

            # Compare naive datetime from form with aware datetime from timezone.now()
            # Make timezone.now() naive if start_time is naive, or make start_time aware
            # Assuming settings.USE_TZ=True (default), model fields are aware, form fields may be naive
            # Best practice is often to make form fields aware if USE_TZ=True
            # Simpler check (might have issues around DST changes if naive):
            # if start_time.replace(tzinfo=None) < timezone.now().replace(tzinfo=None):
            # Safer check:
            if timezone.is_naive(start_time):
                 now_naive = timezone.make_naive(timezone.now(), timezone.get_current_timezone())
                 if start_time < now_naive:
                     self.add_error('start_time', "Start time cannot be in the past.")
            elif start_time < timezone.now(): # If start_time is aware
                 self.add_error('start_time', "Start time cannot be in the past.")

        return cleaned_data

    # Optional: Add __init__
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
# --- ADD NEW SEARCH FORM ---
class DoctorSearchForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        required=False,
        label="Doctor Name",
        widget=forms.TextInput(attrs={'placeholder': 'Enter name...'})
    )
    specialization = forms.CharField(
        max_length=100,
        required=False,
        label="Specialization",
        widget=forms.TextInput(attrs={'placeholder': 'Enter specialization...'})
    )
    # Add other fields to search by later if needed (e.g., location)

# --- END NEW SEARCH FORM ---
