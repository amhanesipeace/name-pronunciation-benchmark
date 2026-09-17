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

from collections import defaultdict
from statistics import median

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


def per_language_vs_english(rows: list[dict]) -> list[dict]:
    """Each African language vs English, with Holm-Bonferroni corrected p."""
    by = cers_by_language(rows)
    eng = by.get("english", [])
    results = []
    for lang in sorted(l for l in by if l != "english"):
        cers = by[lang]
        u, p = mannwhitneyu(cers, eng, alternative="greater")
        delta = cliffs_delta(cers, eng)
        results.append({"language": lang, "n": len(cers), "median": median(cers),
                        "U": float(u), "p": float(p), "cliffs_delta": delta,
                        "effect": effect_label(delta)})

    # Holm-Bonferroni: sort by p ascending, scale by (m - rank), keep monotonic.
    order = sorted(results, key=lambda r: r["p"])
    m = len(order)
    prev = 0.0
    for i, r in enumerate(order):
        holm = min(1.0, r["p"] * (m - i))
        prev = max(prev, holm)
        r["p_holm"] = prev
    return results
