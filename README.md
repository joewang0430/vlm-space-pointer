# VLM Robot Pointer

This project builds a low-cost VLM-guided pointing system.

Goal:
Given a camera image and a natural language target such as "the cup on the table",
the system asks a VLM to estimate the target location, aims a laser at it using a
pan (and eventually tilt) rotation stage, and re-checks the photo with the VLM to
verify the laser landed on the right object. Once verified, a rangefinder mounted
co-aligned with the laser measures the distance, giving direction + distance
without needing to physically reach the object.

Current scope:
- No grasping.
- No full robotic manipulation.
- No autonomous navigation.
- No physical reach/touch (the telescoping actuator is deferred — see docs/hardware_inventory.md).
- Only tabletop object localization and physical laser pointing + distance measurement.

Hardware (full specs in docs/hardware_inventory.md):
- Windows laptop
- Arduino UNO R3
- EMEET SmartCam C960 webcam
- Rotation: 25KG 270° servos driven via PCA9685 (pan, and eventually tilt)
- Laser: 650nm 5mW dot laser module, switched via a MOSFET trigger module
- Rangefinder: VL53L1X ToF distance sensor, mounted co-aligned with the laser
- External power supplies (separate from Arduino logic power)
- (Deferred) linear actuator + H-bridge, for a possible later "reach and touch" phase