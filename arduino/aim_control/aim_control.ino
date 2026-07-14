// Aim control: combines pan servo positioning and laser on/off under
// one serial protocol.
//
// Serial commands (newline-terminated):
//   "1"            -> laser ON
//   "0"            -> laser OFF
//   any other number (e.g. "217") -> move pan servo to that PCA9685 pulse value

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

const int SERVO_CHANNEL = 8;
const int SERVO_FREQ = 50;
const int MOSFET_SIGNAL_PIN = 8;

void setup() {
  Serial.begin(9600);

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
