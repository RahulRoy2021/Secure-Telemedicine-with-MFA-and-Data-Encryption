# chat/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.http import (
    JsonResponse, HttpResponseBadRequest, HttpResponseForbidden,
    HttpResponseServerError, Http404, HttpResponse,StreamingHttpResponse
)
from django.utils import timezone # Ensure timezone is imported if needed elsewhere
from django.contrib import messages # Optional: For showing messages like "Support unavailable"
import traceback # Import traceback for detailed error logging
import base64 # <-- Import for encoding/decoding nonce/key
import tempfile # <-- Import for temporary file during encryption
# Keep necessary imports for other views/logic
from .models import ChatMessage
from django.urls import reverse
from .encryption import (
    generate_aes_key,
    encrypt_file_key,
    decrypt_file_key,
    encrypt_file_stream,
    decrypt_file_stream,
    # Keep text functions if views need them, but likely handled elsewhere (consumers)
    # encrypt_message,
    # decrypt_message,
)
from .models import ChatMessage
from django.core.files.storage import default_storage
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import os

User = get_user_model()
CHUNK_SIZE = 64 * 1024 # Define chunk size for streaming

# --- Helper Function to find the designated Admin ---
def get_designated_admin():
    """Finds the first active superuser to act as the admin contact."""
    # Prioritize active superusers
    admin_user = User.objects.filter(is_active=True, is_superuser=True).order_by('id').first()
    return admin_user

# --- Views ---

@login_required
def chat_list_or_redirect_view(request):
    """
    If user is admin (superuser), show chat list.
    If user is not admin, redirect them to start chat with the designated admin.
    """
    if request.user.is_superuser:
        # Admin User: Show list of users they have chatted with
        user = request.user
        # Find users who have sent a message to the admin or received one from the admin
        chat_partners_ids = set(
            list(ChatMessage.objects.filter(sender=user, receiver__is_superuser=False).values_list('receiver_id', flat=True)) +
            list(ChatMessage.objects.filter(receiver=user, sender__is_superuser=False).values_list('sender_id', flat=True))
        )
        # Ensure we only list non-admin users
        chat_users = User.objects.filter(id__in=chat_partners_ids, is_superuser=False).exclude(id=user.id).order_by('username')
        return render(request, 'chat/chat_list.html', {'chat_users': chat_users})
    else:
        # Regular User: Redirect to the view that starts the admin chat
        # Assumes you named the URL pattern 'start_admin_chat' in urls.py
        return redirect('start_admin_chat')

@login_required
def start_admin_chat_redirect_view(request):
    """
    Finds the designated admin and redirects the regular user to the chat room with them.
    """
    if request.user.is_superuser:
        # If an admin somehow lands here, send them to their chat list
        return redirect('chat_home')

    admin_user = get_designated_admin()

    if admin_user:
        # Redirect to the chat room URL with the admin's username
        # Assumes you named the URL pattern 'chat_room' in urls.py
        return redirect('chat:chat_room', receiver_username=admin_user.username)
    else:
        # Handle case where no admin is found
        messages.error(request, "Support chat is currently unavailable. No admin account found.")
        # Redirect to homepage or another appropriate page
        # Replace 'home' with your actual homepage URL name if different
        try:
             return redirect('home')
        except Exception:
             # Fallback if 'home' URL doesn't exist
             return HttpResponse("Support chat is currently unavailable.", status=503)


@login_required
def chat_room_view(request, receiver_username):
    """
    Displays the chat room interface for conversation with receiver_username.
    Handles both admin viewing chat with user, and user viewing chat with admin.
    """
    receiver = get_object_or_404(User, username=receiver_username)

    # Prevent self-chat
    if request.user == receiver:
        messages.warning(request, "You cannot chat with yourself.")
        # Redirect admin to list, user will be redirected eventually by chat_home view
        return redirect('chat_home')

    # Authorization check:
    is_requester_admin = request.user.is_superuser
    is_receiver_admin = receiver.is_superuser

    # Allow if:
    # 1. Requester is admin AND receiver is not admin (Admin chatting with User)
    # 2. Requester is not admin AND receiver is admin (User chatting with Admin)
    # Disallow Admin-Admin and User-User chat through this view for now
    if is_requester_admin == is_receiver_admin:
         messages.error(request, "Invalid chat participant combination.")
         # Send admin home, send user likely back to start_admin_chat which redirects home
         return redirect('chat_home')


    # Pass receiver to template - JS will fetch history
    return render(request, 'chat/chat_room.html', {
        'receiver': receiver,
    })
