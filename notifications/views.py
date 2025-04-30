# notifications/views.py
from django.shortcuts import render, redirect, get_object_or_404 # Added get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Notification
from django.http import JsonResponse # For API view later

# --- NEW VIEW for Notification List Page ---
@login_required
def notification_list(request):
    # Optionally mark all as read when the user visits this page
    # Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)

    # Fetch all notifications for the user, newest first
    notifications = Notification.objects.filter(recipient=request.user).order_by('-timestamp')

    context = {
        'notifications': notifications
    }
    # Create this template next
    return render(request, 'notifications/notification_list.html', context)
# --- END NEW VIEW ---

# --- Optional: API view to get unread count (for red dot) ---
@login_required
def get_unread_notification_count(request):
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'unread_count': count})

# --- Optional: API view to mark notifications as read ---
# @login_required
# def mark_notifications_read(request):
#     if request.method == 'POST':
#         Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
#         return JsonResponse({'status': 'success'})
#     return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@require_POST # Ensure this action is done via POST
@login_required
def mark_notifications_read(request):
    """
    Marks all unread notifications for the logged-in user as read.
    """
    try:
        updated_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        print(f"--- Marked {updated_count} notifications as read for {request.user.username} ---")
        return JsonResponse({'status': 'success', 'marked_read': updated_count})
    except Exception as e:
        print(f"--- Error marking notifications read for {request.user.username}: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
