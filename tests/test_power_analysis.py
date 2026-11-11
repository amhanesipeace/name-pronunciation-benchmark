"""Tests for the subsampling power analysis."""
import random
from pathlib import Path

import pytest

from power_analysis import (load, power_curve, report, smallest_n_for_power,
                            subsample_power, _split)

ROOT = Path(__file__).resolve().parent.parent


def _rows(spec):
    # spec: list of (language, cer)
    return [{"language": lang, "cer": c} for lang, c in spec]


def test_split_pools_african_languages():
    eng, afr = _split(_rows([("english", 0.0), ("igbo", 0.4), ("hausa", 0.5)]))
    assert eng == [0.0] and sorted(afr) == [0.4, 0.5]


def test_subsample_power_high_for_separated_groups():
    # English all 0, African all high -> every draw should be significant.
    eng = [0.0] * 20
    afr = [0.5] * 20
    res = subsample_power(eng, afr, 5, iters=100, rng=random.Random(0))
    assert res["n_eng"] == 5 and res["n_afr"] == 5
    assert res["power"] == 1.0
    assert res["median_delta"] > 0.9


def test_subsample_power_low_for_overlapping_groups():
    # Identical distributions -> the one-sided test should rarely fire.
    eng = [0.3] * 20
    afr = [0.3] * 20
    res = subsample_power(eng, afr, 10, iters=100, rng=random.Random(1))
    assert res["power"] < 0.1          # degenerate draws -> p=1, not significant


def test_subsample_caps_n_at_available():
    res = subsample_power([0.0] * 4, [0.5] * 30, 10, iters=10,
                          rng=random.Random(0))
    assert res["n_eng"] == 4 and res["n_afr"] == 10   # capped to the smaller pool


def test_power_curve_is_monotone_ish_and_seeded():
    rows = _rows([("english", 0.0)] * 20 + [("igbo", 0.5)] * 20)
    a = power_curve(rows, ns=[5, 10], iters=50, seed=0)
    b = power_curve(rows, ns=[5, 10], iters=50, seed=0)
    assert [r["power"] for r in a] == [r["power"] for r in b]   # reproducible
    assert all(r["power"] == 1.0 for r in a)                    # clean separation


def test_smallest_n_for_power():
    curve = [{"n": 5, "power": 0.4}, {"n": 10, "power": 0.85},
             {"n": 20, "power": 1.0}]
    assert smallest_n_for_power(curve, 0.80) == 10
    assert smallest_n_for_power(curve, 0.999) == 20
    assert smallest_n_for_power([{"n": 5, "power": 0.1}], 0.80) is None


def test_report_mentions_representativeness_and_conclusion():
    rows = _rows([("english", 0.0)] * 20 + [("hausa", 0.5)] * 20)
    text = report(rows, iters=50)
    assert "representativeness" in text.lower()
    assert "Conclusion" in text and "power" in text.lower()


def test_reproducibility_small_samples_still_detect_gap():
    """From the committed clean-baseline run: even the smallest tested sample is
    well-powered, so the gap is not a small-n artefact."""
    scores = ROOT / "outputs" / "scores.csv"
    if not scores.exists():
        pytest.skip("outputs/scores.csv not present")
    rows = load(ROOT / "outputs")
    curve = power_curve(rows, ns=[5, 20], iters=200, seed=0)
    assert curve[0]["power"] > 0.8     # even 5/group detects it most of the time
    assert curve[-1]["power"] > 0.99   # full sample: essentially always
