// ============================================================
// ITT569 - Monkey Intruder Detection System
// ESP32-S3-WROOM Firmware v2 — corrected for ESP32S3_EYE pin map
// ============================================================
// Board:  ESP32-S3-WROOM (third-party, ESP32S3_EYE camera layout)
// Camera: OV3660 via FPC (CAMERA_MODEL_ESP32S3_EYE pin mapping)
// ============================================================

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>

// ── WiFi credentials ──────────────────────────────────────────
const char* WIFI_SSID     = "UiTM WiFi STUDENT";
const char* WIFI_PASSWORD = "4Xx.59Dm3Upq6t&";

// ── Laptop server URL ─────────────────────────────────────────
// Run ipconfig in Windows CMD, copy your WiFi IPv4 address
// Example: "http://192.168.1.105:5000/classify"
const char* SERVER_URL = "http://10.6.45.159:5000/classify";

// ── Camera pins (CAMERA_MODEL_ESP32S3_EYE) ───────────────────
#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  15
#define SIOD_GPIO_NUM  4
#define SIOC_GPIO_NUM  5
#define Y2_GPIO_NUM    11
#define Y3_GPIO_NUM    9
#define Y4_GPIO_NUM    8
#define Y5_GPIO_NUM    10
#define Y6_GPIO_NUM    12
#define Y7_GPIO_NUM    18
#define Y8_GPIO_NUM    17
#define Y9_GPIO_NUM    16
#define VSYNC_GPIO_NUM 6
#define HREF_GPIO_NUM  7
#define PCLK_GPIO_NUM  13

// ── Peripheral pins (all free from camera) ───────────────────
#define PIN_PIR         14   // PIR sensor OUT
#define PIN_SERVO       21   // MG90S signal wire
#define PIN_BUZZER      47   // Active buzzer +
#define PIN_LED_GREEN   45   // Green  LED (system ready)
#define PIN_LED_YELLOW  46   // Yellow LED (motion detected)
#define PIN_LED_RED     48   // Red    LED (intruder confirmed)

// ── Servo positions ───────────────────────────────────────────
#define SERVO_CENTER  90
#define SERVO_LEFT    45
#define SERVO_RIGHT  135

// ── Timing constants ──────────────────────────────────────────
#define COOLDOWN_MS      30000  // 30s between alerts
#define BUZZER_DURATION   3000  // 3s buzzer on alarm
#define CAPTURE_DELAY      500  // ms to wait after servo moves

// ── Globals ───────────────────────────────────────────────────
Servo cameraServo;
unsigned long lastAlertTime = 0;
bool systemReady = false;

// ── Camera init ───────────────────────────────────────────────
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_QVGA;  // 320x240
  config.jpeg_quality = 12;
  config.fb_count     = 1;
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAM] Init failed: 0x%x\n", err);
    return false;
  }

  // OV3660 sensor tuning
  sensor_t* s = esp_camera_sensor_get();
  if (s != NULL) {
    s->set_brightness(s, 1);
    s->set_saturation(s, 0);
    s->set_vflip(s, 1);
    s->set_hmirror(s, 0);
  }
  Serial.println("[CAM] Initialised OK");
  return true;
}

// ── WiFi ──────────────────────────────────────────────────────
void connectWiFi() {
  Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] Connected. IP: %s\n",
                  WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WiFi] FAILED. Check SSID/password.");
  }
}

// ── LED helpers ───────────────────────────────────────────────
void setLEDs(bool green, bool yellow, bool red) {
  digitalWrite(PIN_LED_GREEN,  green  ? HIGH : LOW);
  digitalWrite(PIN_LED_YELLOW, yellow ? HIGH : LOW);
  digitalWrite(PIN_LED_RED,    red    ? HIGH : LOW);
}

void blinkLED(int pin, int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(pin, HIGH); delay(delayMs);
    digitalWrite(pin, LOW);  delay(delayMs);
  }
}

// ── Capture and classify ──────────────────────────────────────
String captureAndClassify() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[CAM] Capture failed");
    return "error";
  }
  Serial.printf("[CAM] Captured %d bytes\n", fb->len);

  String result = "error";

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "image/jpeg");
    http.setTimeout(10000);

    int httpCode = http.POST(fb->buf, fb->len);
    if (httpCode == HTTP_CODE_OK) {
      result = http.getString();
      result.trim();
      Serial.printf("[HTTP] Server response: %s\n", result.c_str());
    } else {
      Serial.printf("[HTTP] Failed, code: %d\n", httpCode);
    }
    http.end();
  } else {
    Serial.println("[WiFi] Not connected — skipping classify");
  }

  esp_camera_fb_return(fb);
  return result;
}

// ── Alarm ─────────────────────────────────────────────────────
void triggerAlarm() {
  Serial.println("[ALARM] Monkey confirmed — triggering alarm!");
  setLEDs(false, false, true);
  digitalWrite(PIN_BUZZER, HIGH);
  delay(BUZZER_DURATION);
  digitalWrite(PIN_BUZZER, LOW);
}

void resetToIdle() {
  setLEDs(true, false, false);
  cameraServo.write(SERVO_CENTER);
  delay(300);
}

// ── setup() ───────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(1500);  // Give USB CDC time to connect
  Serial.println("\n[SYS] ITT569 Monkey Detection System v2 starting...");

  // Peripheral pins
  pinMode(PIN_PIR,        INPUT);
  pinMode(PIN_BUZZER,     OUTPUT);
  pinMode(PIN_LED_GREEN,  OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED,    OUTPUT);

  digitalWrite(PIN_BUZZER,     LOW);
  digitalWrite(PIN_LED_GREEN,  LOW);
  digitalWrite(PIN_LED_YELLOW, LOW);
  digitalWrite(PIN_LED_RED,    LOW);

  // Servo
  cameraServo.attach(PIN_SERVO, 500, 2400);
  cameraServo.write(SERVO_CENTER);
  delay(500);
  Serial.println("[SYS] Servo initialised");

  // Camera
  Serial.println("[SYS] Initialising camera...");
  if (!initCamera()) {
    Serial.println("[SYS] FATAL: Camera init failed.");
    Serial.println("[SYS] Check FPC cable is fully locked.");
    while (true) {
      blinkLED(PIN_LED_RED, 3, 200);
      delay(800);
    }
  }

  // WiFi
  connectWiFi();

  systemReady = true;
  setLEDs(true, false, false);  // Green = ready
  Serial.println("[SYS] System ready. Monitoring for motion...");
}

// ── loop() ────────────────────────────────────────────────────
void loop() {
  if (!systemReady) return;

  // Cooldown check
  if ((millis() - lastAlertTime) < COOLDOWN_MS) return;

  // PIR check
  if (digitalRead(PIN_PIR) == HIGH) {
    Serial.println("[PIR] Motion detected!");
    setLEDs(false, true, false);  // Yellow = motion

    // Alternate servo direction each trigger
    static bool toggleSide = false;
    cameraServo.write(toggleSide ? SERVO_LEFT : SERVO_RIGHT);
    toggleSide = !toggleSide;
    delay(CAPTURE_DELAY);

    // Classify
    String result = captureAndClassify();

    if (result == "monkey") {
      triggerAlarm();
      lastAlertTime = millis();
    } else if (result == "clear") {
      Serial.println("[SYS] Clear — no monkey. Resuming.");
    } else {
      Serial.println("[SYS] Classification error. Resuming.");
    }

    resetToIdle();
  }

  delay(100);
}
