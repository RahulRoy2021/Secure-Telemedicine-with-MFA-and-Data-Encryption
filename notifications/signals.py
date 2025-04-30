# notifications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync # To call async channel layer from sync signal
from channels.layers import get_channel_layer # To get the channel layer
from .models import Notification
import json

@receiver(post_save, sender=Notification)
def send_notification_on_save(sender, instance, created, **kwargs):
    """
    Sends a WebSocket message when a new Notification object is created.
    """
    # Only send if the notification was just created
    if created:
        print(f"--- Signal: New notification created (ID: {instance.id}) for {instance.recipient.username} ---")
        channel_layer = get_channel_layer()
        # Define a group name specific to the recipient user
        user_group_name = f'user_notifications_{instance.recipient.username}'

        # Prepare the payload to send via WebSocket
        payload = {
            'type': 'send_notification', # This matches the handler method name in the consumer
            'notification': {
                'id': instance.id,
                'message': instance.message,
                'timestamp': instance.timestamp.isoformat(),
                'is_read': instance.is_read,
                'link': instance.link or '#' # Send '#' if link is None/empty
            }
        }

        # Use async_to_sync to call the async group_send from the sync signal handler
        try:
            async_to_sync(channel_layer.group_send)(
                user_group_name,
                payload
            )
            print(f"--- Signal: Sent notification payload to group {user_group_name} ---")
        except Exception as e:
             print(f"--- Signal ERROR: Failed to send notification to group {user_group_name}: {e} ---")