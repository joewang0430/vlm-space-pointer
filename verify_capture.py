"""Fixes the likely bug in earlier scripts: cv2.VideoCapture can return
a stale buffered frame if you call read() only once right after an
event (like turning the laser on). This flushes several frames first
to force a fresh, live one before saving.
"""

import time

import cv2
import serial

PULSES_TO_TEST = [260, 270, 280, 290, 300, 310, 320, 330, 340, 350, 360]


def get_fresh_frame(cap, flush_count=5):
    for _ in range(flush_count):
        cap.read()
    ok, frame = cap.read()
    return ok, frame


def main():
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

    with serial.Serial("COM3", 9600, timeout=2) as arduino:
        time.sleep(2)
        print("banner:", arduino.readline().decode(errors="replace").strip())

        for pulse in PULSES_TO_TEST:
            arduino.write(f"{pulse}\n".encode())
            time.sleep(0.3)
            print(f"pulse {pulse} ack:", arduino.readline().decode(errors="replace").strip())
            time.sleep(1.0)  # let it settle

            arduino.write(b"1\n")
            time.sleep(0.3)
            print("  laser on ack:", arduino.readline().decode(errors="replace").strip())
            time.sleep(0.5)  # extra margin before capturing

            ok, frame = get_fresh_frame(cap)
            print(f"  frame captured: {ok}")
            if ok:
                path = f"captures/verify/pulse_{pulse}.jpg"
                cv2.imwrite(path, frame)
                print(f"  saved: {path}")

            time.sleep(1.0)  # keep laser on a bit longer so it's easy to see by eye

            arduino.write(b"0\n")
            time.sleep(0.3)
            print("  laser off ack:", arduino.readline().decode(errors="replace").strip())
            time.sleep(0.5)

    cap.release()


if __name__ == "__main__":
    main()
