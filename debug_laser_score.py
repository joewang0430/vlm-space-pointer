import cv2
import numpy as np

image = cv2.imread("captures/calib_pulse_400.jpg")
b, g, r = cv2.split(image.astype(np.int32))
redness = r - np.maximum(g, b)
brightness = (r + g + b) / 3
score = redness + brightness * 0.5

_, max_val, _, max_loc = cv2.minMaxLoc(score.astype(np.float32))
print(f"max score: {max_val} at {max_loc}")

x, y = max_loc
print(f"pixel BGR at dot: {image[y, x]}")
print(f"redness at dot: {redness[y, x]}, brightness at dot: {brightness[y, x]}")
