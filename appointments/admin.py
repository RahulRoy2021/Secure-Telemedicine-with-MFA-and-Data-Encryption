# appointments/admin.py
from django.contrib import admin
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_type', 'requested_date', 'requested_time', 'status', 'created_at')
    list_filter = ('status', 'appointment_type', 'requested_date')
    search_fields = ('patient__username', 'doctor__username', 'symptoms')
    # Add other configurations as needed