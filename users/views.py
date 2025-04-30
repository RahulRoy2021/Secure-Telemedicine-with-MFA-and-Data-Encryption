# telemedicine_platform/users/views.py
import os # To construct paths
from django.conf import settings # To get BASE_DIR
from django.http import JsonResponse # To return prediction
import json # To parse request body
import traceback
from django.views.decorators.csrf import csrf_protect # Or ensure CSRF handled by JS fetch
from django.http import JsonResponse 
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone # Already imported
from django.db.models import Q
#import google.generativeai as genai
# --- Import forms and models needed ---
from .forms import (
    CustomUserCreationForm,
    DoctorProfileForm,
    DoctorReviewForm,
    AvailabilitySlotForm, # <-- Import the new form
    DoctorSearchForm
)
from .models import (
    PatientProfile,
    DoctorProfile,
    DoctorReview,
    AvailabilitySlot

)
# ---------------------------------------

# Assuming medical_records app exists and model is needed elsewhere
try:
    from medical_records.models import MedicalRecord
except ImportError:
    MedicalRecord = None

# Assuming appointments app exists for dashboard example
try:
    from appointments.models import Appointment
except ImportError:
    Appointment = None

User = get_user_model()

# --- Existing Views (home, register, user_login, user_logout, manage_doctor_profile, add_doctor_review) ---
# Keep all the existing view functions as they were...

@login_required
def home(request):
    context = {}

    # --- Patient Logic (keep as is) ---
    if request.user.is_patient:
        if MedicalRecord:
            try: context['medical_record'] = MedicalRecord.objects.filter(patient=request.user).first()
            except Exception as e: print(f"Error fetching medical record: {e}"); context['medical_record'] = None
        doctors = User.objects.filter(doctor_profile__isnull=False, is_active=True).select_related('doctor_profile')
        context['doctors'] = doctors

    # --- Doctor Logic (Modified Query) ---
    elif request.user.is_doctor:
        try:
            # doctor_profile = request.user.doctor_profile # May not be needed if only filtering by request.user

            if Appointment:
                now = timezone.now()
                today = now.date()

                # --- Fetch only the single *next* PENDING or CONFIRMED appointment ---
                next_appointment_for_action = Appointment.objects.filter(
                    doctor=request.user,
                    status__in=['PENDING', 'CONFIRMED'], # Only show actionable ones here
                    requested_date__gte=today # From today onwards
                ).select_related('patient').order_by('requested_date', 'requested_time').first() # Get the first one
                # --- End new query ---

                # Add this single appointment (or None) to context
                context['next_appointment_for_action'] = next_appointment_for_action

            else:
                print("Appointment model not found.")
                context['next_appointment_for_action'] = None

        except Exception as e:
             print(f"Error fetching doctor dashboard data for {request.user.username}: {e}")
             context['next_appointment_for_action'] = None


    # --- Admin Logic (keep as is) ---
    elif request.user.is_superuser:
        pass

    return render(request, "users/home.html", context)

def register(request):
    # ... keep existing ...
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data.get('role')
            if role == 'DOCTOR':
                DoctorProfile.objects.create(user=user)
            else:
                PatientProfile.objects.create(user=user)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect("home")
    else:
        form = CustomUserCreationForm()
    return render(request, "users/register.html", {"form": form}) # Updated cite: 1 if needed

def user_login(request):
    # ... keep existing ...
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            error_message = "Invalid username or password."
            return render(request, "users/login.html", {"error": error_message}) # Updated cite: 2 if needed
    return render(request, "users/login.html") # Updated cite: 2 if needed

@login_required
def user_logout(request):
    # ... keep existing ...
    logout(request)
    return redirect('login')

@login_required
def manage_doctor_profile(request):
    # ... keep existing ...
    try:
        profile = request.user.doctor_profile
    except DoctorProfile.DoesNotExist:
        messages.error(request, "Doctor profile not found.")
        return redirect('home')

    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DoctorProfileForm(instance=profile)

    context = {'form': form}
    return render(request, 'users/manage_doctor_profile.html', context)

