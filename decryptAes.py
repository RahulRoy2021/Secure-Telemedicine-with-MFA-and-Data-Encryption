from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from PIL import Image
import numpy as np

# Load the saved key from a file
def load_key(filename):
    return np.load(filename)

# Adjust the key length to match AES requirements
def prepare_key(key):
    key_scaled = (key.flatten() * 255).astype(np.uint8)
    key_bytes = key_scaled.tobytes()
    return key_bytes[:16].ljust(16, b'\x00')

# Function to decrypt the image using AES
# Decrypt image and handle size
def decrypt_image(encrypted_image_path, key):
    with open(encrypted_image_path, 'rb') as f:
        iv = f.read(16)  # Read the IV (16 bytes)
        width = int.from_bytes(f.read(4), 'big')  # Read width (4 bytes)
        height = int.from_bytes(f.read(4), 'big')  # Read height (4 bytes)
        encrypted_img = f.read()  # Read the rest (ciphertext)

    cipher = AES.new(prepare_key(key), AES.MODE_CBC, iv=iv)
    decrypted_img = unpad(cipher.decrypt(encrypted_img), AES.block_size)

    # Reshape decrypted bytes to original image dimensions
    img_array = np.frombuffer(decrypted_img, dtype=np.uint8).reshape(height, width, 3)
    img = Image.fromarray(img_array)

    return img


if __name__ == "__main__":
    # Paths
    encrypted_path = "encrypted_image.bin"  # Encrypted image file
    key_path = "key.npy"  # Key file
    decrypted_path = "decrypted_image.png"  # Decrypted output

    # Load the cryptographic key
    key = load_key(key_path)
    print("Using Key for Decryption:", key)

    # Decrypt the image
    decrypted_img = decrypt_image(encrypted_path, key)
    decrypted_img.save(decrypted_path)

    print(f"Image decrypted and saved to {decrypted_path}")
