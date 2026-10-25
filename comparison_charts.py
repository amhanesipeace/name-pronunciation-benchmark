"""Regenerate the engine-comparison and carrier-effect bar charts from scores.

These two figures (`docs/engine_comparison.png`, `docs/carrier_effect.png`) were
historically committed without a generator, so they could not be reproduced from
the repo. This script rebuilds both from the committed score tables: a grouped
bar of English vs African mean CER across a chosen set of runs.

    python comparison_charts.py engines    # docs/engine_comparison.png
    python comparison_charts.py carrier     # docs/carrier_effect.png
    python comparison_charts.py all         # both

Reproducible from the committed score tables — no TTS/ASR stack required.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")            # headless: render straight to a file
from matplotlib.figure import Figure

from aggregate_results import summarise

ENGLISH = "#00b894"      # two series (English vs African); every bar is also
AFRICAN = "#5b8cff"      # value-labelled, so colour is never the only cue.

# Named figures: (output, title, [(bar label, run dir), ...]).
FIGURES = {
    "engines": (
        "docs/engine_comparison.png",
        "Name-pronunciation error by TTS engine (English voice, n=80)",
        [("gTTS", "outputs"), ("espeak-ng", "outputs_espeak"),
         ("MMS (neural)", "outputs_mms")],
    ),
    "carrier": (
        "docs/carrier_effect.png",
        "Carrier sentences unmask bias — esp. in the neural engine (n=80)",
        [("gTTS\nisolated", "outputs"), ("gTTS\n+carrier", "outputs_gtts_carrier"),
         ("MMS\nisolated", "outputs_mms"), ("MMS\n+carrier", "outputs_mms_carrier")],
    ),
}


def build_groups(runs: list[tuple[str, str]]) -> list[dict]:
    """[(label, run_dir)] -> [{label, english_cer, african_cer}] via summarise."""
    groups = []
    for label, run in runs:
        s = summarise(Path(run))
        if not s:
            continue
        groups.append({"label": label, "english_cer": s["english_cer"],
                       "african_cer": s["african_cer"]})
    return groups


def render(groups: list[dict], *, title: str, out_path: str | Path) -> Path:
    if not groups:
        raise ValueError("no runs to plot")
    xs = range(len(groups))
    w = 0.38
    fig = Figure(figsize=(max(6.0, 1.7 * len(groups) + 1.5), 5.0), dpi=120)
    ax = fig.add_subplot(111)
    for i, (key, colour, off) in enumerate(
            [("english_cer", ENGLISH, -w / 2), ("african_cer", AFRICAN, w / 2)]):
        for x, g in zip(xs, groups):
            ax.bar(x + off, g[key], width=w, color=colour,
                   label=None if x else ("English names" if i == 0 else "African names"))
            ax.text(x + off, g[key] + 0.015, f"{g[key]:.2f}", ha="center",
                    va="bottom", fontsize=8, color="#333")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([g["label"] for g in groups], fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Mean Character Error Rate (lower = better)")
    ax.set_title(title, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=0)
    ax.legend(fontsize=9, loc="upper left", frameon=False)
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    return out_path


def make(name: str) -> Path:
    out, title, runs = FIGURES[name]
    return render(build_groups(runs), title=title, out_path=out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("which", choices=[*FIGURES, "all"], default="all", nargs="?")
    args = ap.parse_args()
    names = list(FIGURES) if args.which == "all" else [args.which]
    for name in names:
        try:
            print(f"wrote {make(name)}")
        except ValueError as e:
            print(f"skipped {name}: {e}")


if __name__ == "__main__":
    main()
