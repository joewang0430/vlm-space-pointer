"""Careful, slow calibration sweep -- every frame is saved, nothing is
trusted without a human looking at the image afterward.
"""

import time

import cv2
import serial

PULSES_TO_TEST = [280, 310, 340, 370, 400, 430]


def main():
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

    with serial.Serial("COM3", 9600, timeout=2) as arduino:
        time.sleep(2)
        print("banner:", arduino.readline().decode(errors="replace").strip())

        for pulse in PULSES_TO_TEST:
            arduino.write(f"{pulse}\n".encode())
            time.sleep(0.3)
            print(f"pulse {pulse} ack:", arduino.readline().decode(errors="replace").strip())
            time.sleep(0.8)  # let it settle

            arduino.write(b"1\n")
            time.sleep(0.3)
            print("  laser on ack:", arduino.readline().decode(errors="replace").strip())
            time.sleep(0.3)

            ok, frame = cap.read()
            print(f"  frame captured: {ok}")
            if ok:
                cv2.imwrite(f"captures/careful_pulse_{pulse}.jpg", frame)

            arduino.write(b"0\n")
            time.sleep(0.3)
            print("  laser off ack:", arduino.readline().decode(errors="replace").strip())
            time.sleep(0.5)

    cap.release()


if __name__ == "__main__":
    main()
