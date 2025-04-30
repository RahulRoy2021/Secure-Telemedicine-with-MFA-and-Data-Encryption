from django.urls import path
from .views import medical_record_form

urlpatterns = [
    path("record/", medical_record_form, name="medical_record_form"),
]
