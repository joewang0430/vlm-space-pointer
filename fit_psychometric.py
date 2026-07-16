"""Fits psychometric curves to the E1 data and reports JNDs.

Two curves per target (see docs/experiment_log.md § E1 RESULTS):
  1. Direction curve: P(correct | directional answer) vs offset delta,
     fit with the standard psychometric form
         P(delta) = 0.5 + (0.5 - lambda) * (1 - exp(-(delta/alpha)^beta))
     i.e. chance (0.5) at delta -> 0 rising to (1 - lambda) as delta -> inf,
     where lambda is the lapse rate. JND = the delta where P = 0.75.
  2. Hit-report curve: P(on_target reported) vs delta (no parametric fit;
     reported as raw proportions -- it encodes the object's angular width).

Exclusions: bottle offset -25 (dot physically out of camera frame --
stimulus absent; see experiment log). Bootstrap CIs for the JND by
resampling queries within each (target, offset) cell.

Usage: .venv/Scripts/python.exe fit_psychometric.py
Writes: results/e1_fit_summary.txt and prints the same to stdout.
"""

import csv
from collections import defaultdict

import numpy as np
from scipy.optimize import curve_fit

TARGETS = ["bear", "folder", "bottle"]
EXCLUDE = {("bottle", -25)}  # (label, signed offset): stimulus out of frame
N_BOOT = 2000
RNG = np.random.default_rng(0)


def psychometric(delta, alpha, beta, lapse):
    return 0.5 + (0.5 - lapse) * (1.0 - np.exp(-((delta / alpha) ** beta)))


def jnd_from_params(alpha, beta, lapse):
    """Offset where P(correct) = 0.75, from inverting the curve."""
    if lapse >= 0.25:  # asymptote never reaches 0.75
        return np.inf
    inner = 0.25 / (0.5 - lapse)
    return alpha * (-np.log(1.0 - inner)) ** (1.0 / beta)


def load(label):
    rows = list(csv.DictReader(open(f"results/e1_{label}.csv", encoding="utf-8")))
    per_query = []  # (delta, is_directional, correct, on_target)
    for r in rows:
        off = int(r["offset"])
        if (label, off) in EXCLUDE:
            continue
        per_query.append((
            abs(off),
            r["vlm_direction"] in ("left", "right"),
            r["correct"] == "True",
            r["on_target"] == "True",
        ))
    return per_query


def fit_direction_curve(per_query):
    """Fit on per-cell proportions of correct among directional answers."""
    cells = defaultdict(lambda: [0, 0])  # delta -> [n_directional, n_correct]
    for delta, is_dir, correct, _ in per_query:
        if is_dir:
            cells[delta][0] += 1
            cells[delta][1] += int(correct)
    deltas = np.array(sorted(d for d in cells if cells[d][0] > 0), dtype=float)
    n = np.array([cells[d][0] for d in deltas], dtype=float)
    k = np.array([cells[d][1] for d in deltas], dtype=float)
    p = k / n
    popt, _ = curve_fit(
        psychometric, deltas, p,
        p0=[8.0, 2.0, 0.05],
        bounds=([0.5, 0.3, 0.0], [60.0, 10.0, 0.4]),
        sigma=np.sqrt(np.maximum(p * (1 - p), 0.01) / n),
        maxfev=20000,
    )
    return deltas, n, k, popt


def bootstrap_jnd(per_query):
    directional = [(d, c) for d, is_dir, c, _ in per_query if is_dir]
    by_delta = defaultdict(list)
    for d, c in directional:
        by_delta[d].append(c)
    jnds = []
    for _ in range(N_BOOT):
        cells_d, cells_n, cells_k = [], [], []
        for d, outcomes in by_delta.items():
            outcomes = np.array(outcomes)
            resampled = RNG.choice(outcomes, size=len(outcomes), replace=True)
            cells_d.append(d)
            cells_n.append(len(resampled))
            cells_k.append(resampled.sum())
        deltas = np.array(cells_d, dtype=float)
        n = np.array(cells_n, dtype=float)
        p = np.array(cells_k, dtype=float) / n
        try:
            popt, _ = curve_fit(
                psychometric, deltas, p,
                p0=[8.0, 2.0, 0.05],
                bounds=([0.5, 0.3, 0.0], [60.0, 10.0, 0.4]),
                sigma=np.sqrt(np.maximum(p * (1 - p), 0.01) / n),
                maxfev=20000,
            )
            j = jnd_from_params(*popt)
            if np.isfinite(j):
                jnds.append(j)
        except RuntimeError:
            continue
    return np.percentile(jnds, [2.5, 50, 97.5]) if jnds else None


def main():
    lines = []
    for label in TARGETS:
        per_query = load(label)
        deltas, n, k, (alpha, beta, lapse) = fit_direction_curve(per_query)
        jnd = jnd_from_params(alpha, beta, lapse)
        ci = bootstrap_jnd(per_query)

        lines.append(f"=== {label} ===")
        lines.append("direction curve cells (delta: correct/directional):")
        for d, nn, kk in zip(deltas, n, k):
            lines.append(f"  {int(d):3d}: {int(kk)}/{int(nn)} ({100*kk/nn:.0f}%)")
        lines.append(f"fit: alpha={alpha:.2f} beta={beta:.2f} lapse={lapse:.3f}")
        lines.append(f"JND (75% correct): {jnd:.1f} pulses")
        if ci is not None:
            lines.append(f"JND bootstrap median {ci[1]:.1f}, 95% CI [{ci[0]:.1f}, {ci[2]:.1f}]")

        cells_t = defaultdict(lambda: [0, 0])
        for delta, _, _, on_t in per_query:
            cells_t[delta][0] += 1
            cells_t[delta][1] += int(on_t)
        lines.append("hit-report curve (delta: on_target/total):")
        for d in sorted(cells_t):
            tot, hit = cells_t[d]
            lines.append(f"  {d:3d}: {hit}/{tot} ({100*hit/tot:.0f}%)")
        lines.append("")

    out = "\n".join(lines)
    print(out)
    with open("results/e1_fit_summary.txt", "w", encoding="utf-8") as f:
        f.write(out)
    print("written: results/e1_fit_summary.txt")


if __name__ == "__main__":
    main()
