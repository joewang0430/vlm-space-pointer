"""Converts a VLM-reported target pixel coordinate into a PCA9685 pulse
value for the pan servo.

Recalibrated 2026-07-15 after the camera+laser assembly was detached and
physically remounted, which invalidated the prior 2026-07-12 fit. Same
methodology: moved the servo through 11 pulse values (270-360, step 10;
260 fell outside the frame) and had the user directly read off (by eye,
not automated detection -- classical image processing proved unreliable
earlier) where the laser dot landed in a labeled pixel grid. Fit a line
through the 10 in-frame (pixel_x, pulse) points: max residual ~2.3 pulse
units.

Distance caveat: this calibration mixes the camera's own (distance-
independent) angular resolution with the parallax between the laser's
pivot and the camera's optical center (which IS distance-dependent).
It was measured at several meters, where parallax is negligible, so it
should be treated as approximate for close-up (tabletop-range) targets
-- the aim->verify->correct VLM loop is what's responsible for closing
that residual gap, not this formula.

Valid roughly over pulse range [270, 360] / pixel_x range [70, 618],
the window where the laser dot fell inside the camera's current field
of view. Outside that the fit is extrapolation.
"""

PULSE_PER_PIXEL = -0.17041
PULSE_AT_PIXEL_ZERO = 372.97

# Sanity clamp -- keep any single command inside the mechanically safe
# range even if a wildly out-of-window pixel_x is passed in.
SERVO_PULSE_MIN = 100
SERVO_PULSE_MAX = 520


def pixel_to_servo_pulse(pixel_x: int, image_width: int = None) -> int:
    """VLM target pixel_x -> PCA9685 pulse value for the pan servo.
    image_width is accepted for backwards compatibility but unused --
    the fit is in absolute pixel_x, not normalized, since it was
    calibrated directly against real captured frames."""
    pulse = PULSE_PER_PIXEL * pixel_x + PULSE_AT_PIXEL_ZERO
    pulse = max(SERVO_PULSE_MIN, min(SERVO_PULSE_MAX, pulse))
    return round(pulse)


if __name__ == "__main__":
    for pixel_x in [0, 100, 200, 300, 400, 500, 600, 640]:
        pulse = pixel_to_servo_pulse(pixel_x)
        print(f"pixel_x={pixel_x} -> pulse={pulse}")
