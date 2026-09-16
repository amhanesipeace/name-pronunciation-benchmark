"""Analyze a scored run: per-language stats + a bar chart.

Example:
    python analyze.py --scores outputs/scores.csv --out outputs/analysis \
                      --title "gTTS (English voice)"

Reads   a scores.csv (from score.py)
Writes  <out>/summary.csv  and  <out>/cer_by_language.png
Prints  the per-language summary table.
"""
import argparse
import csv
from pathlib import Path

from ttsbench.analyze import load_scores, summarize, plot_cer_by_language


def main():
    ap = argparse.ArgumentParser(
        description="Aggregate scores.csv into per-language stats + a chart")
    ap.add_argument("--scores", type=Path, default="outputs/scores.csv")
    ap.add_argument("--out", type=Path, default="outputs/analysis")
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    summary = summarize(load_scores(args.scores))

    print(f"{'language':10}{'n':>4}{'mean_CER':>10}{'match_rate':>12}")
    for s in summary:
        print(f"{s['language']:10}{s['n']:>4}{s['mean_cer']:>10.2f}"
              f"{s['match_rate']:>12.0%}")

    summary_path = args.out / "summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "language", "n", "mean_cer", "std_cer", "match_rate"])
        writer.writeheader()
        writer.writerows(summary)

    chart_path = plot_cer_by_language(summary, args.out / "cer_by_language.png",
                                     args.title)

    eng = next((s for s in summary if s["language"] == "english"), None)
    afr = [s for s in summary if s["language"] != "english"]
    if eng and afr:
        afr_mean = sum(s["mean_cer"] for s in afr) / len(afr)
        print(f"\nEnglish mean CER {eng['mean_cer']:.2f} vs African "
              f"{afr_mean:.2f}  (gap {afr_mean - eng['mean_cer']:+.2f})")

    print(f"\nSummary: {summary_path}")
    print(f"Chart:   {chart_path}")


if __name__ == "__main__":
    main()
