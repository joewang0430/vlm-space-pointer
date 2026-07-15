# Hardware Inventory and Wiring Context

## Current Project Goal

Build a low-cost VLM-guided physical pointer system.

The system uses a webcam and VLM to locate a target object on a table. A visible marker, such as a low-power red laser or LED, is used for pointing verification. A simple mechanical device then physically points toward or approaches the target object.

This is not a grasping robot. It only needs to point, align, extend, or stop near the object.

---

## Main Computer

- Windows laptop
- VS Code
- Arduino IDE 2
- Python backend planned
- Claude Code used inside the repo

The Windows laptop handles:
- webcam capture
- image processing
- VLM API call
- serial communication with Arduino

---

## Camera

### Existing camera
- EMEET SmartCam C960 USB webcam

Usage:
- Connected directly to Windows laptop by USB
- Used for tabletop image capture
- First version can use this camera even if it is not manual focus

Known issue:
- It may have auto-focus / auto-exposure
- This may cause image instability when a laser or LED marker appears
- For now, use it first and only replace it if image stability becomes a problem

---

## Microcontroller

### Existing controller
- Arduino UNO R3

Connection:
- Computer to Arduino through USB-B cable
- USB provides serial communication and Arduino logic power

Arduino role:
- Receives commands from Python over Serial
- Controls PWM driver / relay / motor driver / MOSFET module
- Does not directly power motors or actuators

Important:
- Motors and actuators must use external power
- Arduino GND must be connected to external power GND

---

## Servo PWM Driver

### PCA9685 16-channel PWM driver
- Quantity: 2 boards available

Planned use:
- Control multiple servo motors if using servos
- Use I2C from Arduino

Typical wiring:
- Arduino 5V -> PCA9685 VCC
- Arduino GND -> PCA9685 GND
- Arduino A4 -> PCA9685 SDA
- Arduino A5 -> PCA9685 SCL
- External 5V/6V servo power -> PCA9685 V+
- External power GND -> PCA9685 GND

Important:
- PCA9685 VCC is logic power
- PCA9685 V+ is servo power
- Servo power must not come from Arduino 5V

---

## Linear Actuator / Telescopic Rod

### Existing linear actuator
- 18 inch / 450 mm stroke linear actuator
- 1000N
- 14 mm/s
- 12V
- IP54
- Built-in limit switches assumed

Clarification:
- 450 mm is stroke length, not total retracted length
- Retracted length is longer than 450 mm
- Fully extended length equals retracted length + 450 mm

Planned use:
- Forward/backward extension
- Similar to a billiard-cue-like pointing device

Control requirement:
- Needs polarity reversal for extend/retract
- Must be controlled through H-bridge motor driver
- Do not connect directly to Arduino

---

## H-Bridge Motor Driver

### Existing H-bridge modules
- 43A H-Bridge modules, quantity: 2
- BTS7960 or similar high-current H-bridge style module

Planned use:
- Control the 12V linear actuator
- One direction = extend
- Opposite direction = retract
- Stop = no drive / brake depending on wiring and code

Typical wiring concept:
- 12V power supply positive -> H-bridge motor power positive
- 12V power supply negative -> H-bridge motor power GND
- H-bridge output terminals -> linear actuator two motor wires
- Arduino digital pins -> H-bridge control pins
- Arduino GND -> H-bridge GND

Important:
- External 12V power is required
- Common ground with Arduino is required
- First code must move actuator only for short timed pulses
- Do not run full extension/retraction until direction and stop behavior are verified

---

## Rotation Module

Current idea:
- Horizontal rotation module controls direction
- It may be implemented by servo motor, stepper motor, or motorized turntable depending on available hardware

Known available related parts:
- 25KG 270-degree servo motors, quantity: 2
- PCA9685 driver available for servo control

Recommended first approach:
- Use one high-torque servo as horizontal rotation if mechanically possible
- Drive it through PCA9685
- Power it with external 5V/6V supply, not Arduino

### Servo calibration (measured 2026-07-12, PCA9685 channel 8)
- Mechanical extremes: pulse **100** and pulse **520** (12-bit PCA9685 tick values, 50Hz)
- Center: pulse **310**
- Full range spans the servo's rated 270 degrees
- Direction, confirmed matching the camera's view (user observed facing the same way the laser points): **larger pulse -> rotates left -> smaller pixel_x in the image; smaller pulse -> rotates right -> larger pixel_x**. Implemented (sign included) in `pixel_to_angle.py`.

---

## Laser / Visible Marker

### Existing planned marker
- 650 nm red laser module
- 5V
- 5 mW
- Dot laser
- Small 6 mm style module

Usage:
- Used as visible pointing marker
- Can be mounted near the pointer tip or on the moving head

Important safety:
- Do not use strong laser
- Do not point at eyes, people, reflective metal, mirrors, or windows
- Use only brief activation during testing
- Prefer aiming downward toward tabletop

Control:
- Do not power the laser directly from an Arduino IO pin if current is uncertain
- Use MOSFET trigger module or transistor switch

---

## MOSFET Trigger Modules

### Existing MOSFET modules
- 5V-36V trigger MOSFET modules
- 15A normal / 30A max type
- Quantity: 5

Planned use:
- Switch laser or LED marker on/off
- Possibly switch other low-voltage loads

Typical laser wiring concept:
- External 5V positive -> laser positive
- Laser negative -> MOSFET output/load negative
- MOSFET power GND -> external 5V GND
- Arduino digital pin -> MOSFET trigger/input
- Arduino GND -> MOSFET GND

Important:
- Common ground required
- Test first with LED before laser

---

## Distance Sensors

