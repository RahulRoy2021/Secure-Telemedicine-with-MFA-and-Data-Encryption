# notifications/admin.py
from django.contrib import admin
from .models import Notification # Import your Notification model

# Simple registration (makes the model visible in the admin)
admin.site.register(Notification)

# Optional: If you want to customize how Notifications appear in the admin later
# you can create a ModelAdmin class like this:
# class NotificationAdmin(admin.ModelAdmin):
#     list_display = ('recipient', 'message_preview', 'timestamp', 'is_read', 'link')
#     list_filter = ('is_read', 'timestamp')
#     search_fields = ('recipient__username', 'message')
#     list_editable = ('is_read',) # Allow editing read status directly in the list
#     readonly_fields = ('recipient', 'message', 'timestamp', 'link') # Typically don't edit these here
#
#     def message_preview(self, obj):
#          # Show truncated message in list view
#          return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
#     message_preview.short_description = 'Message' # Column header
#
# admin.site.register(Notification, NotificationAdmin) # Register with custom options