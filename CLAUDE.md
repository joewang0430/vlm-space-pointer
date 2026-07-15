# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Status
Core pipeline complete and demonstrated end-to-end (2026-07-15): `aim_verify_loop.py` runs the full VLM-guided aim -> verify -> correct -> measure closed loop against a live target description passed as a CLI argument, e.g. `.venv/Scripts/python.exe aim_verify_loop.py the Pepsi cola bottle`. It captures an initial frame, asks the VLM for a rough target pixel location, converts that to a servo pulse via `pixel_to_angle.py`, fires the laser, then repeatedly re-captures and asks the VLM a qualitative left/right/on-target question, nudging the servo with an adaptive step size until it confirms on-target -- at which point it triggers a TF-Luna distance reading over the same Arduino connection and prints the result. Firmware is `arduino/aim_control/aim_control.ino` (single sketch handling servo pulse, laser on/off, and `"D"`-triggered distance read). Python venv is at `.venv/` (create with `python -m venv .venv`; install deps with `.venv/Scripts/pip.exe install -r requirements.txt`). Older standalone test scripts (`camera_test.py`, `serial_test.py`, `vlm_test.py`, etc.) remain at the repo root for isolated module testing; see the **Current Development Rule** section for the full list.

## Project Name
VLM-Guided Physical Pointer System

## Core Idea
This project builds a low-cost physical pointing system driven by a vision-language model.

The system observes a tabletop scene through a webcam. Given a natural language command such as "point to the cup on the table", the backend sends the image to a VLM. The VLM estimates the target object's location and the backend converts it into rotation angles. A pan (and eventually tilt/Z) rotation stage aims a laser at the target. A second photo is taken and sent back to the VLM to verify the laser dot actually landed on the correct object; if not, the angle is corrected and re-verified. Once verified, a rangefinder module mounted co-aligned with the laser (same aim point) is triggered to measure distance. The combination of the verified aim angle(s) and the measured distance gives the target's position without needing to physically reach or touch it.

## What This Project Is
- A tabletop object localization and physical pointing demo.
- A VLM-in-the-loop closed-loop localization system.
- A low-cost embodied AI prototype.
- A system that connects computer vision, VLM reasoning, Arduino control, and simple hardware motion.

## What This Project Is Not
- Not a full robot arm grasping project.
- Not a manipulation or pick-and-place system.
- Not an end-to-end trained embodied AI model.
- Not a navigation project.
- Not a high-precision industrial robotics system.

## Current Hardware
Full specs and wiring plans live in `docs/hardware_inventory.md` — that file is the source of truth for exact part numbers, voltages, and pin connections. Summary of what's actually on hand:
- Windows laptop, Arduino UNO R3, EMEET SmartCam C960 USB webcam
- Rotation: 2x 25KG 270° servo motors, driven via 2x PCA9685 16-channel PWM drivers (I2C)
- Laser: 650nm / 5V / 5mW dot laser module, switched via one of 5x MOSFET trigger modules
- Distance: **TF-Luna LiDAR (UART)** — ordered 2026-07-12, primary rangefinder. Chosen specifically because it talks UART, not I2C, so it can't collide with the PCA9685's I2C bus.
- Distance (deprioritized): 4x VL53L1X ToF sensors (I2C) — works fine in isolation but proved unreliable sharing the I2C bus with the PCA9685 (intermittent init/read failures, occasional corrupted readings) even after fixing two real code bugs along the way. Not pursued further; see `docs/hardware_inventory.md` § Distance Sensors for the full writeup.
- Power: 12V 10A supply, 3-12V 5A adjustable supply, dedicated 5V/6V servo power, DC barrel connectors
- Deferred: 450mm/1000N/12V linear actuator + 2x 43A H-bridge modules (BTS7960-style) — kept for a possible later "reach and touch" phase, not part of the current design

## Intended Mechanical Design
Distance is obtained via a ToF rangefinder (TF-Luna, UART), not via physically reaching the object — this removes the need for the telescoping arm to touch or approach the target.

- A horizontal (pan) rotation axis, built from a 25KG servo driven through PCA9685, aims the laser at the computed target angle. A vertical (tilt/Z) axis may be added later (a second servo) so the system isn't limited to a flat plane.
- The camera may be mounted on its own rotation axis, or fixed and rely on the laser/pan axis alone — to be decided once the rotation rig is physically built.
- The laser and the TF-Luna are mounted co-aligned (pointing the same direction), so once the laser is confirmed on-target via VLM feedback, the TF-Luna reading at that same orientation gives the distance to that exact point. TF-Luna's blind zone is below 0.2m — keep the mechanical layout so sensor-to-target distance stays above that.
- The **linear actuator / telescopic rod is deferred**. Reason: the actuator (450mm stroke) is heavy enough that mounting it horizontally on a small rotation motor creates too much torque for the motor to handle reliably. Not discarded — could return later as an optional "reach and touch" phase once the pointing + distance system works, but it is out of scope now.

