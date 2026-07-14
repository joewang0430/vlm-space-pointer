"""Overlays a labeled pixel-coordinate grid on every image in
captures/verify/, saving a *_grid.jpg version next to each original so
coordinates can be read off directly.
"""

import glob
import os

import cv2

GRID_SPACING = 40
FOLDER = "captures/verify"


def draw_coordinate_grid(image, spacing: int = GRID_SPACING):
    grid = image.copy()
    height, width = grid.shape[:2]
    for x in range(0, width, spacing):
        cv2.line(grid, (x, 0), (x, height), (0, 255, 0), 1)
        cv2.putText(grid, str(x), (x + 2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)
    for y in range(0, height, spacing):
        cv2.line(grid, (0, y), (width, y), (0, 255, 0), 1)
        cv2.putText(grid, str(y), (2, y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)
    return grid


def main():
    paths = sorted(glob.glob(os.path.join(FOLDER, "pulse_*.jpg")))
    paths = [p for p in paths if not p.endswith("_grid.jpg")]

    for path in paths:
        image = cv2.imread(path)
        if image is None:
            continue
        grid = draw_coordinate_grid(image)
        out_path = path.replace(".jpg", "_grid.jpg")
        cv2.imwrite(out_path, grid)
        print(f"saved {out_path}")


if __name__ == "__main__":
    main()
