# notifications/models.py
from django.db import models
from django.conf import settings # To link to your CustomUser model
from django.utils import timezone

class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, # Delete notification if user is deleted
        related_name='notifications' # How to get notifications for a user (user.notifications.all())
    )
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False, db_index=True) # Index for faster filtering of unread
    link = models.URLField(max_length=255, null=True, blank=True) # Optional link to relevant page

    def __str__(self):
        read_status = "Read" if self.is_read else "Unread"
        return f"Notification for {self.recipient.username} ({read_status}): {self.message[:50]}..."

    class Meta:
        ordering = ['-timestamp'] # Show newest notifications first
        indexes = [
            models.Index(fields=['recipient', 'is_read']), # Index for fetching unread for a user
        ]