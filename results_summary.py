"""Compute the headline numbers once, as a machine-readable source of truth.

The figures quoted across README/FINDINGS/PAPER — per-engine effect sizes and
their CIs, the pooled cross-engine meta-analysis, and the recovery rates with
their Wilson intervals — are all recomputed here from the committed score tables
and written to ``results_summary.json``. One authoritative place the numbers come
from, so a drift between the prose and the data is a failing test rather than a
silent error (see ``tests/test_results_summary.py``).

    python results_summary.py            # writes results_summary.json + prints

Reproducible from the committed scores; no TTS/ASR stack required.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import error_taxonomy as tax
import meta_analysis as meta
from ttsbench.stats import english_vs_african, english_vs_african_ci

SCHEMA_VERSION = 1

# The three independent engines (isolated-word, n=80) that the meta-analysis and
# the per-engine headline both use.
ENGINE_RUNS = {"gTTS": "outputs", "eSpeak": "outputs_espeak", "MMS": "outputs_mms"}
# The clean-baseline run the recovery taxonomy is reported on.
TAXONOMY_RUN = "outputs"
LEXICON = "data/common_english_words.txt"


def _load(run_dir: Path) -> list[dict]:
    return list(csv.DictReader(open(run_dir / "scores.csv", encoding="utf-8")))


def _round_ci(ci: dict, nd: int = 4) -> dict:
    """Keep just the point/interval fields of a bootstrap CI, rounded."""
    return {k: round(ci[k], nd) for k in ("point", "lo", "hi") if k in ci}


def engine_block(run_dir: Path, *, n_boot: int, seed: int) -> dict | None:
    rows = _load(run_dir)
    st = english_vs_african(rows)
    if not st:
        return None
    ci = english_vs_african_ci(rows, n_boot=n_boot, seed=seed)
    return {
        "n_english": st["english_n"], "n_african": st["african_n"],
        "english_median_cer": round(st["english_median"], 4),
        "african_median_cer": round(st["african_median"], 4),
        "cliffs_delta": round(st["cliffs_delta"], 4),
        "effect": st["effect"],
        "prob_superiority": round(st["prob_superiority"], 4),
        "mannwhitney_p": st["p"],
        "mean_gap_ci": _round_ci(ci["gap_ci"]),
        "cliffs_delta_ci": _round_ci(ci["cliffs_delta_ci"]),
        "prob_superiority_ci": _round_ci(ci["prob_superiority_ci"]),
    }


def recovery_block(run_dir: Path, lexicon_path: str) -> dict:
    lexicon = tax.load_lexicon(lexicon_path)
    summ = tax.summarise(_load(run_dir), lexicon)
    out = {}
    for grp in ("english", "african"):
        g = summ.get(grp, {})
        ci = g.get("recovered_ci", {})
        out[grp] = {
            "n": g.get("n", 0),
            "recovered_rate": round(g.get("recovered_rate", 0.0), 4),
            "recovered_ci": {"lo": round(ci.get("lo", 0.0), 4),
                             "hi": round(ci.get("hi", 0.0), 4)},
        }
    return out


def pooled_block(runs: dict[str, list[dict]], *, n_boot: int, seed: int) -> dict | None:
    pooled = meta.meta_analyze(runs, n_boot=n_boot, seed=seed)["pooled"]
    if not pooled:
        return None
    return {
        "k_engines": pooled["k"],
        "pooled_cliffs_delta": round(pooled["pooled_delta"], 4),
        "ci": {"lo": round(pooled["lo"], 4), "hi": round(pooled["hi"], 4)},
        "effect": pooled["effect"],
        "I2_percent": round(pooled["I2"], 1),
        "Q": round(pooled["Q"], 3),
        "tau2": round(pooled["tau2"], 4),
        "p_heterogeneity": pooled["p_heterogeneity"],
    }


def build_summary(*, n_boot: int = 2000, seed: int = 0,
                  root: Path = Path(".")) -> dict:
    engines = {}
    for label, d in ENGINE_RUNS.items():
        block = engine_block(root / d, n_boot=n_boot, seed=seed)
        if block:
            engines[label] = block
    pooled_runs = {label: meta.load_run(root / d) for label, d in ENGINE_RUNS.items()
                   if (root / d / "scores.csv").exists()}
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_from": "committed outputs*/scores.csv (no TTS/ASR stack)",
        "bootstrap": {"n_boot": n_boot, "seed": seed},
        "engines": engines,
        "pooled_meta_analysis": pooled_block(pooled_runs, n_boot=n_boot, seed=seed),
        "recovery_rates": recovery_block(root / TAXONOMY_RUN, str(root / LEXICON)),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results_summary.json")
    args = ap.parse_args()

    summary = build_summary(n_boot=args.n_boot, seed=args.seed)
    out = Path(args.out)
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Written to {out}")


if __name__ == "__main__":
    main()
