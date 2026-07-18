"""Annotates the apparatus photo with component labels and arrows for
the paper's Fig. 1. Coordinates are in ORIGINAL image pixels (2420x1816)
and were read by eye from the photo -- verify the rendered output before
accepting (arrow placement is the error-prone part).

Usage: .venv/Scripts/python.exe annotate_apparatus.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

IMG = "paper/figures/fig_apparatus_raw.jpeg"
OUT = "paper/figures/fig_apparatus_annotated.jpg"

# label text, arrow tip (component), text anchor (empty area)
LABELS = [
    ("webcam",              (885, 665),   (330, 330)),
    ("TF-Luna rangefinder", (1125, 1010), (1150, 230)),
    ("laser diode",         (960, 1230),  (620, 1560)),
    ("pan servo",           (1110, 1265), (1250, 1650)),
    ("MOSFET switch",       (1400, 1150), (1750, 1680)),
    ("PCA9685",             (1790, 1340), (2230, 1200)),
    ("Arduino UNO",         (1890, 1080), (2150, 780)),
    ("breadboard",          (1450, 850),  (1650, 380)),
    ("adjustable PSU",      (570, 1270),  (250, 900)),
]

img = mpimg.imread(IMG)
h, w = img.shape[:2]
fig, ax = plt.subplots(figsize=(w / 300, h / 300), dpi=300)
ax.imshow(img)
ax.axis("off")

for text, tip, anchor in LABELS:
    ax.annotate(
        text, xy=tip, xytext=anchor,
        fontsize=13, fontweight="bold", color="white",
        ha="center", va="center",
        bbox=dict(boxstyle="round,pad=0.35", fc="black", alpha=0.75, ec="none"),
        arrowprops=dict(arrowstyle="->", color="yellow", lw=2.2,
                        shrinkA=2, shrinkB=2),
    )

fig.tight_layout(pad=0)
fig.savefig(OUT, bbox_inches="tight", pad_inches=0)
print(f"written: {OUT}")
