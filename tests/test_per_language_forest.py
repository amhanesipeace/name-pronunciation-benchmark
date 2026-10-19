"""Tests for the per-language forest plot renderer (no synthesis data needed)."""
import pytest

from per_language_forest import render


def _row(lang, delta, lo, hi, p_holm):
    return {"language": lang, "n": 20, "median": 0.3, "U": 300.0, "p": p_holm,
            "cliffs_delta": delta, "effect": "large",
            "delta_lo": lo, "delta_hi": hi, "p_holm": p_holm}


def test_render_writes_png(tmp_path):
    rows = [
        _row("yoruba", 0.89, 0.73, 1.00, 3e-7),   # significant
        _row("igbo", 0.84, 0.65, 1.00, 6e-7),     # significant
        _row("hausa", 0.74, 0.53, 0.90, 3e-6),    # significant
    ]
    out = render(rows, title="test", out_path=tmp_path / "plf.png")
    assert out.exists()
    assert out.stat().st_size > 0


def test_render_handles_non_significant(tmp_path):
    out = render([_row("hausa", 0.10, -0.20, 0.35, 0.40)],
                 title="n.s.", out_path=tmp_path / "ns.png")
    assert out.exists()


def test_render_empty_raises():
    with pytest.raises(ValueError):
        render([], title="x", out_path="unused.png")


def test_render_requires_ci(tmp_path):
    rows = [{"language": "hausa", "n": 20, "median": 0.3, "cliffs_delta": 0.7,
             "effect": "large", "p": 1e-6, "p_holm": 1e-6}]  # no delta_lo/hi
    with pytest.raises(ValueError):
        render(rows, title="x", out_path=tmp_path / "nope.png")