# --- API / Utility Views ---
# Example: History view (ensure authorization allows admin/user correctly)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_history(request, sender_username, receiver_username):
    user1 = get_object_or_404(User, username=sender_username)
    user2 = get_object_or_404(User, username=receiver_username)

    # Allow if the request user is one of the participants in the chat
    if request.user != user1 and request.user != user2:
        return Response({"error": "Unauthorized to view this history"}, status=status.HTTP_403_FORBIDDEN)

    # Additional check: Ensure one participant is an admin and the other is not?
    is_user1_admin = user1.is_superuser
    is_user2_admin = user2.is_superuser
    if is_user1_admin == is_user2_admin:
        # Disallow history viewing for admin-admin or user-user chats via this API
        # Adjust if your policy allows these types of chats elsewhere
        return Response({"error": "Invalid participant types for chat history"}, status=status.HTTP_403_FORBIDDEN)


    try:
        messages_qs = ChatMessage.objects.filter(
            (Q(sender=user1) & Q(receiver=user2)) |
            (Q(sender=user2) & Q(receiver=user1))
        ).filter(is_deleted=False).order_by("timestamp").select_related('sender', 'receiver')

        data = []
        # print(f"\n--- HISTORY API VIEW: Fetching history for {sender_username} and {receiver_username}") # Optional log
        for msg in messages_qs:
            # Ensure we handle decryption safely - moved out from basic example
            # It's better handled via a model method or serializer that checks keys/permissions
            # For now, assume msg.get_decrypted_message() handles it or remove decryption here
            # if this view doesn't need plaintext. If plaintext needed, implement robust decryption.

            # Use the model method preferably, assuming it exists and handles deleted state
            decrypted_text = msg.get_decrypted_message() # Assumes this handles None/errors/deleted

            # Fallback/Explicit handling if model method isn't robust
            if msg.is_deleted:
                decrypted_text = "[Message deleted]"
            elif msg.encrypted_message:
                # !! WARNING: Ensure decrypt_message is safe and handles errors !!
                # Consider removing decryption from API view if not strictly necessary
                # decrypted_text = decrypt_message(msg.encrypted_message) or "" # Example
                # Using the presumed safer model method is better:
                decrypted_text = msg.get_decrypted_message() or "" # Ensure it returns "" if no text
            else:
                decrypted_text = "" # File message with no caption

            download_url = None
            if msg.attached_file and msg.original_filename: # Check if it's a file message
                try:
                    # Use reverse with the correct namespace and view name
                    download_url = reverse('chat:download_decrypted_file', args=[msg.id])
                except Exception as url_e:
                     print(f"Error reversing download URL for msg {msg.id}: {url_e}")

            data.append({
                'id': msg.id,
                "sender_username": msg.sender.username,
                "receiver_username": msg.receiver.username,
                "message": decrypted_text,
                "download_url": download_url,
                "original_filename": msg.original_filename,
                "timestamp": msg.timestamp.isoformat(),
                "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
                "is_deleted": msg.is_deleted
            })

        return Response(data)
    except Exception as e:
        print(f"--- HISTORY API VIEW: General Error: {e}")
        traceback.print_exc() # Log full traceback
        return Response({"error": f"An unexpected error occurred fetching history: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Keep upload/download views - they should be role-agnostic based on message access
@csrf_exempt # Keep ONLY if not using standard Django sessions/CSRF middleware properly
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_chat_file(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        temp_file_path = None # For cleanup

        # --- Encryption Logic ---
        try:
            file_key = generate_aes_key() # Unique key for this file
            encrypted_file_key_bytes = encrypt_file_key(file_key) # Encrypt the file key with master key

            # Create a temporary file to store encrypted content
            # Using 'wb+' allows writing then reading if needed, 'delete=False' keeps it until manually removed
            with tempfile.NamedTemporaryFile(mode='wb+', delete=False) as temp_encrypted_file:
                temp_file_path = temp_encrypted_file.name # Get path for later use/cleanup
                print(f"--- UPLOAD: Encrypting to temp file: {temp_file_path}")
                # Encrypt stream to temp file, get nonce
                nonce = encrypt_file_stream(uploaded_file, temp_encrypted_file, file_key)
                if nonce is None:
                    raise Exception("File encryption stream failed.")

            # Now save the *encrypted* temp file content to permanent storage
            safe_username = "".join(c for c in user.username if c.isalnum() or c in ('-', '_')).rstrip()
            # Use a unique name for the saved encrypted file (e.g., using UUID or timestamp)
            encrypted_file_name = f"{safe_username}_{timezone.now().strftime('%Y%m%d%H%M%S%f')}.bin"
            encrypted_file_path = os.path.join('chat_files_encrypted', encrypted_file_name) # Store in separate dir

            # Open the temp encrypted file to read ('rb') and save to final storage
            print(f"--- UPLOAD: Saving encrypted temp file {temp_file_path} to {encrypted_file_path}")
            with open(temp_file_path, 'rb') as f_to_save:
                 saved_path = default_storage.save(encrypted_file_path, f_to_save)
            print(f"--- UPLOAD: Saved encrypted file to: {saved_path}")

            # Prepare metadata for ChatMessage creation (by consumer/client)
            metadata = {
                'saved_path': saved_path, # Path to ENCRYPTED file in storage
                'original_filename': uploaded_file.name,
                'mime_type': uploaded_file.content_type,
                'nonce_b64': base64.urlsafe_b64encode(nonce).decode(), # Store nonce (base64 encoded)
                'encrypted_key_b64': base64.urlsafe_b64encode(encrypted_file_key_bytes).decode() # Store encrypted key (base64 encoded)
            }
            # Return metadata needed to create the ChatMessage object
            return JsonResponse(metadata, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"--- UPLOAD VIEW: Error encrypting/saving file: {e}")
            traceback.print_exc()
            return JsonResponse({'error': f'Failed to process file: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
             # Clean up the temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    print(f"--- UPLOAD: Cleaning up temp file: {temp_file_path}")
                    os.remove(temp_file_path)
                except Exception as e_clean:
                     print(f"--- UPLOAD: Error cleaning up temp file {temp_file_path}: {e_clean}")

    return JsonResponse({'error': 'Invalid request method.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
@login_required
def download_decrypted_file(request, message_id):
    """
    Decrypts and streams the file attached to a ChatMessage.
    """
    try:
        message = get_object_or_404(ChatMessage, pk=message_id)

        # 1. Check permissions (User must be sender or receiver)
        if request.user != message.sender and request.user != message.receiver:
            return HttpResponseForbidden("Permission denied.")

        # 2. Check if file metadata exists
        if not message.attached_file or not message.encrypted_file_key or not message.nonce_b64:
             raise Http404("File metadata missing or file not attached.")

        # 3. Get metadata
        encrypted_path = message.attached_file.name # Path stored in DB field
        if not default_storage.exists(encrypted_path):
             raise Http404("Encrypted file not found in storage.")

        nonce = base64.urlsafe_b64decode(message.nonce_b64.encode()) # Decode base64 nonce
        encrypted_file_key_bytes = base64.urlsafe_b64decode(message.encrypted_file_key.encode()) # Decode base64 key
        mime_type = message.mime_type or 'application/octet-stream' # Default mime type
        original_filename = message.original_filename or encrypted_path.split('/')[-1] # Fallback name

        # 4. Decrypt the file key using the master key
        try:
            file_key = decrypt_file_key(encrypted_file_key_bytes)
        except InvalidToken:
             print(f"--- DOWNLOAD: InvalidToken decrypting file key for msg {message_id}")
             messages.error(request, "Decryption failed: Key error.")
             return HttpResponseServerError("Decryption key error.") # Or redirect

        # 5. Define a generator function for streaming decryption
        def file_decryption_iterator(file_name, key, nonce, chunk_size):
            try:
                 with default_storage.open(file_name, 'rb') as encrypted_file_stream:
                     read_nonce = encrypted_file_stream.read(12) # Read nonce from file start
                     if read_nonce != nonce:
                         print(f"--- DOWNLOAD: Nonce mismatch for msg {message_id}! DB: {nonce.hex()}, File: {read_nonce.hex()}")
                         # Don't yield anything if nonce is wrong
                         raise ValueError("Nonce mismatch during decryption - file may be corrupt or incorrect.")

                     aesgcm = AESGCM(key)
                     while True:
                         chunk = encrypted_file_stream.read(chunk_size)
                         if not chunk:
                             break # End of file
                         try:
                            decrypted_chunk = aesgcm.decrypt(nonce, chunk, None)
                            yield decrypted_chunk
                         except InvalidToken:
                            print(f"--- DOWNLOAD: InvalidToken during chunk decryption for msg {message_id}!")
                            # Stop yielding if tag is invalid
                            raise ValueError("File integrity check failed during decryption.")
            except Exception as e:
                 print(f"--- DOWNLOAD: Error during streaming decryption for msg {message_id}: {e}")
                 # How to signal error in stream? Raise an exception the StreamingHttpResponse might catch.
                 raise

        # 6. Create and return the StreamingHttpResponse
        try:
            response = StreamingHttpResponse(
                file_decryption_iterator(encrypted_path, file_key, nonce, CHUNK_SIZE),
                content_type=mime_type
            )
            response['Content-Disposition'] = f'attachment; filename="{original_filename}"'
            # Note: Content-Length cannot be set easily for generators
            return response
        except ValueError as e: # Catch errors raised from the iterator
             messages.error(request, f"File decryption failed: {e}")
             # Redirect or return an error page
             return redirect(request.META.get('HTTP_REFERER', 'home'))


    except Http404 as e:
        raise e # Let Django handle 404
    except Exception as e:
        print(f"--- DOWNLOAD VIEW: General error processing download for message {message_id}: {e}")
        traceback.print_exc()
        messages.error(request, "An error occurred while processing the file.")
        return HttpResponseServerError("An error occurred while processing the file.")