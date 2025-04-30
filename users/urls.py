# users/urls.py
from django.urls import path
# --- Import ALL the views used in urlpatterns ---
from .views import (
    user_login,
    register,
    home,
    user_logout,
    manage_doctor_profile,
    add_doctor_review,
    manage_availability,  # <-- Import the new availability view
    search_doctors,
    
)

urlpatterns = [
    path("", home, name="home"),
    path("login/", user_login, name="login"),
    path("register/", register, name="register"),
    path('logout/', user_logout, name='logout'),
    path('profile/manage/', manage_doctor_profile, name='manage_doctor_profile'),
    path('reviews/add/<int:doctor_user_id>/', add_doctor_review, name='add_doctor_review'),

    # --- ADD URL PATTERN FOR MANAGING AVAILABILITY ---
    path('profile/availability/', manage_availability, name='manage_availability'),
    path('search/doctors/', search_doctors, name='search_doctors'),
]