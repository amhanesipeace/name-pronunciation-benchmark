"""Phoneme-level scoring of a synthesis run — ASR-independent.

Reads phones directly from each clip with a universal phoneme recogniser
(allosaurus), and — where a reference pronunciation exists in the dataset's
`ipa` column — measures a Phoneme Error Rate (PER) against it.

Example:
    python phoneme_score.py --run outputs --names data/names.csv

Writes  <run>/phoneme_scores.csv  (recognised phones + PER where a ref exists)
Prints  per-language PER summary and reference coverage.

NOTE: run this on an ISOLATED-name synthesis (no --carrier), so the recognised
phones correspond to the name alone. References for African-language names must
be supplied/validated by native speakers (the `ipa` column); until then PER is
reported only for names that carry a trusted reference.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

from ttsbench.phonemes import recognize_phones, phoneme_error_rate


def main():
    ap = argparse.ArgumentParser(description="ASR-independent phoneme scoring")
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--names", type=Path, default="data/names.csv")
    args = ap.parse_args()

    refs = {r["id"]: r.get("ipa", "").strip()
            for r in csv.DictReader(open(args.names, encoding="utf-8"))}

    with open(args.run / "manifest.csv", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["status"] == "ok"]

    print("Recognising phones (allosaurus; first run downloads a small model)...\n")
    scored = []
    for r in rows:
        phones = recognize_phones(args.run / r["audio_path"])
        ref = refs.get(r["id"], "")
        per = round(phoneme_error_rate(ref, phones), 3) if ref else ""
        scored.append({
            "id": r["id"], "name": r["name"], "language": r["language"],
            "engine": r["engine"], "reference_ipa": ref,
            "recognised_phones": phones, "per": per,
        })
        per_str = f"PER={per:.2f}" if ref else "PER=  (no ref)"
        print(f"  {r['language']:8} {r['name']:14} {per_str:16} phones: {phones}")

    out_path = args.run / "phoneme_scores.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "id", "name", "language", "engine",
            "reference_ipa", "recognised_phones", "per"])
        w.writeheader()
        w.writerows(scored)

    # Summary: PER by language (where references exist) + coverage.
    by_lang = defaultdict(list)
    for s in scored:
        by_lang[s["language"]].append(s)

    print("\n=== Phoneme Error Rate by language (lower = better) ===")
    print(f"{'language':10}{'n':>4}{'with_ref':>10}{'mean_PER':>10}")
    for lang in sorted(by_lang):
        g = by_lang[lang]
        withref = [s for s in g if s["per"] != ""]
        per = f"{mean(s['per'] for s in withref):.2f}" if withref else "—"
        print(f"{lang:10}{len(g):>4}{len(withref):>10}{per:>10}")

    missing = sorted({s["language"] for s in scored if s["per"] == ""})
    if missing:
        print(f"\nNo reference IPA yet for: {', '.join(missing)} — these need "
              "native-speaker–validated pronunciations before PER is meaningful.")
    print(f"\nPhoneme scores written to {out_path}")


if __name__ == "__main__":
    main()
