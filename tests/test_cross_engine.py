"""Tests for cross-engine agreement (no synthesis data needed)."""
import math

import pytest

from cross_engine import correlations, paired, render


def _run(items):
    # items: list of (id, name, language, cer)
    return {i: {"id": i, "name": n, "language": lang, "cer": str(c)}
            for i, n, lang, c in items}


def test_paired_matches_ids_and_filters_name_mismatch():
    a = _run([("n1", "Ada", "igbo", 0.2), ("n2", "Bob", "english", 0.0),
              ("n3", "Xy", "hausa", 0.5)])
    b = _run([("n1", "Ada", "igbo", 0.3), ("n2", "Bob", "english", 0.1),
              ("n3", "DIFFERENT", "hausa", 0.4)])        # name mismatch -> dropped
    rows = paired(a, b)
    assert {r["id"] for r in rows} == {"n1", "n2"}
    assert rows[0]["cer_a"] == 0.2 and rows[0]["cer_b"] == 0.3


def test_correlations_perfectly_monotonic():
    rows = [{"id": str(k), "name": str(k), "language": "igbo" if k else "english",
             "cer_a": k / 10, "cer_b": k / 10} for k in range(6)]
    corr = correlations(rows)
    assert corr["all"]["rho"] == pytest.approx(1.0)
    assert corr["all"]["n"] == 6
    assert "african" in corr


def test_correlations_too_few_points_is_nan():
    rows = [{"id": "1", "name": "a", "language": "igbo", "cer_a": 0.1, "cer_b": 0.2}]
    corr = correlations(rows)
    assert math.isnan(corr["all"]["rho"])
    assert corr["all"]["n"] == 1


def test_render_writes_png(tmp_path):
    rows = [{"id": str(k), "name": str(k),
             "language": "english" if k % 3 == 0 else "yoruba",
             "cer_a": (k % 5) / 5, "cer_b": (k % 4) / 4} for k in range(12)]
    corr = correlations(rows)
    out = render(rows, corr, label_a="A", label_b="B", out_path=tmp_path / "x.png")
    assert out.exists() and out.stat().st_size > 0


def test_render_empty_raises():
    with pytest.raises(ValueError):
        render([], {"all": {"rho": 0, "p": 1, "n": 0},
                    "african": {"rho": 0, "p": 1, "n": 0}},
               label_a="A", label_b="B", out_path="unused.png")
