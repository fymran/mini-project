# ITT569 Monkey Intruder Detection Project

## 1. Project Overview
This project is an IoT-based monkey intruder detection system built for the ITT569 mini project. It combines hardware sensing, camera capture, machine learning inference, and remote alerting into one working pipeline.

The system is designed to:
- detect motion using a PIR sensor,
- capture an image with an ESP32-S3 camera module,
- send the image to a Python server,
- classify the image using a YOLOv8 custom model,
- save the result, and
- notify the user through Telegram if a monkey is detected.

---

## 2. What the Project Does
The overall flow is:
1. The ESP32-S3 board powers on and connects to Wi-Fi.
2. The PIR sensor monitors for motion.
3. When motion is detected, the board positions the camera and captures an image.
4. The image is sent to the Flask server at the laptop/PC endpoint.
5. The server runs the trained YOLOv8 model and decides whether the image contains a monkey.
6. If a monkey is detected, the system saves the image, logs the result, and sends an alert to Telegram.

---

## 3. Main Components

### Hardware
The hardware side is implemented mainly in the Arduino sketch files:
- [esp32s3_firmware/esp32s3_firmware.ino](esp32s3_firmware/esp32s3_firmware.ino)
- [esp32s3_firmware2/esp32s3_firmware2.ino](esp32s3_firmware2/esp32s3_firmware2.ino)
- [diagnostic/diagnostic.ino](diagnostic/diagnostic.ino)
- [diagnostic2/diagnostic2.ino](diagnostic2/diagnostic2.ino)
- [serial_test/serial_test.ino](serial_test/serial_test.ino)

These sketches control:
- ESP32-S3 camera initialization,
- Wi-Fi connection,
- PIR motion sensing,
- servo movement,
- LEDs and buzzer,
- HTTP image upload to the server.

### Software / Server
The main server application is in [server.py](server.py). It provides:
- a Flask endpoint for image classification,
- YOLOv8 model loading,
- image saving with bounding boxes,
- CSV logging of every result,
- Telegram alert sending.

There is also an older prototype server in [serverttest.py](serverttest.py), which used MobileNetV2 instead of YOLOv8.

### Model
The trained detection model is expected at:
- the path configured in [server.py](server.py)

The current version uses a custom YOLOv8 model file named best.pt.

---

## 4. End-to-End Workflow

### Step 1: Power On the ESP32-S3 Device
The ESP32-S3 board starts up, initializes the camera, connects to Wi-Fi, and prepares the PIR sensor and output devices.

### Step 2: Motion Triggered Capture
When the PIR sensor detects movement, the board moves the camera angle if needed and captures a frame.

### Step 3: Image Sent to the Server
The captured JPEG image is posted to the Flask server endpoint at /classify.

### Step 4: Server Runs Inference
The server loads the trained model and runs inference on the image.

### Step 5: Result Handling
- If the model detects a monkey, the server marks the result as monkey.
- If no monkey is detected, the result is clear.

### Step 6: Logging and Alerting
The server then:
- saves the image to the Desktop captures folder,
- records the outcome in a CSV log,
- optionally sends a Telegram alert with the image.

---

## 5. Project Files and Their Purpose

### [server.py](server.py)
Main production server.
It handles:
- Flask server startup,
- YOLOv8 inference,
- image saving,
- CSV logging,
- Telegram notifications.

### [serverttest.py](serverttest.py)
Older test version using MobileNetV2.
Useful as a reference for the earlier prototype pipeline.

### [requirements.txt](requirements.txt)
Lists the Python dependencies needed to run the server.

### [SETUP_INSTRUCTIONS.txt](SETUP_INSTRUCTIONS.txt)
Contains the original Windows setup guide with installation and wiring information.

### Firmware sketches
The Arduino sketches are used to test and run the embedded system on the ESP32-S3 board.
They include diagnostic versions for checking hardware like LEDs, buzzer, PIR, servo, and serial communication.

---

## 6. Setup Summary

### Python Environment
Install the required libraries using:
- pip install flask ultralytics pillow requests

### Model File
Place the trained YOLOv8 model file at the path configured in [server.py](server.py).

### Wi-Fi and Server Address
Update the ESP32 firmware to use the correct Wi-Fi credentials and your laptop’s local IP address.

### Telegram Setup
If you want alerts, configure a Telegram bot token and chat ID before running the server.

---

## 7. How to Run the Project
1. Start the Python server from [server.py](server.py).
2. Ensure the model file exists at the configured model path.
3. Upload the firmware to the ESP32-S3 board.
4. Power the board and wait for Wi-Fi connection.
5. Trigger the PIR sensor to start image capture and classification.
6. Check the saved images and CSV log on the Desktop.

---

## 8. Outputs Produced by the System
The system generates:
- saved images in the Desktop captures folder,
- a detection log CSV file,
- Telegram notifications for monkey detections,
- terminal logs from the server and ESP32 board.

---

## 9. Notes and Limitations
- The newer version uses a custom YOLOv8 model instead of the earlier MobileNetV2 approach.
- The system is still a prototype and may need tuning for lighting, camera angle, and model accuracy.
- Telegram alerting depends on a valid bot token and chat ID.
- The server must be running before the ESP32-S3 sends images.

---

## 10. Summary
This project is a complete prototype of an intelligent farm security system. It connects embedded hardware, computer vision, and cloud-style notification features into one pipeline that can detect a monkey intrusion and respond automatically.
