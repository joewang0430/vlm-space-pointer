# Experiment Log & Sprint Plan (started 2026-07-15)

Single source of truth for the paper sprint. If Claude's session context is
lost, THIS FILE plus `CLAUDE.md` restores the full working state. Update it
whenever a decision is made or data lands.

## Deadline
- Paper submission: **morning of 2026-07-18** (work may run through the night
  of 07-17). Other projects are set aside; full-scale plan chosen over a
  reduced one, explicitly at the user's direction.

## Paper decision (settled 2026-07-15)
- Adopt the advisor-provided framework **"VLMs are Comparators, Not
  Regressors"** (`paper/论文框架与内容_VLMs_are_Comparators.pdf`) with three
  amendments agreed with the user:
  1. **E1 ground truth by construction**: anchor pulse u* per target verified
     by the user's own eyes; offsets are commanded in pulse space. No
     automated laser-dot detection anywhere in E1.
  2. **E2 success judgment**: human review of final frames (≈384 photos,
     ~1h) is the primary method; an automated detector is optional and, if
     used, must be human-audited on a sample.
  3. **Models**: GPT-4o only as the primary condition; open-weights model is
     an optional stretch, its absence noted as a limitation.
- Rangefinder (TF-Luna): demo capability only, NOT an experimental variable.
  Its imperfect co-alignment with the laser (can miss narrow objects
  sideways) goes into Limitations honestly.
- Writing order: System (done) -> Theory (adopt from framework, polish) ->
  Experiments (after data) -> Discussion/Limitations -> Related Work ->
  Intro -> Abstract last.

## Paper repo state
- `paper/main.tex`: IEEEtran skeleton, compiles (`main.pdf`). System section
  fully written from verified facts. Everything else is TODO comments on
  purpose (not settled / no data yet). `paper/` is gitignored.
- Toolchain: MiKTeX 25.12 + latexmk + VS Code LaTeX Workshop all verified
  working; MiKTeX set to auto-install missing packages.

## Calibration (third fit, 2026-07-15 evening — CURRENT)
- `pixel_to_angle.py`: `PULSE_PER_PIXEL = -0.16959`,
  `PULSE_AT_PIXEL_ZERO = 368.81`, R^2 = 0.998, max residual 2.03 pulses,
  valid pulse [270, 360] / pixel_x [40, 592].
- Cause of refit: TF-Luna rewiring slightly rotated laser vs camera
  (intercept shifted ~4 pulses, slope unchanged). Detected by 3-point spot
  check; refit from 10 user-eye-read points (pulse 260 fell out of frame).
- Lesson reconfirmed: user's eye readings are authoritative; Claude misread
  one spot-check dot by ~50px, user's 11-point series was self-consistent.

## Scene 1 (LOCKED as of 2026-07-15 evening — do not move anything)
- Three anchor targets on/against the bed wall (~desk-to-wall distance):
  - **polar bear plush** — large, white plush. Center ≈ x225. Moved forward
    off the wall (closer depth than wall plane — fine for E1, small known
    parallax bias for E2 open-loop, which is itself a paper point).
  - **blue folder** — large, dark, flat. Center ≈ x350.
  - **black bottle** — narrow, dark. Center ≈ x490.
- Anchors (user-eye-verified, horizontal center):
  - bear **u\* = 331**, folder **u\* = 308**, bottle **u\* = 280**.
- Known spacing compromise (room wall prevents ideal 150px gaps): at the
  largest offsets the dot can land ON a neighbor object. Affected cells
  (~36/576 queries): folder +25 -> lands near/on bear; bear −25 -> on
  folder; bottle +25 -> on folder. Analysis must annotate these queries
  (computable from u*, offset, and measured spans; every frame is saved)
  and fit the psychometric curve both with and without them (sensitivity
  analysis). Wide targets also mean small offsets stay ON the object ->
  VLM "on_target" answers there are expected and form a second curve
  P(on_target | δ), not wasted data.

## Model version
- All E1 calls used the API alias `gpt-4o`. Checked 2026-07-16 ~02:30
  (immediately after E1 finished, same night): the alias resolves to
  **`gpt-4o-2024-08-06`**. All 576 E1 queries ran within a single ~2h
  window on the same night, so this snapshot almost certainly served
  every call. Caveat for the paper: per-call resolved version was not
  logged in the CSVs (protocol gap found in post-hoc audit); re-check
  the alias resolution again right before and after E2 runs.

