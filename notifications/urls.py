# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications' # Keep the app name

urlpatterns = [
    # URL for the list page
    path('', views.notification_list, name='notification_list'),

    # URL for the unread count API
    path('api/unread-count/', views.get_unread_notification_count, name='unread_count_api'),

    path('api/mark-read/', views.mark_notifications_read, name='mark_read_api'),
]