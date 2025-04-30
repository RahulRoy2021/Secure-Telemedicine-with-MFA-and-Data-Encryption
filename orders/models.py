# In medical_records/models.py OR orders/models.py

from django.db import models
from django.conf import settings # To link to your CustomUser model
from django.utils import timezone

class MedicineOrder(models.Model):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Keep order even if doctor account deleted
        related_name='issued_medicine_orders',
        limit_choices_to={'doctor_profile__isnull': False}, # Ensure it's a doctor
        null=True # Allow null if doctor is deleted
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, # Delete orders if patient deleted? Or SET_NULL?
        related_name='received_medicine_orders',
        limit_choices_to={'patient_profile__isnull': False} # Ensure it's a patient
    )
    # --- How to store the actual order? ---
    # Option 1: Simple Text Field (Easiest to start)
    order_details = models.TextField(
        help_text="List medications, dosage, frequency, duration, and any other instructions."
    )

    # Option 2: Structured Data (More complex, better for processing)
    # Requires PostgreSQL usually for good JSONField support, or use TextField and parse JSON manually
    # order_items = models.JSONField(
    #    default=list,
    #    help_text="List of items, e.g., [{'name':'MedA', 'dosage':'10mg', 'qty':30}]"
    # )
    # OR create a separate OrderItem model linked via ForeignKey

    notes = models.TextField(blank=True, null=True, help_text="Additional notes for the patient or pharmacy.")
    created_at = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)
    # Consider adding a status field later if needed (e.g., 'sent', 'filled')

    def __str__(self):
        # Use pk for uniqueness as doctor might be null
        doctor_name = self.doctor.username if self.doctor else "[Deleted Doctor]"
        return f"Order (ID: {self.pk}) for {self.patient.username} by Dr. {doctor_name} on {self.created_at.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-created_at'] # Show newest orders first by default