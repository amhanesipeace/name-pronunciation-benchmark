"""Tests for the name-length confound check."""
import math
from pathlib import Path

import pytest

from length_confound import (cer_length_corr, length_gap, load, matched_gap,
                             report, split)

ROOT = Path(__file__).resolve().parent.parent


def _rows(spec):
    # spec: list of (language, cer, length)
    return [{"id": str(i), "language": lang, "cer": c, "len": n}
            for i, (lang, c, n) in enumerate(spec)]


def test_split_separates_english_from_african():
    eng, afr = split(_rows([("english", 0.0, 5), ("igbo", 0.4, 6),
                            ("hausa", 0.3, 7)]))
    assert len(eng) == 1 and len(afr) == 2


def test_length_gap_detects_longer_african():
    rows = _rows([("english", 0.0, 4)] * 10 + [("yoruba", 0.4, 9)] * 10)
    lg = length_gap(rows)
    assert lg["african_median_len"] > lg["english_median_len"]
    assert lg["p"] < 0.05


def test_cer_length_corr_flat_when_no_relationship():
    # CER constant across lengths -> no usable correlation (nan guard)
    rows = _rows([("igbo", 0.5, n) for n in range(3, 13)])
    assert math.isnan(cer_length_corr(rows)["rho"])


def test_matched_gap_restricts_to_overlap_band():
    rows = _rows([("english", 0.0, 5), ("english", 0.0, 6),
                  ("igbo", 0.5, 6), ("igbo", 0.5, 20)])  # 20 is out of band
    mg = matched_gap(rows)
    # overlap = [max(min_eng, min_afr), min(max_eng, max_afr)] = [6, 6]
    assert mg["lo"] == 6 and mg["hi"] == 6
    assert mg["english_n"] == 1 and mg["african_n"] == 1   # only length-6 names
    assert mg["african_cer"] > mg["english_cer"]


def test_report_mentions_conclusion():
    rows = _rows([("english", 0.0, 5)] * 6 + [("igbo", 0.5, 6)] * 6)
    text = report(rows)
    assert "length" in text.lower() and "Conclusion" in text


def test_reproducibility_length_does_not_explain_gap():
    """From the committed clean-baseline run: length doesn't predict CER, and
    the gap persists at matched lengths."""
    scores = ROOT / "outputs" / "scores.csv"
    if not scores.exists():
        pytest.skip("outputs/scores.csv not present")
    rows = load(ROOT / "outputs", ROOT / "data" / "names.csv")
    _, afr = split(rows)
    assert abs(cer_length_corr(afr)["rho"]) < 0.3        # length ~ not predictive
    mg = matched_gap(rows)
    assert mg["african_cer"] > mg["english_cer"] + 0.2   # large in-band gap
    assert mg["p"] < 1e-4                                 # still significant
