"""E2 batch runner: three aiming strategies compared head-to-head on the
same objects with user-anchored ground truth (see docs/experiment_log.md).

Strategies (all share the same VLM initial coordinate estimate step):
  open      -- open-loop regression: aim once at the regressor estimate,
               no correction (pays the full calibration+regression residual).
  halving   -- step-halving heuristic (same logic as aim_verify_loop.py):
               fixed step, halved on direction flip, terminate on on_target.
  bisection -- probabilistic bisection with the E1-measured 3-outcome
               error model; queries the posterior median, fuses on_target,
               re-aims at the posterior median after termination.

Every trial logs to results/e2_<scene>.csv (one row per trial, terminal
error computed against the anchored u*) and saves initial/final frames
under captures/e2/<scene>/ for the human hit-rate review.

OBJECTS must be filled in with user-anchored u* values before running.
Usage: .venv/Scripts/python.exe e2_closed_loop.py <scene_label>
"""

import csv
import json
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
    ask_vlm_target_location,
    clamp_pulse,
    draw_coordinate_grid,
    get_fresh_frame,
    send_command,
)
from pixel_to_angle import pixel_to_servo_pulse
from probabilistic_bisection import ProbabilisticBisection

load_dotenv()

# (label, VLM target description, anchored u*, PB curve class)
# u* values are anchored per scene by the user's own eyes -- fill in
# before each scene's run. PB curve class picks which E1 psychometric
# fit the bisection strategy uses: "bear" (large/plain), "folder"
# (large/high-contrast), "bottle" (small/narrow).
OBJECTS = [
    # ("bear", "the polar bear plush toy", 331, "bear"),
]

STRATEGIES = ["open", "halving", "bisection"]
REPS = 8
MAX_ITERATIONS = 16
INITIAL_STEP = 15
MIN_STEP = 3

CSV_FIELDS = [
    "timestamp", "scene", "object", "strategy", "rep",
    "initial_estimate_x", "initial_pulse", "u_star",
    "final_pulse", "terminal_error", "iterations",
    "stop_reason", "history", "initial_image", "final_image",
]


def capture(cap, path, grid=False):
    ok, frame = get_fresh_frame(cap)
    if not ok:
        raise RuntimeError("camera read failed")
    if grid:
        frame = draw_coordinate_grid(frame)
    cv2.imwrite(path, frame)
    return frame


def initial_estimate(client, cap, target, img_path):
    frame = capture(cap, img_path, grid=True)
    h, w = frame.shape[:2]
    coords = ask_vlm_target_location(client, img_path, target, w, h)
    return int(coords["x"])


def query_vlm(client, cap, arduino, target, img_path):
    """Aim is already set; fire laser, capture, ask, laser off."""
    send_command(arduino, "1")
    time.sleep(0.3)
    frame_path = img_path
    capture(cap, frame_path)
    send_command(arduino, "0")
    return ask_vlm_direction(client, frame_path, target)


def run_open(client, cap, arduino, target, pulse0, img_dir, tag):
    send_command(arduino, str(pulse0))
    time.sleep(1)
    final_img = f"{img_dir}/{tag}_final.jpg"
    send_command(arduino, "1")
    time.sleep(0.3)
    capture(cap, final_img)
    send_command(arduino, "0")
    return pulse0, 1, "open_loop", [], final_img


