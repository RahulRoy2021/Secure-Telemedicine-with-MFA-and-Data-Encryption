# appointments/urls.py

from django.urls import path
from . import views # Import views from the appointments app

# --- MAKE SURE THIS LINE EXISTS ---
app_name = 'appointments'
# ------------------------------------

urlpatterns = [
    # URL for the patient view (if primarily used by patients)
    path('upcoming/', views.view_upcoming_appointments, name='view_upcoming_appointments'),

    # URL for the doctor's list of appointments (Upcoming & Cancelled)
    path('my-list/', views.doctor_all_appointments, name='doctor_appointment_list'),

    # URL FOR CANCELLING BY DOCTOR
    path('<int:appointment_id>/cancel-by-doctor/', views.cancel_appointment_doctor, name='cancel_appointment_doctor'),

    # Add other appointment-related URLs here later (e.g., detail view, booking)
    
    path('<int:appointment_id>/confirm-by-doctor/', views.confirm_appointment_doctor, name='confirm_appointment_doctor'),
    path('history/', views.appointment_history, name='appointment_history'),
    path('book/doctor/<int:doctor_user_id>/', views.view_doctor_availability, name='view_doctor_availability'),
    path('book/create/', views.create_appointment, name='create_appointment')
]