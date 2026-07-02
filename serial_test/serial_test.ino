// ============================================================
// ITT569 SERIAL TEST v2 — CH343 UART bridge fix
// Uses Serial0 which maps to hardware UART0 via CH343
// ============================================================

// CH343 is a hardware UART bridge connected to UART0 (TX/RX pins)
// Serial0 = UART0 = what goes through CH343 to your PC
// Serial  = USB CDC = the other USB-C port (not what you're using)
#define DBG Serial0

void setup() {
  DBG.begin(115200);
  delay(500);
  DBG.println("=== SERIAL TEST v2 OK ===");
  DBG.println("CH343 UART bridge confirmed working.");
  DBG.printf("CPU freq: %d MHz\n", ESP.getCpuFreqMHz());
  DBG.printf("Free heap: %d bytes\n", ESP.getFreeHeap());
  DBG.println("=========================");
}

void loop() {
  DBG.println("[ALIVE] Board running...");
  delay(2000);
}
