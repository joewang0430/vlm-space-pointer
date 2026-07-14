"""One-off: fit pulse = a*pixel_x + b from the two calibration sweeps.
The (295, 73) point is excluded -- it breaks the otherwise monotonic
trend and is almost certainly a bad detection (noise/reflection), not
a real reading.
"""

import numpy as np

samples = [
    (250, 572), (265, 473), (280, 385), (325, 304), (340, 225), (355, 142), (370, 33),  # run 1
    (325, 334), (340, 254), (280, 415),  # run 2 (excluding outlier 295->73)
]

pulses = np.array([s[0] for s in samples], dtype=float)
pixel_xs = np.array([s[1] for s in samples], dtype=float)

a, b = np.polyfit(pixel_xs, pulses, 1)
print(f"pulse = {a:.5f} * pixel_x + {b:.2f}")

# Report fit quality
predicted = a * pixel_xs + b
residuals = pulses - predicted
print(f"residuals: {residuals}")
print(f"max abs residual: {np.max(np.abs(residuals)):.1f} pulse units")
