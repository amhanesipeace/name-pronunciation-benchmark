"""Tests for the leave-one-out / jackknife influence check."""
from pathlib import Path

import pytest

from influence import (leave_one_language_out, leave_one_name_out, load,
                       report, _pooled)

ROOT = Path(__file__).resolve().parent.parent


def _rows(spec):
    # spec: list of (language, cer); ids are auto-assigned.
    return [{"id": f"n{i:03d}", "language": lang, "cer": c}
            for i, (lang, c) in enumerate(spec)]


def test_pooled_reports_positive_gap():
    rows = _rows([("english", 0.0)] * 5 + [("igbo", 0.5)] * 5)
    res = _pooled(rows)
    assert res["cliffs_delta"] > 0
    assert res["median_gap"] > 0


def test_lolo_drops_each_african_language():
    rows = _rows([("english", 0.0)] * 4
                 + [("igbo", 0.5)] * 4 + [("hausa", 0.6)] * 4)
    lolo = leave_one_language_out(rows)
    dropped = {r["dropped"] for r in lolo}
    assert dropped == {"igbo", "hausa"}          # english is never dropped
    # Each row's african_n reflects one language removed (8 - 4 = 4).
    assert all(r["african_n"] == 4 for r in lolo)
    assert all(r["cliffs_delta"] > 0 for r in lolo)


def test_lolo_detects_a_single_outlier_language():
    # English ~ Igbo (no gap), but Hausa is far worse. Dropping Hausa should
    # collapse the pooled delta; dropping Igbo should leave it large.
    rows = _rows([("english", 0.1)] * 6 + [("igbo", 0.1)] * 6
                 + [("hausa", 0.9)] * 6)
    by_dropped = {r["dropped"]: r for r in leave_one_language_out(rows)}
    assert by_dropped["hausa"]["cliffs_delta"] < 0.2    # gap gone w/o Hausa
    assert by_dropped["igbo"]["cliffs_delta"] > 0.8     # gap intact w/o Igbo


def test_jackknife_range_tight_when_no_single_name_dominates():
    rows = _rows([("english", 0.0)] * 10 + [("yoruba", 0.5)] * 10)
    jack = leave_one_name_out(rows)
    assert jack["n"] == 20
    assert jack["min"] > 0                              # never flips sign
    assert jack["max"] - jack["min"] < 0.1              # tight range
    assert "id" in jack["most_influential"]


def test_report_mentions_both_checks_and_conclusion():
    rows = _rows([("english", 0.0)] * 6 + [("igbo", 0.5)] * 6
                 + [("hausa", 0.6)] * 6)
    text = report(rows)
    assert "Leave-one-language-out" in text
    assert "jackknife" in text.lower()
    assert "Conclusion" in text


def test_reproducibility_gap_survives_leave_one_out():
    """From the committed clean-baseline run: the pooled gap survives dropping
    any one African language, and no single name collapses it."""
    scores = ROOT / "outputs" / "scores.csv"
    if not scores.exists():
        pytest.skip("outputs/scores.csv not present")
    rows = load(ROOT / "outputs")
    lolo = leave_one_language_out(rows)
    assert len(lolo) == 3                               # yoruba, igbo, hausa
    assert all(r["p"] < 0.05 and r["cliffs_delta"] > 0.5 for r in lolo)
    jack = leave_one_name_out(rows)
    assert jack["min"] > 0.5                            # stays large, never near 0
    assert jack["swing"] < 0.1                          # no dominant name
