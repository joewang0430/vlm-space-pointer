// TF-Luna standalone test: reads distance over UART via SoftwareSerial
// (Arduino's one hardware UART is already used for USB/computer comms)
// and prints it. TF-Luna wiring: pin1=5V, pin2=RXD->D3, pin3=TXD->D2,
// pin4=GND, pin5/6 unused.
//
// TF-Luna outputs a 9-byte frame continuously at its configured rate:
//   0x59 0x59 Dist_L Dist_H Strength_L Strength_H Temp_L Temp_H Checksum
//
// SoftwareSerial at TF-Luna's default 115200 baud drops/corrupts a
// meaningful fraction of frames (a known SoftwareSerial limitation, not
// a wiring problem -- confirmed separately). Rather than risk sending a
// raw command to reconfigure the sensor's baud rate, readDistance()
// just discards checksum failures and waits for the next valid frame --
// at this frame rate, one valid reading arrives within tens of
// milliseconds even with ~50% loss, which is fine for an "aim then
// measure once" use case.

#include <SoftwareSerial.h>

const int LUNA_RX_PIN = 2;  // Arduino D2 -- receives from Luna's TXD (pin 3)
const int LUNA_TX_PIN = 3;  // Arduino D3 -- sends to Luna's RXD (pin 2)

SoftwareSerial lunaSerial(LUNA_RX_PIN, LUNA_TX_PIN);

// Blocks until one valid checksummed frame arrives, or timeout_ms
// elapses (returns -1 on timeout). Discards invalid frames silently.
int readDistanceCm(unsigned long timeout_ms = 200) {
  uint8_t buf[9];
  uint8_t idx = 0;
  unsigned long start = millis();

  while (millis() - start < timeout_ms) {
    if (lunaSerial.available() > 0) {
      uint8_t b = lunaSerial.read();

      if (idx == 0 || idx == 1) {
        if (b == 0x59) {
          buf[idx++] = b;
        } else {
          idx = 0;
        }
      } else {
        buf[idx++] = b;
        if (idx == 9) {
          uint8_t checksum = 0;
          for (int i = 0; i < 8; i++) checksum += buf[i];
          if (checksum == buf[8]) {
            return buf[2] | (buf[3] << 8);
          }
          idx = 0;  // bad frame, keep listening
        }
      }
    }
  }
  return -1;  // timed out without a valid frame
}

void setup() {
  Serial.begin(9600);
  lunaSerial.begin(115200);
  Serial.println("TF-Luna test starting");
}

void loop() {
  int distance_cm = readDistanceCm();
  if (distance_cm >= 0) {
    Serial.print("distance_cm: ");
    Serial.println(distance_cm);
  } else {
    Serial.println("timed out waiting for a valid frame");
  }
  delay(500);
}
