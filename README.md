# Secure-Telemedicine-with-MFA-and-Data-Encryption

Overview
This project focuses on developing a secure telemedicine platform that ensures confidential communication between patients and healthcare providers. It integrates Multi-Factor Authentication (MFA) and Advanced Encryption Techniques to safeguard sensitive medical data.

Features Implemented So Far
Data Security with AES Encryption:
Encrypts and decrypts medical images using AES (Advanced Encryption Standard).
Cryptographic Key Generation using GANs:
Utilizes Generative Adversarial Networks to create high-entropy, unpredictable cryptographic keys.
Image Handling with OpenCV:
Processes and encrypts medical images for secure transmission.
Multi-Factor Authentication (MFA):
Implements Time-Based One-Time Passwords (TOTP) and email-based OTPs for secure access control.
Python-Based Implementation:
Built using TensorFlow, NumPy, PyCryptodome, and OpenCV.

Project Objectives
Secure transmission and storage of sensitive medical data.
Implement robust access control through MFA.
Provide a scalable encryption system suitable for real-time applications.

Technologies Used
Programming Language: Python
Libraries:
TensorFlow: For GAN implementation.
NumPy: For mathematical operations.
PyCryptodome: For AES encryption and decryption.
OpenCV: For image processing.
Flask: For building the user interface (future work).

Folder Structure

Secure-Telemedicine/
│
├── gan_key_generation.py        # Script for GAN-based key generation
├── encryption_aes.py            # Script for AES encryption
├── decryption_aes.py            # Script for AES decryption
├── requirements.txt             # Python dependencies
├── README.md                    # Project description
├── data/                        # Sample input/output data
│   ├── example_image.png        # Sample input image
│   ├── encrypted_image.bin      # Encrypted image output
│   ├── decrypted_image.png      # Decrypted image output
│
└── results/                     # Performance metrics and analysis
    ├── npcr_uaci_metrics.txt    # NPCR and UACI results
    ├── performance_charts.png   # Graphical analysis of results
