"""What *kind* of error is the bias? Decomposing CER into edit operations.

Character Error Rate is a single number: it says *how wrong* a name came out,
not *how* it went wrong. Two names with the same CER can fail very differently —
one by dropping half its syllables (deletions), another by having every sound
heard as a different one (substitutions), a third by the recogniser hallucinating
extra characters (insertions, e.g. a name expanded into an English word).

This script traces the edit distance behind each name's CER back into its three
operation types (`scoring.edit_ops`) and aggregates them per language group. By
construction substitutions + deletions + insertions = edit distance, so the three
*rates* (each op count over the total reference characters) sum exactly to the
micro-averaged CER — the decomposition is complete, not an approximation.

    python error_profile.py              # writes docs/error_profile.md + prints

Reproducible from the committed score tables (which carry the ASR transcription
per name) — no TTS/ASR stack required.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ttsbench.scoring import edit_ops

# Edit-operation colours, in fixed categorical order (dataviz theme slots 1–3):
# substitution = blue, deletion = orange, insertion = aqua. Validated for CVD
# separation (worst adjacent ΔE 9.2) against the light surface; the aqua's sub-3:1
# surface contrast is relieved by the in-segment labels and the markdown table.
OP_ORDER = ("substitutions", "deletions", "insertions")
OP_COLOURS = {"substitutions": "#2a78d6", "deletions": "#eb6834",
              "insertions": "#1baf7a"}
OP_LABELS = {"substitutions": "Substitution (heard as a different character)",
             "deletions": "Deletion (a character dropped)",
             "insertions": "Insertion (a character added)"}
# The three per-op rates (op count / reference chars) that sum to each group's CER.
_RATE = {"substitutions": "sub_rate", "deletions": "del_rate",
         "insertions": "ins_rate"}


def load(run_dir: Path) -> list[dict]:
    """Scored rows; each carries the intended name and its ASR transcription."""
    rows = []
    for r in csv.DictReader(open(run_dir / "scores.csv", encoding="utf-8")):
        rows.append({"id": r["id"], "language": r["language"],
                     "name": r["name"], "transcription": r["transcription"]})
    return rows


def profile(rows: list[dict]) -> dict:
    """Pool edit operations over a set of rows and express them as rates.

    Rates are micro-averaged (total ops / total reference characters), so
    sub_rate + del_rate + ins_rate == the group's character error rate, and the
    mix percentages say what share of the *errors* each operation accounts for.
    """
    s = d = i = chars = 0
    for r in rows:
        o = edit_ops(r["name"], r["transcription"])
        s += o["substitutions"]
        d += o["deletions"]
        i += o["insertions"]
        chars += o["ref_len"]
    errors = s + d + i
    return {
        "n": len(rows), "chars": chars,
        "substitutions": s, "deletions": d, "insertions": i, "errors": errors,
        "cer": errors / chars if chars else 0.0,
        "sub_rate": s / chars if chars else 0.0,
        "del_rate": d / chars if chars else 0.0,
        "ins_rate": i / chars if chars else 0.0,
        # Share of the errors (not the characters) carried by each op type.
        "sub_share": s / errors if errors else 0.0,
        "del_share": d / errors if errors else 0.0,
        "ins_share": i / errors if errors else 0.0,
    }


def render_figure(rows: list[dict],
                  out_path: str | Path = "docs/error_profile.png") -> Path:
    """Stacked horizontal bars: each group's CER split into its edit operations.

    Bar length is the group's (micro-averaged) CER; the segments are the
    substitution / deletion / insertion rates, which sum to it — so one figure
    carries both *how wrong* each group is and *what kind* of error it is. The
    near-zero English bar beside the long African ones is the asymmetry itself.
    """
    from matplotlib.figure import Figure
    from matplotlib.patches import Patch

    groups = [("English", "english"), ("Yoruba", "yoruba"),
              ("Igbo", "igbo"), ("Hausa", "hausa")]
    profiles = [(label, profile([r for r in rows if r["language"] == lang]))
                for label, lang in groups]

    fig = Figure(figsize=(8.0, 3.2), dpi=120)
    ax = fig.add_subplot(111)
    ys = range(len(profiles))
    for yi, (_, p) in zip(ys, profiles):
        left = 0.0
        for op in OP_ORDER:
            w = p[_RATE[op]]
            if w <= 0:
                continue
            ax.barh(yi, w, left=left, color=OP_COLOURS[op], height=0.62,
                    edgecolor="white", linewidth=1.5)
            if w >= 0.035:                         # label only segments with room
                ax.text(left + w / 2, yi, f"{w:.2f}", va="center", ha="center",
                        fontsize=8, color="white", fontweight="bold")
            left += w
    ax.set_yticks(list(ys))
    ax.set_yticklabels([f"{label}\n(n={p['n']})" for label, p in profiles],
                       fontsize=9)
    ax.invert_yaxis()                              # English at the top
    ax.set_xlim(0, max(0.05, max(p["cer"] for _, p in profiles) * 1.12))
    ax.set_xlabel("character error rate  (segments sum to CER)")
    ax.set_title("What kind of error: CER split into edit operations", fontsize=12)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.legend(handles=[Patch(color=OP_COLOURS[op], label=OP_LABELS[op])
                       for op in OP_ORDER],
              fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=1, frameon=False)
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    return out_path


def _mix(p: dict) -> str:
    return (f"{p['sub_share']:.0%} substitution / "
            f"{p['del_share']:.0%} deletion / {p['ins_share']:.0%} insertion")


def report(rows: list[dict]) -> str:
    eng = profile([r for r in rows if r["language"] == "english"])
    afr = profile([r for r in rows if r["language"] != "english"])
    per_lang = {lang: profile([r for r in rows if r["language"] == lang])
                for lang in ("yoruba", "igbo", "hausa")}

    dominant = max(("substitution", afr["sub_share"]),
                   ("deletion", afr["del_share"]),
                   ("insertion", afr["ins_share"]), key=lambda kv: kv[1])

    lines = [
        "# What kind of error is the bias? (CER decomposition)",
        "",
        "Generated by `error_profile.py` from the committed scores "
        "(gTTS isolated, the clean-baseline run). Each name's CER is traced back "
        "into the edit operations that produced it — substitutions (a character "
        "heard as a different one), deletions (a character of the name dropped), "
        "and insertions (a character not in the name added). The three *rates* "
        "sum to the group's character error rate.",
        "",
        "![Stacked bars of each group's CER split into substitution, deletion and "
        "insertion rates: English is near-zero while the African languages are "
        "dominated by substitutions, then insertions](error_profile.png)",
        "",
        "| Group | n | CER | sub rate | del rate | ins rate | error mix (S/D/I) |",
        "| --- | --: | --: | --: | --: | --: | --- |",
        f"| English | {eng['n']} | {eng['cer']:.3f} | {eng['sub_rate']:.3f} | "
        f"{eng['del_rate']:.3f} | {eng['ins_rate']:.3f} | {_mix(eng)} |",
        f"| African (all) | {afr['n']} | {afr['cer']:.3f} | {afr['sub_rate']:.3f} | "
        f"{afr['del_rate']:.3f} | {afr['ins_rate']:.3f} | {_mix(afr)} |",
    ]
    for lang, p in per_lang.items():
        lines.append(
            f"| {lang.capitalize()} | {p['n']} | {p['cer']:.3f} | "
            f"{p['sub_rate']:.3f} | {p['del_rate']:.3f} | {p['ins_rate']:.3f} | "
            f"{_mix(p)} |")

    lines += [
        "",
        "**Reading it.**",
        "",
        f"- English names are essentially error-free (CER {eng['cer']:.3f}), so "
        "there is no meaningful error structure to decompose on that side — the "
        "asymmetry itself is the finding.",
        f"- The African-name gap is dominated by **{dominant[0]}s** "
        f"({dominant[1]:.0%} of all errors): the recogniser mostly hears "
        "*different* characters, not a shortened or padded version of the name.",
        f"- **Insertions** account for {afr['ins_share']:.0%} of African errors — "
        "the character-level signature of a name being *expanded into other "
        "words* (extra sounds the name never had), consistent with the "
        "English-word substitutions quantified in the error taxonomy.",
        f"- **Deletions** are rare ({afr['del_share']:.0%}): names are not simply "
        "being clipped or dropped; they are being re-pronounced as something else.",
        "",
        "**Why it matters.** Two systems can share a CER yet fail differently. A "
        "deletion-heavy failure looks like *under-articulation* (syllables lost); "
        "a substitution/insertion-heavy failure like this one looks like "
        "*mis-identification* — the name is confidently pronounced as a different, "
        "more familiar word. That distinction matters for both diagnosis (where in "
        "the pipeline to intervene) and harm (a name turned into an unrelated "
        "English word is a different experience from a name trailing off).",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default="outputs")
    ap.add_argument("--out", default="docs/error_profile.md")
    ap.add_argument("--figure", default="docs/error_profile.png")
    args = ap.parse_args()

    rows = load(Path(args.run))
    if not rows:
        print(f"No scored rows in {args.run}. Run the pipeline first.")
        return
    text = report(rows)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    fig_path = render_figure(rows, args.figure)
    print(text)
    print(f"Written to {out} and {fig_path}")


if __name__ == "__main__":
    main()
