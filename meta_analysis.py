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

import matplotlib
matplotlib.use("Agg")            # headless: render straight to a file
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
from scipy.stats import chi2

from ttsbench.stats import (cers_by_language, cliffs_delta_ci, effect_label)

# Status colours (not a series palette): significance is a state. Reused from
# forest_plot.py so the two figures read as one system, already palette-validated.
SIG = "#2f6fed"        # CI excludes 0 -> a real gap
NSIG = "#9aa5b1"       # CI includes 0 -> not distinguishable from zero
POOLED = "#111827"     # the random-effects summary diamond (its own dark ink)
ZERO = "#b0b0b0"

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


def render_figure(studies: list[dict], pooled: dict | None,
                  out_path: str | Path = "docs/meta_analysis.png") -> Path:
    """Classic meta-analysis forest plot: per-engine effects + a pooled diamond.

    Each engine is a dot at its Cliff's delta with a 95% CI whisker, coloured by
    whether that CI clears zero; the random-effects summary is drawn as the
    conventional diamond at the bottom, its width the pooled 95% CI. A dashed zero
    line and a heterogeneity annotation (I-squared) make the honest reading — a
    consistent direction but heterogeneous magnitude — legible at a glance.
    """
    if not studies:
        raise ValueError("no studies to plot")
    rows = list(studies)
    n = len(rows) + (1 if pooled else 0)

    # Engines top-to-bottom, pooled diamond on the bottom row (y=0).
    ys = list(range(n - 1, (1 if pooled else 0) - 1, -1))
    his = [s["hi"] for s in rows] + ([pooled["hi"]] if pooled else [])
    los = [s["lo"] for s in rows] + ([pooled["lo"]] if pooled else [])
    delta_x = max(his) + 0.06

    fig = Figure(figsize=(8.0, 0.52 * n + 1.7), dpi=120)
    ax = fig.add_subplot(111)
    ax.axvline(0, color=ZERO, lw=1.0, ls="--", zorder=1)

    for y, s in zip(ys, rows):
        c = SIG if s["lo"] > 0 else NSIG
        ax.plot([s["lo"], s["hi"]], [y, y], color=c, lw=2.5,
                solid_capstyle="round", zorder=2)
        ax.plot(s["delta"], y, "o", color=c, ms=7,
                markeredgecolor="white", markeredgewidth=1.0, zorder=3)
        ax.text(delta_x, y, f"{s['delta']:+.2f}", va="center", ha="left",
                fontsize=8, color="#444")

    labels = [s["label"] for s in rows]
    if pooled:
        # The summary diamond: centre at the pooled estimate, span = 95% CI.
        cx, lo, hi = pooled["pooled_delta"], pooled["lo"], pooled["hi"]
        h = 0.3
        ax.add_patch(Polygon([(lo, 0), (cx, h), (hi, 0), (cx, -h)],
                             closed=True, facecolor=POOLED, edgecolor="white",
                             linewidth=1.0, zorder=3))
        ax.text(delta_x, 0, f"{cx:+.2f}", va="center", ha="left",
                fontsize=8, color="#111", fontweight="bold")
        labels = labels + ["Pooled (RE)"]
        ax.text(min(los + [0]) - 0.04, 0 - 0.62,
                f"Heterogeneity: I² = {pooled['I2']:.0f}%  "
                f"(Q = {pooled['Q']:.1f}, p {_p_txt(pooled['p_heterogeneity'])})",
                va="center", ha="left", fontsize=7.5, color="#666", style="italic")

    ax.text(delta_x, ys[0] + 0.8, "δ", va="center", ha="left",
            fontsize=8, color="#444", fontweight="bold")
    yticks = ys + ([0] if pooled else [])
    ax.set_yticks(yticks)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_ylim(-1.1, n - 0.2 + 0.9)
    ax.set_xlim(min(los + [0]) - 0.08, delta_x + 0.14)
    ax.set_xlabel("Cliff's δ (African vs English CER)   "
                  "(→ African names pronounced worse)")
    ax.set_title("Pooling the bias across engines (random-effects meta-analysis)",
                 fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=0)

    ax.legend(
        handles=[
            Line2D([0], [0], color=SIG, marker="o", lw=2.5, markeredgecolor="white",
                   label="engine: 95% CI excludes 0"),
            Line2D([0], [0], color=NSIG, marker="o", lw=2.5, markeredgecolor="white",
                   label="engine: 95% CI includes 0 (saturated)"),
            Line2D([0], [0], color=POOLED, marker="D", lw=0, markersize=8,
                   markeredgecolor="white", label="pooled random-effects estimate"),
        ],
        fontsize=8, loc="upper left", frameon=False)

    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    return out_path


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
    ap.add_argument("--figure", default="docs/meta_analysis.png")
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

    res = meta_analyze(runs, n_boot=args.n_boot, seed=args.seed)
    if res["studies"]:
        fig = render_figure(res["studies"], res["pooled"], args.figure)
        print(f"Figure written to {fig}")


if __name__ == "__main__":
    main()
