"""Forest plot of the African-English CER gap, with 95% bootstrap CIs, per run.

One figure that unifies the whole results matrix: every engine x condition x n run
is a row showing the mean-CER gap (African - English) as a dot with its 95%
bootstrap confidence interval as a whisker, against a reference line at zero.

The colour encodes significance, not a series identity: a run whose CI stays clear
of zero (a real gap) is drawn in the accent colour; a run whose CI crosses zero
(no reliable gap - the metric-saturated isolated-word baselines) is greyed. This
makes the headline visible at a glance: the bias is real wherever the English
baseline is clean, and only the saturated runs are indistinguishable from zero.

    python forest_plot.py            # writes docs/forest_plot.png

Uses Matplotlib's object-oriented Figure API with the headless Agg backend, so it
renders straight to a PNG (consistent with ttsbench/analyze.py).
"""
from __future__ import annotations

import glob
from pathlib import Path

import matplotlib
matplotlib.use("Agg")            # headless: render straight to a file
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from aggregate_results import summarise

# Colours: significance is a *status*, so two meaning-bearing colours (not a
# cycled series palette), each paired with the legend and the zero line so
# identity is never carried by colour alone.
SIG = "#2f6fed"        # CI excludes 0 -> a real gap
NSIG = "#9aa5b1"       # CI includes 0 -> not distinguishable from zero
ZERO = "#b0b0b0"


def build_rows() -> list[dict]:
    """Every scored run, with gap + 95% CI, sorted engine/condition/n."""
    runs = sorted(Path(p).parent for p in glob.glob("outputs*/scores.csv"))
    rows = [r for r in (summarise(d) for d in runs) if r]
    rows.sort(key=lambda r: (r["engine"], r["condition"], r["n"]))
    return rows


def render(rows: list[dict], out_path: str | Path = "docs/forest_plot.png") -> Path:
    """Draw the forest plot for the given rows and save it to out_path."""
    if not rows:
        raise ValueError("no runs to plot")

    labels = [f"{r['engine']} · {r['condition']} · n={r['n']}" for r in rows]
    # Top row first: reverse the y positions so the list reads top-to-bottom.
    ys = list(range(len(rows) - 1, -1, -1))

    max_hi = max(r["gap_hi"] for r in rows)
    min_lo = min(r["gap_lo"] for r in rows)
    delta_x = max_hi + 0.05                       # x for the Cliff's-delta column

    fig = Figure(figsize=(8.0, 0.52 * len(rows) + 1.6), dpi=120)
    ax = fig.add_subplot(111)
    ax.axvline(0, color=ZERO, lw=1.0, ls="--", zorder=1)

    for y, r in zip(ys, rows):
        significant = r["gap_lo"] > 0
        c = SIG if significant else NSIG
        ax.plot([r["gap_lo"], r["gap_hi"]], [y, y], color=c, lw=2.5,
                solid_capstyle="round", zorder=2)
        ax.plot(r["gap"], y, "o", color=c, ms=7,
                markeredgecolor="white", markeredgewidth=1.0, zorder=3)
        ax.text(delta_x, y, f"{r['delta']:+.2f}", va="center", ha="left",
                fontsize=8, color="#444")

    ax.text(delta_x, ys[0] + 0.75, "Cliff's δ", va="center", ha="left",
            fontsize=8, color="#444", fontweight="bold")

    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_ylim(-0.8, len(rows) - 0.2 + 0.9)
    ax.set_xlim(min(min_lo, 0) - 0.05, delta_x + 0.14)
    ax.set_xlabel("African − English mean CER gap   "
                  "(→ African names pronounced worse)")
    ax.set_title("Name-pronunciation bias gap with 95% bootstrap CIs",
                 fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=0)

    ax.legend(
        handles=[
            Line2D([0], [0], color=SIG, marker="o", lw=2.5, markeredgecolor="white",
                   label="95% CI excludes 0 — real gap"),
            Line2D([0], [0], color=NSIG, marker="o", lw=2.5, markeredgecolor="white",
                   label="95% CI includes 0 — n.s. (saturated)"),
        ],
        fontsize=8, loc="lower right", frameon=False)

    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    return out_path


def main():
    rows = build_rows()
    if not rows:
        print("No scored runs found (outputs*/scores.csv). Run the pipeline first.")
        return
    out = render(rows)
    sig = sum(1 for r in rows if r["gap_lo"] > 0)
    print(f"Plotted {len(rows)} runs ({sig} with a CI clear of zero) -> {out}")


if __name__ == "__main__":
    main()
