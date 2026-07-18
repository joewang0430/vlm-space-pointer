"""Converts a VLM-reported target pixel coordinate into a PCA9685 pulse
value for the pan servo.

Recalibrated 2026-07-16 (evening) after the whole camera+laser rig was
deliberately relocated to make room for the 8-object E2 scene (a 3-point
spot check showed a consistent +3..+5 pulse drift against the prior
fit). Same methodology: servo moved through 11 pulse values (260-360,
step 10; all in frame this time) and the user directly read off (by
eye, not automated detection -- classical image processing proved
unreliable earlier) where the laser dot landed in a labeled pixel grid.
Fit through all 11 (pixel_x, pulse) points: R^2 = 0.998, max residual
~2.3 pulse units. Note: this sweep was performed with the E2 objects
already in the scene, so dots landed on surfaces at several depths --
deliberately so, since this makes the fit representative of the depth
distribution the E2 trials actually aim at.

Distance caveat: this calibration mixes the camera's own (distance-
independent) angular resolution with the parallax between the laser's
pivot and the camera's optical center (which IS distance-dependent).
It was measured at several meters, where parallax is negligible, so it
should be treated as approximate for close-up (tabletop-range) targets
-- the aim->verify->correct VLM loop is what's responsible for closing
that residual gap, not this formula.

Valid roughly over pulse range [260, 360] / pixel_x range [17, 638],
the window where the laser dot fell inside the camera's current field
of view. Outside that the fit is extrapolation.
"""

PULSE_PER_PIXEL = -0.16822
PULSE_AT_PIXEL_ZERO = 365.05

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
