"""Tests for meta_analysis.py — the cross-engine random-effects pool.

The maths is checked on hand-built studies with known structure (so the pooling
algebra is pinned down independently of the real data), and the end-to-end
behaviour is checked on tiny synthetic runs.
"""
import math

import pytest

import meta_analysis as ma


# --- random_effects: the pooling algebra ------------------------------------

def _study(label, delta, se):
    return {"label": label, "delta": delta, "se": se}


def test_random_effects_needs_two_studies():
    assert ma.random_effects([]) is None
    assert ma.random_effects([_study("a", 0.5, 0.1)]) is None


def test_random_effects_no_heterogeneity_is_a_clean_average():
    # Two identical estimates with identical SEs: Q~0, I2~0, tau2=0, pooled = the
    # common value, and the pooled SE is the usual sqrt(v/2) inverse-variance SE.
    r = ma.random_effects([_study("a", 0.4, 0.1), _study("b", 0.4, 0.1)])
    assert r["pooled_delta"] == pytest.approx(0.4, abs=1e-9)
    assert r["Q"] == pytest.approx(0.0, abs=1e-9)
    assert r["I2"] == pytest.approx(0.0, abs=1e-9)
    assert r["tau2"] == pytest.approx(0.0, abs=1e-9)
    assert r["se"] == pytest.approx(0.1 / math.sqrt(2), rel=1e-6)


def test_random_effects_detects_heterogeneity():
    # Two precise but very different estimates -> large Q, high I2, positive tau2.
    r = ma.random_effects([_study("a", 0.9, 0.05), _study("b", 0.1, 0.05)])
    assert r["Q"] > 3.84                        # well past the 1-df 5% point
    assert r["I2"] > 50
    assert r["tau2"] > 0
    # Pooled estimate sits between the two inputs.
    assert 0.1 < r["pooled_delta"] < 0.9


def test_random_effects_ci_brackets_the_estimate():
    r = ma.random_effects([_study("a", 0.6, 0.1), _study("b", 0.5, 0.1)])
    assert r["lo"] < r["pooled_delta"] < r["hi"]
    assert r["lo"] == pytest.approx(r["pooled_delta"] - 1.96 * r["se"])


# --- engine_effect / meta_analyze: end to end -------------------------------

def _rows(african_cers, english_cers):
    rows = [{"id": f"a{i}", "name": f"afr{i}", "language": "yoruba", "cer": c}
            for i, c in enumerate(african_cers)]
    rows += [{"id": f"e{i}", "name": f"eng{i}", "language": "english", "cer": c}
             for i, c in enumerate(english_cers)]
    return rows


def test_engine_effect_positive_gap():
    # African names clearly worse than English -> large positive delta.
    eff = ma.engine_effect("X", _rows([0.8, 0.9, 1.0, 0.7], [0.0, 0.1, 0.0, 0.05]),
                           n_boot=200, seed=0)
    assert eff["delta"] > 0.5
    assert eff["se"] > 0
    assert eff["n_african"] == 4 and eff["n_english"] == 4


def test_engine_effect_none_without_english():
    assert ma.engine_effect("X", _rows([0.5, 0.6], []), n_boot=50) is None


def test_meta_analyze_pools_two_engines():
    runs = {
        "clean": _rows([0.8, 0.9, 1.0, 0.7], [0.0, 0.0, 0.1, 0.0]),
        "saturated": _rows([0.5, 0.45, 0.55, 0.5], [0.5, 0.5, 0.45, 0.5]),
    }
    res = ma.meta_analyze(runs, n_boot=200, seed=0)
    assert len(res["studies"]) == 2
    assert res["pooled"] is not None
    assert res["pooled"]["k"] == 2
    # The clean engine shows a bigger gap than the saturated one.
    by = {s["label"]: s["delta"] for s in res["studies"]}
    assert by["clean"] > by["saturated"]


def test_report_mentions_pooled_and_heterogeneity():
    runs = {
        "clean": _rows([0.8, 0.9, 1.0, 0.7], [0.0, 0.0, 0.1, 0.0]),
        "saturated": _rows([0.5, 0.45, 0.55, 0.5], [0.5, 0.5, 0.45, 0.5]),
    }
    text = ma.report(runs, n_boot=200, seed=0)
    assert "random-effects" in text
    assert "Combined Cliff" in text
    assert "I²" in text
