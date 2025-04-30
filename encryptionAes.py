from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LeakyReLU
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from PIL import Image
import numpy as np
import os

# Generator Model (GAN) to generate cryptographic keys
def build_generator(latent_dim):
    model = Sequential()
    model.add(Dense(128, input_dim=latent_dim))
    model.add(LeakyReLU(alpha=0.01))
    model.add(Dense(256))
    model.add(LeakyReLU(alpha=0.01))
    model.add(Dense(512))
    model.add(LeakyReLU(alpha=0.01))
    model.add(Dense(32, activation='sigmoid'))  # Key size is 32 floats
    return model

# Function to generate cryptographic key using GAN generator
def generate_key_gan(generator, latent_dim):
    noise = np.random.normal(0, 1, (1, latent_dim))  # Random noise for key generation
    generated_key = generator.predict(noise)
    return generated_key

# Adjust the key length to match AES requirements
def prepare_key(key):
    key_scaled = (key.flatten() * 255).astype(np.uint8)
    key_bytes = key_scaled.tobytes()
    return key_bytes[:16].ljust(16, b'\x00')

# Function to encrypt the image using AES
def encrypt_image(image_path, key):
    img = Image.open(image_path).convert('RGB')
    img_array = np.array(img)
    img_bytes = img_array.tobytes()

    cipher = AES.new(prepare_key(key), AES.MODE_CBC)
    encrypted_img = cipher.encrypt(pad(img_bytes, AES.block_size))

    return encrypted_img, cipher.iv, img.size

# Save the encrypted image and IV along with size
def save_encrypted_image(encrypted_img, iv, size, filename):
    with open(filename, 'wb') as f:
        f.write(iv)  # Store the IV (16 bytes)
        f.write(size[0].to_bytes(4, 'big') + size[1].to_bytes(4, 'big'))  # Store width and height (4 bytes each)
        f.write(encrypted_img)  # Store encrypted image


# Save the generated key to a file
def save_key(key, filename):
    np.save(filename, key)

if __name__ == "__main__":
    # GAN settings
    latent_dim = 100
    generator = build_generator(latent_dim)
    generator.compile(optimizer='adam', loss='binary_crossentropy')

    # Generate the cryptographic key
    key = generate_key_gan(generator, latent_dim)
    print("Generated Key from GAN:", key)

    # Paths
    image_path = "images.jpeg"  # Input image
    encrypted_path = "encrypted_image.bin"  # Encrypted output
    key_path = "key.npy"  # Key storage

    # Encrypt the image
    encrypted_img, iv, size = encrypt_image(image_path, key)
    save_encrypted_image(encrypted_img, iv, size, encrypted_path)
    save_key(key, key_path)

    print(f"Image encrypted and saved to {encrypted_path}")
    print(f"Key saved to {key_path}")