## E1 — data audit (07-16, post-hoc; full details in chat, key points)
- Clean: 0 contradictory answers (on_target + direction simultaneously);
  no lighting drift (mean frame brightness 135-139 across all blocks);
  no first-half/second-half accuracy drift; bottle answers side-balanced.
- Disclose in paper: (1) bear/folder show side asymmetry -- offsets toward
  the cluttered side of the scene are judged worse (bear 76% vs 100%,
  folder 84% vs 96%) => comparator accuracy is context-dependent and the
  pooled curve averages the two sides; (2) anchoring precision is +-1-2
  pulses (human-eye limit), which only blurs the delta=1-2 cells, far
  below the measured JNDs of 4-11 pulses; (3) bottle -25 exclusion
  (stimulus out of frame) + the protocol gap that allowed it (safety
  check covered servo range but not camera frame); (4) n=12/cell =>
  wide CIs, lean on the JND ordering not exact values; (5) bear's
  directional data only exists for delta>=5, so its JND partly reflects
  object half-width -- always present JND alongside the hit-curve width.

## E1 — RESULTS (completed night of 07-15 -> 07-16, 576/576 queries)
- All three blocks ran clean; raw data `results/e1_{bear,folder,bottle}.csv`,
  every frame archived under `captures/e1/<label>/`.
- **bear** (u*=331): offsets 1-3 -> VLM says on_target 24/24 (dot truly on
  the ~6-pulse-wide bear); transition at 8; direction accuracy 83% (12),
  94% (18), 100% (25).
- **folder** (u*=308): same shape; direction accuracy 100% for 12/18/25.
- **bottle** (u*=280, narrow): directional answers from offset 1 already;
  accuracy climbs 43% (1) -> 88% (8) -> 96% (18). Offset **-25 is INVALID**:
  the dot physically leaves the camera frame (verified by viewing
  q007_off-25_rep1.jpg -- no dot anywhere). Exclude those 12 queries from
  the curve.
- **Finding 1 (contamination null result)**: bottle +25 puts the dot ON the
  folder, yet direction judgment was 11/11 correct -- dot-on-neighbor does
  not degrade the comparator. The pre-registered sensitivity exclusion is
  unnecessary; keep the cells.
- **Finding 2 (hallucination under absent stimulus)**: with the dot out of
  frame (bottle -25), only 3/12 answers honestly said laser not visible;
  9/12 fabricated a direction, all of them wrong. Important negative result
  for VLM-as-verifier designs.
- Analysis plan for fitting: (a) classic direction-error psychometric curve
  P(correct | directional answer) per target; (b) P(on_target | delta) as a
  second curve (encodes object angular width); (c) the bisection algorithm's
  likelihood should use the 3-outcome model {consistent, inconsistent,
  on_target} rather than binary.

## E1 — original design (for reference)
- Script: `e1_psychometric.py <u_star> <label> <target description...>`
- Design: offsets {1,2,3,5,8,12,18,25} × both signs × 12 reps = 192
  queries/target, randomized order; laser on only during capture; uses the
  SAME `ask_vlm_direction` prompt as the closed loop (imported); ground
  truth: positive offset -> dot LEFT of target -> correct answer "right".
- Output: `results/e1_<label>.csv` + audit images `captures/e1/<label>/`.
- ~20-25 min per target block; ~1-1.5h total for three targets.
- Planned commands:
  - `.venv/Scripts/python.exe e1_psychometric.py 331 bear the polar bear plush toy`
  - `.venv/Scripts/python.exe e1_psychometric.py 308 folder the blue folder`
  - `.venv/Scripts/python.exe e1_psychometric.py 280 bottle the black bottle`

## Physical widths & edge-referenced JNDs (07-16, user-verified)
- Edge test: laser stepped pulse-by-pulse around each anchor, 43 photos in
  `captures/edge_test/`, user read first out-of-object offsets:
  bear -3/+4, folder -7/+6, bottle -1/+2.
- Cross-checked against user's pixel reads of e1_scene_check3.jpg at laser
  height (bear 195-238, folder 316-380, bottle 496-514) -- consistent
  within +-1 pulse.
- Edge-referenced JND = center JND - mean half-width:
  bear 11.0-3.5 = **7.5**; folder 5.6-6.5 = **~0**; bottle 4.3-1.5 = **2.8**.
  Corrected story: once size is removed, CONTRAST dominates -- white plush
  on white wall is by far hardest; high-contrast folder resolvable at its
  edge. Present JND always alongside measured width.
