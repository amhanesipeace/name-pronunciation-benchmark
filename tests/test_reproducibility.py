"""Reproducibility guard: the paper's headline numbers must follow from the
committed score tables.

The derived `scores.csv` for each run is checked into the repo (the heavy audio
is not), so every statistic and figure can be regenerated without the TTS/ASR
stack. These tests recompute the headline results straight from those tables and
assert the claims made in README/PAPER/FINDINGS, so a silent change to the data
or the stats code can't drift away from the documented findings.

If a run directory is missing (e.g. a partial checkout), that case is skipped
rather than failed — the point is to guard the numbers that ARE committed.
"""
import csv
from pathlib import Path
from statistics import mean

import pytest

from ttsbench.stats import english_vs_african, per_language_vs_english

ROOT = Path(__file__).resolve().parent.parent


def load(run: str) -> list[dict]:
    path = ROOT / run / "scores.csv"
    if not path.exists():
        pytest.skip(f"{run}/scores.csv not present")
    return list(csv.DictReader(open(path, encoding="utf-8")))


def gap(scores: list[dict]) -> float:
    eng = [float(r["cer"]) for r in scores if r["language"] == "english"]
    afr = [float(r["cer"]) for r in scores if r["language"] != "english"]
    return mean(afr) - mean(eng)


def test_gtts_isolated_large_significant_bias():
    """Claim: clean baseline, large & significant gap (δ≈0.82, gap≈0.36)."""
    s = load("outputs")
    assert len(s) == 80
    st = english_vs_african(s)
    assert st["cliffs_delta"] == pytest.approx(0.82, abs=0.03)
    assert st["effect"] == "large"
    assert st["p"] < 1e-6
    assert gap(s) == pytest.approx(0.36, abs=0.03)


def test_gtts_carrier_still_biased():
    """Claim: gTTS stays significantly biased under the fairer carrier test."""
    st = english_vs_african(load("outputs_gtts_carrier"))
    assert st["cliffs_delta"] == pytest.approx(0.75, abs=0.05)
    assert st["p"] < 1e-5


def test_mms_isolated_is_saturated_not_fair():
    """Claim: MMS isolated-word 'no gap' is a saturation artifact, not fairness:
    the English baseline is bad and the gap is not significant."""
    s = load("outputs_mms")
    eng = [float(r["cer"]) for r in s if r["language"] == "english"]
    assert mean(eng) > 0.5                    # baseline saturated, not clean
    st = english_vs_african(s)
    assert st["p"] > 0.05                      # not significant
    assert gap(s) < 0.1                        # tiny apparent gap


def test_mms_carrier_unmasks_the_gap():
    """Claim: the carrier protocol reveals MMS's real, large, significant gap."""
    s = load("outputs_mms_carrier")
    st = english_vs_african(s)
    assert gap(s) > 0.3                         # large real gap emerges
    assert st["cliffs_delta"] == pytest.approx(0.70, abs=0.05)
    assert st["p"] < 1e-4


def test_every_language_significant_on_clean_baseline():
    """Claim: no single language drives it — all three significant after Holm."""
    rows = per_language_vs_english(load("outputs"), ci=False)
    assert {r["language"] for r in rows} == {"yoruba", "igbo", "hausa"}
    for r in rows:
        assert r["p_holm"] < 0.05
        assert r["effect"] == "large"
