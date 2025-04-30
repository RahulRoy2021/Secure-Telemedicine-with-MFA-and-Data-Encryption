# appointments/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
# --- Import AvailabilitySlot ---
from users.models import AvailabilitySlot # Adjust import path if needed

class Appointment(models.Model):
    # ... (existing patient, doctor fields) ...
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='patient_appointments',
        on_delete=models.CASCADE
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='doctor_appointments',
        limit_choices_to={'doctor_profile__isnull': False},
        on_delete=models.CASCADE
    )

    # --- ADD THIS FIELD ---
    # Link to the specific slot that was booked for this appointment
    availability_slot = models.ForeignKey(
        AvailabilitySlot,
        on_delete=models.SET_NULL, # Keep appointment record even if slot deleted
        null=True, # Allow null because older appts might not have a link
        blank=True, # Allow blank in forms/admin if needed
        related_name='appointment_booked' # Name to access appointment from slot
    )
    # --- END ADDED FIELD ---

    # ... (existing appointment_type, requested_date, requested_time, symptoms, status, etc. fields) ...
    APPOINTMENT_TYPES = [
        ('VIDEO', 'Video Consultation'),
        ('CLINIC', 'Clinic Visit'),
        ('HOME', 'Home Visit'),
     ]
    appointment_type = models.CharField(max_length=10, choices=APPOINTMENT_TYPES, default='VIDEO')
    requested_date = models.DateField()
    requested_time = models.TimeField()
    symptoms = models.TextField(blank=True)
    address = models.TextField(blank=True, null=True)
    APPOINTMENT_STATUS = [
        ('PENDING', 'Pending Confirmation'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED_PATIENT', 'Cancelled by Patient'),
        ('CANCELLED_DOCTOR', 'Cancelled by Doctor'),
        ('NO_SHOW', 'No Show'),
    ]
    status = models.CharField(max_length=20, choices=APPOINTMENT_STATUS, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


    def __str__(self):
         return f"Appointment for {self.patient.username} with {self.doctor.username} on {self.requested_date} at {self.requested_time}"

    class Meta:
        ordering = ['requested_date', 'requested_time']