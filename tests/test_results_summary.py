"""The machine-readable headline summary is the single source of truth.

These assertions pin the numbers quoted in README/FINDINGS/PAPER to the values
recomputed from the committed scores, so a drift between the prose and the data
fails here. Point estimates are deterministic (asserted tightly); bootstrap CI
bounds depend on n_boot (asserted with inequalities).
"""
from pathlib import Path

import pytest

import results_summary as rs

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def summary():
    if not (ROOT / "outputs" / "scores.csv").exists():
        pytest.skip("committed outputs not present")
    return rs.build_summary(n_boot=400, seed=0, root=ROOT)


def test_schema_and_shape(summary):
    assert summary["schema_version"] == rs.SCHEMA_VERSION
    assert set(summary["engines"]) == {"gTTS", "eSpeak", "MMS"}


def test_gtts_headline_numbers(summary):
    g = summary["engines"]["gTTS"]
    assert g["cliffs_delta"] == pytest.approx(0.82, abs=0.02)
    assert g["effect"] == "large"
    assert g["prob_superiority"] == pytest.approx(0.91, abs=0.02)
    assert g["mannwhitney_p"] < 1e-6
    # Even the lower CI bound is a strong effect.
    assert g["prob_superiority_ci"]["lo"] > 0.8
    assert g["cliffs_delta_ci"]["lo"] > 0.6


def test_pooled_meta_analysis(summary):
    p = summary["pooled_meta_analysis"]
    assert p["k_engines"] == 3
    assert p["pooled_cliffs_delta"] > 0
    assert p["I2_percent"] > 50          # genuinely heterogeneous engines


def test_recovery_rates_and_wilson_cis(summary):
    rec = summary["recovery_rates"]
    assert rec["english"]["recovered_rate"] == pytest.approx(1.0)
    assert rec["african"]["recovered_rate"] == pytest.approx(0.28, abs=0.02)
    # Wilson keeps the 100% rate off the degenerate 1.0 lower bound...
    assert rec["english"]["recovered_ci"]["lo"] < 1.0
    # ...and the two intervals do not overlap (English clearly higher).
    assert rec["english"]["recovered_ci"]["lo"] > rec["african"]["recovered_ci"]["hi"]


def test_summary_is_reproducible():
    if not (ROOT / "outputs" / "scores.csv").exists():
        pytest.skip("committed outputs not present")
    a = rs.build_summary(n_boot=300, seed=1, root=ROOT)
    b = rs.build_summary(n_boot=300, seed=1, root=ROOT)
    assert a == b          # seeded bootstrap -> identical output
