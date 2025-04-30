# chat/consumers.py

# --- Imports ---
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import urllib.parse
from django.conf import settings
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatMessage
from .encryption import encrypt_message, decrypt_message
from django.utils import timezone # Ensure timezone is imported
import traceback
import redis.asyncio as redis 
from django.urls import reverse # To generate download URLs
import base64 # To potentially decode if needed (though unlikely here)
# --- End Imports ---

User = get_user_model()
# --- Updated Redis connection setup ---
async def get_redis_connection():
    try:
        # Construct Redis URL from settings if possible, fallback to localhost
        redis_host_config = settings.CHANNEL_LAYERS["default"]["CONFIG"]["hosts"]
        if isinstance(redis_host_config, list) and isinstance(redis_host_config[0], tuple):
            # For tuple format like ("localhost", 6379)
            host = redis_host_config[0][0]
            port = redis_host_config[0][1]
            redis_url = f"redis://{host}:{port}/0" # Assumes DB 0
            print(f"--- Attempting Redis connection using Host/Port: {host}:{port}")
            # Use from_url for consistency, or directly host/port
            # redis_client = redis.Redis(host=host, port=port, db=0, decode_responses=True)
            redis_client = redis.from_url(redis_url, decode_responses=True)
        elif isinstance(redis_host_config, list) and isinstance(redis_host_config[0], str):
             # For URL format like "redis://..."
             redis_url = redis_host_config[0]
             print(f"--- Attempting Redis connection using URL: {redis_url}")
             redis_client = redis.from_url(redis_url, decode_responses=True)
        else:
             # Default fallback
             redis_url = "redis://localhost:6379/0"
             print(f"--- Attempting Redis connection using Fallback URL: {redis_url}")
             redis_client = redis.from_url(redis_url, decode_responses=True)

        await redis_client.ping() # Verify connection
        print("--- Redis connection successful.")
        return redis_client
    except ConnectionRefusedError:
         print(f"--- FATAL: Redis connection refused at inferred URL {redis_url}. Is Redis running?")
         return None
    except Exception as e:
        print(f"--- FATAL: Failed to connect to Redis (URL: {redis_url}): {e}")
        print(traceback.format_exc())
        return None
# --- End Redis setup ---

