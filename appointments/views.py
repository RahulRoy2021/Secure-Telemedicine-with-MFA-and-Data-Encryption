# appointments/views.py

# --- Existing Imports ---
from django.shortcuts import render, redirect, get_object_or_404 # Added redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone # Added timezone
from .models import Appointment
from django.views.decorators.http import require_POST # To ensure only POST requests work
from django.contrib import messages
from django.http import HttpResponseForbidden
# --- Add Q object for OR filtering ---
from django.db.models import Q
from users.models import DoctorProfile, AvailabilitySlot # Import related models
from django.contrib.auth import get_user_model # To get the User model
from .forms import AppointmentBookingForm
from django.core.mail import send_mail # If keeping email
from django.conf import settings
from notifications.models import Notification # Import the new model
from cryptography.fernet import InvalidToken # Import if decrypt_file_key uses it in this file
from django.urls import reverse # May need for notification links

# ------------------------------------
User = get_user_model()
# --- Keep existing view_upcoming_appointments function ---
@login_required
def view_upcoming_appointments(request):
    if not hasattr(request.user, 'patient_profile'):
        return HttpResponseForbidden("Access denied.")
    now = timezone.now()
    upcoming_appointments = Appointment.objects.filter(
        patient=request.user,
        status__in=['PENDING', 'CONFIRMED'],
        requested_date__gte=now.date()
    ).select_related('doctor', 'doctor__doctor_profile').order_by('requested_date', 'requested_time')
    context = {'upcoming_appointments': upcoming_appointments}
    return render(request, 'appointments/upcoming_list.html', context)

# --- Keep existing cancel_appointment_doctor function ---
# --- UPDATED confirm_appointment_doctor ---
@require_POST
@login_required
def confirm_appointment_doctor(request, appointment_id):
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, "Only doctors can confirm appointments.")
        return redirect('home')

    appointment = get_object_or_404(Appointment, pk=appointment_id, doctor=request.user)

    if appointment.status != 'PENDING':
        messages.warning(request, f"Only PENDING appointments can be confirmed (Status: {appointment.get_status_display()}).")
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    patient_email = appointment.patient.email # Keep for email sending if needed
    patient_name = appointment.patient.username
    appointment_date_str = appointment.requested_date.strftime('%A, %B %d, %Y')
    appointment_time_str = appointment.requested_time.strftime('%I:%M %p')
    doctor_name = request.user.get_full_name() or request.user.username

    # Update Status
    appointment.status = 'CONFIRMED'
    appointment.save()
    messages.success(request, f"Appointment with {patient_name} on {appointment.requested_date} has been confirmed.")

    # --- CREATE CONFIRMATION NOTIFICATION for Patient ---
    try:
        notification_message = f"Your appointment with Dr. {doctor_name} on {appointment_date_str} at {appointment_time_str} has been confirmed."
        Notification.objects.create(
            recipient=appointment.patient,
            message=notification_message,
            # link=reverse('appointments:view_upcoming_appointments') # Example link
        )
        print(f"--- Confirmation Notification created for user {appointment.patient.username} ---")
    except Exception as e:
        print(f"--- ERROR creating confirmation notification: {e} ---")
    # --- END NOTIFICATION CREATION ---

    # --- (Optional) Keep Email Sending ---
    # ... email sending code ...
    # --- End Email Sending ---

    return redirect(request.META.get('HTTP_REFERER', 'home'))

# --- UPDATED cancel_appointment_doctor ---
@require_POST
@login_required
def cancel_appointment_doctor(request, appointment_id):
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, "Only doctors can cancel appointments this way.")
        return redirect('home')

    appointment = get_object_or_404(Appointment, pk=appointment_id, doctor=request.user)

    cancellable_statuses = ['PENDING', 'CONFIRMED']
    if appointment.status not in cancellable_statuses:
        messages.warning(request, f"This appointment cannot be cancelled (Status: {appointment.get_status_display()}).")
        # Redirect back to where they came from or home
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    # Get details needed for notification before saving
    patient_name = appointment.patient.username
    appointment_date_str = appointment.requested_date.strftime('%A, %B %d, %Y')
    appointment_time_str = appointment.requested_time.strftime('%I:%M %p')
    doctor_name = request.user.get_full_name() or request.user.username
    linked_slot = appointment.availability_slot

    # Update appointment status
    appointment.status = 'CANCELLED_DOCTOR'
    appointment.save()
    messages.success(request, f"Appointment with {patient_name} on {appointment.requested_date} has been cancelled.") # Message for doctor

    # Mark the slot as available again, IF it exists
    if linked_slot:
        linked_slot.is_booked = False
        linked_slot.save()
        print(f"--- Slot {linked_slot.id} marked as available ---")

    # --- CREATE CANCELLATION NOTIFICATION for Patient ---
    try:
        notification_message = f"Your appointment with Dr. {doctor_name} on {appointment_date_str} at {appointment_time_str} has been cancelled by the doctor."
        Notification.objects.create(
            recipient=appointment.patient,
            message=notification_message,
            # link=reverse('appointments:view_upcoming_appointments') # Example link
        )
        print(f"--- Cancellation Notification created for user {appointment.patient.username} ---")
    except Exception as e:
        print(f"--- ERROR creating cancellation notification: {e} ---")
    # --- END NOTIFICATION CREATION ---

    # --- (Optional) Keep Email Sending ---
    # ... email sending logic for cancellation ...
    # --- End Email Sending ---

    return redirect('home') # Redirect doctor
