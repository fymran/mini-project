// ============================================================
// ITT569 - Monkey Intruder Detection System
// ESP32-S3-WROOM Firmware v4 — dual-core parallel tasks
// ============================================================
// Core 0: continuous camera capture + classification loop
// Core 1: PIR polling + servo rotation (independent)
// ============================================================

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>

#define DBG Serial0

// ── WiFi credentials ──────────────────────────────────────────
const char* WIFI_SSID     = "tenet";
const char* WIFI_PASSWORD = "salambph";

// ── Laptop server URL ─────────────────────────────────────────
const char* SERVER_URL = "http://192.168.5.188:5000/classify";

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

// ── Peripheral pins ───────────────────────────────────────────
#define PIN_PIR         14
#define PIN_SERVO       21
#define PIN_BUZZER      47
#define PIN_LED_GREEN   45
#define PIN_LED_YELLOW  46
#define PIN_LED_RED     48

// ── Servo positions ───────────────────────────────────────────
#define SERVO_POS_A   180    // Facing Position A (e.g., Front)
#define SERVO_POS_B  0    // Facing Position B (e.g., Back)

// ── Timing ───────────────────────────────────────────────────
#define CAPTURE_INTERVAL_MS  1500  // capture every 1.5s (~0.67 FPS)
#define COOLDOWN_MS          30000
#define BUZZER_DURATION      3000
#define SERVO_SETTLE_MS      500

// ── Globals ───────────────────────────────────────────────────
Servo       cameraServo;
TaskHandle_t cameraTaskHandle = NULL;
TaskHandle_t pirTaskHandle    = NULL;

volatile bool monkeyDetected   = false;
volatile unsigned long lastAlertTime = 0;

// Mutex to prevent camera and servo fighting over timing
SemaphoreHandle_t xServoMutex;

// ── LED helpers ───────────────────────────────────────────────
void setLEDs(bool green, bool yellow, bool red) {
  digitalWrite(PIN_LED_GREEN,  green  ? HIGH : LOW);
  digitalWrite(PIN_LED_YELLOW, yellow ? HIGH : LOW);
  digitalWrite(PIN_LED_RED,    red    ? HIGH : LOW);
}

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
  config.frame_size   = FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count     = 2;  // 2 buffers for smoother capture
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.grab_mode    = CAMERA_GRAB_LATEST;  // always get freshest frame

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    DBG.printf("[CAM] Init failed: 0x%x\n", err);
    return false;
  }
  sensor_t* s = esp_camera_sensor_get();
  if (s) {
    s->set_brightness(s, 1);
    s->set_saturation(s, 0);
    s->set_vflip(s, 1);
    s->set_hmirror(s, 0);
  }
  DBG.println("[CAM] Initialised OK");
  return true;
}

// ── WiFi ──────────────────────────────────────────────────────
void connectWiFi() {
  DBG.printf("[WiFi] Connecting to %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    DBG.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    DBG.printf("\n[WiFi] Connected. IP: %s\n",
               WiFi.localIP().toString().c_str());
  } else {
    DBG.println("\n[WiFi] FAILED. Check credentials.");
  }
}

// ── Capture and classify (called from camera task) ────────────
String captureAndClassify() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) return "error";

  String result = "error";
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "image/jpeg");
    http.setTimeout(10000);
    int code = http.POST(fb->buf, fb->len);
    if (code == HTTP_CODE_OK) {
      result = http.getString();
      result.trim();
    } else {
      DBG.printf("[HTTP] Error code: %d\n", code);
    }
    http.end();
  }
  esp_camera_fb_return(fb);
  return result;
}

// ── Alarm ─────────────────────────────────────────────────────
void triggerAlarm() {
  DBG.println("[ALARM] Monkey confirmed!");
  setLEDs(false, false, true);
  digitalWrite(PIN_BUZZER, HIGH);
  delay(BUZZER_DURATION);
  digitalWrite(PIN_BUZZER, LOW);
  setLEDs(true, false, false);
}

// ============================================================
// CORE 0 TASK — continuous camera capture + classify
// ============================================================
void cameraTask(void* pvParameters) {
  DBG.println("[Core0] Camera task started.");

  for (;;) {
    // Skip during cooldown
    if ((millis() - lastAlertTime) < COOLDOWN_MS) {
      vTaskDelay(pdMS_TO_TICKS(500));
      continue;
    }

    // Try to take the mutex. If the servo is moving, we wait or skip 
    // to avoid blurry images and power spikes!
    if (xSemaphoreTake(xServoMutex, pdMS_TO_TICKS(100)) == pdTRUE) {
      
      // CRITICAL FIX FOR FB-OVF: Flush the main buffer queue first 
      // This discards any stale frames that piled up during delays
      camera_fb_t* flush_fb = esp_camera_fb_get();
      if (flush_fb) {
        esp_camera_fb_return(flush_fb);
      }

      setLEDs(false, true, false);  // Yellow = processing
      
      String result = captureAndClassify();
      DBG.printf("[Core0] Result: %s\n", result.c_str());

      // Release the mutex immediately after capture so the Servo can use it
      xSemaphoreGive(xServoMutex);

      if (result == "monkey") {
        monkeyDetected = true;
        lastAlertTime  = millis();
        triggerAlarm();
        monkeyDetected = false;
      } else {
        setLEDs(true, false, false);  // Back to green
      }
    }

    // Wait before next capture
    vTaskDelay(pdMS_TO_TICKS(CAPTURE_INTERVAL_MS));
  }
}

