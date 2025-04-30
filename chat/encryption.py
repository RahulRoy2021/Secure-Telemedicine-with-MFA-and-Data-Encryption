# chat/encryption.py

import os
import base64
from cryptography.fernet import Fernet, InvalidToken

# --- Imports for AES File Encryption ---
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
# -------------------------------------

# --- Master Key for encrypting FILE keys (Keep this VERY secure) ---
# This is your existing Fernet key, acting as a master key now.
# IMPORTANT: In production, load this from environment variables or secrets manager.
MASTER_KEY = b'wwWesaVyNBjtlDgpnGKvWaiHLeTspowC2pfLUFW8ZCA='
master_cipher = Fernet(MASTER_KEY)
# --- End Master Key ---

# Chunk size for reading/writing files during streaming encryption/decryption
CHUNK_SIZE = 64 * 1024 # 64KB

# === Fernet Functions for TEXT Messages (Keep As Is) ===

def encrypt_message(plaintext):
    """Encrypts a TEXT message using Fernet."""
    if not plaintext:
        return ""
    # print(f"--- ENCRYPTING TEXT: Original text: {plaintext}") # Keep debug prints if needed
    try:
        encrypted_bytes = master_cipher.encrypt(plaintext.encode())
        return encrypted_bytes.decode()
    except Exception as e:
        print(f"--- TEXT ENCRYPTING Failed - Exception: {e}")
        return f"Encryption Error: {e}"


def decrypt_message(encrypted_text):
    """Decrypts a TEXT message using Fernet."""
    if not encrypted_text:
        return ""
    # print(f"--- DECRYPTING TEXT: Attempting on: {encrypted_text}") # Keep debug prints if needed
    try:
        encrypted_bytes = encrypted_text.encode()
        decrypted_bytes = master_cipher.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()
    except InvalidToken:
        print("--- TEXT DECRYPTING Failed - Invalid Token")
        return f"[DECRYPTION FAILED - Invalid Token] Original: {encrypted_text}"
    except Exception as e:
        print(f"--- TEXT DECRYPTING Failed - Exception: {e}")
        return f"[DECRYPTION FAILED - {type(e).__name__}] Original: {encrypted_text}"

# === AES-GCM Functions for FILE Encryption ===

def generate_aes_key():
    """Generates a new random 256-bit (32-byte) AES key."""
    return AESGCM.generate_key(bit_length=256)

def encrypt_file_key(file_key_bytes):
    """Encrypts the per-file AES key using the master Fernet key."""
    # Uses the same Fernet cipher defined at the top
    return master_cipher.encrypt(file_key_bytes)

def decrypt_file_key(encrypted_file_key_bytes):
    """Decrypts the per-file AES key using the master Fernet key."""
    # Uses the same Fernet cipher defined at the top
    return master_cipher.decrypt(encrypted_file_key_bytes)

def encrypt_file_stream(input_stream, output_stream, key):
    """
    Reads from input_stream, encrypts using AES-GCM, writes to output_stream.
    Returns the unique nonce used for this encryption (bytes).
    Writes nonce + encrypted data to output_stream.
    """
    try:
        aesgcm = AESGCM(key)
        nonce = os.urandom(12) # Generate 12-byte nonce, unique per file/key combo
        output_stream.write(nonce) # Prepend nonce to the encrypted data
        while True:
            chunk = input_stream.read(CHUNK_SIZE)
            if not chunk:
                break # End of file
            encrypted_chunk = aesgcm.encrypt(nonce, chunk, None) # Associated data = None
            output_stream.write(encrypted_chunk)
        print(f"--- File Encryption: Success. Nonce: {nonce.hex()} ---")
        return nonce
    except Exception as e:
        print(f"--- File Encryption Error: {e} ---")
        # Consider raising the exception for the view/consumer to handle
        raise # Re-raise the exception

def decrypt_file_stream(input_stream, output_stream, key):
    """
    Reads from input_stream (expects nonce prepended), decrypts using AES-GCM,
    writes decrypted data to output_stream. Returns True on success, False on failure.
    """
    try:
        nonce = input_stream.read(12) # Read the 12-byte nonce from the start
        if len(nonce) != 12:
            print("--- File Decryption Error: Could not read full nonce. ---")
            return False
        print(f"--- File Decryption: Using Nonce: {nonce.hex()} ---")
        aesgcm = AESGCM(key)
        while True:
            chunk = input_stream.read(CHUNK_SIZE)
            if not chunk:
                break # End of file
            decrypted_chunk = aesgcm.decrypt(nonce, chunk, None)
            output_stream.write(decrypted_chunk)
        print(f"--- File Decryption: Success. ---")
        return True
    except InvalidToken: # Specific error for failed authentication/decryption
         print("--- File Decryption Error: InvalidToken (Data corrupted or wrong key/nonce) ---")
         return False
    except Exception as e:
        print(f"--- File Decryption Error: {e} ---")
        return False