"""Empirical pixel<->pulse calibration: moves the servo through several
pulse values, fires the laser at each, and finds the laser dot's pixel
position with classical image processing (not the VLM -- much more
reliable and free). Fits a line through the (pulse, pixel_x) points and
prints the result to paste into pixel_to_angle.py.
"""

import time

import cv2
import numpy as np
import serial

CAMERA_INDEX = 1
PORT = "COM3"
BAUD_RATE = 9600

# Pulse values to sample. Center (310) was found NOT visible in the
# camera's current frame -- pulse 400 was, so scanning around there to
# find where the laser dot actually stays in view.
CALIBRATION_PULSES = [350, 380, 400, 420, 440, 460]


def find_laser_dot(image):
    """Finds the brightest small spot in the image with at least a slight
    red tint (the laser dot is often overexposed to near-white, so redness
    alone is not very discriminating -- brightness is the primary signal).
    Returns (x, y) in pixel coordinates, or None if nothing plausible found.
    """
    b, g, r = cv2.split(image.astype(np.int32))
    redness = r - np.maximum(g, b)
    brightness = (r + g + b) / 3

    # Brightness is the primary signal; redness is just a weak tiebreaker
    # so a plain bright white light source doesn't also qualify.
    candidate_mask = (brightness > 200) & (redness > 3)
    if not np.any(candidate_mask):
        return None

    brightness_masked = np.where(candidate_mask, brightness, -1)
    _, max_val, _, max_loc = cv2.minMaxLoc(brightness_masked.astype(np.float32))
    return max_loc  # (x, y)


def send_command(arduino: serial.Serial, command: str) -> str:
    arduino.write(f"{command}\n".encode())
    time.sleep(0.3)
    return arduino.readline().decode(errors="replace").strip()


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

    samples = []

    with serial.Serial(PORT, BAUD_RATE, timeout=2) as arduino:
        time.sleep(2)
        arduino.readline()  # discard "ready"

        for pulse in CALIBRATION_PULSES:
            print(send_command(arduino, str(pulse)))
            time.sleep(1)  # let the servo settle
            print(send_command(arduino, "1"))  # laser on
            time.sleep(0.3)

            ok, frame = cap.read()
            if not ok:
                print(f"pulse={pulse}: camera read failed, skipping")
                send_command(arduino, "0")
                continue

            dot = find_laser_dot(frame)
            print(send_command(arduino, "0"))  # laser off

            if dot is None:
                print(f"pulse={pulse}: no laser dot found in frame")
                continue

            x, y = dot
            print(f"pulse={pulse} -> laser dot at pixel ({x}, {y})")
            cv2.imwrite(f"captures/calib_pulse_{pulse}.jpg", frame)
            samples.append((pulse, x))

    cap.release()

    if len(samples) < 2:
        print("Not enough samples to fit a line.")
        return

    pulses = np.array([s[0] for s in samples], dtype=float)
    pixel_xs = np.array([s[1] for s in samples], dtype=float)

    # Fit pulse = a * pixel_x + b
    a, b = np.polyfit(pixel_xs, pulses, 1)
    print(f"\nFitted: pulse = {a:.5f} * pixel_x + {b:.2f}")
    print("Paste these into pixel_to_angle.py's calibration if they look sane.")


if __name__ == "__main__":
    main()
