# delete_test.py

from django.contrib.auth import get_user_model
from chat.models import ChatMessage
from appointments.models import Appointment
from medical_records.models import MedicalRecord
from users.models import PatientProfile, DoctorProfile # Import profiles too
from django.db import transaction
import traceback

User = get_user_model()
user_id_to_delete = 8 # Make sure this ID exists and is the one causing problems

print(f"--- Attempting deletion test for User ID: {user_id_to_delete} ---")

try:
    user_to_delete = User.objects.get(pk=user_id_to_delete)
    print(f"Found user: {user_to_delete.username}")
except User.DoesNotExist:
    print(f"User with ID {user_id_to_delete} not found.")
    # exit() # Exit doesn't work well when run via pipe, just stop processing

else: # Only proceed if user was found
    try:
        with transaction.atomic():
            print(f"\n--- Starting deletion attempt within transaction for user {user_id_to_delete} ---")

            # Try deleting related objects first
            print("Attempting to delete related MedicalRecord(s)...")
            deleted_count, _ = MedicalRecord.objects.filter(patient=user_to_delete).delete()
            print(f"Deleted {deleted_count} MedicalRecord(s) as patient.")
            # Handle doctor relation (SET_NULL - no deletion needed, but check just in case)
            # updated_count = MedicalRecord.objects.filter(doctor=user_to_delete).update(doctor=None)
            # print(f"Updated {updated_count} MedicalRecord(s) setting doctor to NULL.")

            print("Attempting to delete related Appointment(s)...")
            deleted_count, _ = Appointment.objects.filter(patient=user_to_delete).delete()
            print(f"Deleted {deleted_count} Appointment(s) as patient.")
            deleted_count, _ = Appointment.objects.filter(doctor=user_to_delete).delete()
            print(f"Deleted {deleted_count} Appointment(s) as doctor.")

            print("Attempting to delete related ChatMessage(s)...")
            deleted_count, _ = ChatMessage.objects.filter(sender=user_to_delete).delete()
            print(f"Deleted {deleted_count} ChatMessage(s) as sender.")
            deleted_count, _ = ChatMessage.objects.filter(receiver=user_to_delete).delete()
            print(f"Deleted {deleted_count} ChatMessage(s) as receiver.")

            print("Attempting to delete PatientProfile...")
            deleted_count, _ = PatientProfile.objects.filter(user=user_to_delete).delete()
            print(f"Deleted {deleted_count} PatientProfile(s).")

            print("Attempting to delete DoctorProfile...")
            deleted_count, _ = DoctorProfile.objects.filter(user=user_to_delete).delete()
            print(f"Deleted {deleted_count} DoctorProfile(s).")

            # --- Add delete attempts for ANY OTHER related models here ---
            # print("Attempting to delete OtherModel...")
            # OtherModel.objects.filter(user=user_to_delete).delete()
            # print("OtherModel deleted.")
            # ---

            print("\nAttempting to delete CustomUser itself...")
            user_to_delete.delete()
            print(f"--- Successfully deleted CustomUser {user_id_to_delete} and related objects! ---")
            print("--- TRANSACTION SUCCEEDED (but might be rolled back unless committed explicitly outside script) ---")
            # Note: By default, running via shell in transaction might rollback unless you manage commit

    except Exception as e:
        print(f"\n--- ERROR occurred during deletion attempt for user {user_id_to_delete} ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {e}")
        print("--- Traceback ---")
        traceback.print_exc()
        print("--- End Traceback ---")
        print("\nThe error likely occurred trying to delete the object type mentioned just BEFORE this error message.")