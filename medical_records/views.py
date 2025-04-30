# medical_records/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import MedicalRecord
from .forms import MedicalRecordForm
# --- Add this import ---
from django.utils import timezone
# -----------------------

@login_required
def medical_record_form(request):
    """ Allow the user to create or edit their medical record """

    # --- MODIFY THIS LINE ---
    # Provide default values for required fields when creating
    defaults_for_create = {
        'record_date': timezone.now().date(), # Use today's date as default
        # Add defaults for any other *required* fields in MedicalRecord if needed
        # 'diagnosis': 'Initial Record', # Example, if diagnosis was required
    }
    medical_record, created = MedicalRecord.objects.get_or_create(
        patient=request.user,
        defaults=defaults_for_create # Pass the defaults here
    )
    # --- END MODIFICATION ---

    if request.method == "POST":
        # Pass instance=medical_record to update the fetched/created record
        form = MedicalRecordForm(request.POST, request.FILES, instance=medical_record)
        if form.is_valid():
            # The form's save method will handle the encryption via the model's save()
            form.save()
            # Optionally add a success message
            # messages.success(request, "Medical record saved successfully.")
            return redirect('home') # Redirect to home page after saving
    else:
        # Display the form for an existing or newly created (empty) record
        # The form's __init__ likely handles decryption for display now
        form = MedicalRecordForm(instance=medical_record)
        # This explicit decryption setting might be redundant if form init handles it
        # decrypted_data = medical_record.get_decrypted_data()
        # form.initial["diagnosis"] = decrypted_data["diagnosis"]
        # form.initial["prescription"] = decrypted_data["prescription"]
        # form.initial["test_results"] = decrypted_data["test_results"]


    return render(request, "medical_records/medical_record_form.html", {"form": form})