"""Tests for the statistics helpers."""
from ttsbench.stats import (cliffs_delta, effect_label, cers_by_language,
                            english_vs_african)


def test_cliffs_delta_extremes():
    # every a > every b  -> delta = +1
    assert cliffs_delta([5, 6, 7], [1, 2, 3]) == 1.0
    # every a < every b  -> delta = -1
    assert cliffs_delta([1, 2], [5, 6]) == -1.0
    # identical distributions -> 0
    assert cliffs_delta([1, 2, 3], [1, 2, 3]) == 0.0


def test_effect_label_thresholds():
    assert effect_label(0.05) == "negligible"
    assert effect_label(0.2) == "small"
    assert effect_label(0.4) == "medium"
    assert effect_label(0.8) == "large"


def test_cers_by_language_groups():
    rows = [
        {"language": "english", "cer": "0.0"},
        {"language": "english", "cer": "0.1"},
        {"language": "yoruba", "cer": "0.5"},
    ]
    grouped = cers_by_language(rows)
    assert grouped["english"] == [0.0, 0.1]
    assert grouped["yoruba"] == [0.5]


def test_english_vs_african_detects_gap():
    rows = ([{"language": "english", "cer": "0.0"} for _ in range(10)] +
            [{"language": "yoruba", "cer": "0.6"} for _ in range(10)])
    result = english_vs_african(rows)
    assert result is not None
    assert result["cliffs_delta"] > 0.9      # African clearly worse
    assert result["p"] < 0.01


def test_english_vs_african_needs_both_groups():
    rows = [{"language": "english", "cer": "0.0"}]
    assert english_vs_african(rows) is None
