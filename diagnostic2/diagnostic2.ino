// ============================================================
// ITT569 DIAGNOSTIC v2 — updated for ESP32S3_EYE pin map
// Safe pins only: 14, 21, 45, 46, 47, 48
// ============================================================

#include <ESP32Servo.h>

#define PIN_PIR         14
#define PIN_SERVO       21
#define PIN_BUZZER      47
#define PIN_LED_GREEN   45
#define PIN_LED_YELLOW  46
#define PIN_LED_RED     48

Servo testServo;

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("=== ITT569 DIAGNOSTIC v2 START ===");

  pinMode(PIN_PIR,        INPUT);
  pinMode(PIN_BUZZER,     OUTPUT);
  pinMode(PIN_LED_GREEN,  OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED,    OUTPUT);

  digitalWrite(PIN_BUZZER,     LOW);
  digitalWrite(PIN_LED_GREEN,  LOW);
  digitalWrite(PIN_LED_YELLOW, LOW);
  digitalWrite(PIN_LED_RED,    LOW);

  Serial.println("[TEST] Green LED ON");
  digitalWrite(PIN_LED_GREEN, HIGH); delay(1000);
  digitalWrite(PIN_LED_GREEN, LOW);

  Serial.println("[TEST] Yellow LED ON");
  digitalWrite(PIN_LED_YELLOW, HIGH); delay(1000);
  digitalWrite(PIN_LED_YELLOW, LOW);

  Serial.println("[TEST] Red LED ON");
  digitalWrite(PIN_LED_RED, HIGH); delay(1000);
  digitalWrite(PIN_LED_RED, LOW);

  Serial.println("[TEST] Buzzer ON 500ms");
  digitalWrite(PIN_BUZZER, HIGH); delay(500);
  digitalWrite(PIN_BUZZER, LOW);
  Serial.println("[TEST] Buzzer OFF");

  Serial.println("[TEST] Servo -> 90 centre");
  testServo.attach(PIN_SERVO, 500, 2400);
  testServo.write(90);  delay(1000);
  Serial.println("[TEST] Servo -> 45 left");
  testServo.write(45);  delay(1000);
  Serial.println("[TEST] Servo -> 135 right");
  testServo.write(135); delay(1000);
  Serial.println("[TEST] Servo -> 90 centre");
  testServo.write(90);  delay(500);
  testServo.detach();

  Serial.println("=== DIAGNOSTIC COMPLETE ===");
  Serial.println("Waiting for PIR motion — wave your hand near the sensor...");
}

void loop() {
  if (digitalRead(PIN_PIR) == HIGH) {
    Serial.println("[PIR] Motion detected!");
    digitalWrite(PIN_LED_YELLOW, HIGH);
    delay(200);
    digitalWrite(PIN_LED_YELLOW, LOW);
  }
  delay(100);
}