class ChatConsumer(AsyncWebsocketConsumer):

    # --- connect method (no changes) ---
   # In chat/consumers.py

    # In chat/consumers.py
    redis = None # Store connection per instance

    async def connect(self):
        self.sender_username = self.scope["user"].username
        if not self.scope["user"].is_authenticated:
            print(f"--- User not authenticated. Closing connection.")
            await self.close(); return

        self.receiver_username = self.scope["url_route"]["kwargs"].get("username")
        if not self.receiver_username:
            print(f"--- {self.sender_username}: Receiver username missing. Closing connection.")
            await self.close(); return

        # Prevent self-chat if desired
        if self.sender_username == self.receiver_username:
             print(f"--- {self.sender_username}: Attempting self-chat. Closing connection.")
             await self.close(); return

        # --- Connect to Redis (using the updated function) ---
        self.redis = await get_redis_connection()
        if not self.redis:
            print(f"--- {self.sender_username}: Closing connection due to Redis failure.")
            await self.close(code=1011) # Internal error
            return
        # ------------------------------------------------------


        user_list = sorted([self.sender_username, self.receiver_username])
        self.room_group_name = f"chat_{user_list[0]}_{user_list[1]}"
        self.presence_key = f"presence_{self.room_group_name}" # Key for Redis set
        self.notification_group_name = f'user_notifications_{self.sender_username}'

        
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        # --- ADD: Join user-specific notification group ---
        await self.channel_layer.group_add(self.notification_group_name, self.channel_name)
        # -------------------------------------------------
        await self.accept()
        print(f"--- {self.sender_username}: WebSocket accepted for room '{self.room_group_name}'")

        # --- Presence Logic: Add user and check if first connection ---
        try:
            # Use the connected redis client (self.redis)
            elements_added = await self.redis.sadd(self.presence_key, self.sender_username)
            if elements_added > 0:
                print(f"--- Presence: '{self.sender_username}' first connection to '{self.presence_key}'. Broadcasting online.")
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "user_status_broadcast",
                        "event_type": "user_online",
                        "username": self.sender_username,
                    }
                )
            else:
                 print(f"--- Presence: '{self.sender_username}' already present in '{self.presence_key}'. No broadcast.")

            # --- Send Correct Initial Status of the *Other* User ---
            is_receiver_online = await self.redis.sismember(self.presence_key, self.receiver_username)
            initial_receiver_status = "user_online" if is_receiver_online else "user_offline"
            print(f"--- Presence: Sending initial status for '{self.receiver_username}' as '{initial_receiver_status}' to '{self.sender_username}'")
            await self.send_payload({
                 "type": initial_receiver_status,
                 "username": self.receiver_username
            })
        except Exception as e:
             print(f"--- ERROR during Redis connect logic for {self.sender_username}: {e}")
             print(traceback.format_exc())

    async def disconnect(self, close_code):
        print(f"--- {self.sender_username}: Disconnecting (Code: {close_code}). Groups: {getattr(self, 'room_group_name', 'N/A')}, {getattr(self, 'notification_group_name', 'N/A')}")
        redis_conn = getattr(self, 'redis', None)
        room_group = getattr(self, 'room_group_name', None)
        notification_group = getattr(self, 'notification_group_name', None) # Get notification group name
        presence_key = getattr(self, 'presence_key', None)

        # --- Presence Logic: Remove user ---
        if redis_conn and presence_key and room_group:
            try:
                elements_removed = await redis_conn.srem(presence_key, self.sender_username)
                if elements_removed > 0:
                     is_still_present = await redis_conn.sismember(presence_key, self.sender_username)
                     if not is_still_present:
                        print(f"--- Presence: '{self.sender_username}' LAST connection removed. Broadcasting offline.")
                        # Send offline status to the CHAT room group
                        await self.channel_layer.group_send(
                             room_group, # Send to chat room
                             {"type": "user_status_broadcast", "event_type": "user_offline", "username": self.sender_username}
                        )
            except Exception as e:
                 print(f"--- ERROR during Redis presence disconnect logic: {e}")
                 print(traceback.format_exc()) # Log full traceback
            finally:
                # Close Redis connection pool - do this after all redis operations
                try:
                    await redis_conn.connection_pool.disconnect()
                    print(f"--- {self.sender_username}: Redis connection pool disconnected.")
                except Exception as e_redis_close:
                     print(f"--- ERROR closing redis pool: {e_redis_close}")
        else:
             print(f"--- {self.sender_username}: Skipping Redis presence logic on disconnect (missing info).")
        # --- End Presence ---


        # --- Leave channel layer groups ---
        # This block should be *outside* the redis_conn check
        try:
            if room_group:
                 print(f"--- {self.sender_username}: Discarding from chat group: {room_group}")
                 await self.channel_layer.group_discard(room_group, self.channel_name)
            else:
                 print(f"--- {self.sender_username}: No chat room group found to discard.")

            # --- Leave notification group ---
            if notification_group:
                 print(f"--- {self.sender_username}: Discarding from notification group: {notification_group}")
                 await self.channel_layer.group_discard(notification_group, self.channel_name)
            else:
                 print(f"--- {self.sender_username}: No notification group found to discard.")
            # -------------------------------

        except Exception as e:
             print(f"--- ERROR discarding groups for {self.sender_username} during disconnect: {e}")
             print(traceback.format_exc()) # Print full error

    async def user_status_broadcast(self, event):
        """
        Handles forwarding user online/offline status events FROM the channel layer
        TO the client IF the event is about the *other* user.
        """
        event_type = event.get("event_type")
        username = event.get("username")
        if hasattr(self, 'receiver_username') and username == self.receiver_username:
            payload = { "type": event_type, "username": username }
            print(f"--- {self.sender_username}: Received status broadcast ('{event_type}' for '{username}'). Sending to client.")
            await self.send_payload(payload)
        # else: # No need to log ignored broadcasts unless debugging
            # print(f"--- {self.sender_username}: Ignored status broadcast ('{event_type}' for '{username}').")


    # --- receive method (Updated chat_message block) ---
    async def receive(self, text_data):
        print(f"--- CONSUMER Raw Receive: {text_data[:500]}") # Print first 500 chars
        start_time = timezone.now()
        print(f"--- {start_time.isoformat()} CONSUMER (receive): START processing raw data: {text_data[:150]}...")
        try:
            data = json.loads(text_data)
            message_type = data.get("type", "chat_message")
            print(f"--- CONSUMER Parsed Type: {message_type}")
            sender_username = self.scope["user"].username
            receiver_username = self.receiver_username

            t_users_start = timezone.now() # ... (logging)
            sender = await self.get_user(sender_username)
            receiver = await self.get_user(receiver_username)
            t_users_end = timezone.now() # ... (logging)
            if not sender or not receiver: # ... (error handling) ...
                return

            # --- Handle Edit/Delete (keep existing logic) ---
            if message_type == "edit_message":
                # ... (keep existing edit logic) ...
                pass # Placeholder
            elif message_type == "delete_message":
                # ... (keep existing delete logic) ...
                pass # Placeholder

            # --- Handle Text Message (keep existing logic) ---
            elif message_type == "chat_message":
                message = data.get("message")
                if not message: return # ... (logging) ...
                # ... (logging) ...
                encrypted_content = encrypt_message(message)
                # Call save_message (Note: file-related args will be None)
                saved_instance = await self.save_message(
                    sender_obj=sender,
                    receiver_obj=receiver,
                    encrypted_content=encrypted_content,
                    file_path=None,
                    encrypted_file_key_b64=None, # Send None for key
                    nonce_b64=None, # Send None for nonce
                    original_filename=None,
                    mime_type=None
                )
                if not saved_instance: return # ... (logging) ...
                # ... (logging) ...
                # Broadcast text message details
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message_broadcast",
                        "id": saved_instance.id,
                        "message": message, # Send original plaintext for broadcast
                        "sender_username": sender_username,
                        "timestamp": saved_instance.timestamp.isoformat(),
                        "edited_at": None, # Not edited on creation
                        "is_deleted": False,
                        # File fields are null for text messages
                        "original_filename": None,
                        "download_url": None,
                    }
                 )
                # ... (logging) ...

            # --- UPDATED: Handle Media Message (Process Metadata from Upload View) ---
            elif message_type == "media_message":
                print(f"--- CONSUMER: Received media_message data: {data}")
                # Extract ALL metadata sent from frontend (originating from upload_chat_file view)
                caption = data.get("caption", "")
                saved_path = data.get("saved_path") # Path to ENCRYPTED file
                original_filename = data.get("original_filename")
                mime_type = data.get("mime_type")
                nonce_b64 = data.get("nonce_b64")
                encrypted_key_b64 = data.get("encrypted_key_b64")

                # Basic validation of received metadata
                if not saved_path or not original_filename or not nonce_b64 or not encrypted_key_b64:
                    print(f"--- CONSUMER (media): ERROR - Missing required file metadata in WebSocket message.")
                    # Optionally send an error back to the sender client
                    return

                # Encrypt caption if present
                encrypted_caption = encrypt_message(caption) if caption else None

                # Save ChatMessage with all metadata
                saved_instance = await self.save_message(
                    sender_obj=sender,
                    receiver_obj=receiver,
                    encrypted_content=encrypted_caption, # Save encrypted caption
                    file_path=saved_path, # Save path to encrypted file
                    encrypted_file_key_b64=encrypted_key_b64, # Save encrypted key
                    nonce_b64=nonce_b64, # Save nonce
                    original_filename=original_filename,
                    mime_type=mime_type
                )

                if not saved_instance:
                    print(f"--- CONSUMER (media): FAILED to save media message to DB, skipping broadcast.")
                    # Optionally send an error back to the sender client
                    return

                print(f"--- CONSUMER (media): Saved media message (ID: {saved_instance.id})")

                # Generate download URL for broadcasting
                download_url = None
                try:
                    download_url = reverse('chat:download_decrypted_file', args=[saved_instance.id])
                    print(f"--- CONSUMER (media): Generated download URL: {download_url}")
                except Exception as url_e:
                    print(f"--- CONSUMER (media): ERROR generating download URL for msg {saved_instance.id}: {url_e}")

                # Broadcast media message details (including download URL)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "media_message_broadcast",
                        "id": saved_instance.id,
                        "sender_username": sender_username,
                        "caption": caption, # Send original caption for display
                        "original_filename": original_filename,
                        "download_url": download_url, # Send the URL for the download link
                        "timestamp": saved_instance.timestamp.isoformat(),
                        "edited_at": None,
                        "is_deleted": False,
                    }
                 )
                print(f"--- CONSUMER (media): Broadcasted media message details for ID {saved_instance.id}")
            # --- END UPDATED Media Message Handling ---

            # --- Handle Typing (keep existing logic) ---
            elif message_type == "typing_start":
                 await self.channel_layer.group_send( self.room_group_name, { "type": "typing_start_broadcast", "sender_username": sender_username, })
            elif message_type == "typing_stop":
                 await self.channel_layer.group_send( self.room_group_name, { "type": "typing_stop_broadcast", "sender_username": sender_username, })
            else: print(f"--- CONSUMER (receive): Unknown message type: {message_type}")

        except json.JSONDecodeError: print(f"--- CONSUMER (receive): ERROR - Invalid JSON.")
        except Exception as e: print(f"--- CONSUMER (receive): ERROR processing message. {e}"); print(traceback.format_exc())
        finally: end_time = timezone.now(); print(f"--- {end_time.isoformat()} CONSUMER (receive): END processing message (Total: {(end_time-start_time).total_seconds():.3f}s)")
    # --- End receive method ---

    # --- NEW Broadcast Handlers ---
    async def message_edited_broadcast(self, event):
        payload = {
            "type": "message_edited", # Use this type for JS handler
            "message_id": event.get("message_id"),
            "new_message": event.get("new_message"),
            "edited_at": event.get("edited_at"),
            # Optionally include sender_username if needed for client-side checks
        }
        await self.send_payload(payload)

    async def message_deleted_broadcast(self, event):
        payload = {
            "type": "message_deleted", # Use this type for JS handler
            "message_id": event.get("message_id"),
             # Optionally include sender_username if needed for client-side checks
        }
        await self.send_payload(payload)
    # --- Message Handlers (No changes needed here from previous version) ---
    async def chat_message_broadcast(self, event):
        payload = { "type": "chat_message",
                   "id": event.get("id"),
                   "message": event.get("message", ""),
                   "sender_username": event.get("sender_username", "Unknown"),
                   "timestamp": event.get("timestamp",timezone.now().isoformat()),
                   "original_filename": None,
                    "download_url": None,
                   }
        await self.send_payload(payload) # Send to all including sender

    async def typing_start_broadcast(self, event):
        payload = { "type": "typing_start", "sender_username": event.get("sender_username"), }
        if self.sender_username != event.get("sender_username"): # Keep check for typing
            await self.send_payload(payload)

    async def typing_stop_broadcast(self, event):
        payload = { "type": "typing_stop", "sender_username": event.get("sender_username"), }
        if self.sender_username != event.get("sender_username"): # Keep check for typing
            await self.send_payload(payload)

    async def media_message_broadcast(self, event):
        # print(f"--- {timezone.now().isoformat()} CONSUMER (media_broadcast): Sending media msg ID {event.get('message_id')} from {event.get('sender_username')}") # Optional verbose log
        payload = {
            "type": "media_message", # Match JS handler
            "id": event.get("id"),
            "sender_username": event.get("sender_username"),
            "caption": event.get("caption", ""), # Send original caption
            "original_filename": event.get("original_filename"),
            "download_url": event.get("download_url"), # Send generated download URL
            "timestamp": event.get("timestamp"),
            "edited_at": event.get("edited_at"),
            "is_deleted": event.get("is_deleted"),
            "message": event.get("caption", ""), # Include caption as 'message' for consistency if needed by JS appendMessage
        }
        await self.send_payload(payload) # Send to all including sender

    # --- Helper function to send payload (no changes) ---
    async def send_payload(self, payload):
         try: await self.send(text_data=json.dumps(payload))
         except Exception as e: print(f"--- {timezone.now().isoformat()} CONSUMER (send_payload): Error sending payload: {e}")

    # --- Database helpers (No changes needed here - keep as sync def) ---
    # --- NEW Database Helpers ---
    @database_sync_to_async
    def edit_message_in_db(self, message_id, user_obj, new_content):
        """ Edits a message in the DB if the user is the sender. Returns instance or None. """
        try:
            message_instance = ChatMessage.objects.get(pk=message_id, sender=user_obj, is_deleted=False)
            # Add more checks? E.g., prevent editing files? Prevent editing very old messages?
            message_instance.encrypted_message = encrypt_message(new_content)
            message_instance.edited_at = timezone.now()
            # Clear file fields if editing a file message to become text? Or prevent editing files?
            # message_instance.attached_file = None
            # message_instance.encrypted_file_key = None
            # ... etc.
            message_instance.save()
            print(f"--- CONSUMER (edit_message): Edited message ID {message_id}")
            return message_instance
        except ChatMessage.DoesNotExist:
            print(f"--- CONSUMER (edit_message): Message {message_id} not found or user mismatch.")
            return None
        except Exception as e:
            print(f"--- CONSUMER (edit_message): Error editing message {message_id}: {e}")
            return None

    @database_sync_to_async
    def delete_message_in_db(self, message_id, user_obj):
        """ Marks a message as deleted if the user is the sender. Returns True/False. """
        try:
            message_instance = ChatMessage.objects.get(pk=message_id, sender=user_obj)
            if message_instance.is_deleted:
                 print(f"--- CONSUMER (delete_message): Message {message_id} already deleted.")
                 return False # Or True, depending on desired behaviour

            # --- Soft Delete ---
            message_instance.is_deleted = True
            # Optional: Clear sensitive data on delete?
            # message_instance.encrypted_message = encrypt_message("[Deleted]") # Or None
            # message_instance.attached_file = None # Decide if you want to delete files from storage too
            # message_instance.encrypted_file_key = None
            # ...
            message_instance.save()
            print(f"--- CONSUMER (delete_message): Soft deleted message ID {message_id}")
            return True

            # --- Hard Delete (Alternative) ---
            # message_instance.delete()
            # print(f"--- CONSUMER (delete_message): Hard deleted message ID {message_id}")
            # return True
        except ChatMessage.DoesNotExist:
            print(f"--- CONSUMER (delete_message): Message {message_id} not found or user mismatch.")
            return False
        except Exception as e:
            print(f"--- CONSUMER (delete_message): Error deleting message {message_id}: {e}")
            return False
        
    @database_sync_to_async
    def get_user(self, username):
         """Synchronously gets user from DB."""
         # ... (keep as is) ...
         try: return User.objects.get(username=username)
         except User.DoesNotExist: print(f"--- CONSUMER (get_user): User '{username}' not found."); return None
         except Exception as e: print(f"--- CONSUMER (get_user): Error fetching user '{username}': {e}"); return None

    @database_sync_to_async
    def save_message(self, sender_obj, receiver_obj, encrypted_content, file_path, encrypted_file_key_b64, nonce_b64, original_filename, mime_type):
        """
        Synchronously saves message to DB. Handles both text and file metadata.
        Returns instance or None.
        """
        message_instance = None
        try:
            message_instance = ChatMessage.objects.create(
                sender=sender_obj,
                receiver=receiver_obj,
                encrypted_message=encrypted_content, # Will be None for file-only messages
                attached_file=file_path, # Path to ENCRYPTED file, None for text-only
                encrypted_file_key=encrypted_file_key_b64, # Base64 encoded encrypted key
                nonce_b64=nonce_b64, # Base64 encoded nonce
                original_filename=original_filename,
                mime_type=mime_type,
            )
            file_info = f", File: {original_filename}" if original_filename else ""
            print(f"--- CONSUMER (save_message): Saved message (ID: {message_instance.id}{file_info}) from {sender_obj.username}")
        except Exception as e:
            print(f"--- CONSUMER (save_message): Error saving ChatMessage: {e}")
            print(traceback.format_exc())
        return message_instance
    # --- END UPDATED HELPER ---
    async def send_notification(self, event):
        """
        Handles the 'send_notification' type message received from the channel layer group
        (triggered by the post_save signal on the Notification model).
        Sends the notification details down the WebSocket to this specific user.
        """
        try:
            notification_data = event.get('notification')
            if notification_data:
                print(f"--- Consumer {self.sender_username}: Received notification broadcast (ID: {notification_data.get('id')}). Sending to client.")
                # Send payload to the connected client WebSocket
                await self.send_payload({
                    'type': 'new_notification', # Use a distinct type for the frontend JS
                    'notification': notification_data
                })
            else:
                 print(f"--- Consumer {self.sender_username}: Received 'send_notification' event without notification data.")
        except Exception as e:
            print(f"--- Consumer {self.sender_username}: Error processing send_notification event: {e}")
    # --- END NEW HANDLER ---
    # End of ChatConsumer class