// ============================================================
// CORE 1 TASK — PIR polling + servo rotation
// ============================================================
// ============================================================
// CORE 1 TASK — 180-Degree Flip-Flop State Machine
// ============================================================
void pirTask(void* pvParameters) {
  DBG.println("[Core1] PIR task started.");
  
  // State variable: true = Facing Zone A, false = Facing Zone B
  static bool facingZoneA = true; 

  // Set initial physical startup position safely using the mutex
  if (xSemaphoreTake(xServoMutex, portMAX_DELAY) == pdTRUE) {
    cameraServo.write(facingZoneA ? SERVO_POS_A : SERVO_POS_B);
    xSemaphoreGive(xServoMutex);
  }

  for (;;) {
    // Check if the sensor detects an intruder in the current "blind spot"
    if (digitalRead(PIN_PIR) == HIGH) {
      DBG.println("[Core1] Motion detected behind camera! Executing 180° flip...");

      // Acquire mutex so the camera pipeline pauses and stays safe during rotation
      if (xSemaphoreTake(xServoMutex, pdMS_TO_TICKS(200)) == pdTRUE) {
        
        // Toggle our state to look at the opposite zone
        facingZoneA = !facingZoneA;
        int targetAngle = facingZoneA ? SERVO_POS_A : SERVO_POS_B;

        // Perform the sweep
        cameraServo.write(targetAngle);
        vTaskDelay(pdMS_TO_TICKS(SERVO_SETTLE_MS)); // Wait for physical arm to arrive

        xSemaphoreGive(xServoMutex); // Hand control back to Core 0

        // ─── THE NON-NEGOTIABLE BLIND WINDOW ───
        // The sensor just swept across the room, so its output pin is guaranteed HIGH.
        // We force Core 1 to ignore it until the motion signal naturally clears out.
        DBG.println("[Core1] Entering blinding window to clear swing false-positives...");
        
        vTaskDelay(pdMS_TO_TICKS(4000)); // 4-second baseline cooldown for the hardware
        
        while (digitalRead(PIN_PIR) == HIGH) {
          vTaskDelay(pdMS_TO_TICKS(200)); // Actively hold until the hardware pin drops LOW
        }
        
        DBG.printf("[Core1] Monitoring resumed. Now guarding Zone %s\n", facingZoneA ? "A" : "B");
      }
    }
    vTaskDelay(pdMS_TO_TICKS(100)); // Small poll delay to yield CPU time
  }
}

// ── setup() ───────────────────────────────────────────────────
void setup() {
  DBG.begin(115200);
  delay(500);
  DBG.println("\n[SYS] ITT569 v4 — dual-core starting...");

  pinMode(PIN_PIR,        INPUT);
  pinMode(PIN_BUZZER,     OUTPUT);
  pinMode(PIN_LED_GREEN,  OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED,    OUTPUT);
  digitalWrite(PIN_BUZZER,     LOW);
  setLEDs(false, false, false);

  // Servo
  cameraServo.attach(PIN_SERVO, 500, 2400);
  cameraServo.write(SERVO_POS_A);
  delay(300);
  DBG.println("[SYS] Servo OK");

  // Camera
  DBG.println("[SYS] Initialising camera...");
  if (!initCamera()) {
    DBG.println("[SYS] FATAL: Camera failed.");
    while (true) {
      setLEDs(false, false, true); delay(300);
      setLEDs(false, false, false); delay(300);
    }
  }

  // WiFi
  connectWiFi();

  // Mutex
  xServoMutex = xSemaphoreCreateMutex();

  // Launch tasks on specific cores
  xTaskCreatePinnedToCore(
    cameraTask,         // function
    "CameraTask",       // name
    8192,               // stack size (bytes)
    NULL,               // parameters
    1,                  // priority
    &cameraTaskHandle,  // handle
    0                   // Core 0
  );

  xTaskCreatePinnedToCore(
    pirTask,
    "PIRTask",
    4096,
    NULL,
    1,
    &pirTaskHandle,
    1                   // Core 1
  );

  setLEDs(true, false, false);
  DBG.println("[SYS] Both tasks running. System ready.");
}

// loop() is empty — both tasks handle everything
void loop() {
  vTaskDelay(pdMS_TO_TICKS(1000));
}
