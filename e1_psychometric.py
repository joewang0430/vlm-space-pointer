"""E1: psychometric measurement of the VLM left/right comparator.

Protocol: the anchor pulse u* (the pulse that centers the laser dot on
the target, established beforehand and verified by the user's own eyes)
is passed on the command line -- ground truth therefore comes from
construction, not from any automated detection. The script then visits
u = u* + offset for every offset in OFFSETS x both signs x REPS
repetitions, in randomized order. For each query it moves the servo,
briefly fires the laser, captures a fresh frame, and asks the VLM the
same left/right question used by the closed loop (imported from
aim_verify_loop so E1 measures exactly the comparator the loop uses).
The correct answer is known from the sign of the offset: a positive
offset moves the dot LEFT of the target (larger pulse -> smaller
pixel_x), so the target is to the RIGHT of the dot.

Each query is logged to results/e1_<label>.csv and its frame saved
under captures/e1/<label>/ so every answer can be audited afterwards.

Usage:
  .venv/Scripts/python.exe e1_psychometric.py <u_star> <label> <target description...>
e.g.
  .venv/Scripts/python.exe e1_psychometric.py 312 polar_bear the polar bear plush toy
"""

import csv
import os
import random
import sys
import time
from datetime import datetime

import cv2
import serial
from dotenv import load_dotenv
from openai import OpenAI

from aim_verify_loop import (
    BAUD_RATE,
    CAMERA_INDEX,
    PORT,
    ask_vlm_direction,
    get_fresh_frame,
    send_command,
)
from pixel_to_angle import SERVO_PULSE_MAX, SERVO_PULSE_MIN

load_dotenv()

OFFSETS = [1, 2, 3, 5, 8, 12, 18, 25]  # pulse units, log-ish spacing
REPS = 12  # repetitions per (offset, sign) point
SETTLE_S = 1.0  # servo settle time before capture

CSV_FIELDS = [
    "timestamp", "target", "u_star", "offset", "pulse",
    "ground_truth", "vlm_direction", "correct",
    "laser_visible", "on_target", "confidence", "reasoning", "image",
]


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return
    u_star = int(sys.argv[1])
    label = sys.argv[2]
    target = " ".join(sys.argv[3:]).strip()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set.")
        return
    client = OpenAI(api_key=api_key)

    # Refuse to run if any query would leave the mechanically safe range.
    worst_low = u_star - max(OFFSETS)
    worst_high = u_star + max(OFFSETS)
    if worst_low < SERVO_PULSE_MIN or worst_high > SERVO_PULSE_MAX:
        print(f"u_star={u_star} with max offset {max(OFFSETS)} would leave "
              f"safe pulse range [{SERVO_PULSE_MIN}, {SERVO_PULSE_MAX}] -- aborting")
        return

    queries = [(off * sign, rep)
               for off in OFFSETS for sign in (+1, -1) for rep in range(REPS)]
    random.shuffle(queries)
    print(f"target: {target} | u*={u_star} | {len(queries)} queries")

    os.makedirs("results", exist_ok=True)
    img_dir = f"captures/e1/{label}"
    os.makedirs(img_dir, exist_ok=True)
    csv_path = f"results/e1_{label}.csv"
    write_header = not os.path.exists(csv_path)

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    n_correct = 0
    n_answered = 0

    with serial.Serial(PORT, BAUD_RATE, timeout=2) as arduino, \
         open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        time.sleep(2)
        arduino.readline()  # discard "ready"

        for i, (offset, rep) in enumerate(queries, 1):
            pulse = u_star + offset
            # positive offset -> larger pulse -> dot LEFT of target ->
            # target is to the RIGHT of the dot
            ground_truth = "right" if offset > 0 else "left"

            send_command(arduino, str(pulse))
            time.sleep(SETTLE_S)
            send_command(arduino, "1")
            time.sleep(0.3)

            ok, frame = get_fresh_frame(cap)
            send_command(arduino, "0")  # laser off right after capture
            if not ok:
                print(f"[{i}/{len(queries)}] camera read failed, skipping")
                continue

            image_path = f"{img_dir}/q{i:03d}_off{offset:+d}_rep{rep}.jpg"
            cv2.imwrite(image_path, frame)

            try:
                result = ask_vlm_direction(client, image_path, target)
            except Exception as e:
                print(f"[{i}/{len(queries)}] VLM call failed: {e} -- skipping")
                continue

            answer = result.get("target_direction")
            correct = (answer == ground_truth)
            if answer in ("left", "right"):
                n_answered += 1
                n_correct += int(correct)

            writer.writerow({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "target": target,
                "u_star": u_star,
                "offset": offset,
                "pulse": pulse,
                "ground_truth": ground_truth,
                "vlm_direction": answer,
                "correct": correct,
                "laser_visible": result.get("laser_visible"),
                "on_target": result.get("on_target"),
                "confidence": result.get("confidence"),
                "reasoning": result.get("reasoning"),
                "image": image_path,
            })
            f.flush()
            print(f"[{i}/{len(queries)}] offset={offset:+d} truth={ground_truth} "
                  f"vlm={answer} {'OK' if correct else 'X'}")

        send_command(arduino, str(u_star))  # park back on target

    cap.release()
    print(f"\ndone: {n_correct}/{n_answered} correct among answered queries")
    print(f"log: {csv_path}")


if __name__ == "__main__":
    main()
