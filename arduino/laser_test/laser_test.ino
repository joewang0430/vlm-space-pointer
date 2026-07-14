// Laser/MOSFET switch test: verifies the Arduino can trigger the MOSFET
// driver module to turn the laser on and off, over serial commands.
// Commands (same protocol as arduino/serial_test):
//   '1' -> laser ON
//   '0' -> laser OFF
//
// Safety: keep activations brief, aim the laser down at the tabletop,
// never at eyes, people, or reflective/mirrored surfaces.

const int MOSFET_SIGNAL_PIN = 8;

void setup() {
  pinMode(MOSFET_SIGNAL_PIN, OUTPUT);
  digitalWrite(MOSFET_SIGNAL_PIN, LOW);
  Serial.begin(9600);
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();

    if (command == '1') {
      digitalWrite(MOSFET_SIGNAL_PIN, HIGH);
      Serial.println("LASER ON");
    } else if (command == '0') {
      digitalWrite(MOSFET_SIGNAL_PIN, LOW);
      Serial.println("LASER OFF");
    }
  }
}
