# users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
# --- Import your models ---
from .models import CustomUser, DoctorProfile, PatientProfile,AvailabilitySlot
# --- Import the correct Add form ---
from .forms import CustomUserAdminAddForm

# ----------------------------------
# Remove imports no longer needed if debugging is off
# from django.db import IntegrityError
# from django.contrib import messages
# from django.utils.html import escape


class CustomUserAdmin(UserAdmin):
    # Use the ModelForm-based add form
    add_form = CustomUserAdminAddForm

    # Form layout for the 'change' page
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "email", "phone_number")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser",)}),
        ("Groups & Permissions", {"fields": ("groups", "user_permissions")}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Form layout for the 'add' page
    # Needs 'password2' for the admin template display
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            # --- CORRECTED FIELDS ---
            'fields': ('username', 'email', 'password'),
            # ----------------------
        }),
    )

    list_display = ("username", "email", "phone_number", "is_staff", "is_doctor", "is_patient")
    search_fields = ("username", "email", "phone_number")
    ordering = ("username",)
    readonly_fields = ('last_login', 'date_joined', 'is_doctor', 'is_patient')

    # Remove debugging methods now
    # def add_view(...): ...
    # def save_model(...): ...

admin.site.register(AvailabilitySlot)
# Register CustomUser model
admin.site.register(CustomUser, CustomUserAdmin)

# Keep profile registrations
@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username',)

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'consultation_charges')
    search_fields = ('user__username', 'specialization')
    list_filter = ('specialization',)