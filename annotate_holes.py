"""Label the two blue power screw-terminal blocks on the MOSFET module,
separate from the J1 signal header (already numbered in an earlier pass).
"""

import cv2

INPUT_IMAGE = "captures/mosfet_closeup.png"
OUTPUT_IMAGE = "captures/mosfet_terminals_labeled.png"

image = cv2.imread(INPUT_IMAGE)

LABELS = {
    "A": (700, 175),
    "B": (700, 400),
}

for label, (x, y) in LABELS.items():
    cv2.circle(image, (x, y), 55, (0, 0, 255), 4)
    cv2.putText(image, label, (x - 20, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 0, 255), 4, cv2.LINE_AA)

cv2.imwrite(OUTPUT_IMAGE, image)
print(f"saved {OUTPUT_IMAGE}")
