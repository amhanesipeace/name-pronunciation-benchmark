"""Tests for the comparison-chart generator (no synthesis data needed)."""
import pytest

from comparison_charts import render


def _g(label, en, af):
    return {"label": label, "english_cer": en, "african_cer": af}


def test_render_writes_png(tmp_path):
    groups = [_g("gTTS", 0.01, 0.37), _g("espeak", 0.64, 0.90),
              _g("MMS", 0.87, 0.90)]
    out = render(groups, title="engines", out_path=tmp_path / "cmp.png")
    assert out.exists() and out.stat().st_size > 0


def test_render_single_group(tmp_path):
    out = render([_g("gTTS", 0.01, 0.37)], title="one", out_path=tmp_path / "one.png")
    assert out.exists()


def test_render_empty_raises():
    with pytest.raises(ValueError):
        render([], title="x", out_path="unused.png")
