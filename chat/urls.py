# chat/urls.py
from django.urls import path
from . import views # Import views from the chat app

app_name = 'chat' # Define the application namespace

urlpatterns = [
    path('', views.chat_list_or_redirect_view, name='chat_home'),
    path('support/', views.start_admin_chat_redirect_view, name='start_admin_chat'),
    path('<str:receiver_username>/', views.chat_room_view, name='chat_room'),

    # --- CORRECTED NAME for download view ---
    path('download/<int:message_id>/', views.download_decrypted_file, name='download_decrypted_file'),
    # ---------------------------------------

    path('api/upload/', views.upload_chat_file, name='upload_chat_file_api'), # Renamed API slightly for clarity
    path('api/history/<str:sender_username>/<str:receiver_username>/', views.get_chat_history, name='get_chat_history_api'), # Renamed API slightly
]