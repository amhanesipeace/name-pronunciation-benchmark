"""Score a synthesis run: transcribe each clip with ASR and measure error vs
the intended name, then summarise the bias gap by language.

Example:
    python score.py --run outputs_espeak --model base

Reads   <run>/manifest.csv  (+ the audio it points to)
Writes  <run>/scores.csv    (per-name transcription + CER + exact match)
Prints  a per-language summary and the English-vs-African CER gap.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

from ttsbench.scoring import Transcriber, char_error_rate, normalize


def main():
    ap = argparse.ArgumentParser(
        description="Score a synthesis run via ASR back-transcription")
    ap.add_argument("--run", type=Path, required=True,
                    help="run directory containing manifest.csv + audio/")
    ap.add_argument("--model", default="base",
                    help="faster-whisper model size: tiny|base|small (default: base)")
    args = ap.parse_args()

    manifest = args.run / "manifest.csv"
    with open(manifest, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["status"] == "ok"]

    print(f"Loading Whisper model '{args.model}' (first run downloads it)...\n")
    transcriber = Transcriber(args.model)

    scored = []
    for r in rows:
        audio = args.run / r["audio_path"]
        heard = transcriber.transcribe(audio)
        cer = char_error_rate(r["name"], heard)
        match = int(normalize(heard) == normalize(r["name"]))
        scored.append({
            "id": r["id"], "name": r["name"], "language": r["language"],
            "engine": r["engine"], "transcription": heard,
            "cer": round(cer, 3), "exact_match": match,
        })
        print(f"  {r['language']:8} {r['name']:14} heard as {heard!r:26} "
              f"CER={cer:.2f}{'  <-- miss' if not match else '  ok'}")

    # Write per-name scores.
    out_path = args.run / "scores.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "name", "language", "engine",
            "transcription", "cer", "exact_match"])
        writer.writeheader()
        writer.writerows(scored)

    # Per-language summary.
    by_lang = defaultdict(list)
    for s in scored:
        by_lang[s["language"]].append(s)

    print("\n=== Bias summary (lower CER = better) ===")
    print(f"{'language':10}{'n':>4}{'mean_CER':>10}{'match_rate':>12}")
    for lang in sorted(by_lang):
        g = by_lang[lang]
        print(f"{lang:10}{len(g):>4}{mean(x['cer'] for x in g):>10.2f}"
              f"{mean(x['exact_match'] for x in g):>12.0%}")

    eng = [x["cer"] for x in scored if x["language"] == "english"]
    afr = [x["cer"] for x in scored if x["language"] != "english"]
    if eng and afr:
        print(f"\nEnglish mean CER: {mean(eng):.2f}   "
              f"African mean CER: {mean(afr):.2f}   "
              f"gap: {mean(afr) - mean(eng):+.2f}")
    print(f"\nScores written to {out_path}")


if __name__ == "__main__":
    main()
