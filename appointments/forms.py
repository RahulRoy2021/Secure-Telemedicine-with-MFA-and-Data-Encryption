# appointments/forms.py
from django import forms
from .models import Appointment # Import Appointment model

class AppointmentBookingForm(forms.Form):
    # Add fields the patient needs to fill just before confirming
    symptoms = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Briefly describe your symptoms or reason for visit'}),
        required=False # Make optional or required as needed
    )
    appointment_type = forms.ChoiceField(
        choices=Appointment.APPOINTMENT_TYPES, # Get choices from the model
        required=True,
        widget=forms.RadioSelect # Or forms.Select for dropdown
    )
    # We could add appointment_type selection here if not determined earlier
    # appointment_type = forms.ChoiceField(choices=Appointment.APPOINTMENT_TYPES)

    # Hidden fields for slot and doctor will be handled in the template/view