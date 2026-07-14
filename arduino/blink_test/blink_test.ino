// Blink test: verifies the toolchain (Arduino IDE / arduino-cli) can
// compile and upload to the board, and that the board itself is alive.
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
  delay(500);
}
