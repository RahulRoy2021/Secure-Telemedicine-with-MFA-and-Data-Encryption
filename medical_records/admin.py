from django.contrib import admin
from .models import MedicalRecord

class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'record_date', 'description', 'created_at','updated_at')  # Ensure these fields exist
    list_filter = ('record_date', 'doctor')  # Filtering by date and doctor
    search_fields = ('patient__username', 'doctor__username', 'diagnosis', 'description')

admin.site.register(MedicalRecord, MedicalRecordAdmin)

