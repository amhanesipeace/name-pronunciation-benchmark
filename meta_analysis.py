"""Pool the per-engine bias into one estimate — a random-effects meta-analysis.

`forest_plot.py` *displays* every engine's African-English gap side by side; it
does not combine them. This asks the next question a reader asks of several
independent systems: **what is the overall effect, and how consistent is it
across engines?** We pool the three independent TTS systems (gTTS, espeak-ng,
Meta MMS) with a DerSimonian-Laird random-effects model and report the pooled
effect, its confidence interval, and formal heterogeneity (Q, I-squared, tau^2).

Why Cliff's delta is the quantity we pool. The *mean-CER gap* is not comparable
across engines: espeak and isolated MMS saturate the ASR metric (their English
baselines are already poor), so a gap in their compressed CER scale means
something different from a gap in gTTS's clean scale. Cliff's delta is a
rank-based, scale-free effect size in [-1, 1], so it is comparable across engines
even when absolute CER is not — the same reason the per-name analyses
(`hardest_names.py`, `cross_engine.py`) rank rather than average.

What the pool is honest about. A random-effects model (not fixed-effect) is the
right choice precisely because the engines are *not* estimating one identical
number: a clean-baseline engine shows a large delta and a saturated one a small
delta, so between-engine heterogeneity is expected and is reported, not hidden.
The scientific claim the pool supports is directional consistency plus a positive
combined effect, with magnitude that depends on baseline quality.

    python meta_analysis.py              # writes docs/meta_analysis.md + prints

Reproducible from the committed score tables for the three engines — no TTS/ASR
stack required. Uses scipy only for the chi-square heterogeneity p-value.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from scipy.stats import chi2

from ttsbench.stats import (cers_by_language, cliffs_delta_ci, effect_label)

# The three distinct engines at n=80, isolated-word condition — genuinely
# independent systems (two commercial/neural, one formant synthesiser).
DEFAULT_RUNS = {"gTTS": "outputs", "eSpeak": "outputs_espeak", "MMS": "outputs_mms"}

# A standard error can be driven to ~0 by a degenerate bootstrap (e.g. a fully
# saturated baseline); floor it so a single study cannot take infinite weight.
_SE_FLOOR = 1e-6


def load_run(run_dir: Path) -> list[dict]:
    rows = []
    for r in csv.DictReader(open(run_dir / "scores.csv", encoding="utf-8")):
        rows.append({"id": r["id"], "name": r["name"],
                     "language": r["language"], "cer": float(r["cer"])})
    return rows


def _split(rows: list[dict]) -> tuple[list[float], list[float]]:
    """(african_cers, english_cers) for one run."""
    by = cers_by_language(rows)
    eng = by.get("english", [])
    afr = [c for lang, cers in by.items() if lang != "english" for c in cers]
    return afr, eng


def engine_effect(label: str, rows: list[dict], *, n_boot: int = 2000,
                  seed: int = 0) -> dict | None:
    """One engine's Cliff's delta (African vs English) with a bootstrap SE.

    Returns the point estimate, its bootstrap standard error (used as the
    study's within-engine uncertainty in the pool), the 95% CI, the sample
    sizes, and the qualitative effect label. ``None`` if a group is empty.
    """
    afr, eng = _split(rows)
    if not afr or not eng:
        return None
    ci = cliffs_delta_ci(afr, eng, n_boot=n_boot, seed=seed)
    return {
        "label": label,
        "delta": ci["point"],
        "se": max(ci["se"], _SE_FLOOR),
        "lo": ci["lo"],
        "hi": ci["hi"],
        "n_african": len(afr),
        "n_english": len(eng),
        "effect": effect_label(ci["point"]),
    }


def random_effects(studies: list[dict]) -> dict | None:
    """DerSimonian-Laird random-effects pool of per-engine effect sizes.

    Each study contributes an effect ``delta`` and a within-study variance
    ``se**2``. We estimate the between-study variance ``tau^2`` from Cochran's Q,
    then combine with random-effects weights ``1 / (v_i + tau^2)``. Returns the
    pooled estimate with a 95% CI, plus the heterogeneity statistics Q (with its
    chi-square p-value), I-squared (share of variance that is between-engine, not
    sampling noise), and tau^2. Needs at least two studies.
    """
    k = len(studies)
    if k < 2:
        return None
    deltas = [s["delta"] for s in studies]
    variances = [s["se"] ** 2 for s in studies]

    # Fixed-effect weights and weighted mean (the basis for Cochran's Q).
    w = [1.0 / v for v in variances]
    sum_w = sum(w)
    theta_fixed = sum(wi * d for wi, d in zip(w, deltas)) / sum_w

    # Cochran's Q and the DerSimonian-Laird between-study variance tau^2.
    q = sum(wi * (d - theta_fixed) ** 2 for wi, d in zip(w, deltas))
    df = k - 1
    c = sum_w - sum(wi ** 2 for wi in w) / sum_w
    tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0

    # Random-effects weights, pooled estimate, and its CI.
    w_star = [1.0 / (v + tau2) for v in variances]
    sum_wstar = sum(w_star)
    theta = sum(wi * d for wi, d in zip(w_star, deltas)) / sum_wstar
    se = math.sqrt(1.0 / sum_wstar)

    i2 = max(0.0, (q - df) / q) * 100 if q > 0 else 0.0
    p_het = float(chi2.sf(q, df)) if df > 0 else float("nan")
    return {
        "k": k,
        "pooled_delta": theta,
        "se": se,
        "lo": theta - 1.96 * se,
        "hi": theta + 1.96 * se,
        "effect": effect_label(theta),
        "Q": q,
        "df": df,
        "p_heterogeneity": p_het,
        "I2": i2,
        "tau2": tau2,
    }


def meta_analyze(runs: dict[str, list[dict]], *, n_boot: int = 2000,
                 seed: int = 0) -> dict:
    """Per-engine effects plus the random-effects pool across them."""
    studies = []
    for label, rows in runs.items():
        eff = engine_effect(label, rows, n_boot=n_boot, seed=seed)
        if eff:
            studies.append(eff)
    return {"studies": studies, "pooled": random_effects(studies)}


def _p_txt(p: float) -> str:
    if p != p:  # nan
        return "n/a"
    return "< 0.001" if p < 0.001 else f"= {p:.3f}"


def report(runs: dict[str, list[dict]], *, n_boot: int = 2000,
           seed: int = 0) -> str:
    res = meta_analyze(runs, n_boot=n_boot, seed=seed)
    studies, pooled = res["studies"], res["pooled"]
    lines = [
        "# Pooling the bias across engines: a random-effects meta-analysis",
        "",
        "Generated by `meta_analysis.py` from the committed scores for "
        f"{len(studies)} independent TTS systems "
        f"({', '.join(s['label'] for s in studies)}), isolated-word condition. "
        "The effect size is **Cliff's delta** (African vs English CER), a "
        "rank-based, scale-free measure that is comparable across engines even "
        "though their absolute CER scales are not (espeak and isolated MMS "
        "saturate the ASR metric). Each engine's within-system uncertainty is a "
        f"seeded bootstrap standard error ({n_boot} resamples); the engines are "
        "combined with a DerSimonian-Laird **random-effects** model.",
        "",
        "## Per-engine effect sizes",
        "",
        "| Engine | n (Afr/Eng) | Cliff's δ | 95% CI | Effect |",
        "| --- | --- | --: | --- | --- |",
    ]
    for s in studies:
        lines.append(
            f"| {s['label']} | {s['n_african']}/{s['n_english']} | "
            f"{s['delta']:+.3f} | [{s['lo']:+.3f}, {s['hi']:+.3f}] | {s['effect']} |")
    lines.append("")

    if pooled is None:
        lines += ["_Need at least two engines to pool._", ""]
        return "\n".join(lines)

    lines += [
        "## Pooled (random-effects)",
        "",
        f"**Combined Cliff's δ = {pooled['pooled_delta']:+.3f}** "
        f"(95% CI [{pooled['lo']:+.3f}, {pooled['hi']:+.3f}], "
        f"{pooled['effect']} effect), pooling {pooled['k']} engines.",
        "",
        f"- **Heterogeneity:** Q = {pooled['Q']:.2f} on {pooled['df']} df "
        f"(p {_p_txt(pooled['p_heterogeneity'])}), "
        f"I² = {pooled['I2']:.0f}%, τ² = {pooled['tau2']:.3f}.",
        "",
    ]
    direction = all(s["delta"] > 0 for s in studies)
    ci_clear = pooled["lo"] > 0
    interp = []
    if ci_clear:
        interp.append(
            "The pooled interval stays above zero, so the combined evidence for an "
            "African-English gap is positive across independent systems.")
    else:
        interp.append(
            "The pooled interval includes zero, so the *combined* estimate is not "
            "on its own conclusive — read it alongside the clean-baseline engine.")
    if direction:
        interp.append("Every engine points the same way (δ > 0).")
    if pooled["I2"] >= 50:
        interp.append(
            f"But heterogeneity is high (I² = {pooled['I2']:.0f}%): the engines are "
            "**not** estimating one common number. This is expected and is the "
            "point of using a random-effects model — magnitude tracks baseline "
            "quality (a clean-baseline engine shows a large delta; a metric-"
            "saturated one a small delta), while direction is consistent. The "
            "honest reading is a consistent *direction* with engine-dependent "
            "*magnitude*, not a single universal effect size.")
    lines += [" ".join(interp), ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", nargs="+", default=None,
                    help="label=dir pairs; default the three isolated runs")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="docs/meta_analysis.md")
    args = ap.parse_args()

    spec = DEFAULT_RUNS
    if args.runs:
        spec = dict(pair.split("=", 1) for pair in args.runs)
    try:
        runs = {label: load_run(Path(d)) for label, d in spec.items()}
    except FileNotFoundError as exc:
        print(f"Missing scores for a run ({exc}). Score those engines first.")
        return
    text = report(runs, n_boot=args.n_boot, seed=args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"Written to {out}")


if __name__ == "__main__":
    main()
