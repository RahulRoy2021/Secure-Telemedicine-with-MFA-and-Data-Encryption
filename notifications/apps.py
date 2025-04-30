# notifications/apps.py
from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        # Import signals module here to ensure it's loaded
        # when the app registry is ready.
        try:
            import notifications.signals
            print("--- Notifications signals imported successfully. ---")
        except ImportError:
             print("--- Warning: Could not import notifications.signals. ---")