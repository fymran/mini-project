// ============================================================
// ITT569 DIAGNOSTIC v3 — CH343 UART bridge fix
// Serial0 used throughout for CH343 hardware UART
// ============================================================

#include <ESP32Servo.h>

#define DBG Serial0

#define PIN_PIR         14
#define PIN_SERVO       21
#define PIN_BUZZER      47
#define PIN_LED_GREEN   45
#define PIN_LED_YELLOW  46
#define PIN_LED_RED     48

Servo testServo;

void setup() {
  DBG.begin(115200);
  delay(500);
  DBG.println("=== ITT569 DIAGNOSTIC v3 START ===");

  pinMode(PIN_PIR,        INPUT);
  pinMode(PIN_BUZZER,     OUTPUT);
  pinMode(PIN_LED_GREEN,  OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED,    OUTPUT);

  digitalWrite(PIN_BUZZER,     LOW);
  digitalWrite(PIN_LED_GREEN,  LOW);
  digitalWrite(PIN_LED_YELLOW, LOW);
  digitalWrite(PIN_LED_RED,    LOW);

  DBG.println("[TEST] Green LED ON");
  digitalWrite(PIN_LED_GREEN, HIGH); delay(1000);
  digitalWrite(PIN_LED_GREEN, LOW);

  DBG.println("[TEST] Yellow LED ON");
  digitalWrite(PIN_LED_YELLOW, HIGH); delay(1000);
  digitalWrite(PIN_LED_YELLOW, LOW);

  DBG.println("[TEST] Red LED ON");
  digitalWrite(PIN_LED_RED, HIGH); delay(1000);
  digitalWrite(PIN_LED_RED, LOW);

  DBG.println("[TEST] Buzzer ON 500ms");
  digitalWrite(PIN_BUZZER, HIGH); delay(500);
  digitalWrite(PIN_BUZZER, LOW);
  DBG.println("[TEST] Buzzer OFF");

  DBG.println("[TEST] Servo -> 90 centre");
  testServo.attach(PIN_SERVO, 500, 2400);
  testServo.write(90);  delay(1000);
  DBG.println("[TEST] Servo -> 45 left");
  testServo.write(45);  delay(1000);
  DBG.println("[TEST] Servo -> 135 right");
  testServo.write(135); delay(1000);
  DBG.println("[TEST] Servo -> 90 centre");
  testServo.write(90);  delay(500);
  testServo.detach();

  DBG.println("=== DIAGNOSTIC COMPLETE ===");
  DBG.println("Waiting for PIR — wave your hand near the sensor...");
}

void loop() {
  if (digitalRead(PIN_PIR) == HIGH) {
    DBG.println("[PIR] Motion detected!");
    digitalWrite(PIN_LED_YELLOW, HIGH);
    delay(200);
    digitalWrite(PIN_LED_YELLOW, LOW);
  }
  delay(100);
}