def run_halving(client, cap, arduino, target, pulse0, img_dir, tag):
    pulse = pulse0
    step = INITIAL_STEP
    last_dir = None
    history = []
    final_img = None
    stop = "max_iters"
    send_command(arduino, str(pulse))
    time.sleep(1)
    for it in range(1, MAX_ITERATIONS + 1):
        final_img = f"{img_dir}/{tag}_iter{it}.jpg"
        r = query_vlm(client, cap, arduino, target, final_img)
        history.append({"pulse": pulse, "dir": r.get("target_direction"),
                        "on": r.get("on_target"), "vis": r.get("laser_visible")})
        if not r.get("laser_visible", False):
            stop = "invisible"
            break
        if r.get("on_target", False) and r.get("confidence") != "low":
            stop = "on_target"
            break
        d = r.get("target_direction")
        if d not in ("left", "right"):
            stop = "unclear"
            break
        if last_dir is not None and d != last_dir:
            step = max(MIN_STEP, step // 2)
        last_dir = d
        pulse = clamp_pulse(pulse + (abs(step) if d == "left" else -abs(step)))
        send_command(arduino, str(pulse))
        time.sleep(1)
    return pulse, len(history), stop, history, final_img


def run_bisection(client, cap, arduino, target, pulse0, curve_class, img_dir, tag):
    pb = ProbabilisticBisection(curve_class)
    pb.warm_start(pulse0, sigma=6.0)
    history = []
    final_img = None
    stop = "max_iters"
    for it in range(1, MAX_ITERATIONS + 1):
        pulse = pb.next_query()
        send_command(arduino, str(pulse))
        time.sleep(1)
        final_img = f"{img_dir}/{tag}_iter{it}.jpg"
        r = query_vlm(client, cap, arduino, target, final_img)
        out = ("on_target" if r.get("on_target", False) and r.get("confidence") != "low"
               else r.get("target_direction") if r.get("laser_visible", False)
               else "invisible")
        history.append({"pulse": pulse, "out": out})
        if out in ("left", "right", "on_target"):
            pb.update(pulse, out)
        if out == "on_target":
            stop = "on_target"
            break
        if out == "invisible" and it > 1:
            stop = "invisible"
            break
    final_pulse = pb.estimate()
    send_command(arduino, str(final_pulse))
    time.sleep(1)
    # capture the true final state at the re-aimed pulse
    send_command(arduino, "1")
    time.sleep(0.3)
    final_img2 = f"{img_dir}/{tag}_final.jpg"
    capture(cap, final_img2)
    send_command(arduino, "0")
    return final_pulse, len(history), stop, history, final_img2


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    scene = sys.argv[1]
    if not OBJECTS:
        print("OBJECTS is empty -- fill in anchored u* values first (see docstring)")
        return

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set.")
        return
    client = OpenAI(api_key=api_key)

    img_dir = f"captures/e2/{scene}"
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs("results", exist_ok=True)
    csv_path = f"results/e2_{scene}.csv"
    write_header = not os.path.exists(csv_path)

    cells = [(obj, strat, rep)
             for obj in OBJECTS for strat in STRATEGIES for rep in range(1, REPS + 1)]
    random.shuffle(cells)
    print(f"scene {scene}: {len(cells)} trials")

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    with serial.Serial(PORT, BAUD_RATE, timeout=2) as arduino, \
         open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        time.sleep(2)
        arduino.readline()

        for i, ((label, desc, u_star, curve), strat, rep) in enumerate(cells, 1):
            tag = f"{label}_{strat}_r{rep}"
            init_img = f"{img_dir}/{tag}_initial.jpg"
            try:
                x0 = initial_estimate(client, cap, desc, init_img)
                pulse0 = pixel_to_servo_pulse(x0)
                if strat == "open":
                    fp, iters, stop, hist, fimg = run_open(
                        client, cap, arduino, desc, pulse0, img_dir, tag)
                elif strat == "halving":
                    fp, iters, stop, hist, fimg = run_halving(
                        client, cap, arduino, desc, pulse0, img_dir, tag)
                else:
                    fp, iters, stop, hist, fimg = run_bisection(
                        client, cap, arduino, desc, pulse0, curve, img_dir, tag)
            except Exception as e:
                print(f"[{i}/{len(cells)}] {tag} FAILED: {e}")
                send_command(arduino, "0")
                continue

            err = abs(fp - u_star)
            writer.writerow({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "scene": scene, "object": label, "strategy": strat, "rep": rep,
                "initial_estimate_x": x0, "initial_pulse": pulse0, "u_star": u_star,
                "final_pulse": fp, "terminal_error": err, "iterations": iters,
                "stop_reason": stop, "history": json.dumps(hist),
                "initial_image": init_img, "final_image": fimg,
            })
            f.flush()
            print(f"[{i}/{len(cells)}] {tag}: err={err} iters={iters} stop={stop}")

    cap.release()
    print(f"done -- {csv_path}")


if __name__ == "__main__":
    main()
