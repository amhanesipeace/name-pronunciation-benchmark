"""Sensitivity analysis: is the measured bias robust to the ASR scorer?

Re-scores one synthesis run with several faster-whisper model sizes and reports
the English-vs-African CER gap for each. The audio is identical across rows — only
the recognizer changes — so a gap that holds across model sizes is a property of
the TTS system, not an artefact of one particular recognizer. This addresses the
"you only used one ASR scorer" limitation directly.

    python sensitivity.py --run outputs --models tiny base small
"""
import argparse
import csv
from pathlib import Path
from statistics import mean

from ttsbench.scoring import (Transcriber, char_error_rate, strip_carrier)
from ttsbench.stats import english_vs_african, mean_gap_ci


def score_run(run_dir: Path, model_size: str) -> list[dict]:
    """Transcribe every clip in a run with one model size; return CER rows."""
    with open(run_dir / "manifest.csv", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["status"] == "ok"]
    transcriber = Transcriber(model_size)
    scored = []
    for r in rows:
        heard_full = transcriber.transcribe(run_dir / r["audio_path"])
        carrier = r.get("carrier", "")
        heard = strip_carrier(heard_full, carrier) if carrier else heard_full
        scored.append({
            "name": r["name"], "language": r["language"],
            "cer": round(char_error_rate(r["name"], heard), 3),
        })
    return scored


def main():
    ap = argparse.ArgumentParser(
        description="Re-score a run with multiple Whisper sizes (robustness check)")
    ap.add_argument("--run", type=Path, default=Path("outputs"),
                    help="run directory with manifest.csv + audio/ (default: outputs)")
    ap.add_argument("--models", nargs="+", default=["tiny", "base", "small"],
                    help="faster-whisper sizes to compare (default: tiny base small)")
    ap.add_argument("--out", type=Path, default=Path("docs/sensitivity_whisper.md"))
    args = ap.parse_args()

    results = []
    for model in args.models:
        print(f"\n=== Scoring {args.run} with Whisper '{model}' "
              f"(first use downloads it) ===")
        scored = score_run(args.run, model)
        eng = [s["cer"] for s in scored if s["language"] == "english"]
        afr = [s["cer"] for s in scored if s["language"] != "english"]
        stat = english_vs_african(scored)
        ci = mean_gap_ci(afr, eng)
        results.append({
            "model": model, "n": len(scored),
            "english_cer": mean(eng), "african_cer": mean(afr),
            "gap": mean(afr) - mean(eng),
            "gap_lo": ci["lo"], "gap_hi": ci["hi"],
            "delta": stat["cliffs_delta"], "effect": stat["effect"],
            "p": stat["p"],
        })
        print(f"  English {mean(eng):.2f} | African {mean(afr):.2f} | "
              f"gap +{mean(afr) - mean(eng):.2f} [{ci['lo']:.2f}, {ci['hi']:.2f}] | "
              f"delta {stat['cliffs_delta']:+.2f} ({stat['effect']}) | p {stat['p']:.1e}")

    robust = all(r["gap_lo"] > 0 for r in results)
    if robust:
        takeaway = (
            "**Takeaway:** the African–English gap stays positive with a 95% CI "
            "clear of zero at *every* model size tested — the result is robust to "
            "the choice of recognizer, not an artefact of one ASR model.")
    else:
        crossed = ", ".join(r["model"] for r in results if r["gap_lo"] <= 0)
        takeaway = (
            f"**Takeaway:** the gap holds at most sizes, but its 95% CI includes "
            f"zero for: {crossed} — interpret those with caution.")

    lines = [
        "# Sensitivity to the ASR scorer (Whisper model size)",
        "",
        f"Run: `{args.run}` (gTTS, English voice, isolated names). Each row "
        "re-scores the **same audio** with a different faster-whisper model size, "
        "so only the recognizer varies.",
        "",
        "| Whisper model | n | English CER | African CER | gap | gap 95% CI "
        "| Cliff's δ | p |",
        "|---------------|--:|------------:|------------:|----:|-----------"
        "|----------|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['model']} | {r['n']} | {r['english_cer']:.2f} | "
            f"{r['african_cer']:.2f} | **+{r['gap']:.2f}** | "
            f"[{r['gap_lo']:.2f}, {r['gap_hi']:.2f}] | "
            f"{r['delta']:+.2f} ({r['effect']}) | {r['p']:.1e} |")
    lines += ["", takeaway, ""]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWritten to {args.out}")


if __name__ == "__main__":
    main()