# --- NEW VIEW FOR DOCTOR'S APPOINTMENT LIST ---
@login_required
def doctor_all_appointments(request):
    """
    Displays a list of upcoming and cancelled appointments for the logged-in doctor.
    """
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, "Access denied.")
        return redirect('home')

    # Fetch appointments with relevant statuses for this doctor
    appointments_list = Appointment.objects.filter(
        doctor=request.user,
        status__in=[
            'PENDING',
            'CONFIRMED',
            'CANCELLED_DOCTOR',
            'CANCELLED_PATIENT'
            # Add 'COMPLETED', 'NO_SHOW' here if you want them included as well
        ]
    ).select_related('patient').order_by('-requested_date', '-requested_time') # Order by most recent date first

    context = {
        'appointments_list': appointments_list
    }
    # Create this new template file
    return render(request, 'appointments/doctor_appointment_list.html', context)


@login_required
def appointment_history(request):
    """
    Displays a list of past (Completed, Cancelled, No Show) appointments
    for the logged-in patient.
    """
    # 1. Check if user is a patient
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, "Access denied. Only patients can view appointment history.")
        # Or redirect to an appropriate page if non-patients might access this URL
        return redirect('home')

    # 2. Fetch past/inactive appointments for this patient
    past_appointments = Appointment.objects.filter(
        patient=request.user,
        status__in=[
            'COMPLETED',
            'CANCELLED_DOCTOR',
            'CANCELLED_PATIENT',
            'NO_SHOW'
        ]
    ).select_related('doctor').order_by('-requested_date', '-requested_time') # Show most recent first

    # 3. Prepare context
    context = {
        'past_appointments': past_appointments
    }

    # 4. Render the new template
    # Create this new template file
    return render(request, 'appointments/appointment_history.html', context)
@login_required
def view_doctor_availability(request, doctor_user_id):
    """
    Displays available (future, not booked) time slots for a specific doctor.
    """
    # Ensure the viewer is a patient
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, "Only patients can book appointments.")
        return redirect('home')

    # Get the requested doctor (ensure they are actually a doctor)
    doctor_user = get_object_or_404(User, pk=doctor_user_id, doctor_profile__isnull=False)
    doctor_profile = doctor_user.doctor_profile # Get the related profile

    # Get available slots for this doctor
    now = timezone.now()
    available_slots = AvailabilitySlot.objects.filter(
        doctor=doctor_profile,
        is_booked=False,      # Only show slots that are not already booked
        start_time__gte=now   # Only show slots starting now or in the future
    ).order_by('start_time')
    booking_form = AppointmentBookingForm()
    context = {
        'doctor': doctor_user, # Pass the doctor user object
        'doctor_profile': doctor_profile, # Pass the profile object
        'available_slots': available_slots,
        'booking_form': booking_form
    }
    # Create this new template
    return render(request, 'appointments/select_slot.html', context)

@require_POST
@login_required
def create_appointment(request):
    # ... (keep checks for patient, getting doctor_id, slot_id, fetching doctor, fetching slot) ...
    if not hasattr(request.user, 'patient_profile'): # ... redirect ...
        pass # Placeholder
    try: doctor_id = int(request.POST.get('doctor_id')); slot_id = int(request.POST.get('slot_id'))
    except: # ... redirect ...
        pass # Placeholder
    doctor = get_object_or_404(User, pk=doctor_id, doctor_profile__isnull=False)
    slot = get_object_or_404(AvailabilitySlot, pk=slot_id, doctor=doctor.doctor_profile)

    # ... (keep checks if slot booked or in past) ...
    if slot.is_booked: # ... redirect ...
        pass # Placeholder
    if slot.start_time < timezone.now(): # ... redirect ...
        pass # Placeholder

    form = AppointmentBookingForm(request.POST)
    if form.is_valid():
        try:
            appointment = Appointment.objects.create(
                patient=request.user,
                doctor=doctor,
                requested_date=slot.start_time.date(),
                requested_time=slot.start_time.time(),
                status='PENDING',
                symptoms=form.cleaned_data.get('symptoms', ''),
                appointment_type=form.cleaned_data.get('appointment_type'), # Get from form
                # --- SAVE THE LINK TO THE SLOT ---
                availability_slot=slot
                # --------------------------------
            )

            # Mark the slot as booked
            slot.is_booked = True
            slot.save()

            messages.success(request, f"Appointment with Dr. {doctor.username} on {appointment.requested_date} requested successfully!")
            return redirect('appointments:view_upcoming_appointments')

        except Exception as e:
            messages.error(request, f"An error occurred while booking: {e}")
            return redirect('appointments:view_doctor_availability', doctor_user_id=doctor.id)
    else:
        # ... (keep handling for invalid form) ...
        messages.error(request, "Please check the details provided.")
        return redirect('appointments:view_doctor_availability', doctor_user_id=doctor.id)

# --- END UPDATED VIEW ---