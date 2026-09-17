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
from ttsbench.stats import english_vs_african, per_language_vs_english


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

    # --- Statistical significance ---------------------------------------
    rows = load_scores(args.scores)
    lines = ["Statistical test: African vs English name CER",
             "(Mann-Whitney U, one-sided African>English; Cliff's delta effect size)",
             ""]
    overall = english_vs_african(rows)
    if overall:
        lines += [
            f"English:  n={overall['english_n']:>3}  median CER={overall['english_median']:.3f}",
            f"African:  n={overall['african_n']:>3}  median CER={overall['african_median']:.3f}",
            f"Mann-Whitney U={overall['U']:.0f}  p={overall['p']:.2e}",
            f"Cliff's delta={overall['cliffs_delta']:+.3f} ({overall['effect']} effect)",
            "",
            "Per-language vs English (Holm-corrected):",
        ]
        for r in per_language_vs_english(rows):
            sig = "significant" if r["p_holm"] < 0.05 else "n.s."
            lines.append(
                f"  {r['language']:8} n={r['n']:>3} median={r['median']:.3f}  "
                f"p={r['p']:.2e}  p_holm={r['p_holm']:.2e}  "
                f"delta={r['cliffs_delta']:+.3f} ({r['effect']}, {sig})")
    else:
        lines.append("Not enough data (need both English and non-English names).")

    report = "\n".join(lines)
    print("\n" + report)
    stats_path = args.out / "stats.txt"
    stats_path.write_text(report + "\n", encoding="utf-8")

    print(f"\nSummary: {summary_path}")
    print(f"Chart:   {chart_path}")
    print(f"Stats:   {stats_path}")


if __name__ == "__main__":
    main()
