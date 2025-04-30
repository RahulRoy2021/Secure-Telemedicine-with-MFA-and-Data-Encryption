# chat/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
# Keep these imports if used elsewhere
from .encryption import encrypt_message, decrypt_message # Ensure decrypt_message is imported if needed elsewhere
import os # Import os for generating filename

# Define a function to create unique filenames for uploads
def user_directory_path(instance, filename):
    # Save encrypted files to a different sub-directory
    # file will be uploaded to MEDIA_ROOT/chat_files_encrypted/<username>/<filename.bin>
    username = instance.sender.username if instance.sender else 'unknown'
    safe_username = "".join(c for c in username if c.isalnum() or c in ('-', '_')).rstrip()
    # Consider using a generic or unique name for the encrypted file on disk
    # filename = f"{uuid.uuid4()}.bin" # Example using UUID
    return f'chat_files_encrypted/{safe_username}/{filename}' # Changed directory

class ChatMessage(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_messages")
    # Make text message optional
    encrypted_message = models.TextField(null=True, blank=True) # Existing text message field
    # Add field for uploaded file
    # The 'upload_to' function organizes uploads into user-specific folders
    attached_file = models.FileField(upload_to=user_directory_path, null=True, blank=True) # Existing file field
    # Keep timestamp
    timestamp = models.DateTimeField(default=timezone.now)

    # --- NEW FIELDS FOR FILE ENCRYPTION ---
    encrypted_file_key = models.TextField(null=True, blank=True)
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    mime_type = models.CharField(max_length=100, null=True, blank=True)
    # Stores the base64-encoded unique nonce used for AES-GCM encryption
    nonce_b64 = models.CharField(max_length=20, null=True, blank=True) # 12 bytes nonce -> 16 base64 chars
    # --- END ADDED FIELD ---
    # --- END NEW FIELDS ---
     # --- NEW FIELDS for Edit/Delete ---
    is_deleted = models.BooleanField(default=False) # For soft delete
    edited_at = models.DateTimeField(null=True, blank=True) # Timestamp for edits
    # --- END NEW FIELDS ---

    # Remove the custom save method that caused double encryption (if you had one)
    # def save(self, *args, **kwargs): ... (REMOVE/COMMENT OUT)

    # Method to get file URL (useful for templates/APIs) - this URL will point to encrypted data now
    def get_file_url(self):
        if self.attached_file and hasattr(self.attached_file, 'url'):
            return self.attached_file.url
        return None

    # Keep get_decrypted_message if used for text messages
    def get_decrypted_message(self):
        if self.is_deleted:
            return "[Message deleted]" # Or simply return None/empty string if you hide deleted messages in the frontend
        if self.encrypted_message:
             # Ensure you handle potential decryption errors gracefully here if needed
             return decrypt_message(self.encrypted_message)
        return None # Return None if no text message
         # Return special text if deleted

    def __str__(self):
        # Update str representation if desired, e.g., show original_filename
        file_info = f" [File: {self.original_filename}]" if self.original_filename else ""
        status = "[DELETED] " if self.is_deleted else ("[EDITED] " if self.edited_at else "")
        text_preview = f": {self.get_decrypted_message()[:20]}..." if self.encrypted_message and not self.is_deleted else ""
        return f"Chat from {self.sender.username} to {self.receiver.username} at {self.timestamp.strftime('%Y-%m-%d %H:%M')} {status}{text_preview}{file_info}"