@login_required
def add_doctor_review(request, doctor_user_id):
    # ... keep existing ...
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, "Only patients can leave reviews.")
        return redirect('home')
    doctor_profile = get_object_or_404(DoctorProfile, pk=doctor_user_id)
    existing_review = DoctorReview.objects.filter(doctor=doctor_profile, patient=request.user).first()
    if existing_review:
        messages.info(request, f"You have already reviewed Dr. {doctor_profile.user.username}.")
        return redirect('home')
    if request.method == 'POST':
        form = DoctorReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.doctor = doctor_profile
            review.patient = request.user
            review.rating = int(form.cleaned_data['rating'])
            review.save()
            doctor_profile.update_average_rating()
            messages.success(request, f"Your review for Dr. {doctor_profile.user.username} has been submitted.")
            return redirect('home')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DoctorReviewForm()
    context = {'form': form,'doctor_profile': doctor_profile}
    return render(request, 'users/add_review.html', context)


# --- NEW VIEW FOR MANAGING AVAILABILITY ---
@login_required
def manage_availability(request):
    # 1. Ensure user is a doctor and get their profile
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, "You must be a doctor to manage availability.")
        return redirect('home')
    doctor_profile = request.user.doctor_profile # Already fetched via related manager

    # 2. Handle Deletion Request (if applicable)
    if request.method == 'POST' and 'delete_slot' in request.POST:
        slot_id_to_delete = request.POST.get('slot_id')
        try:
            # Ensure the slot belongs to the logged-in doctor before deleting
            slot_to_delete = get_object_or_404(AvailabilitySlot, pk=slot_id_to_delete, doctor=doctor_profile)
            # Optional: Check if the slot is booked before allowing deletion
            if slot_to_delete.is_booked:
                 messages.warning(request, "Cannot delete a slot that is already booked for an appointment.")
            else:
                slot_to_delete.delete()
                messages.success(request, "Availability slot deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting slot: {e}")
        # Redirect back to the same page to show updated list
        return redirect('manage_availability') # Use the name from urls.py

    # 3. Handle Form Submission for Adding New Slot
    if request.method == 'POST': # This assumes any POST not marked for deletion is for adding
        form = AvailabilitySlotForm(request.POST)
        if form.is_valid():
            # Basic Overlap Check (Example - refine as needed)
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']
            overlapping_slots = AvailabilitySlot.objects.filter(
                doctor=doctor_profile,
                start_time__lt=end_time, # Starts before new one ends
                end_time__gt=start_time   # Ends after new one starts
            )
            if overlapping_slots.exists():
                messages.error(request, "The new slot overlaps with an existing availability slot.")
                # Re-render page with form errors (overlap isn't a standard form error here)
                # We need existing slots and the form for the context below
            else:
                slot = form.save(commit=False)
                slot.doctor = doctor_profile
                slot.save()
                messages.success(request, "New availability slot added successfully.")
                # Redirect back to the same page to show updated list
                return redirect('manage_availability') # Use the name from urls.py
        else:
             # Form is invalid, fall through to render page with form errors
             messages.error(request, "Please correct the errors in the form below.")

    # 4. Handle GET Request (or POST with form errors)
    # Fetch existing slots (e.g., future slots)
    existing_slots = AvailabilitySlot.objects.filter(
        doctor=doctor_profile,
        start_time__gte=timezone.now() # Only show future slots
    ).order_by('start_time')

    # Prepare the form for adding a new slot
    # If the request was POST and form was invalid, 'form' will be the invalid form instance
    # Otherwise (GET request), create a new empty form
    if request.method != 'POST' or 'delete_slot' in request.POST:
         form = AvailabilitySlotForm()
         # else: the invalid form from the POST handling above is already in the 'form' variable

    context = {
        'form': form, # Form for adding new slots
        'existing_slots': existing_slots # List of current/future slots
    }
    # You need to create this template
    return render(request, 'users/manage_availability.html', context)
