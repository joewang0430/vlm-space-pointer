"""End-to-end aim test: capture a photo, ask the VLM for the target's
pixel coordinates, convert to a servo pulse, move the pan servo there,
then fire the laser briefly to visually confirm the aim.
"""

import base64
import json
import os
import time

import cv2
import serial
from dotenv import load_dotenv
from openai import OpenAI

from pixel_to_angle import pixel_to_servo_pulse

load_dotenv()

CAMERA_INDEX = 1
PORT = "COM3"
BAUD_RATE = 9600
GRID_SPACING = 80
TARGET_DESCRIPTION = "the cup"


def draw_coordinate_grid(image, spacing: int = GRID_SPACING):
    grid = image.copy()
    height, width = grid.shape[:2]
    line_color = (0, 255, 0)
    text_color = (0, 0, 255)
    font = cv2.FONT_HERSHEY_SIMPLEX

    for x in range(0, width, spacing):
        cv2.line(grid, (x, 0), (x, height), line_color, 1)
        cv2.putText(grid, str(x), (x + 2, 14), font, 0.4, text_color, 1, cv2.LINE_AA)

    for y in range(0, height, spacing):
        cv2.line(grid, (0, y), (width, y), line_color, 1)
        cv2.putText(grid, str(y), (2, y + 12), font, 0.4, text_color, 1, cv2.LINE_AA)

    return grid


def ask_vlm_for_coordinates(client: OpenAI, grid_image_path: str, target: str, width: int, height: int) -> dict:
    with open(grid_image_path, "rb") as f:
        image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"The image is {width}x{height} pixels and has a coordinate grid "
                            f"overlaid on it: green lines every {GRID_SPACING} pixels, labeled in red "
                            "with the x pixel value along the top edge and the y pixel value along "
                            "the left edge. Use these gridlines to precisely determine pixel "
                            f"coordinates -- do not just guess from proportions. Find {target} and "
                            'return its precise pixel coordinates as JSON: {"x": <int>, "y": <int>}. '
                            "x is the horizontal position from the left edge, "
                            "y is the vertical position from the top edge."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                ],
            }
        ],
    )

    return json.loads(response.choices[0].message.content)


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set.")
        return

    client = OpenAI(api_key=api_key)

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    ok, image = cap.read()
    cap.release()
    if not ok:
        print("Could not capture from camera.")
        return

    os.makedirs("captures", exist_ok=True)
    cv2.imwrite("captures/aim_input.jpg", image)

    height, width = image.shape[:2]
    grid_image = draw_coordinate_grid(image)
    cv2.imwrite("captures/aim_input_grid.jpg", grid_image)

    coords = ask_vlm_for_coordinates(client, "captures/aim_input_grid.jpg", TARGET_DESCRIPTION, width, height)
    print(f"VLM says {TARGET_DESCRIPTION} is at: {coords}")

    pulse = pixel_to_servo_pulse(coords["x"], width)
    print(f"converted to servo pulse: {pulse}")

    with serial.Serial(PORT, BAUD_RATE, timeout=2) as arduino:
        time.sleep(2)
        arduino.readline()  # discard "ready" banner

        arduino.write(f"{pulse}\n".encode())
        time.sleep(0.3)
        print(arduino.readline().decode(errors="replace").strip())

        time.sleep(1)  # let the servo settle

        arduino.write(b"1\n")
        time.sleep(0.3)
        print(arduino.readline().decode(errors="replace").strip())

        time.sleep(2)  # keep the laser on briefly to observe

        arduino.write(b"0\n")
        time.sleep(0.3)
        print(arduino.readline().decode(errors="replace").strip())

    x, y = coords["x"], coords["y"]
    cv2.drawMarker(image, (x, y), (0, 0, 255), markerType=cv2.MARKER_CROSS, markerSize=40, thickness=3)
    cv2.imwrite("captures/aim_result.jpg", image)
    print("Saved captures/aim_result.jpg -- compare the marked pixel to where the laser actually landed.")


if __name__ == "__main__":
    main()
