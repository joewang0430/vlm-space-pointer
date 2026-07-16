"""Probabilistic bisection controller driven by the E1-measured error model.

Maintains a posterior over the unknown on-target pulse u* on an integer
pulse grid. Each VLM answer updates the posterior pointwise via Bayes'
rule using a THREE-outcome likelihood measured in E1 (see
docs/experiment_log.md § E1 RESULTS):

  - "on_target": likelihood h(delta) -- the hit-report curve, which
    encodes the target's angular width;
  - "left"/"right": likelihood (1 - h(delta)) * psi(delta) if the answer
    points from the query toward theta, else (1 - h(delta)) * (1 - psi(delta)),
    where psi is the fitted direction psychometric curve;
  - anything else (invisible/unknown): no update.

The next query is always the posterior median (Horstein 1963; optimal
per Ben-Or & Hassidim 2008), generalized to distance-dependent noise by
evaluating the likelihood pointwise on the grid.

Run this file directly to simulate PB vs the step-halving heuristic vs
open-loop regression on synthetic oracles drawn from the fitted E1
curves for each target: .venv/Scripts/python.exe probabilistic_bisection.py
"""

import numpy as np

# Direction curve psi(delta) parameters fitted by fit_psychometric.py
# (results/e1_fit_summary.txt, 2026-07-16): P(correct direction | answered).
PSI_PARAMS = {
    "bear":   dict(alpha=11.69, beta=5.97, lapse=0.008),
    "folder": dict(alpha=6.36, beta=2.72, lapse=0.000),
    "bottle": dict(alpha=6.37, beta=0.96, lapse=0.000),
}

# Hit-report curve h(delta) as raw measured proportions (linearly
# interpolated between measured offsets; zero beyond the last).
HIT_CURVE = {
    "bear":   ([0, 1, 2, 3, 5, 8, 12], [1.0, 1.0, 1.0, 1.0, 0.96, 0.58, 0.0]),
    "folder": ([0, 1, 2, 3, 5, 8, 12], [1.0, 0.92, 0.79, 0.46, 0.38, 0.46, 0.0]),
    "bottle": ([0, 1, 2, 3, 5, 8], [0.6, 0.17, 0.58, 0.29, 0.04, 0.0]),
}


def psi(delta, alpha, beta, lapse):
    delta = np.asarray(delta, dtype=float)
    return 0.5 + (0.5 - lapse) * (1.0 - np.exp(-((np.maximum(delta, 1e-9) / alpha) ** beta)))


def hit_prob(delta, curve):
    xs, ys = curve
    return np.interp(np.asarray(delta, dtype=float), xs, ys, left=ys[0], right=0.0)


class ProbabilisticBisection:
    def __init__(self, target_class, pulse_lo=270, pulse_hi=360):
        self.grid = np.arange(pulse_lo, pulse_hi + 1)
        self.post = np.full(len(self.grid), 1.0 / len(self.grid))
        self.psi_p = PSI_PARAMS[target_class]
        self.hit_c = HIT_CURVE[target_class]

    def warm_start(self, u_hat, sigma=6.0):
        """Sharpen the prior around a regressor estimate (optional)."""
        w = np.exp(-0.5 * ((self.grid - u_hat) / sigma) ** 2) + 1e-3
        self.post = w / w.sum()

    def next_query(self):
        cdf = np.cumsum(self.post)
        return int(self.grid[np.searchsorted(cdf, 0.5)])

    def update(self, u, outcome):
        """outcome: 'left' (dot must move left => theta > u since larger
        pulse moves the dot left), 'right' (theta < u), or 'on_target'."""
        delta = np.abs(self.grid - u)
        h = hit_prob(delta, self.hit_c)
        if outcome == "on_target":
            like = np.maximum(h, 1e-6)
        elif outcome in ("left", "right"):
            p_corr = psi(delta, **self.psi_p)
            toward = self.grid > u if outcome == "left" else self.grid < u
            like = (1.0 - h) * np.where(toward, p_corr, 1.0 - p_corr)
            like = np.maximum(like, 1e-9)
        else:
            return  # invisible/unknown: no information
        self.post = self.post * like
        self.post /= self.post.sum()

    def estimate(self):
        return self.next_query()


# ---------------------------------------------------------------------------
# Simulation: synthetic oracle drawn from the same measured curves.
# ---------------------------------------------------------------------------

def oracle(u, u_star, target_class, rng):
    delta = abs(u - u_star)
    if rng.random() < hit_prob(delta, HIT_CURVE[target_class]):
        return "on_target"
    p_corr = float(psi(delta, **PSI_PARAMS[target_class]))
    truth = "left" if u_star > u else "right"  # larger pulse = dot left
    wrong = "right" if truth == "left" else "left"
    return truth if rng.random() < p_corr else wrong


def run_pb(u_star, target_class, rng, max_iters=16, start_offset=8):
    """Fair comparison: PB gets the same warm start (a regressor estimate
    start_offset away from truth) as step-halving. On an on_target answer
    it fuses that information too and re-aims at the posterior median
    (one extra servo move, no extra VLM query)."""
    pb = ProbabilisticBisection(target_class)
    u_hat = u_star + start_offset * rng.choice([-1, 1])
    pb.warm_start(u_hat, sigma=6.0)
    for t in range(1, max_iters + 1):
        u = pb.next_query()
        out = oracle(u, u_star, target_class, rng)
        pb.update(u, out)
        if out == "on_target":
            return t, abs(pb.estimate() - u_star)
    return max_iters, abs(pb.estimate() - u_star)


def run_step_halving(u_star, target_class, rng, max_iters=16,
                     initial_step=15, min_step=3, start_offset=8):
    u = u_star + start_offset * rng.choice([-1, 1])
    step = initial_step
    last_dir = None
    for t in range(1, max_iters + 1):
        out = oracle(u, u_star, target_class, rng)
        if out == "on_target":
            return t, abs(u - u_star)
        if out not in ("left", "right"):
            return t, abs(u - u_star)
        if last_dir is not None and out != last_dir:
            step = max(min_step, step // 2)
        last_dir = out
        u += step if out == "left" else -step
    return max_iters, abs(u - u_star)


def main():
    rng = np.random.default_rng(1)
    n_sims = 2000
    print(f"{n_sims} simulated trials per cell; u* drawn uniformly in [285, 345]")
    print(f"{'target':8s} | {'strategy':14s} | median iters | median terminal err | mean terminal err")
    for target_class in ["bear", "folder", "bottle"]:
        for name, fn in [("bisection", run_pb), ("step-halving", run_step_halving)]:
            iters, errs = [], []
            for _ in range(n_sims):
                u_star = int(rng.integers(285, 346))
                t, e = fn(u_star, target_class, rng)
                iters.append(t)
                errs.append(e)
            print(f"{target_class:8s} | {name:14s} | {np.median(iters):12.1f} | "
                  f"{np.median(errs):19.1f} | {np.mean(errs):17.2f}")


if __name__ == "__main__":
    main()