- Bonus finding: VLM's on_target window doesn't match physical extent and
  differs in direction by target -- bear over-reported (still "on target"
  at ~2x physical width), folder under-reported (dot physically ON folder
  at delta=3-5, on_target only ~40%). The comparator's hit predicate is
  not the physical overlap predicate.

## Distance measurements & TF-Luna misalignment (07-16 night, IMPORTANT)
- User tape measurements (authoritative): bear **132cm**, folder **183cm**,
  bottle **192cm** (rig to object).
- TF-Luna readings at the same anchors: bear 204 (x5, stable), folder
  bimodal 194/204, bottle 188.
- Diagnosis: **the TF-Luna hit NONE of the three objects.** Bear +72cm
  error proves the sensor's axis diverges from the laser by >=4-5 degrees
  (angular mounting error, not the small lateral offset previously
  assumed); every reading is some background surface; bottle's apparent
  agreement is a depth coincidence (likely bedding).
- Consequence: the Pepsi-bottle 196cm reading from 07-15 is retroactively
  suspect (was never tape-verified). Do NOT report any TF-Luna distance
  as a success until the sensor is re-aligned and verified against tape.
- Firmware gap: aim_control ignores the TF-Luna signal-strength field;
  low-strength (unreliable) distances are accepted silently. Fix if the
  distance channel is ever used for real claims.
- For the paper: distance stays demo-only; write this up as a quantified
  co-alignment limitation (with the bear +72cm example). TODO before any
  distance demo: hand-probe to map the Luna's true aim direction
  (object-independent), re-align mount, re-verify against tape.

## Simulation results (07-16 ~02:00, probabilistic_bisection.py)
- PB implemented with the 3-outcome likelihood {left, right, on_target}
  using the E1-fitted psi(delta) and raw hit curves; query = posterior
  median; on on_target it fuses that answer and re-aims at the posterior
  median. Fair comparison: both strategies warm-start 8 pulses from truth.
- Result: PB does NOT dominate. Mean terminal error better on bear
  (5.1 vs 7.2) and folder (5.2 vs 5.5); slightly worse on bottle
  (2.0 vs 1.2). Median iterations identical.
- Interpretation: termination is dominated by the hit-report curve --
  wide targets get declared "on target" up to ~8 pulses away, so ALL
  strategies hit the same comparator-imposed floor. This is exactly
  Proposition 1 (JND-governed resolution). Paper headline must be
  reframed honestly: "terminal accuracy is comparator-limited, not
  algorithm-limited (predicted, simulated, and hardware-verified);
  PB adds robustness to early errors, not a big query-count win."
  Do NOT fill the framework's "XX fewer queries" placeholder with a
  big number -- the evidence doesn't support it.

## E2 — closed-loop comparison (designed, not yet built)
- 8 objects × 2 scene layouts × 3 strategies × 8 reps = 384 trials.
- Strategies: (a) open-loop coordinate regression (aim once via
  `pixel_to_angle.py`, no correction); (b) step-halving (current
  `aim_verify_loop.py` logic); (c) probabilistic bisection using the E1
  error model (NEW CODE, ~50 lines, validate in simulation first).
- Metrics: hit rate (human-judged final frames), iterations/queries,
  terminal angular error |u_final − u*| (u* anchored per object), API cost.
- Tests framework predictions P1 (terminal error tracks JND) and P2
  (simulated iteration counts match hardware).

## Schedule
- **07-15 (tonight)**: run E1 all three blocks -> core data in hand.
- **07-16**: fit curves + JND figures; write & simulate probabilistic
  bisection; write E2 batch runner; anchor 8 objects (user, ~15 min);
  run E2 scene 1 overnight (~192 trials).
- **07-17**: rearrange to scene 2 + run (~192 trials); user reviews final
  frames (~1h); stats + figures; write Experiments/Intro/Abstract; polish.
- **07-18 early morning**: final PDF, submit.
- Safety: during unattended runs the laser sweeps the bed zone repeatedly —
  nobody in the beam path at eye height; don't lie on the bed during runs.

## Working rules (hard-learned, do not violate)
- The user's eyes are the ground-truth instrument. Claude never trusts its
  own image reading over the user's, and never trusts VLM self-reports.
- No file writes/edits/deletes, no installs, no hardware actions without an
  explicit instruction for that specific action. Questions are questions,
  not commands. Reverting something also requires an instruction.
- Verify tool "success" reports against actual state (files on disk,
  registry, device responses) before reporting completion.
- The user must be physically present for: anchoring, scene changes, final
  frame review. Everything else can run unattended.
