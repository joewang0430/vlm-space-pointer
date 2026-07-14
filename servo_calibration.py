"""Servo calibration: send one pulse value, the Arduino (and PCA9685)
holds the servo there so the real-world angle can be measured by hand
after this script exits (PCA9685 keeps outputting the PWM signal on
its own once set).

Usage: python servo_calibration.py <pulse_value>
"""

import sys
import time
import serial

PORT = "COM3"
BAUD_RATE = 9600


def main():
    if len(sys.argv) != 2:
        print("usage: servo_calibration.py <pulse_value>")
        return

    pulse = sys.argv[1]

    with serial.Serial(PORT, BAUD_RATE, timeout=2) as arduino:
        time.sleep(2)
        arduino.readline()  # discard the "ready" banner
        arduino.write((pulse + "\n").encode())
        time.sleep(0.3)
        print(arduino.readline().decode(errors="replace").strip())


if __name__ == "__main__":
    main()
