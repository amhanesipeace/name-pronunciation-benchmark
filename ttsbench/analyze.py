"""Aggregate a scores.csv into per-language statistics and a bar chart.

Turns the raw per-name scores into the headline the benchmark is about:
how pronunciation error differs by the name's language of origin.

We use Matplotlib's object-oriented Figure API (not pyplot) and the headless
"Agg" backend, so it renders to a PNG file without needing a display.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

import matplotlib
matplotlib.use("Agg")            # headless: render straight to a file
from matplotlib.figure import Figure


def load_scores(path: str | Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarize(rows: list[dict]) -> list[dict]:
    """Per-language: count, mean CER, std dev, exact-match rate.
    Sorted by mean CER ascending (so English, typically lowest, comes first)."""
    by_lang: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_lang[r["language"]].append(r)

    summary = []
    for lang, group in by_lang.items():
        cers = [float(r["cer"]) for r in group]
        matches = [int(r["exact_match"]) for r in group]
        summary.append({
            "language": lang,
            "n": len(group),
            "mean_cer": mean(cers),
            "std_cer": pstdev(cers) if len(cers) > 1 else 0.0,
            "match_rate": mean(matches),
        })
    summary.sort(key=lambda s: s["mean_cer"])
    return summary


def plot_cer_by_language(summary: list[dict], out_path: str | Path,
                         title: str = "") -> Path:
    """Bar chart of mean CER per language; English is highlighted."""
    langs = [s["language"] for s in summary]
    means = [s["mean_cer"] for s in summary]
    stds = [s["std_cer"] for s in summary]
    # highlight the English (baseline) bar in a different colour
    colors = ["#00b894" if lang == "english" else "#5b8cff" for lang in langs]

    fig = Figure(figsize=(6.4, 4.2), dpi=120)
    ax = fig.add_subplot(111)
    bars = ax.bar(langs, means, yerr=stds, capsize=4, color=colors)
    ax.set_ylabel("Mean Character Error Rate  (lower = better)")
    ax.set_xlabel("Name language of origin")
    ax.set_title(title or "TTS name-pronunciation error by language")
    ax.set_ylim(0, max(means + [0.1]) * 1.3)
    for bar, m in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{m:.2f}", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()

    out_path = Path(out_path)
    fig.savefig(out_path)
    return out_path