# --- END NEW VIEW ---
# --- ADD NEW SEARCH VIEW ---
@login_required # Or remove if public search is allowed
def search_doctors(request):
    """
    Displays a search form and lists doctors matching the GET query parameters.
    """
    # Ensure only patients can search? Or allow anyone? Assume patient for now.
    # if not hasattr(request.user, 'patient_profile'):
    #    messages.error(request, "Only patients can search for doctors.")
    #    return redirect('home')

    form = DoctorSearchForm(request.GET or None) # Populate with GET data if submitted
    doctors = User.objects.filter(
        doctor_profile__isnull=False, is_active=True
    ).select_related('doctor_profile').order_by('username') # Base query

    # Filter based on form submission (GET parameters)
    if form.is_valid():
        name_query = form.cleaned_data.get('name')
        spec_query = form.cleaned_data.get('specialization')

        if name_query:
            # Filter by username OR first_name OR last_name containing the query
            doctors = doctors.filter(
                Q(username__icontains=name_query) |
                Q(first_name__icontains=name_query) |
                Q(last_name__icontains=name_query)
            )
        if spec_query:
            doctors = doctors.filter(
                doctor_profile__specialization__icontains=spec_query
            )

    context = {
        'form': form,
        'doctors': doctors
    }
    # Create this new template
    return render(request, 'users/search_doctors.html', context)

# --- END NEW SEARCH VIEW ---
# --- NEW PREDICTION VIEW USING GEMINI API ---
# @csrf_protect # Consider CSRF if not handled by API gateway/other means
# def predict_disease(request):
#     """
#     Handles AJAX request with symptoms, queries Gemini API for potential causes,
#     and returns the list. INCLUDES STRONG DISCLAIMERS.
#     """
#     if request.method != 'POST':
#         return JsonResponse({'error': 'Invalid request method'}, status=405)

#     # --- Configure Gemini ---
#     api_key = getattr(settings, 'GEMINI_API_KEY', None)
#     if not api_key:
#         print("--- ERROR: GEMINI_API_KEY not found in settings. ---")
#         return JsonResponse({'error': 'API key not configured on server.'}, status=500)

#     try:
#         genai.configure(api_key=api_key)
#         # Choose a suitable model (e.g., gemini-1.5-flash is often fast and capable)
#         model = genai.GenerativeModel('gemini-1.5-flash')
#     except Exception as e:
#          print(f"--- ERROR configuring Gemini: {e} ---")
#          return JsonResponse({'error': 'Failed to configure prediction service.'}, status=500)
#     # --- End Configuration ---

#     try:
#         data = json.loads(request.body)
#         symptoms_input = data.get('symptoms', '').strip()

#         if not symptoms_input:
#             return JsonResponse({'error': 'No symptoms provided.'}, status=400)

#         print(f"--- Received symptoms for Gemini: {symptoms_input} ---")

#         # --- Construct Prompt ---
#         # Be very specific about the desired output and limitations
#         prompt = (
#             f"Based *only* on general knowledge patterns from your training data, list potential medical conditions "
#             f"commonly associated with the following symptoms: '{symptoms_input}'. "
#             f"Do NOT provide a diagnosis, medical advice, or probabilities. "
#             f"List only potential condition names, separated by commas. "
#             f"If unsure or symptoms are too vague, state 'Could not determine specific conditions'."
#         )
#         # ------------------------

#         # --- Call Gemini API ---
#         print("--- Calling Gemini API... ---")
#         # Add safety settings if desired
#         # safety_settings = [...]
#         response = model.generate_content(
#              prompt,
#              # safety_settings=safety_settings
#         )
#         print("--- Gemini API Response Received ---")
#         # ---------------------

#         # --- Parse Response & Add Disclaimer ---
#         potential_causes_text = response.text.strip()
#         print(f"--- Gemini Response Text: {potential_causes_text} ---")

#         # Basic check if the model refused or gave a generic answer
#         if "could not determine" in potential_causes_text.lower() or not potential_causes_text:
#              result_text = "Could not determine specific potential conditions based on the provided symptoms."
#         else:
#              # Present the raw list, clearly marked as possibilities
#              result_text = f"You may have potential associated conditions (based on AI text patterns, NOT a diagnosis):\n- {potential_causes_text.replace(',', '\n- ')}"

#         # Add the MANDATORY disclaimer
#         disclaimer = "\n\n**Disclaimer:** This is AI-generated information based on symptom patterns and is NOT a medical diagnosis or advice. It may be inaccurate or incomplete. Please consult a qualified healthcare professional for any health concerns."

#         return JsonResponse({'potential_causes': result_text + disclaimer})
#         # --- End Response Parsing ---

#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON data in request body'}, status=400)
#     except Exception as e:
#         print(f"--- ERROR during Gemini prediction: {e} ---")
#         traceback.print_exc()
#         return JsonResponse({'error': f'An error occurred while processing the request: {str(e)}'}, status=500)
# --- END NEW PREDICTION VIEW ---