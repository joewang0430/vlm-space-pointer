"""Closed-loop aiming: move the servo toward the VLM's initial pixel
estimate, fire the laser, then repeatedly ask the VLM a simple
left/right/on-target question (not for precise coordinates -- that
proved unreliable) and nudge the servo with an adaptive step size:
shrink the step whenever the requested direction flips (overshoot),
keep it the same when it doesn't.
"""

import base64
import json
import os
import sys
import time

import cv2
import serial
from dotenv import load_dotenv
from openai import OpenAI

from pixel_to_angle import PULSE_PER_PIXEL, SERVO_PULSE_MAX, SERVO_PULSE_MIN, pixel_to_servo_pulse

load_dotenv()

CAMERA_INDEX = 1
PORT = "COM3"
BAUD_RATE = 9600
GRID_SPACING = 40
DEFAULT_TARGET_DESCRIPTION = "the polar bear plush toy"
MAX_ITERATIONS = 16
INITIAL_STEP = 15  # pulse units, matches the calibration sample spacing
MIN_STEP = 3


def get_fresh_frame(cap, flush_count=5):
    """Discards buffered frames so the frame returned reflects the
    camera's current live state (cv2.VideoCapture otherwise can return
    a stale frame from before the laser/servo command took effect)."""
    for _ in range(flush_count):
        cap.read()
    ok, frame = cap.read()
    return ok, frame


def draw_coordinate_grid(image, spacing: int = GRID_SPACING):
    grid = image.copy()
    height, width = grid.shape[:2]
    for x in range(0, width, spacing):
        cv2.line(grid, (x, 0), (x, height), (0, 255, 0), 1)
        cv2.putText(grid, str(x), (x + 2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
    for y in range(0, height, spacing):
        cv2.line(grid, (0, y), (width, y), (0, 255, 0), 1)
        cv2.putText(grid, str(y), (2, y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
    return grid


def ask_vlm_target_location(client: OpenAI, image_path: str, target: str, width: int, height: int) -> dict:
    with open(image_path, "rb") as f:
        image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"The image is {width}x{height} pixels with a coordinate grid: green lines "
                        f"every {GRID_SPACING}px, x labeled along the top, y labeled along the left. "
                        f"Find {target} and return its precise pixel coordinates as JSON: "
                        '{"x": <int>, "y": <int>}.'
                    ),
                },
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ],
        }],
    )
    return json.loads(response.choices[0].message.content)


def ask_vlm_direction(client: OpenAI, image_path: str, target: str) -> dict:
    """Qualitative judgment only -- on_target yes/no, and if no, whether
    the target is left or right of the laser dot. Deliberately NOT
    asking for pixel coordinates, since that proved unreliable.

    Asks for a short "reasoning" field before the verdict (forces the
    model to describe both positions before concluding, which tends to
    catch lazy/loose judgments) and a confidence level -- the caller
    should only trust on_target=true when confidence isn't "low". This
    is a moderate prompt improvement, not a fix for the model's
    underlying visual-precision limits -- expect it to reduce, not
    eliminate, false "on target" calls.
    """
    with open(image_path, "rb") as f:
        image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "There should be a small, bright red/pink laser dot visible in this image. "
                        f"Compare its position to {target}. Strict rule: on_target is true ONLY if "
                        f"the laser dot is directly touching or clearly overlapping {target}'s body "
                        "-- being nearby on the same surface (e.g. the bed, table, floor next to it) "
                        "does NOT count as on_target. Return JSON with these keys, in this order: "
                        '{"reasoning": "<one sentence describing where the laser dot is and where '
                        f'{target} is, and whether they overlap>", "laser_visible": <true/false>, '
                        '"on_target": <true/false>, "confidence": "high"|"medium"|"low", '
                        '"target_direction": "left"|"right"|"unknown"}. '
                        "target_direction is which way the laser dot needs to move to reach "
                        f"{target} (i.e. which side of the laser dot {target} is currently on). "
                        'Set it to "unknown" only if laser_visible is false or on_target is true.'
                    ),
                },
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ],
        }],
    )
    return json.loads(response.choices[0].message.content)


