from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LeakyReLU
import numpy as np
import tensorflow as tf

# Set a fixed random seed for reproducibility
seed_value = 42
np.random.seed(seed_value)
tf.random.set_seed(seed_value)

# Generator Model (GAN) to generate cryptographic keys
def build_generator(latent_dim):
    model = Sequential()
    model.add(Dense(128, input_dim=latent_dim))
    model.add(LeakyReLU(alpha=0.01))
    model.add(Dense(256))
    model.add(LeakyReLU(alpha=0.01))
    model.add(Dense(512))
    model.add(LeakyReLU(alpha=0.01))
    model.add(Dense(32, activation='sigmoid'))  # Key size is 32 bytes
    return model

# Discriminator Model (optional, for training purposes only)
# def build_discriminator():
#     model = Sequential()
#     model.add(Dense(512, input_dim=32))
#     model.add(LeakyReLU(alpha=0.01))
#     model.add(Dense(256))
#     model.add(LeakyReLU(alpha=0.01))
#     model.add(Dense(1, activation='sigmoid'))
#     return model

# GAN Model
def build_gan(generator, discriminator):
    discriminator.trainable = False
    model = Sequential()
    model.add(generator)
    model.add(discriminator)
    return model

# Generate cryptographic key using the trained GAN generator
def generate_key_gan(generator, latent_dim):
    # Random noise for key generation (reproducible due to fixed seed)
    noise = np.random.normal(0, 1, (1, latent_dim))
    generated_key = generator.predict(noise)
    return generated_key

# Build and compile the GAN
latent_dim = 100  # Size of random noise vector
generator = build_generator(latent_dim)
#discriminator = build_discriminator()
#gan = build_gan(generator, discriminator)

# You would need to train the GAN here with proper data if desired

# Generate cryptographic key using GAN generator
key_gan = generate_key_gan(generator, latent_dim)
print("Generated Key from GAN:", key_gan)
