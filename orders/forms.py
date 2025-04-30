# orders/forms.py
from django import forms
from .models import MedicineOrder
from users.models import CustomUser # To filter patients
# Import Appointment model to query completed appointments
from appointments.models import Appointment # Adjust import if needed

class MedicineOrderForm(forms.ModelForm):
    # Define patient field here but we will override queryset in __init__
    patient = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(), # Start with empty queryset
        label="Select Patient (must have completed appointment)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        # Pop the 'user' (the doctor) from kwargs BEFORE calling super
        doctor = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if doctor and doctor.is_doctor:
            # Find patient IDs who have a COMPLETED appointment with this doctor
            completed_patient_ids = Appointment.objects.filter(
                doctor=doctor,
                status='COMPLETED'
            ).values_list('patient_id', flat=True).distinct()

            # Set the queryset for the patient field
            self.fields['patient'].queryset = CustomUser.objects.filter(
                pk__in=completed_patient_ids,
                is_active=True # Still ensure patient is active
            ).order_by('username')
        else:
            # If no doctor provided or user is not a doctor, keep queryset empty
            # or handle error as appropriate for your application logic
             self.fields['patient'].queryset = CustomUser.objects.none()


    class Meta:
        model = MedicineOrder
        # Fields the doctor fills in:
        fields = ['patient', 'order_details', 'notes']
        widgets = {
            'order_details': forms.Textarea(attrs={'rows': 6, 'class': 'form-control', 'placeholder': 'Enter medication, dosage, frequency, duration...'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Optional notes...'}),
        }
        labels = {
            'order_details': "Order Details (Medication, Dosage, etc.)",
            'notes': "Additional Notes (Optional)",
        }