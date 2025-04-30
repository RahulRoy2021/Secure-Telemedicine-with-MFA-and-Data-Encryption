# telemedicine_platform/users/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings # Import settings
# --- Import validators for rating ---
from django.core.validators import MaxValueValidator, MinValueValidator
# ------------------------------------
# Signals imports (keep if you implement automatic profile creation)
# from django.db.models.signals import post_save
# from django.dispatch import receiver

class CustomUser(AbstractUser):
    # Keep core fields
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)

    # Keep groups/permissions fixes if they are working for you
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="customuser_set", # Custom related_name
        blank=True
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="customuser_set", # Custom related_name
        blank=True
    )

    # Add property methods for easy role checking (optional but helpful)
    @property
    def is_patient(self):
        return hasattr(self, 'patient_profile')

    @property
    def is_doctor(self):
        return hasattr(self, 'doctor_profile')

    # is_staff and is_superuser are still used for admin roles

    def __str__(self):
        return self.username

# --- PROFILE MODELS ---

class PatientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, # Use settings.AUTH_USER_MODEL
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='patient_profile'
    )
    # Add any patient-specific fields here later if needed
    # e.g., date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Patient Profile: {self.user.username}"

class DoctorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, # Use settings.AUTH_USER_MODEL
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='doctor_profile'
    )
    # Existing fields
    specialization = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='doctors/', null=True, blank=True)
    degree = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    consultation_charges = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    

    # Fields added for Manage Profile feature (awards removed)
    experience_years = models.PositiveIntegerField(null=True, blank=True, verbose_name="Years of Experience")
    qualifications = models.TextField(blank=True, null=True, help_text="List your qualifications, one per line.")
    clinic_name = models.CharField(max_length=200, blank=True, null=True)
    clinic_address = models.TextField(blank=True, null=True, verbose_name="Clinic Address")

    # Fields added for Rating System
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, default=None)
    rating_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Doctor Profile: {self.user.username}"

    # Optional: Method to update average rating (call this from your review submission view)
    def update_average_rating(self):
        reviews = self.reviews_received.all() # Using related_name from DoctorReview
        count = reviews.count()
        if count > 0:
            total = sum(review.rating for review in reviews)
            self.average_rating = round(total / count, 2) # Round the average
        else:
            self.average_rating = None # Or 0.00 if you prefer
        self.rating_count = count
        # Save only the updated fields for efficiency
        self.save(update_fields=['average_rating', 'rating_count'])

# Add near other models in users/models.py
class AvailabilitySlot(models.Model):
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='availability_slots'
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    # You could add constraints, e.g., end_time must be after start_time

    class Meta:
        ordering = ['start_time']
        # Ensure a doctor doesn't have overlapping slots (optional, requires validation)
        # unique_together = ('doctor', 'start_time') # Basic check

    def __str__(self):
        # Format times for display, requires timezone import if not already there
        # from django.utils import timezone
        # local_start = timezone.localtime(self.start_time)
        # local_end = timezone.localtime(self.end_time)
        # return f"Dr. {self.doctor.user.username} available: {local_start.strftime('%Y-%m-%d %H:%M')} - {local_end.strftime('%H:%M')}"
        # Simpler version without timezone handling shown here:
         return f"Dr. {self.doctor.user.username} available: {self.start_time.strftime('%Y-%m-%d %H:%M')} - {self.end_time.strftime('%H:%M')}"
    
# --- NEW MODEL FOR REVIEWS/RATINGS ---
class DoctorReview(models.Model):
    doctor = models.ForeignKey(
        DoctorProfile, # Link to the DoctorProfile
        on_delete=models.CASCADE,
        related_name='reviews_received' # Allows easy access from DoctorProfile instance
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Link to the user who wrote the review
        on_delete=models.CASCADE, # Or SET_NULL if you want to keep anonymous reviews
        related_name='reviews_given'
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)] # Example: 1 to 5 stars
    )
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevent a patient from reviewing the same doctor multiple times
        unique_together = ('doctor', 'patient')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for {self.doctor.user.username} by {self.patient.username} ({self.rating} stars)"

# --- Optional: Signal to create default profiles ---
# (Keep your signal code here if you were using it)
# Example:
# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         if instance.is_staff or instance.is_superuser: # Or based on some other field set during creation
#             pass # Admins might not need a patient/doctor profile automatically
#         # elif instance.is_doctor: # If you had a way to set this during user creation
#         #     DoctorProfile.objects.create(user=instance)
#         else: # Default to creating a patient profile
#             PatientProfile.objects.create(user=instance)

# --- NEW FORM FOR AVAILABILITY SLOTS ---
