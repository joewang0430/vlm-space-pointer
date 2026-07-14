// Aim-then-measure test: this is the actual usage pattern for the
// project (move servo to a position, let it settle, THEN read
// distance) rather than continuous simultaneous use of both I2C
// devices. Moves between two positions, measuring distance at each.

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <VL53L1X.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();
VL53L1X sensor;

const int SERVO_CHANNEL = 8;
const int SERVO_FREQ = 50;
const uint16_t PULSE_A = 150;
const uint16_t PULSE_B = 350;

const int SENSOR_SHUT_PIN = 9;

void resetSensor() {
  pinMode(SENSOR_SHUT_PIN, OUTPUT);
  digitalWrite(SENSOR_SHUT_PIN, LOW);
  delay(10);
  digitalWrite(SENSOR_SHUT_PIN, HIGH);
  delay(10);  // datasheet boot time is ~1.2ms, pad it generously
}

void moveServoTo(uint16_t pulse) {
  pwm.setPWM(SERVO_CHANNEL, 0, pulse);
}

// Manual timeout wrapper -- the library's own blocking read() timeout
// may not be configured, so poll dataReady() ourselves with a hard cap.
int readDistanceWithTimeout(unsigned long timeout_ms) {
  unsigned long start = millis();
  while (!sensor.dataReady()) {
    if (millis() - start > timeout_ms) {
      Serial.println("  dataReady() timed out");
      return -1;
    }
  }
  return sensor.read(false);  // non-blocking read now that data is ready
}

void setup() {
  Serial.begin(9600);
  delay(500);
  Serial.println("setup starting");

  Wire.begin();
  Wire.setWireTimeout(25000, true);

  // VL53L1X FIRST, before touching PCA9685 at all.
  bool sensorReady = false;
  for (int attempt = 1; attempt <= 10 && !sensorReady; attempt++) {
    resetSensor();
    Serial.print("VL53L1X init attempt ");
    Serial.println(attempt);
    sensorReady = sensor.init();
    if (!sensorReady) {
      delay(200);
    }
  }

  if (!sensorReady) {
    Serial.println("VL53L1X not found after 10 attempts -- check wiring");
    while (1) {}
  }
  sensor.setDistanceMode(VL53L1X::Long);
  sensor.setMeasurementTimingBudget(50000);
  sensor.startContinuous(50);
  Serial.println("VL53L1X ready");

  // PCA9685 AFTER VL53L1X is already up and running.
  Serial.println("testing distance BEFORE pwm.begin()");
  int before = readDistanceWithTimeout(1000);
  Serial.print("distance before pwm.begin() (mm): ");
  Serial.println(before);

  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);
  delay(10);
  Serial.println("PCA9685 ready (setPWM NOT called yet)");

  int afterBegin = readDistanceWithTimeout(1000);
  Serial.print("distance after pwm.begin(), before any setPWM (mm): ");
  Serial.println(afterBegin);
}

void loop() {
  delay(2000);
}
