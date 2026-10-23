"""Quantify *how* names fail: recovered, replaced by English, or garbled.

The qualitative finding — African names get turned into unrelated English words
(*Emeka* -> "America", *Folake* -> "For Locker") — becomes a measurement here.
Each name's ASR transcription is sorted into one of four outcomes:

  - **recovered**  — exact match, or near (CER <= 0.15): the name survived.
  - **english_sub** — not recovered, but a majority of the content words are
    ordinary English words the recognizer reached for instead of the name.
  - **garble**     — not recovered and mostly novel non-words (*Oluwaseun* ->
    "Alois Seyoon"): the recognizer produced nonsense.
  - **dropped**    — empty transcription.

"Ordinary English word" is decided against a bundled list of the ~10k most common
English words (`data/common_english_words.txt`, public domain). Because that list
is deliberately *common*-only, it misses words like "locker"/"bail", so the
english_sub rate is a **conservative lower bound** — the true rate is higher.

    python error_taxonomy.py            # docs/error_taxonomy.md + .png

Reproducible from the committed score tables — no TTS/ASR stack required.
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")            # headless: render straight to a file
from matplotlib.figure import Figure
from matplotlib.patches import Patch

RECOVER_CER = 0.15               # at/below this CER the name counts as recovered
MAJORITY = 0.5                   # share of content words that must be English

# Outcome is a quality ladder (good -> bad): a status palette, shown with a
# legend AND a percent label in every segment, so colour is never the sole cue.
ORDER = ["recovered", "english_sub", "garble", "dropped"]
LABELS = {"recovered": "recovered", "english_sub": "replaced by English word(s)",
          "garble": "garbled (non-words)", "dropped": "dropped (empty)"}
COLOURS = {"recovered": "#0a9d78", "english_sub": "#e8a33d",
           "garble": "#c2410c", "dropped": "#334155"}


def load_lexicon(path: str | Path) -> set[str]:
    out = set()
    for line in open(path, encoding="utf-8"):
        w = line.strip().lower()
        if w and not w.startswith("#"):
            out.add(w)
    return out


def content_tokens(text: str) -> list[str]:
    """Alphabetic tokens of length >= 2 (drops 'a'/'I' and punctuation)."""
    return [w for w in re.findall(r"[a-z']+", text.lower()) if len(w) >= 2]


def classify(name: str, transcription: str, cer: float, exact: bool,
             lexicon: set[str]) -> str:
    if exact or cer <= RECOVER_CER:
        return "recovered"
    toks = content_tokens(transcription)
    if not toks:
        return "dropped"
    name_words = set(re.findall(r"[a-z']+", name.lower()))
    english = [w for w in toks if w in lexicon and w not in name_words]
    return "english_sub" if len(english) / len(toks) >= MAJORITY else "garble"


def summarise(rows: list[dict], lexicon: set[str]) -> dict:
    """Per-group (english/african) outcome counts and key rates."""
    groups: dict[str, Counter] = {"english": Counter(), "african": Counter()}
    for r in rows:
        grp = "english" if r["language"] == "english" else "african"
        cat = classify(r["name"], r["transcription"], float(r["cer"]),
                       r.get("exact_match") in ("1", 1, True, "True"), lexicon)
        groups[grp][cat] += 1
    out = {}
    for grp, c in groups.items():
        n = sum(c.values())
        errors = n - c["recovered"]
        out[grp] = {
            "n": n, "counts": c,
            "recovered_rate": c["recovered"] / n if n else 0.0,
            "english_sub_of_errors": c["english_sub"] / errors if errors else 0.0,
        }
    return out


def examples(rows: list[dict], lexicon: set[str], per_cat: int = 3) -> dict:
    seen: dict[str, list[str]] = {k: [] for k in ORDER}
    for r in rows:
        if r["language"] == "english":
            continue
        cat = classify(r["name"], r["transcription"], float(r["cer"]),
                       r.get("exact_match") in ("1", 1, True, "True"), lexicon)
        if len(seen[cat]) < per_cat:
            seen[cat].append(f'{r["name"]} → "{r["transcription"].strip()}"')
    return seen


def render_figure(summary: dict, out_path: str | Path = "docs/error_taxonomy.png") -> Path:
    groups = [g for g in ("english", "african") if summary.get(g, {}).get("n")]
    if not groups:
        raise ValueError("no groups to plot")
    fig = Figure(figsize=(8.0, 2.6), dpi=120)
    ax = fig.add_subplot(111)
    ys = range(len(groups))
    for yi, grp in zip(ys, groups):
        c = summary[grp]["counts"]
        n = summary[grp]["n"]
        left = 0.0
        for cat in ORDER:
            frac = (c[cat] / n) if n else 0.0
            if frac <= 0:
                continue
            ax.barh(yi, frac, left=left, color=COLOURS[cat], height=0.6,
                    edgecolor="white", linewidth=1.5)
            if frac >= 0.06:                        # label only segments with room
                ax.text(left + frac / 2, yi, f"{frac*100:.0f}%", va="center",
                        ha="center", fontsize=9, color="white", fontweight="bold")
            left += frac
    ax.set_yticks(list(ys))
    ax.set_yticklabels([f"{g.capitalize()} names\n(n={summary[g]['n']})" for g in groups],
                       fontsize=9)
    ax.set_xlim(0, 1)
    ax.set_xlabel("share of names")
    ax.set_title("How the recognizer renders each name", fontsize=12)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    present = [cat for cat in ORDER
               if any(summary[g]["counts"][cat] for g in groups)]
    ax.legend(handles=[Patch(color=COLOURS[c], label=LABELS[c])
                       for c in present],
              fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.35),
              ncol=len(present), frameon=False)
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    return out_path


def render_markdown(summary: dict, exs: dict) -> str:
    af = summary.get("african", {})
    en = summary.get("english", {})
    lines = [
        "# How names fail: recovered, replaced by English, or garbled",
        "",
        "Generated by `error_taxonomy.py` from the committed scores (gTTS "
        "isolated, the clean-baseline run). Each name's transcription is sorted "
        "into one outcome; “English word” is judged against the ~10k most "
        "common English words, so the *replaced by English* rate is a "
        "**conservative lower bound**.",
        "",
        "| outcome | English | African |",
        "|---------|--------:|--------:|",
    ]
    for cat in ORDER:
        ec = en.get("counts", {}).get(cat, 0)
        ac = af.get("counts", {}).get(cat, 0)
        en_n, af_n = en.get("n", 0) or 1, af.get("n", 0) or 1
        lines.append(f"| {LABELS[cat]} | {ec} ({100*ec/en_n:.0f}%) "
                     f"| {ac} ({100*ac/af_n:.0f}%) |")
    lines += [
        "",
        f"- **English names are recovered {100*en.get('recovered_rate',0):.0f}% "
        f"of the time; African names only {100*af.get('recovered_rate',0):.0f}%.**",
        f"- Of the African names that were *not* recovered, at least "
        f"**{100*af.get('english_sub_of_errors',0):.0f}%** were replaced by "
        f"ordinary English words/phrases rather than a novel approximation.",
        "",
        "![How the recognizer renders each name](error_taxonomy.png)",
        "",
        "Examples (African names):",
        "",
    ]
    for cat in ORDER:
        if exs.get(cat):
            lines.append(f"- *{LABELS[cat]}:* " + "; ".join(exs[cat]))
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default="outputs")
    ap.add_argument("--lexicon", default="data/common_english_words.txt")
    ap.add_argument("--out", default="docs/error_taxonomy.md")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(Path(args.run) / "scores.csv", encoding="utf-8")))
    if not rows:
        print(f"No scored rows in {args.run}. Run the pipeline first.")
        return
    lex = load_lexicon(args.lexicon)
    summary = summarise(rows, lex)
    exs = examples(rows, lex)
    fig = render_figure(summary, Path(args.out).with_suffix(".png"))
    text = render_markdown(summary, exs)
    Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    print(f"Written to {args.out} and {fig}")


if __name__ == "__main__":
    main()
