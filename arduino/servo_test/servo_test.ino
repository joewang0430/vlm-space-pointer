// PCA9685 + one servo test: sweeps the servo on channel 8 slowly back
// and forth within a conservative mid-range, to verify I2C control
// works before attempting full-range motion.
//
// Debug build: scans the I2C bus at startup and prints each pulse value
// it sends, so a serial monitor shows whether the PCA9685 is actually
// being reached and commanded.

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

const int SERVO_CHANNEL = 8;
const int SERVO_FREQ = 50;

// Conservative mid-range pulse values (out of a typical 102-512 full
// range) -- avoids driving into the servo's mechanical end stops until
// the real safe range is known.
const uint16_t PULSE_MIN = 150;
const uint16_t PULSE_MAX = 350;

void scanI2C() {
  Serial.println("Scanning I2C bus...");
  int found = 0;
  for (uint8_t address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    uint8_t error = Wire.endTransmission();
    if (error == 0) {
      Serial.print("  found device at 0x");
      Serial.println(address, HEX);
      found++;
    }
  }
  if (found == 0) {
    Serial.println("  no I2C devices found -- check VCC/GND/SDA/SCL wiring");
  }
}

void setup() {
  Serial.begin(9600);
  delay(500);
  Wire.begin();
  Wire.setClock(50000);  // slow down I2C to improve breadboard signal margin
  Wire.setWireTimeout(25000, true);
  scanI2C();

  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);
  delay(10);
  Serial.println("PCA9685 initialized, starting sweep");
}

void loop() {
  for (uint16_t pulse = PULSE_MIN; pulse <= PULSE_MAX; pulse += 2) {
    pwm.setPWM(SERVO_CHANNEL, 0, pulse);
    Serial.print("pulse: ");
    Serial.println(pulse);
    delay(15);
  }
  delay(500);

  for (uint16_t pulse = PULSE_MAX; pulse >= PULSE_MIN; pulse -= 2) {
    pwm.setPWM(SERVO_CHANNEL, 0, pulse);
    Serial.print("pulse: ");
    Serial.println(pulse);
    delay(15);
  }
  delay(500);
}
