"""Generates the paper's E1 figures as vector PDFs into paper/figures/.

Fig. 2 (fig_psychometric.pdf): P(correct direction | directional answer)
vs offset, per target, with fitted curves (Eq. 2 form), Wilson binomial
CIs, chance/JND-criterion lines, and per-target JND markers.

Fig. 3 (fig_hitcurve.pdf): P(on_target reported) vs offset per target,
with the user-measured physical half-widths marked, showing that the
VLM's hit window does not coincide with physical extent.

Colors: Okabe-Ito colorblind-safe palette; identity is additionally
encoded by marker shape and line style (grayscale/CVD-safe).

Usage: .venv/Scripts/python.exe make_figures.py
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fit_psychometric import fit_direction_curve, jnd_from_params, load, psychometric

PULSE_TO_DEG = 270.0 / 420.0  # 270 degrees over pulse range 100-520

STYLE = {
    "bear":   dict(color="#0072B2", marker="o", ls="-",  label="bear"),
    "folder": dict(color="#D55E00", marker="s", ls="--", label="folder"),
    "bottle": dict(color="#009E73", marker="^", ls=":",  label="bottle"),
}
# User-measured physical half-widths in pulses (edge test, 2026-07-16)
HALF_WIDTH = {"bear": 3.5, "folder": 6.5, "bottle": 1.5}

plt.rcParams.update({
    "font.size": 8,
    "font.family": "serif",
    "axes.linewidth": 0.6,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "legend.frameon": False,
    "pdf.fonttype": 42,
})


def wilson_ci(k, n, z=1.96):
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return center - half, center + half


def fig_psychometric(out_path):
    fig, ax = plt.subplots(figsize=(3.5, 2.7))
    for label, style in STYLE.items():
        per_query = load(label)
        deltas, n, k, popt = fit_direction_curve(per_query)
        p = k / n
        lo, hi = wilson_ci(k, n)
        ax.errorbar(deltas, p, yerr=[p - lo, hi - p], fmt=style["marker"],
                    color=style["color"], ms=3.5, lw=0.8, capsize=1.5,
                    elinewidth=0.6, zorder=3)
        xs = np.linspace(0.8, 30, 300)
        ax.plot(xs, psychometric(xs, *popt), style["ls"], color=style["color"],
                lw=1.4, label=style["label"], zorder=2)
        jnd = jnd_from_params(*popt)
        ax.axvline(jnd, color=style["color"], lw=0.6, ls=style["ls"], alpha=0.55,
                   ymax=0.5, zorder=1)

    ax.axhline(0.5, color="0.45", lw=0.6, ls="-", zorder=1)
    ax.axhline(0.75, color="0.45", lw=0.6, ls=(0, (2, 2)), zorder=1)
    ax.text(29.5, 0.505, "chance", ha="right", va="bottom", fontsize=6.5, color="0.35")
    ax.text(29.5, 0.755, "JND criterion", ha="right", va="bottom", fontsize=6.5, color="0.35")

    ax.set_xscale("log")
    ax.set_xticks([1, 2, 3, 5, 8, 12, 18, 25])
    ax.set_xticklabels([1, 2, 3, 5, 8, 12, 18, 25])
    ax.set_xlim(0.8, 30)
    ax.set_ylim(0.0, 1.05)
    ax.set_xlabel("offset $\\delta$ (pulse units)")
    ax.set_ylabel("P(correct direction)")
    ax.legend(loc="lower right", fontsize=6.5)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(pad=0.3)
    fig.savefig(out_path)
    plt.close(fig)


def fig_hitcurve(out_path):
    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    for label, style in STYLE.items():
        per_query = load(label)
        cells = {}
        for delta, _, _, on_t in per_query:
            cells.setdefault(delta, []).append(on_t)
        deltas = np.array(sorted(cells))
        p = np.array([np.mean(cells[d]) for d in deltas])
        n = np.array([len(cells[d]) for d in deltas])
        lo, hi = wilson_ci(p * n, n)
        ax.errorbar(deltas, p, yerr=[p - lo, hi - p], fmt=style["marker"],
                    color=style["color"], ms=3.5, lw=1.1, ls=style["ls"],
                    capsize=1.5, elinewidth=0.6, label=style["label"])
        ax.axvline(HALF_WIDTH[label], color=style["color"], lw=0.9, ls=style["ls"],
                   alpha=0.6, ymax=0.35)

    ax.set_xscale("log")
    ax.set_xticks([1, 2, 3, 5, 8, 12, 18, 25])
    ax.set_xticklabels([1, 2, 3, 5, 8, 12, 18, 25])
    ax.set_xlim(0.8, 30)
    ax.set_ylim(-0.03, 1.05)
    ax.set_xlabel("offset $\\delta$ from anchored center (pulse units)")
    ax.set_ylabel("P(reports on-target)")
    ax.legend(loc="upper right", fontsize=6.5)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(pad=0.3)
    fig.savefig(out_path)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs("paper/figures", exist_ok=True)
    fig_psychometric("paper/figures/fig_psychometric.pdf")
    fig_hitcurve("paper/figures/fig_hitcurve.pdf")
    print("written: paper/figures/fig_psychometric.pdf, paper/figures/fig_hitcurve.pdf")
