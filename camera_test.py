"""Camera module test: scan available webcams and save one frame from each.

Run this once to figure out which camera index corresponds to the EMEET
C960 (vs. the laptop's built-in camera), then hardcode that index in later
scripts.
"""

import cv2
import os

OUTPUT_DIR = "captures"
MAX_INDEX_TO_SCAN = 5


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    found_any = False

    for index in range(MAX_INDEX_TO_SCAN):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            continue

        ok, frame = cap.read()
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        if not ok:
            print(f"[index {index}] opened but failed to read a frame, skipping")
            continue

        found_any = True
        out_path = os.path.join(OUTPUT_DIR, f"cam_index_{index}.jpg")
        cv2.imwrite(out_path, frame)
        print(f"[index {index}] resolution {width}x{height} -> saved to {out_path}")

    if not found_any:
        print("No usable camera found. Check: camera plugged in, Windows camera privacy setting enabled.")


if __name__ == "__main__":
    main()
