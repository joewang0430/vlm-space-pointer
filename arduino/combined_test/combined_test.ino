// Combined test: sweeps the pan servo (PCA9685 channel 8) continuously
// while listening for laser on/off commands over serial at the same
// time, so both can be re-verified together after re-wiring.
//
// Serial commands:
//   '1' -> laser ON
//   '0' -> laser OFF

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

const int SERVO_CHANNEL = 8;
const int SERVO_FREQ = 50;
const uint16_t PULSE_MIN = 150;
const uint16_t PULSE_MAX = 350;

const int MOSFET_SIGNAL_PIN = 8;

void checkLaserCommand() {
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

void setup() {
  Serial.begin(9600);

  pinMode(MOSFET_SIGNAL_PIN, OUTPUT);
  digitalWrite(MOSFET_SIGNAL_PIN, LOW);

  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);
  delay(10);
}

void loop() {
  for (uint16_t pulse = PULSE_MIN; pulse <= PULSE_MAX; pulse += 2) {
    pwm.setPWM(SERVO_CHANNEL, 0, pulse);
    checkLaserCommand();
    delay(15);
  }
  delay(200);

  for (uint16_t pulse = PULSE_MAX; pulse >= PULSE_MIN; pulse -= 2) {
    pwm.setPWM(SERVO_CHANNEL, 0, pulse);
    checkLaserCommand();
    delay(15);
  }
  delay(200);
}
