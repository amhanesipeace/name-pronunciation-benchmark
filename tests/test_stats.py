"""Tests for the statistics helpers."""
import pytest

from ttsbench.stats import (cliffs_delta, effect_label, cers_by_language,
                            english_vs_african, english_vs_african_permutation,
                            permutation_test, bootstrap_ci,
                            probability_of_superiority)


def test_bootstrap_ci_reports_a_reproducible_se():
    a = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    r1 = bootstrap_ci(lambda x: sum(x) / len(x), (a,), n_boot=500, seed=0)
    r2 = bootstrap_ci(lambda x: sum(x) / len(x), (a,), n_boot=500, seed=0)
    assert r1["se"] > 0                       # a varying statistic has spread
    assert r1["se"] == r2["se"]               # seeded -> reproducible
    assert r1["lo"] <= r1["point"] <= r1["hi"]


def test_bootstrap_ci_empty_sample_has_zero_se():
    r = bootstrap_ci(lambda x: sum(x) / len(x) if x else 0.0, ([],), n_boot=100)
    assert r["se"] == 0.0 and r["n_boot"] == 0


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


def test_probability_of_superiority_extremes_and_ties():
    # every a > every b -> PS = 1
    assert probability_of_superiority([5, 6, 7], [1, 2, 3]) == 1.0
    # every a < every b -> PS = 0
    assert probability_of_superiority([1, 2], [5, 6]) == 0.0
    # identical values -> all ties -> PS = 0.5
    assert probability_of_superiority([1, 2, 3], [1, 2, 3]) == 0.5
    # empty -> defined as 0.5 (no information)
    assert probability_of_superiority([], [1, 2]) == 0.5


def test_probability_of_superiority_matches_cliffs_delta_without_ties():
    a, b = [0.3, 0.6, 0.9, 0.5], [0.0, 0.1, 0.2, 0.05]
    ps = probability_of_superiority(a, b)
    # PS = (delta + 1) / 2 exactly when there are no ties.
    assert ps == pytest.approx((cliffs_delta(a, b) + 1) / 2)


def test_english_vs_african_reports_probability_of_superiority():
    rows = ([{"language": "english", "cer": "0.0"} for _ in range(10)] +
            [{"language": "yoruba", "cer": "0.6"} for _ in range(10)])
    st = english_vs_african(rows)
    assert st["prob_superiority"] == pytest.approx(1.0)   # all African worse


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


# --- permutation_test -------------------------------------------------------

def test_permutation_test_detects_clear_separation():
    afr = [0.5, 0.6, 0.7, 0.55, 0.65]
    eng = [0.0, 0.01, 0.02, 0.0, 0.03]
    res = permutation_test(afr, eng, n_perm=2000, seed=0)
    assert res["observed_gap"] > 0.5
    assert res["p"] < 0.01                    # no reshuffle rivals a clean gap
    assert res["n_perm"] == 2000


def test_permutation_test_null_when_groups_identical():
    same = [0.2, 0.3, 0.4, 0.5]
    res = permutation_test(same, list(same), n_perm=1000, seed=0)
    assert res["observed_gap"] == 0.0
    assert res["p"] > 0.2                      # no real gap -> not significant


def test_permutation_p_never_zero_and_is_seeded():
    afr, eng = [1.0, 1.0, 1.0], [0.0, 0.0, 0.0]
    a = permutation_test(afr, eng, n_perm=500, seed=7)
    b = permutation_test(afr, eng, n_perm=500, seed=7)
    assert a["p"] == b["p"]                     # reproducible for a fixed seed
    assert a["p"] >= 1 / (500 + 1)             # (b+1)/(m+1): never exactly 0
    assert a["p"] <= 1.0
    # A different seed draws different permutations (sanity: still a valid p).
    assert 0 < permutation_test(afr, eng, n_perm=500, seed=8)["p"] <= 1.0


def test_permutation_empty_group_is_safe():
    assert permutation_test([], [0.1], n_perm=10)["p"] == 1.0
    assert english_vs_african_permutation(
        [{"language": "english", "cer": "0.0"}]) is None


def test_english_vs_african_permutation_agrees_with_rank_test():
    rows = ([{"language": "english", "cer": "0.0"} for _ in range(10)] +
            [{"language": "yoruba", "cer": "0.6"} for _ in range(10)])
    perm = english_vs_african_permutation(rows, n_perm=2000, seed=0)
    assert perm["p"] < 0.01                    # same verdict as the MWU test
