"""Generates the E2 paper figures.

fig_scene_pair.pdf : side-by-side scene-2 comparison -- (a) operator's
    phone photo (human view) vs (b) the system camera's own frame with
    the coordinate-grid overlay (what the VLM actually sees).

fig_e2_results.pdf : (a) hit rate per strategy per scene (Wilson 95%
    CIs); (b) terminal-error distributions per strategy (box + jittered
    points). Strategy colors are Okabe-Ito hues distinct from the ones
    used for objects in the E1 figures.

Usage: .venv/Scripts/python.exe make_figures_e2.py
"""

import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.size": 8,
    "font.family": "serif",
    "axes.linewidth": 0.6,
    "legend.frameon": False,
    "pdf.fonttype": 42,
})

STRAT_STYLE = {
    "open":      dict(color="#999999", label="open-loop"),
    "halving":   dict(color="#E69F00", label="step-halving"),
    "bisection": dict(color="#56B4E9", label="prob.\\ bisection"),
}

EDGES = {
    "scene1": {"umbrella": (-9, 10), "bowl": (-4, 5), "calculator": (-2, 4),
               "tissuebox": (-5, 8), "slipper": (-2, 4), "bottle": (-3, 3),
               "bear": (-3, 4), "folder": (-5, 7)},
    "scene2": {"folder": (-3, 8), "bear": (-3, 6), "bottle": (-2, 4),
               "tissuebox": (-6, 8), "bowl": (-4, 6), "calculator": (-2, 4),
               "slipper": (-3, 4), "umbrella": (-4, 10)},
}


def load_trials():
    trials = []
    for scene in ["scene1", "scene2"]:
        for r in csv.DictReader(open(f"results/e2_{scene}.csv", encoding="utf-8")):
            off = int(r["final_pulse"]) - int(r["u_star"])
            lo, hi = EDGES[scene][r["object"]]
            trials.append(dict(scene=scene, strategy=r["strategy"],
                               err=int(r["terminal_error"]), hit=lo < off < hi))
    return trials


def wilson(k, n, z=1.96):
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return center - half, center + half


def fig_scene_pair(out):
    human = mpimg.imread("paper/figures/fig_scene2_raw.jpeg")
    system = mpimg.imread("captures/e2_scene2_check2.jpg")
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.75))
    for ax, img, title in [
        (axes[0], human, "(a) operator's view of scene 2"),
        (axes[1], system, "(b) system camera view (grid overlay)"),
    ]:
        ax.imshow(img)
        ax.set_title(title, fontsize=8)
        ax.axis("off")
    fig.tight_layout(pad=0.4)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_e2_results(out):
    trials = load_trials()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.5))

    # (a) hit rates per scene, grouped by strategy
    strategies = ["open", "halving", "bisection"]
    width = 0.35
    xs = np.arange(3)
    for i, scene in enumerate(["scene1", "scene2"]):
        rates, los, his = [], [], []
        for s in strategies:
            sel = [t for t in trials if t["scene"] == scene and t["strategy"] == s]
            k = sum(t["hit"] for t in sel)
            rates.append(k / len(sel))
            lo, hi = wilson(k, len(sel))
            los.append(rates[-1] - lo)
            his.append(hi - rates[-1])
        pos = xs + (i - 0.5) * width
        colors = [STRAT_STYLE[s]["color"] for s in strategies]
        bars = ax1.bar(pos, rates, width * 0.92, color=colors,
                       alpha=1.0 if i else 0.55, edgecolor="white", linewidth=0.5)
        ax1.errorbar(pos, rates, yerr=[los, his], fmt="none", ecolor="0.25",
                     elinewidth=0.7, capsize=1.5)
        for p, rte in zip(pos, rates):
            ax1.text(p, 0.03, f"{100*rte:.0f}", ha="center", fontsize=6.5,
                     color="black")
    ax1.set_xticks(xs)
    ax1.set_xticklabels(["open-loop", "step-halving", "prob. bisection"], fontsize=7.5)
    ax1.set_ylabel("hit rate")
    ax1.set_ylim(0, 1.0)
    ax1.set_title("(a) hit rate (light: scene 1, solid: scene 2)", fontsize=8)
    ax1.spines[["top", "right"]].set_visible(False)

    # (b) terminal error distributions (combined scenes)
    rng = np.random.default_rng(0)
    for i, s in enumerate(strategies):
        errs = np.array([t["err"] for t in trials if t["strategy"] == s])
        jitter = rng.uniform(-0.13, 0.13, len(errs))
        ax2.plot(i + jitter, errs, "o", ms=2, alpha=0.25,
                 color=STRAT_STYLE[s]["color"], mec="none")
        ax2.hlines(np.median(errs), i - 0.22, i + 0.22, color="black", lw=1.4, zorder=3)
    ax2.set_xticks(range(3))
    ax2.set_xticklabels(["open-loop", "step-halving", "prob. bisection"], fontsize=7.5)
    ax2.set_ylabel("terminal error (pulses)")
    ax2.set_title("(b) terminal error, both scenes (bar: median)", fontsize=8)
    ax2.spines[["top", "right"]].set_visible(False)

    fig.tight_layout(pad=0.5)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_scene_pair("paper/figures/fig_scene_pair.pdf")
    fig_e2_results("paper/figures/fig_e2_results.pdf")
    print("written: fig_scene_pair.pdf, fig_e2_results.pdf")
