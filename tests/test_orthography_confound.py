"""Tests for the exotic-spelling (orthography) confound check."""
from pathlib import Path

import pytest

from orthography_confound import (cer_marker_corr, load, marker_count,
                                  marker_gap, report, simple_gap, split)

ROOT = Path(__file__).resolve().parent.parent


def _rows(spec):
    # spec: list of (language, cer, markers)
    return [{"id": str(i), "language": lang, "cer": c, "markers": m}
            for i, (lang, c, m) in enumerate(spec)]


def test_marker_count_flags_non_english_patterns():
    assert marker_count("Ngozi") >= 1          # initial syllabic nasal
    assert marker_count("Nwankwo") >= 2        # nw + kw digraphs
    assert marker_count("Gbenga") >= 1         # gb digraph
    assert marker_count("aeiou") >= 1          # 3+ adjacent vowels
    # plain Latin spelling -> no markers, whether English or African. A medial
    # "w" breaks the vowel run, so Oluwaseun (olu-wa-seun) counts as simple.
    assert marker_count("James") == 0
    assert marker_count("Adebayo") == 0
    assert marker_count("Oluwaseun") == 0


def test_marker_count_excludes_english_digraphs():
    # ch/sh are English-compatible and must not be counted
    assert marker_count("Michael") == 0
    assert marker_count("Joshua") == 0


def test_simple_gap_restricts_to_zero_marker_names():
    rows = _rows([("english", 0.0, 0), ("english", 0.0, 0),
                  ("igbo", 0.5, 0), ("yoruba", 0.5, 2)])  # last is excluded
    sg = simple_gap(rows)
    assert sg["english_n"] == 2 and sg["african_n"] == 1   # marker>0 dropped
    assert sg["african_cer"] > sg["english_cer"]


def test_cer_marker_corr_flat_when_no_relationship():
    import math
    rows = _rows([("igbo", 0.5, m) for m in range(0, 6)])  # constant CER
    assert math.isnan(cer_marker_corr(rows)["rho"])


def test_report_mentions_conclusion():
    rows = _rows([("english", 0.0, 0)] * 6 + [("igbo", 0.5, 0)] * 6)
    text = report(rows)
    assert "spelling" in text.lower() and "Conclusion" in text


def test_reproducibility_spelling_does_not_explain_gap():
    """From the committed clean-baseline run: markers don't predict CER within
    African names, and the full gap persists among plain-spelled names."""
    scores = ROOT / "outputs" / "scores.csv"
    if not scores.exists():
        pytest.skip("outputs/scores.csv not present")
    rows = load(ROOT / "outputs", ROOT / "data" / "names.csv")
    _, afr = split(rows)
    assert abs(cer_marker_corr(afr)["rho"]) < 0.3          # markers ~ not predictive
    sg = simple_gap(rows)
    assert sg["african_cer"] > sg["english_cer"] + 0.2     # large gap among simple
    assert sg["p"] < 1e-4                                   # still significant
    # African names are not meaningfully more "exotically spelled" than English
    assert marker_gap(rows)["p"] > 0.01
