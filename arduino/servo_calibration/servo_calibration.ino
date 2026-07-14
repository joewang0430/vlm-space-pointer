// Servo calibration: holds the pan servo at a requested PCA9685 pulse
// value so the real-world angle can be measured by hand.
// Serial command: send a number (e.g. "150") followed by newline to
// move to that pulse value and hold there.

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

const int SERVO_CHANNEL = 8;
const int SERVO_FREQ = 50;

void setup() {
  Serial.begin(9600);
  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);
  delay(10);
  Serial.println("ready -- send a pulse value (e.g. 150) to move and hold");
}

void loop() {
  if (Serial.available() > 0) {
    int pulse = Serial.parseInt();
    if (pulse > 0) {
      pwm.setPWM(SERVO_CHANNEL, 0, pulse);
      Serial.print("holding at pulse ");
      Serial.println(pulse);
    }
  }
}
