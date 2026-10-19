"""Tests for the bootstrap confidence intervals in ttsbench.stats."""
from statistics import mean

from ttsbench.stats import (_percentile, bootstrap_ci, cliffs_delta_ci,
                            english_vs_african_ci, mean_gap_ci,
                            per_language_vs_english)


def test_percentile_endpoints_and_midpoint():
    vals = [0.0, 1.0, 2.0, 3.0, 4.0]
    assert _percentile(vals, 0.0) == 0.0
    assert _percentile(vals, 1.0) == 4.0
    assert _percentile(vals, 0.5) == 2.0


def test_percentile_interpolates():
    assert _percentile([0.0, 10.0], 0.25) == 2.5


def test_bootstrap_is_reproducible_with_seed():
    a, b = [1.0, 2.0, 3.0, 4.0], [0.0, 0.5, 1.0]
    f = lambda x, y: mean(x) - mean(y)
    r1 = bootstrap_ci(f, (a, b), n_boot=500, seed=42)
    r2 = bootstrap_ci(f, (a, b), n_boot=500, seed=42)
    assert r1 == r2
    # A different seed should (almost surely) move the interval.
    r3 = bootstrap_ci(f, (a, b), n_boot=500, seed=7)
    assert (r3["lo"], r3["hi"]) != (r1["lo"], r1["hi"])


def test_ci_brackets_the_point_estimate():
    a, b = [0.3, 0.4, 0.5, 0.6, 0.7], [0.0, 0.1, 0.2]
    r = mean_gap_ci(a, b, n_boot=1000, seed=0)
    assert r["lo"] <= r["point"] <= r["hi"]


def test_clear_gap_ci_excludes_zero():
    # African names much worse than English -> CI for the gap stays positive.
    afr = [0.6, 0.7, 0.8, 0.9, 0.75, 0.85]
    eng = [0.0, 0.0, 0.05, 0.0, 0.1]
    r = mean_gap_ci(afr, eng, n_boot=2000, seed=0)
    assert r["lo"] > 0.0


def test_no_difference_ci_includes_zero():
    same = [0.2, 0.3, 0.25, 0.35, 0.28]
    r = mean_gap_ci(same, list(same), n_boot=2000, seed=0)
    assert r["lo"] <= 0.0 <= r["hi"]


def test_cliffs_delta_ci_bounds():
    afr = [0.6, 0.7, 0.8, 0.9]
    eng = [0.0, 0.1, 0.2]
    r = cliffs_delta_ci(afr, eng, n_boot=1000, seed=0)
    assert -1.0 <= r["lo"] <= r["point"] <= r["hi"] <= 1.0
    assert r["lo"] > 0.0  # clearly positive effect


def test_empty_sample_returns_degenerate_interval():
    r = bootstrap_ci(lambda x, y: mean(x) - mean(y) if x and y else 0.0,
                     ([1.0, 2.0], []), n_boot=100, seed=0)
    assert r["n_boot"] == 0
    assert r["lo"] == r["hi"] == r["point"]


def test_english_vs_african_ci_from_rows():
    rows = (
        [{"language": "english", "cer": 0.0} for _ in range(5)]
        + [{"language": "yoruba", "cer": 0.6} for _ in range(5)]
    )
    ci = english_vs_african_ci(rows, n_boot=500, seed=0)
    assert ci is not None
    assert ci["gap_ci"]["lo"] > 0.0
    assert "cliffs_delta_ci" in ci


def test_english_vs_african_ci_needs_both_groups():
    rows = [{"language": "english", "cer": 0.0}]
    assert english_vs_african_ci(rows) is None


def test_per_language_ci_attaches_delta_interval():
    rows = (
        [{"language": "english", "cer": 0.0} for _ in range(6)]
        + [{"language": "yoruba", "cer": 0.6} for _ in range(6)]
        + [{"language": "igbo", "cer": 0.5} for _ in range(6)]
    )
    out = per_language_vs_english(rows, n_boot=300)
    assert {r["language"] for r in out} == {"yoruba", "igbo"}
    for r in out:
        assert r["delta_lo"] <= r["cliffs_delta"] <= r["delta_hi"]


def test_per_language_ci_can_be_skipped():
    rows = (
        [{"language": "english", "cer": 0.0} for _ in range(4)]
        + [{"language": "hausa", "cer": 0.6} for _ in range(4)]
    )
    out = per_language_vs_english(rows, ci=False)
    assert out and "delta_lo" not in out[0]