### TF-Luna LiDAR (primary rangefinder, ordered 2026-07-12, arrived and integrated 2026-07-15)
- Single-point ToF LiDAR, range 0.2-8m, 1cm resolution, FOV 2 degrees
- Default interface is UART (I2C possible but not used) -- this is the reason it was chosen
- 5V supply, ships with ready-to-use JST-1.25mm-6Pin cables (male-male and male-to-Dupont), no soldering required
- Blind zone below 0.2m -- confirm actual sensor-to-target distances in the mechanical layout stay above this
- Chosen specifically because it does NOT share the I2C bus with the PCA9685 servo driver, avoiding the reliability problems hit with VL53L1X (see below)
- Wiring (confirmed working): pin1=5V, pin4=GND, **pin3 (TXD) -> Arduino D2**, **pin2 (RXD) -> Arduino D3** -- note TXD/RXD must cross to the Arduino's RX/TX, matching `SoftwareSerial(2, 3)` in code (Arduino's one hardware UART is reserved for USB/PC comms)
- SoftwareSerial at the sensor's default 115200 baud drops/corrupts roughly half of frames -- not a wiring problem, a known SoftwareSerial limitation. Rather than risk an uncertain raw baud-rate-reconfigure command to the sensor, the firmware (`readDistanceCm()` in `arduino/aim_control/aim_control.ino`) just discards checksum failures and retries until a valid frame arrives or a 200ms timeout elapses -- tested stable (zero timeouts over ~120 samples during standalone testing)
- Integrated into `arduino/aim_control/aim_control.ino` behind the `"D"` serial command (replies `DIST:<cm>` or `DIST:TIMEOUT`); `aim_verify_loop.py` calls it once per run, only after the VLM confirms the laser is on-target

### VL53L1X ToF sensors (deprioritized -- see note)
- Quantity: 4
- I2C
- Claimed range around 4 m

Status as of 2026-07-12: works reliably when the ONLY I2C device on the bus (confirmed real distance readings, e.g. 1761mm, 1736mm, 462mm). When sharing the I2C bus with the PCA9685 (servo driver), initialization and/or ranging fails intermittently and non-deterministically (same code, different runs -> sometimes works, sometimes times out, sometimes returns corrupted/impossible values e.g. negative distance). Two real code bugs were found and fixed along the way (Adafruit_PWMServoDriver::begin() silently resets any custom Wire.setClock() -- must reorder if using it; the standalone rangefinder sketch was missing a startContinuous() call), but the underlying non-determinism persisted after both fixes and is most likely a marginal physical connection (hand-soldered header pins / breadboard contact), not something fixable in software. Not pursuing further -- superseded by TF-Luna for the primary distance-sensing role. May be revisited later for a secondary/backup sensor now that the code-level bugs are documented, but is not blocking anything.

Important if VL53L1X is used again:
- Multiple VL53L1X sensors on same I2C bus need address management / XSHUT pins
- Do not use them in the first integration unless needed

---

## Power Supplies

### 12V 10A DC power supply
Planned use:
- Power 12V linear actuator
- Power motor driver / H-bridge motor side

### 3V-12V 5A adjustable power supply
Planned use:
- Testing low-voltage modules
- Could power laser/LED or small motors if voltage is set correctly

### 5V/6V servo power
Need:
- If using high-torque servos, use dedicated 5V/6V high-current power
- Do not power servos from Arduino USB

### DC barrel connectors
- DC 5.5 x 2.1 mm adapters
- Male/female adapters available

Important global power rule:
- Computer USB powers Arduino logic only
- External power powers motors, servos, actuator, laser/LED
- All relevant GNDs must be connected together

---

## Existing High-Level Wiring Plan

### Computer to Arduino
- Windows laptop -> USB-B cable -> Arduino UNO R3
- Used for serial command and Arduino power

### Camera
- EMEET C960 -> USB -> Windows laptop

### Arduino to PCA9685
- 5V -> VCC
- GND -> GND
- A4 -> SDA
- A5 -> SCL

### PCA9685 to Servo
- PCA9685 PWM output -> servo signal
- External servo power -> PCA9685 V+
- Common GND

### Arduino to H-Bridge
- Arduino digital pins -> H-bridge control inputs
- Arduino GND -> H-bridge GND
- External 12V -> H-bridge motor power
- H-bridge motor output -> linear actuator

### Arduino to MOSFET Laser Switch
- Arduino digital pin -> MOSFET trigger
- External 5V -> laser power
- MOSFET switches laser negative side
- Common GND

---

## First Safe Testing Order

Do not test all hardware at once.

1. Camera test only
   - Python + OpenCV captures one image from EMEET C960

2. Arduino test only
   - Upload Blink using Arduino IDE

3. Serial test
   - Python sends simple command to Arduino
   - Arduino replies over Serial

4. LED/MOSFET test
   - Use normal LED first, not laser
   - Test on/off control

5. PCA9685 + one servo test
   - Move one servo slowly between safe angles

6. H-bridge + linear actuator test
   - Use short pulses only
   - Verify extend/retract/stop
   - Do not run full travel at first

7. Laser test
   - Only after MOSFET switching is verified with LED

8. Mechanical integration
   - Mount pointer/laser
   - Mount actuator and rotation module
   - Keep emergency power cutoff accessible

9. VLM loop
   - Only after hardware modules are independently verified

---

## First Development Rule for Claude Code

Do not generate full system code first.

Always ask which test is being run:
- camera_test
- arduino_blink
- serial_test
- led_mosfet_test
- servo_pca9685_test
- actuator_hbridge_test
- laser_test
- vlm_mock_coordinate_test

Start with isolated tests.