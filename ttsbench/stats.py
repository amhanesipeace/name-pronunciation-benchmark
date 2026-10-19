"""Statistical tests for the per-language CER differences.

Why these choices:
  - CER is bounded [0, ~2] and highly skewed (English names are almost all 0),
    so the normality assumption of a t-test does not hold. We use the
    non-parametric **Mann-Whitney U** test (ranks, not means).
  - We report **Cliff's delta** as a distribution-free effect size: statistical
    significance says "there is a difference"; effect size says "how big".
  - For the three per-language comparisons we apply a **Holm-Bonferroni**
    correction, because running multiple tests inflates the false-positive rate.
"""
from __future__ import annotations

import random
from collections import defaultdict
from statistics import mean, median

from scipy.stats import mannwhitneyu


def cers_by_language(rows: list[dict]) -> dict[str, list[float]]:
    by: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        by[r["language"]].append(float(r["cer"]))
    return by


def cliffs_delta(a: list[float], b: list[float]) -> float:
    """Cliff's delta = P(x>y) - P(x<y) for x in a, y in b, range [-1, 1]."""
    gt = lt = 0
    for x in a:
        for y in b:
            if x > y:
                gt += 1
            elif x < y:
                lt += 1
    n = len(a) * len(b)
    return (gt - lt) / n if n else 0.0


def effect_label(delta: float) -> str:
    d = abs(delta)
    if d < 0.147:
        return "negligible"
    if d < 0.33:
        return "small"
    if d < 0.474:
        return "medium"
    return "large"


def english_vs_african(rows: list[dict]) -> dict | None:
    """Pool all non-English names and test African CER > English CER."""
    by = cers_by_language(rows)
    eng = by.get("english", [])
    afr = [c for lang, cers in by.items() if lang != "english" for c in cers]
    if not eng or not afr:
        return None
    u, p = mannwhitneyu(afr, eng, alternative="greater")
    delta = cliffs_delta(afr, eng)
    return {
        "english_n": len(eng), "english_median": median(eng),
        "african_n": len(afr), "african_median": median(afr),
        "U": float(u), "p": float(p),
        "cliffs_delta": delta, "effect": effect_label(delta),
    }


def _percentile(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolated percentile of an already-sorted list (q in [0, 1])."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def bootstrap_ci(fn, samples: tuple[list[float], ...], *, n_boot: int = 2000,
                 confidence: float = 0.95, seed: int = 0) -> dict:
    """Percentile bootstrap confidence interval for an arbitrary statistic.

    Resamples each input sample independently with replacement ``n_boot`` times,
    recomputes ``fn(*resamples)`` each time, and reports the ``confidence``
    central interval of that distribution. The RNG is seeded, so the interval is
    reproducible. ``point`` is the statistic on the observed data.
    """
    pools = [list(s) for s in samples]
    point = fn(*pools)
    if any(len(p) == 0 for p in pools):
        return {"point": point, "lo": point, "hi": point,
                "confidence": confidence, "n_boot": 0}

    rng = random.Random(seed)
    stats = []
    for _ in range(n_boot):
        resamples = [[pool[rng.randrange(len(pool))] for _ in pool] for pool in pools]
        stats.append(fn(*resamples))
    stats.sort()
    alpha = (1 - confidence) / 2
    return {
        "point": point,
        "lo": _percentile(stats, alpha),
        "hi": _percentile(stats, 1 - alpha),
        "confidence": confidence,
        "n_boot": n_boot,
    }


def mean_gap_ci(african: list[float], english: list[float], **kw) -> dict:
    """Bootstrap CI for the mean-CER gap (African − English)."""
    return bootstrap_ci(lambda a, e: mean(a) - mean(e), (african, english), **kw)


def cliffs_delta_ci(african: list[float], english: list[float], **kw) -> dict:
    """Bootstrap CI for Cliff's delta (African vs English)."""
    return bootstrap_ci(lambda a, e: cliffs_delta(a, e), (african, english), **kw)


def english_vs_african_ci(rows: list[dict], **kw) -> dict | None:
    """Mean-gap and Cliff's-delta bootstrap CIs for the pooled comparison.

    Companion to :func:`english_vs_african`: that reports the point estimate and
    significance test; this reports how uncertain the effect is. A gap CI whose
    lower bound stays above 0 is the interval-based counterpart to a significant
    one-sided test.
    """
    by = cers_by_language(rows)
    eng = by.get("english", [])
    afr = [c for lang, cers in by.items() if lang != "english" for c in cers]
    if not eng or not afr:
        return None
    return {
        "gap_ci": mean_gap_ci(afr, eng, **kw),
        "cliffs_delta_ci": cliffs_delta_ci(afr, eng, **kw),
    }


def per_language_vs_english(rows: list[dict], *, ci: bool = True,
                            **boot_kw) -> list[dict]:
    """Each African language vs English, with Holm-Bonferroni corrected p.

    When ``ci`` is true (the default) each result also carries a 95% bootstrap
    confidence interval for its Cliff's delta (``delta_lo``/``delta_hi``), so a
    per-language effect is reported with its uncertainty — consistent with the
    pooled comparison in :func:`english_vs_african_ci`. Pass ``ci=False`` (or
    bootstrap knobs such as ``n_boot``) through ``boot_kw`` to skip or tune it.
    """
    by = cers_by_language(rows)
    eng = by.get("english", [])
    results = []
    for lang in sorted(l for l in by if l != "english"):
        cers = by[lang]
        u, p = mannwhitneyu(cers, eng, alternative="greater")
        delta = cliffs_delta(cers, eng)
        row = {"language": lang, "n": len(cers), "median": median(cers),
               "U": float(u), "p": float(p), "cliffs_delta": delta,
               "effect": effect_label(delta)}
        if ci and cers and eng:
            dci = cliffs_delta_ci(cers, eng, **boot_kw)
            row["delta_lo"] = dci["lo"]
            row["delta_hi"] = dci["hi"]
        results.append(row)

    # Holm-Bonferroni: sort by p ascending, scale by (m - rank), keep monotonic.
    order = sorted(results, key=lambda r: r["p"])
    m = len(order)
    prev = 0.0
    for i, r in enumerate(order):
        holm = min(1.0, r["p"] * (m - i))
        prev = max(prev, holm)
        r["p_holm"] = prev
    return results