def send_command(arduino: serial.Serial, command: str) -> str:
    arduino.write(f"{command}\n".encode())
    time.sleep(0.3)
    return arduino.readline().decode(errors="replace").strip()


def clamp_pulse(pulse: float) -> int:
    return round(max(SERVO_PULSE_MIN, min(SERVO_PULSE_MAX, pulse)))


def main():
    target = " ".join(sys.argv[1:]).strip() or DEFAULT_TARGET_DESCRIPTION
    print(f"target: {target}")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set.")
        return

    client = OpenAI(api_key=api_key)
    os.makedirs("captures", exist_ok=True)

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    ok, frame = get_fresh_frame(cap)
    if not ok:
        print("camera read failed")
        return
    height, width = frame.shape[:2]
    grid = draw_coordinate_grid(frame)
    cv2.imwrite("captures/loop_initial_grid.jpg", grid)

    coords = ask_vlm_target_location(client, "captures/loop_initial_grid.jpg", target, width, height)
    print(f"initial target estimate: {coords}")

    pulse = pixel_to_servo_pulse(coords["x"])
    print(f"initial pulse: {pulse}")

    step = INITIAL_STEP
    last_direction = None
    last_saved_path = None
    invisible_retried = False
    on_target_confirmed = False

    with serial.Serial(PORT, BAUD_RATE, timeout=2) as arduino:
        time.sleep(2)
        arduino.readline()  # discard "ready"

        print(send_command(arduino, str(pulse)))
        time.sleep(1)
        print(send_command(arduino, "1"))  # laser on, stays on during verification

        for iteration in range(1, MAX_ITERATIONS + 1):
            time.sleep(0.5)
            ok, frame = get_fresh_frame(cap)
            if not ok:
                print("camera read failed, stopping")
                break

            path = f"captures/loop_iter{iteration}.jpg"
            cv2.imwrite(path, frame)
            last_saved_path = path

            result = ask_vlm_direction(client, path, target)
            print(f"iteration {iteration}: pulse={pulse} step={step} -> {result}")

            if not result.get("laser_visible", False):
                if not invisible_retried:
                    # A dot landing on the target itself can have low
                    # contrast against a busy/dark label and get missed --
                    # retry once at the same pulse before giving up, rather
                    # than treating one "not visible" as real misalignment.
                    print("laser not visible -- retrying once at the same pulse")
                    invisible_retried = True
                    continue
                print("laser not visible in frame -- stopping, check alignment manually")
                break
            invisible_retried = False

            if result.get("on_target", False):
                if result.get("confidence") == "low":
                    print("on target claimed but confidence is low -- not trusting it, re-checking")
                    time.sleep(0.5)
                    continue
                print("on target -- done")
                on_target_confirmed = True
                break

            direction = result.get("target_direction")
            if direction not in ("left", "right"):
                print(f"unclear direction ({direction}) -- stopping")
                break

            if last_direction is not None and direction != last_direction:
                step = max(MIN_STEP, step // 2)
                print(f"  direction flipped ({last_direction} -> {direction}), shrinking step to {step}")
            last_direction = direction

            # target is to the "left" of the laser dot -> the dot's pixel_x
            # must DECREASE (move left) -> since pulse = negative_slope *
            # pixel_x + b, a smaller pixel_x means a LARGER pulse. So
            # "left" -> increase pulse; "right" -> decrease pulse.
            pulse_delta = abs(step) if direction == "left" else -abs(step)
            pulse = clamp_pulse(pulse + pulse_delta)
            print(send_command(arduino, str(pulse)))
            time.sleep(1)
        else:
            print(f"gave up after {MAX_ITERATIONS} iterations")

        if on_target_confirmed:
            reply = send_command(arduino, "D")
            print(f"distance reading: {reply}")

        print(send_command(arduino, "0"))  # laser off

    cap.release()
    print(f"final result image: {last_saved_path}")


if __name__ == "__main__":
    main()
