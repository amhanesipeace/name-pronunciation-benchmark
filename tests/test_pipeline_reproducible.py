"""End-to-end reproducibility: every analysis runs on the COMMITTED scores.

The other test modules exercise each analysis on synthetic rows. This one closes
the remaining gap: it drives each real entry point against the committed score
tables and asserts it produces output without error — so CI fails if any figure
or report script breaks on the actual data shapes (not just synthetic ones), and
the "regenerate everything from the repo" claim stays true.

Skips cleanly when the committed outputs are absent (partial checkout). Does not
cover `sensitivity.py`, which re-runs Whisper on the audio and so needs the
heavy stack by design.
"""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _in_repo_root(monkeypatch):
    """Scripts resolve run dirs relative to CWD; run from the repo root."""
    if not (ROOT / "outputs" / "scores.csv").exists():
        pytest.skip("committed outputs not present")
    monkeypatch.chdir(ROOT)


def test_aggregate_results_summarises_committed_runs():
    from aggregate_results import summarise
    s = summarise(Path("outputs"))
    assert s and s["n"] == 80 and s["engine"] == "gtts"


def test_forest_plot_builds_and_renders(tmp_path):
    import forest_plot
    rows = forest_plot.build_rows()
    assert len(rows) >= 4                       # several committed runs
    out = forest_plot.render(rows, tmp_path / "forest.png")
    assert out.exists() and out.stat().st_size > 0


def test_per_language_forest_builds_and_renders(tmp_path):
    import per_language_forest
    rows = per_language_forest.build_rows(Path("outputs"))
    assert {r["language"] for r in rows} == {"yoruba", "igbo", "hausa"}
    out = per_language_forest.render(rows, title="t", out_path=tmp_path / "plf.png")
    assert out.exists()


def test_cross_engine_runs_on_committed_carrier_runs(tmp_path):
    import cross_engine
    rows = cross_engine.paired(cross_engine.load(Path("outputs_gtts_carrier")),
                               cross_engine.load(Path("outputs_mms_carrier")))
    assert len(rows) == 80
    corr = cross_engine.correlations(rows)
    assert corr["all"]["rho"] > 0               # positive agreement
    out = cross_engine.render(rows, corr, label_a="a", label_b="b",
                              out_path=tmp_path / "ce.png")
    assert out.exists()


def test_error_taxonomy_runs_on_committed_scores(tmp_path):
    import csv
    from error_taxonomy import load_lexicon, render_figure, summarise
    rows = list(csv.DictReader(open("outputs/scores.csv", encoding="utf-8")))
    s = summarise(rows, load_lexicon("data/common_english_words.txt"))
    assert s["english"]["recovered_rate"] == 1.0
    out = render_figure(s, tmp_path / "tax.png")
    assert out.exists()


def test_comparison_charts_regenerate(tmp_path):
    import comparison_charts
    for name in ("engines", "carrier"):
        groups = comparison_charts.build_groups(comparison_charts.FIGURES[name][2])
        assert len(groups) >= 3
        out = comparison_charts.render(groups, title=name, out_path=tmp_path / f"{name}.png")
        assert out.exists()


def test_per_run_cer_chart_renders(tmp_path):
    from ttsbench.analyze import load_scores, plot_cer_by_language, summarize
    summary = summarize(load_scores("outputs/scores.csv"))
    out = plot_cer_by_language(summary, tmp_path / "cer.png", title="gtts")
    assert Path(out).exists()
