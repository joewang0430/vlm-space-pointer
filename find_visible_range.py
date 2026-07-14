"""Finds the range of PCA9685 pulse values for which the laser dot is
actually visible in the camera's current field of view, by sweeping
outward from the center in both directions. Saves every frame so each
detection can be manually reviewed afterward -- the detector has been
wrong before and should not be trusted blindly.
"""

import time

import cv2
import serial

from calibrate_pixel_to_pulse import find_laser_dot

CAMERA_INDEX = 1
PORT = "COM3"
BAUD_RATE = 9600
CENTER_PULSE = 310
STEP = 15
MAX_STEPS = 15  # bounds the search so it can't run past the mechanical limits


def send_command(arduino: serial.Serial, command: str) -> str:
    arduino.write(f"{command}\n".encode())
    time.sleep(0.3)
    return arduino.readline().decode(errors="replace").strip()


def check_pulse(arduino, cap, pulse):
    send_command(arduino, str(pulse))
    time.sleep(0.6)
    send_command(arduino, "1")
    time.sleep(0.3)
    ok, frame = cap.read()
    send_command(arduino, "0")
    if not ok:
        return None, None

    dot = find_laser_dot(frame)

    marked = frame.copy()
    if dot is not None:
        cv2.drawMarker(marked, dot, (0, 255, 0), cv2.MARKER_CROSS, 30, 2)
    cv2.imwrite(f"captures/range_pulse_{pulse}.jpg", marked)

    return dot, frame


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

    with serial.Serial(PORT, BAUD_RATE, timeout=2) as arduino:
        time.sleep(2)
        arduino.readline()

        print(f"checking center pulse {CENTER_PULSE}")
        center_dot, _ = check_pulse(arduino, cap, CENTER_PULSE)
        print(f"  -> {center_dot}")

        print("scanning right (increasing pulse)...")
        last_visible_right = CENTER_PULSE if center_dot else None
        for step in range(1, MAX_STEPS + 1):
            pulse = CENTER_PULSE + step * STEP
            dot, _ = check_pulse(arduino, cap, pulse)
            print(f"  pulse={pulse} -> {dot}")
            if dot:
                last_visible_right = pulse
            elif last_visible_right is not None:
                break

        print("scanning left (decreasing pulse)...")
        last_visible_left = CENTER_PULSE if center_dot else None
        for step in range(1, MAX_STEPS + 1):
            pulse = CENTER_PULSE - step * STEP
            dot, _ = check_pulse(arduino, cap, pulse)
            print(f"  pulse={pulse} -> {dot}")
            if dot:
                last_visible_left = pulse
            elif last_visible_left is not None:
                break

        print(f"\nvisible range so far: [{last_visible_left}, {last_visible_right}]")
        print("All frames saved to captures/range_pulse_*.jpg for manual review.")

    cap.release()


if __name__ == "__main__":
    main()
