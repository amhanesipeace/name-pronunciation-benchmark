"""Tests for the forest plot renderer (no synthesis data needed)."""
import pytest

from forest_plot import render


def _row(engine, cond, n, gap, lo, hi, delta):
    return {"engine": engine, "condition": cond, "n": n, "gap": gap,
            "gap_lo": lo, "gap_hi": hi, "delta": delta,
            "effect": "large", "p": 1e-6}


def test_render_writes_png(tmp_path):
    rows = [
        _row("gtts", "carrier", 80, 0.24, 0.19, 0.29, 0.75),   # CI clear of 0
        _row("mms", "isolated", 80, 0.04, -0.24, 0.28, 0.12),  # CI crosses 0
    ]
    out = render(rows, tmp_path / "forest.png")
    assert out.exists()
    assert out.stat().st_size > 0


def test_render_handles_single_row(tmp_path):
    out = render([_row("gtts", "isolated", 120, 0.40, 0.34, 0.46, 0.84)],
                 tmp_path / "one.png")
    assert out.exists()


def test_render_empty_raises():
    with pytest.raises(ValueError):
        render([], "unused.png")
