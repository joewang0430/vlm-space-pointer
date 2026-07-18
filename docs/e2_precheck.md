# E2 Pre-Run Checklist (written 2026-07-16, BEFORE any E2 trial)

Every lesson from the E1 post-hoc audit, converted into a pre-run gate.
Nothing runs until the user has read and approved this document.
Items marked [USER] need the user; items marked [AUTO] are script-enforced.

## 1. Quantities that will enter the paper's statistics, and their sources

| Quantity | Source | Verification |
|---|---|---|
| u* anchor per object (x8) | laser + user's eyes | [USER] anchored evening of 07-16 |
| Physical width per object | pulse-step edge test photos | [USER] reads first-out offsets (~10 min, recommended for new objects) |
| Terminal error per trial | \|final_pulse − u*\| | [AUTO] computed, anchors recorded in CSV |
| Hit / miss per trial | final-frame photo | [USER] post-run review, **blinded** (see §5) |
| Iterations, stop reason | runner log | [AUTO] |
| Model snapshot | resolved alias check | [AUTO] logged at batch start AND end |
| Lighting comparability | run at night like E1 | [USER] schedule; [AUTO] frame brightness check in analysis |

## 2. Geometry pre-checks (the bottle −25 lesson)

- [AUTO] All strategies operate within the calibrated pulse window
  **[270, 360]**, whose dot positions are inside the camera frame
  (pixel ≈ [52, 583]). The step-halving clamp and open-loop initial
  pulse are clamped to this window (raw un-clamped estimate still
  logged); the bisection grid is already [270, 360].
- [USER] All 8 objects placed so their bodies intersect the laser line
  height, verified during anchoring (the anchoring process itself
  proves reachability).
- Objects need NOT be far apart (unlike E1): E1 showed dot-on-neighbor
  does not degrade direction judgments, and E2's strategies converge
  toward targets rather than probing large offsets.

## 3. Protocol fidelity (strategy implementations)

- Step-halving reproduces `aim_verify_loop.py` behavior EXACTLY,
  including the retry-once-at-same-pulse on laser-not-visible.
  [FIXED in e2_closed_loop.py before this document was finalized]
- All three strategies share the identical initial VLM coordinate
  estimate procedure (same grid overlay, same prompt).
- Bisection uses E1-fitted curves; each object is assigned a curve
  class (bear-like / folder-like / bottle-like) by size+contrast,
  recorded in the OBJECTS config BEFORE the run starts.
- MAX_ITERATIONS = 16, INITIAL_STEP = 15, MIN_STEP = 3 (same as the
  demonstrated loop).
- Distance (TF-Luna) is NOT part of E2 (sensor misalignment documented
  2026-07-16; no distance claims until re-aligned and tape-verified).

## 4. Run hygiene

- [USER] Rig (camera + servo + laser) untouched; nobody in the beam
  path at eye height during the run; user not on the bed.
- [AUTO] Trial order fully randomized across (object, strategy, rep).
- [AUTO] Every frame archived (`captures/e2/<scene>/`), every trial row
  flushed to CSV immediately (crash loses at most one trial).
- [AUTO] Per-trial failures (camera/serial/API) are logged and skipped,
  never silently retried as a different trial.
- Scene photo captured immediately before the first trial and after the
  last trial (drift evidence).

## 5. Pre-declared analysis (written BEFORE data exists)

- Primary metrics per strategy: hit rate (user-judged), median terminal
  error in pulses, median iterations/VLM queries, invisible-stop count.
- Hit/miss review is **blinded**: final frames are copied to anonymized
  names (review_NNN.jpg) in a random order with a hidden mapping file;
  the user judges hit/miss without knowing strategy or trial identity.
- P1 test: per curve class, compare each strategy's median terminal
  error against that class's E1 JND (center-referenced). Prediction:
  same order of magnitude, for every strategy.
- P2 test: simulate Algorithm 1 and step-halving with the fitted E1
  curves (probabilistic_bisection.py oracle) using the measured initial
  regressor residuals; compare simulated vs hardware iteration
  distributions.
- Pre-declared exclusions: trials with camera/serial/API failures
  (logged with reason). Nothing else is excludable post-hoc.
- Honest headline (from simulation, to be tested, not assumed):
  terminal accuracy is comparator-limited, not algorithm-limited;
  bisection's expected edge is robustness/mean error, not a large
  query-count win.

## 5b. Pre-declared amendments (added evening 07-16, BEFORE any E2 trial)

- **Rig relocation + recalibration**: the whole rig was moved to fit the
  8-object scene; recalibrated from an 11-point user-read sweep
  (PULSE_PER_PIXEL=-0.16822, PULSE_AT_PIXEL_ZERO=365.05, R^2=0.998,
  max residual 2.3). Sweep deliberately performed with objects in scene
  so the fit reflects the depth distribution E2 actually aims at.
  Frame-safe window recomputed: pulse [262, 360].
- **Folder is a boundary case**: anchored at u*=267, only 5 pulses above
  the window floor; its rightward excursions clamp. Declared now;
  analysis reports it in aggregate AND separately.
- **Servo deadband (user-discovered)**: 1-pulse commands from adjacent
  positions sometimes produce no visible motion. Anchoring used a
  swing-and-return convention (park at 400, then approach); E2's loop
  steps do not, so all terminal errors carry an actuation noise floor of
  roughly +-1-2 pulses on top of anchoring precision. Declared as part
  of the error interpretation, not discovered after the fact.
- **Anchors (user-eye, swing-and-return)**: umbrella 343, bowl 326,
  calculator 317, tissue box 306, slipper 295, bottle 288, bear 278,
  folder 267. Curve-class assignments (by size+contrast, fixed before
  run): umbrella/tissue box/folder -> folder-class; bowl/calculator/
  bottle -> bottle-class; slipper/bear -> bear-class.

## 6. Open risks accepted going in

- n = 8 reps/cell gives wide CIs; claims will lean on orderings and
  cross-strategy consistency, not exact values (E1 lesson #4).
- Commercial model may drift mid-run (mitigated by snapshot logging
  before/after; a mid-run version change would be visible and disclosed).
- Anchoring precision ±1-2 pulses floors the measurable terminal error.