## First Engineering Goal
Do not build the full system immediately.

The first goal is to verify the basic software and hardware pipeline:
1. Capture an image from the webcam. ✅ done
2. Save the image. ✅ done
3. Send the image to a VLM and get back target pixel coordinates (using a coordinate-grid overlay for accuracy). ✅ done
4. Convert a target coordinate into a physical command (pixel → rotation angle). ✅ done — empirical pixel↔pulse calibration in `pixel_to_angle.py`, human-verified against real photos
5. Send command from Python to Arduino over serial. ✅ done — unified protocol (pulse number / `"1"` / `"0"` / `"D"`) in `arduino/aim_control/aim_control.ino`
6. Make one hardware module move safely (pan rotation with the laser). ✅ done — servo, laser, and TF-Luna mounted co-aligned and verified moving/firing/reading together

Closing the loop — re-capture after aiming, send to the VLM to verify the laser dot is on the correct object, correct the angle if not, then trigger the rangefinder to capture distance at the verified angle — ✅ done, implemented in `aim_verify_loop.py`, demonstrated end-to-end 2026-07-15 (Pepsi cola bottle target: converged on-target, measured 196cm). Known limitation, worth documenting rather than chasing further: the VLM's on-target judgment isn't perfectly reliable on small/narrow targets or when the laser dot lands on a busy/dark label (low visual contrast) -- the loop's adaptive step-size correction and a retry-on-invisible-dot check mitigate but don't eliminate this.

## Software Architecture
- Python backend:
  - webcam capture
  - image preprocessing
  - coordinate grid overlay
  - VLM API call
  - serial communication with Arduino
- Arduino firmware:
  - receive serial commands
  - drive the PCA9685 (I2C) to move the pan/tilt servo(s)
  - trigger the laser via the MOSFET module
  - read distance from the TF-Luna (UART)

## Development Environment
- Windows
- VS Code for Python
- Arduino IDE for Arduino firmware
- Python packages likely needed:
  - opencv-python
  - pyserial
  - numpy
  - python-dotenv
  - openai or other VLM API SDK
- Arduino libraries likely needed:
  - Adafruit PWM Servo Driver Library (PCA9685) — installed
  - VL53L1X library (Pololu) — installed, deprioritized along with the sensor (see Current Hardware)
  - TF-Luna: no dedicated library required, just parse its UART frame directly (or use `TFLI2C`/`TFMPlus`-style libraries if switched to I2C mode later, which is not the plan)

## Important Constraints
- Keep the system simple.
- Prioritize a working demo over mechanical elegance.
- Avoid unsafe laser usage.
- Do not power motors directly from Arduino.
- Use external power for motors and common ground with Arduino.
- Build and test one module at a time.

## Current Development Rule
Before writing code, clarify which module is being tested. Test order (per `docs/hardware_inventory.md` § First Safe Testing Order), with current status:
1. camera test — ✅ done
2. Arduino blink test — ✅ done
3. serial communication test — ✅ done
4. MOSFET switch test — ✅ done (tested directly with the real laser, not a placeholder LED — a deliberate call since the user had no spare LED/resistor on hand and the laser is low-power enough to do this safely)
5. PCA9685 + one servo test — ✅ done (`arduino/servo_test/`)
6. (deferred) H-bridge + linear actuator test, short pulses only
7. laser test — ✅ done (`arduino/laser_test/`), verified via the MOSFET module with the real laser
8. rangefinder test — ✅ TF-Luna is the plan (arriving 2026-07-13); VL53L1X was tried first and works standalone but is deprioritized (see Current Hardware)
9. mechanical integration (mount laser + rangefinder co-aligned on the servo, keep an emergency power cutoff accessible) — ✅ done
10. VLM loop — ✅ done. Full aim → verify → correct → measure closed loop implemented in `aim_verify_loop.py`, demonstrated end-to-end 2026-07-15.

Additional software-only steps not tied to a specific hardware arrival: pixel-to-angle calibration math — ✅ done, empirical fit in `pixel_to_angle.py` (see docstring for methodology and valid range).

Known-good test scripts to reuse rather than rewrite:
- `aim_verify_loop.py` — the main closed-loop script (aim -> verify -> correct -> measure), takes the target description as CLI args
- `pixel_to_angle.py` — empirical pixel↔servo-pulse calibration
- `verify_capture.py` — careful frame capture (flushes stale buffer) used to gather calibration data
- `camera_test.py`, `serial_test.py`, `vlm_test.py`, `combined_test.py` (servo sweep + laser toggle together) — standalone module tests, repo root
- `arduino/aim_control/` — current firmware (servo + laser + TF-Luna distance, unified serial protocol); `arduino/{blink_test,serial_test,laser_test,servo_test,combined_test,rangefinder_test,aim_and_measure_test,tfluna_test}/` — earlier standalone module tests, kept for reference