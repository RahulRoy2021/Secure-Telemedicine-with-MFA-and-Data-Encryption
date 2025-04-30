from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
from django.utils import timezone

ENCRYPTION_KEY = b'wwWesaVyNBjtlDgpnGKvWaiHLeTspowC2pfLUFW8ZCA='
cipher = Fernet(ENCRYPTION_KEY)

class MedicalRecord(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="medical_records")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="doctor_records")

    diagnosis = models.TextField()
    prescription = models.TextField(blank=True, null=True)
    test_results = models.TextField(blank=True, null=True)
    attached_file = models.FileField(upload_to='medical_records/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    record_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def encrypt_text(self, plaintext):
        """Encrypts medical data before saving."""
        return cipher.encrypt(plaintext.encode()).decode() if plaintext else ""

    def decrypt_text(self, encrypted_text):
        """Decrypts medical data when retrieving."""
        return cipher.decrypt(encrypted_text.encode()).decode() if encrypted_text else ""

    def save(self, *args, **kwargs):
        """Ensure encryption before saving."""
        if not self.diagnosis.startswith("gAAAA"):
            self.diagnosis = self.encrypt_text(self.diagnosis)
        if self.prescription and not self.prescription.startswith("gAAAA"):
            self.prescription = self.encrypt_text(self.prescription)
        if self.test_results and not self.test_results.startswith("gAAAA"):
            self.test_results = self.encrypt_text(self.test_results)
        super().save(*args, **kwargs)

    def get_decrypted_data(self):
        """Return decrypted medical data."""
        return {
            "diagnosis": self.decrypt_text(self.diagnosis),
            "prescription": self.decrypt_text(self.prescription) if self.prescription else None,
            "test_results": self.decrypt_text(self.test_results) if self.test_results else None
        }

    def doctor_name(self):  
        return self.doctor.get_full_name() if self.doctor else "N/A"

    doctor_name.admin_order_field = "doctor"

    def __str__(self):
        return f"Medical Record for {self.patient.username} - {self.record_date.strftime('%Y-%m-%d')}"