"""VLM coordinate test: ask a vision-language model to locate a target
object in an already-captured photo and return pixel coordinates.

A coordinate grid is overlaid on the image before sending it to the VLM --
vertical/horizontal lines at a fixed pixel spacing, labeled along the top
and left edges like a ruler. Without this, a VLM has no ground truth to
anchor a pixel estimate to and is essentially guessing from proportions.

Draws a marker at the returned coordinates on a clean (gridless) copy of
the photo so a human can visually verify the VLM actually pointed at the
right thing.
"""

import base64
import json
import os

import cv2
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

INPUT_IMAGE = "captures/cam_index_1.jpg"
GRID_IMAGE = "captures/vlm_input_grid.jpg"
OUTPUT_IMAGE = "captures/vlm_result.jpg"
TARGET_DESCRIPTION = "the lamp"
GRID_SPACING = 80


def draw_coordinate_grid(image, spacing: int = GRID_SPACING):
    """Return a copy of image with a labeled pixel-coordinate grid overlaid."""
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
        print("OPENAI_API_KEY not set. Create a .env file (see .env.example) with your key.")
        return

    client = OpenAI(api_key=api_key)

    image = cv2.imread(INPUT_IMAGE)
    if image is None:
        print(f"Could not read {INPUT_IMAGE}. Run camera_test.py first.")
        return

    height, width = image.shape[:2]

    grid_image = draw_coordinate_grid(image)
    cv2.imwrite(GRID_IMAGE, grid_image)

    coords = ask_vlm_for_coordinates(client, GRID_IMAGE, TARGET_DESCRIPTION, width, height)
    print(f"VLM says {TARGET_DESCRIPTION} is at: {coords}")

    x, y = coords["x"], coords["y"]
    cv2.drawMarker(image, (x, y), (0, 0, 255), markerType=cv2.MARKER_CROSS, markerSize=40, thickness=3)
    cv2.imwrite(OUTPUT_IMAGE, image)
    print(f"Saved marked image to {OUTPUT_IMAGE} -- check it to see if the marker is on target.")


if __name__ == "__main__":
    main()
