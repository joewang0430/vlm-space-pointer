// Aim control: combines pan servo positioning, laser on/off, and TF-Luna
// distance reading under one serial protocol.
//
// Serial commands (newline-terminated):
//   "1"            -> laser ON
//   "0"            -> laser OFF
//   "D"            -> read one TF-Luna distance sample, reply "DIST:<cm>"
//                      (or "DIST:TIMEOUT" if no valid frame arrives in time)
//   any other number (e.g. "217") -> move pan servo to that PCA9685 pulse value
//
// TF-Luna wiring: pin1=5V, pin2=RXD->D3, pin3=TXD->D2, pin4=GND.
// Read over SoftwareSerial since the hardware UART is tied up by USB/PC
// comms. SoftwareSerial at TF-Luna's default 115200 baud drops/corrupts a
// meaningful fraction of frames (a known SoftwareSerial limitation) --
// readDistanceCm() just discards checksum failures and waits for the next
// valid frame rather than reconfiguring the sensor's baud rate.

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <SoftwareSerial.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

const int SERVO_CHANNEL = 8;
const int SERVO_FREQ = 50;
const int MOSFET_SIGNAL_PIN = 8;

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

  pinMode(MOSFET_SIGNAL_PIN, OUTPUT);
  digitalWrite(MOSFET_SIGNAL_PIN, LOW);

  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);
  delay(10);

  Serial.println("ready");
}

void loop() {
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    if (line == "1") {
      digitalWrite(MOSFET_SIGNAL_PIN, HIGH);
      Serial.println("LASER ON");
    } else if (line == "0") {
      digitalWrite(MOSFET_SIGNAL_PIN, LOW);
      Serial.println("LASER OFF");
    } else if (line == "D") {
      int distance_cm = readDistanceCm();
      if (distance_cm >= 0) {
        Serial.print("DIST:");
        Serial.println(distance_cm);
      } else {
        Serial.println("DIST:TIMEOUT");
      }
    } else {
      int pulse = line.toInt();
      if (pulse > 0) {
        pwm.setPWM(SERVO_CHANNEL, 0, pulse);
        Serial.print("MOVED TO ");
        Serial.println(pulse);
      }
    }
  }
}
