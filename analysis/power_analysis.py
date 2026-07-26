"""Power analysis for the per-category 'stating the policy changes ASR' effect.

Question: at what per-category scenario count n can we resolve the none ->
advisory change, given the effect sizes we observed at n=6?

Method: treat each scenario's observed rate_none / rate_advisory as that
scenario's true success probability, resample n scenarios with replacement,
draw TRIALS Bernoulli trials per posture per scenario, and test the paired
scenario-level deltas with a sign-flip permutation test. Power = fraction of
simulations reaching p < alpha. Fully vectorised across simulations.
"""
import json

import numpy as np

RESULTS = "results/leaderboard_final.json"
TRIALS = 3
ALPHA = 0.05
NSIM = 3000
NPERM = 600
RNG = np.random.default_rng(0)


def perm_p_batch(deltas: np.ndarray) -> np.ndarray:
    """Sign-flip permutation p-values for a batch of paired-delta vectors.

    deltas: (nsim, n). Returns (nsim,) two-sided p-values.
    """
    nsim, n = deltas.shape
    obs = np.abs(deltas.mean(axis=1))
    signs = RNG.choice([1.0, -1.0], size=(NPERM, n))
    # (nsim, NPERM) mean of each sign-flipped permutation
    dist = np.abs(deltas @ signs.T) / n
    return (dist >= obs[:, None] - 1e-12).mean(axis=1)


def simulate(p_none: np.ndarray, p_adv: np.ndarray, n: int) -> float:
    idx = RNG.integers(0, len(p_none), size=(NSIM, n))
    a = RNG.binomial(TRIALS, p_none[idx]) / TRIALS
    b = RNG.binomial(TRIALS, p_adv[idx]) / TRIALS
    return float((perm_p_batch(b - a) < ALPHA).mean())


def load(model_name: str, category: str):
    d = json.load(open(RESULTS, encoding="utf-8"))
    m = [x for x in d["models"] if x["model"] == model_name][0]
    sc = [s for s in m["scenarios"] if s.get("category") == category]
    return (np.array([s["rate_none"] for s in sc]),
            np.array([s["rate_advisory"] for s in sc]))


if __name__ == "__main__":
    grid = [6, 10, 15, 20, 30, 40, 60]
    for category in ["T5_dual_approval_defeat", "T4_structuring"]:
        print(f"\n{'='*78}\n{category}   (trials/scenario={TRIALS}, alpha={ALPHA})\n{'='*78}")
        print(f"{'model':<24}{'none':>7}{'adv':>7}{'delta':>8}{'p@n=6':>8}   "
              + "".join(f"n={n:<5}" for n in grid))
        for model in ["gpt-4o-mini", "qwen3:8b", "gpt-4o", "claude-haiku-4-5-20251001",
                      "llama-3.1-8b-instant"]:
            try:
                p_none, p_adv = load(model, category)
            except (IndexError, KeyError):
                continue
            if len(p_none) == 0:
                continue
            d0 = (p_adv - p_none)[None, :]
            p_obs = perm_p_batch(d0)[0]
            powers = [simulate(p_none, p_adv, n) for n in grid]
            print(f"{model:<24}{p_none.mean():>7.2f}{p_adv.mean():>7.2f}"
                  f"{(p_adv-p_none).mean():>+8.3f}{p_obs:>8.3f}   "
                  + "".join(f"{p:<7.2f}" for p in powers))
