"""Cross-engine agreement: is a name's difficulty intrinsic, or vendor-specific?

If two *independent* TTS systems trip over the *same* names, the difficulty is
largely a property of the name's phonology, not one vendor's bug. We test this by
correlating the per-name Character Error Rate of two runs that cover the same
names, using Spearman's rank correlation (CER is bounded and skewed).

The fair comparison is the **carrier** condition for both engines (the isolated
MMS run is metric-saturated — everything scores badly — so its per-name signal is
noise). We report the correlation across all names and, separately, within the
African names alone (where the English baseline can't inflate agreement), and
draw a scatter of the two engines' per-name CER.

    python cross_engine.py            # docs/cross_engine_carrier.png + numbers

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
from scipy.stats import spearmanr

ENGLISH = "#2f6fed"      # origin is the meaning, shown with a legend (not colour-alone)
AFRICAN = "#c2410c"
DIAG = "#b0b0b0"


def load(run_dir: Path) -> dict[str, dict]:
    path = run_dir / "scores.csv"
    if not path.exists():
        return {}
    return {r["id"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}


def paired(a: dict[str, dict], b: dict[str, dict]) -> list[dict]:
    """Names scored by both runs, as {id, name, language, cer_a, cer_b}."""
    rows = []
    for i in sorted(set(a) & set(b)):
        if a[i]["name"] != b[i]["name"]:
            continue
        rows.append({"id": i, "name": a[i]["name"], "language": a[i]["language"],
                     "cer_a": float(a[i]["cer"]), "cer_b": float(b[i]["cer"])})
    return rows


def correlations(rows: list[dict]) -> dict:
    """Spearman rho (+ p, n) over all pairs and over African names only."""
    def rho(subset):
        if len(subset) < 3:
            return {"rho": float("nan"), "p": float("nan"), "n": len(subset)}
        r = spearmanr([x["cer_a"] for x in subset], [x["cer_b"] for x in subset])
        return {"rho": float(r.correlation), "p": float(r.pvalue), "n": len(subset)}
    afr = [x for x in rows if x["language"] != "english"]
    return {"all": rho(rows), "african": rho(afr)}


def render(rows: list[dict], corr: dict, *, label_a: str, label_b: str,
           out_path: str | Path = "docs/cross_engine_carrier.png") -> Path:
    if not rows:
        raise ValueError("no paired names to plot")

    fig = Figure(figsize=(6.4, 6.0), dpi=120)
    ax = fig.add_subplot(111)
    ax.plot([0, 1], [0, 1], ls="--", color=DIAG, lw=1.0, zorder=1)  # equal-difficulty

    for x in rows:
        c = ENGLISH if x["language"] == "english" else AFRICAN
        ax.plot(x["cer_a"], x["cer_b"], "o", color=c, ms=7, alpha=0.75,
                markeredgecolor="white", markeredgewidth=0.8, zorder=2)

    a, af = corr["all"], corr["african"]
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.03, 1.03)
    ax.set_aspect("equal")
    ax.set_xlabel(f"{label_a} — per-name CER")
    ax.set_ylabel(f"{label_b} — per-name CER")
    ax.set_title("Do independent engines trip over the same names?", fontsize=12)
    ax.text(0.40, 0.14,
            f"Spearman ρ = {a['rho']:.2f} (all, p={a['p']:.1e})\n"
            f"ρ = {af['rho']:.2f} (African only, p={af['p']:.1e})",
            transform=ax.transAxes, va="center", ha="left", fontsize=9, color="#333")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=0)

    ax.legend(
        handles=[
            Line2D([0], [0], color=ENGLISH, marker="o", lw=0, markeredgecolor="white",
                   label="English names"),
            Line2D([0], [0], color=AFRICAN, marker="o", lw=0, markeredgecolor="white",
                   label="African names"),
            Line2D([0], [0], color=DIAG, ls="--", lw=1.0, label="equal difficulty"),
        ],
        fontsize=8, loc="lower right", frameon=False)

    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-a", default="outputs_gtts_carrier")
    ap.add_argument("--run-b", default="outputs_mms_carrier")
    ap.add_argument("--out", default="docs/cross_engine_carrier.png")
    args = ap.parse_args()

    a, b = load(Path(args.run_a)), load(Path(args.run_b))
    rows = paired(a, b)
    if not rows:
        print(f"No names shared by {args.run_a} and {args.run_b}. Run the pipeline first.")
        return
    corr = correlations(rows)
    label_a = Path(args.run_a).name.replace("outputs_", "").replace("_", " ")
    label_b = Path(args.run_b).name.replace("outputs_", "").replace("_", " ")
    out = render(rows, corr, label_a=label_a, label_b=label_b, out_path=args.out)
    for k in ("all", "african"):
        c = corr[k]
        print(f"{k:8} Spearman rho={c['rho']:+.3f}  p={c['p']:.2e}  n={c['n']}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
