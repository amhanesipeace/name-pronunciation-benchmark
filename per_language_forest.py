"""Per-language forest plot: each African language vs English, with 95% CIs.

The master forest plot (`forest_plot.py`) pools all African names per run. This
companion answers the next question a reader asks — *is one language driving the
gap, or are they all affected?* — for a single run. It draws one row per African
language (Yoruba, Igbo, Hausa) showing its **Cliff's delta vs English** as a dot
with a 95% bootstrap confidence interval, against a reference line at zero.

By default it uses `outputs/` (gTTS, isolated), the clean-baseline run where the
English CER is near zero and per-language comparison is most interpretable; pass
another run dir to re-point it.

    python per_language_forest.py                       # docs/per_language_forest.png
    python per_language_forest.py --run outputs_gtts_carrier

Colour encodes significance (Holm-corrected), not series identity, and is paired
with a legend and the zero line, so meaning is never carried by colour alone.
Uses Matplotlib's object-oriented Figure API with the headless Agg backend.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")            # headless: render straight to a file
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from aggregate_results import summarise
from ttsbench.stats import per_language_vs_english

SIG = "#2f6fed"        # Holm-corrected p < 0.05 -> a real gap
NSIG = "#9aa5b1"       # not significant after correction
ZERO = "#b0b0b0"


def build_rows(run_dir: Path) -> list[dict]:
    """Per-language comparison rows (with Cliff's-delta CIs) for one run."""
    scores_path = run_dir / "scores.csv"
    if not scores_path.exists():
        return []
    scores = list(csv.DictReader(open(scores_path, encoding="utf-8")))
    return per_language_vs_english(scores)


def render(rows: list[dict], *, title: str,
           out_path: str | Path = "docs/per_language_forest.png") -> Path:
    """Draw the per-language forest plot and save it to out_path."""
    if not rows:
        raise ValueError("no per-language rows to plot")
    if any("delta_lo" not in r for r in rows):
        raise ValueError("rows lack Cliff's-delta CIs (need per_language_vs_english(ci=True))")

    labels = [r["language"].capitalize() for r in rows]
    # Top row first: reverse the y positions so the list reads top-to-bottom.
    ys = list(range(len(rows) - 1, -1, -1))
    p_x = 1.12                                    # x for the p_holm column

    fig = Figure(figsize=(7.2, 0.6 * len(rows) + 1.7), dpi=120)
    ax = fig.add_subplot(111)
    ax.axvline(0, color=ZERO, lw=1.0, ls="--", zorder=1)

    for y, r in zip(ys, rows):
        significant = r["p_holm"] < 0.05
        c = SIG if significant else NSIG
        ax.plot([r["delta_lo"], r["delta_hi"]], [y, y], color=c, lw=2.5,
                solid_capstyle="round", zorder=2)
        ax.plot(r["cliffs_delta"], y, "o", color=c, ms=8,
                markeredgecolor="white", markeredgewidth=1.0, zorder=3)
        ax.text(p_x, y, f"p={r['p_holm']:.1e}", va="center", ha="left",
                fontsize=8, color="#444")

    ax.text(p_x, ys[0] + 0.6, "Holm p", va="center", ha="left",
            fontsize=8, color="#444", fontweight="bold")

    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_ylim(-0.7, len(rows) - 0.3 + 0.8)
    ax.set_xlim(-0.15, p_x + 0.30)
    ax.set_xlabel("Cliff's δ vs English   (→ this language pronounced worse)")
    ax.set_title(title, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=0)

    ax.legend(
        handles=[
            Line2D([0], [0], color=SIG, marker="o", lw=2.5, markeredgecolor="white",
                   label="significant after Holm correction"),
            Line2D([0], [0], color=NSIG, marker="o", lw=2.5, markeredgecolor="white",
                   label="not significant"),
        ],
        fontsize=8, loc="lower left", frameon=False)

    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default="outputs",
                    help="run directory with scores.csv (default: outputs)")
    ap.add_argument("--out", default="docs/per_language_forest.png")
    args = ap.parse_args()

    run_dir = Path(args.run)
    rows = build_rows(run_dir)
    if not rows:
        print(f"No per-language data in {run_dir}/scores.csv. Run the pipeline first.")
        return

    meta = summarise(run_dir)
    where = f"{meta['engine']} · {meta['condition']}" if meta else run_dir.name
    title = f"Per-language bias vs English — {where}"
    out = render(rows, title=title, out_path=args.out)
    sig = sum(1 for r in rows if r["p_holm"] < 0.05)
    print(f"Plotted {len(rows)} languages ({sig} significant after Holm) -> {out}")


if __name__ == "__main__":
    main()
