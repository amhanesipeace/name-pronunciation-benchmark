"""Qualitative error analysis — turn scores into concrete, memorable examples.

Reads a scores.csv and reports, per language, the names the TTS handled worst
(highest CER) and what the ASR actually heard — e.g. Oluwaseun -> "Alois
Seyoon". Numbers show *that* there's bias; these examples show *what it sounds
like*, which is what makes the finding land.

Example:
    python error_analysis.py --scores outputs/scores.csv --top 5

Prints a Markdown table and (with --out) writes it to a file.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Per-language worst-pronunciation examples")
    ap.add_argument("--scores", type=Path, required=True)
    ap.add_argument("--top", type=int, default=5, help="worst-N per language")
    ap.add_argument("--out", type=Path, help="optional Markdown output file")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.scores, encoding="utf-8")))
    by_lang = defaultdict(list)
    for r in rows:
        r["cer"] = float(r["cer"])
        by_lang[r["language"]].append(r)

    lines = ["# Error analysis — worst-pronounced names by language", ""]
    # English first (usually the clean baseline), then the rest.
    order = (["english"] if "english" in by_lang else []) + \
            sorted(l for l in by_lang if l != "english")

    for lang in order:
        group = sorted(by_lang[lang], key=lambda r: r["cer"], reverse=True)
        worst = group[:args.top]
        avg = sum(r["cer"] for r in group) / len(group)
        lines.append(f"## {lang.capitalize()}  (mean CER {avg:.2f}, n={len(group)})")
        lines.append("")
        lines.append("| name | heard as | CER |")
        lines.append("|------|----------|----:|")
        for r in worst:
            heard = r["transcription"].strip() or "—"
            lines.append(f"| {r['name']} | \"{heard}\" | {r['cer']:.2f} |")
        lines.append("")

    report = "\n".join(lines)
    print(report)
    if args.out:
        args.out.write_text(report + "\n", encoding="utf-8")
        print(f"\nWritten to {args.out}")


if __name__ == "__main__":
    main()
