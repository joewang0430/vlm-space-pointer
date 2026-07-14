// VL53L1X rangefinder test: reads distance over I2C and prints it.

#include <Wire.h>
#include <VL53L1X.h>

VL53L1X sensor;

void scanI2C() {
  Serial.println("Scanning I2C bus...");
  for (uint8_t address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    uint8_t error = Wire.endTransmission();
    if (error == 0) {
      Serial.print("  found device at 0x");
      Serial.println(address, HEX);
    }
  }
  Serial.println("scan done");
}

void setup() {
  Serial.begin(9600);
  delay(500);
  Serial.println("setup starting");
  Wire.begin();
  Wire.setWireTimeout(25000, true);  // 25ms timeout, auto-reset the bus on timeout
  scanI2C();
  Serial.println("calling sensor.init()");

  if (!sensor.init()) {
    Serial.println("VL53L1X not found -- check wiring");
    while (1) {}
  }

  sensor.setDistanceMode(VL53L1X::Long);
  sensor.setMeasurementTimingBudget(50000);
  sensor.startContinuous(50);
  Serial.println("VL53L1X ready");
}

void loop() {
  int distance_mm = sensor.read();
  Serial.print("distance_mm: ");
  Serial.println(distance_mm);
  delay(200);
}
