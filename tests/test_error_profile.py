"""Unit tests for the CER edit-operation decomposition.

Two layers: `scoring.edit_ops` (the backtrace that counts substitutions /
deletions / insertions) and `error_profile` (which pools those ops into rates).
All run on synthetic strings/rows — no committed data needed.
"""
import pytest

import error_profile
from ttsbench.scoring import edit_distance, edit_ops, normalize


def test_identical_strings_are_all_matches():
    o = edit_ops("oluwaseun", "oluwaseun")
    assert o["substitutions"] == 0 and o["deletions"] == 0 and o["insertions"] == 0
    assert o["matches"] == len("oluwaseun")


def test_pure_substitution():
    o = edit_ops("cat", "cot")          # a -> o, same length
    assert o == {"substitutions": 1, "deletions": 0, "insertions": 0,
                 "matches": 2, "ref_len": 3}


def test_pure_deletion_when_hypothesis_shorter():
    o = edit_ops("emeka", "emka")       # 'e' in the name dropped
    assert o["deletions"] == 1 and o["insertions"] == 0 and o["substitutions"] == 0


def test_pure_insertion_when_hypothesis_longer():
    o = edit_ops("ada", "adaa")         # an extra character added
    assert o["insertions"] == 1 and o["deletions"] == 0 and o["substitutions"] == 0


def test_normalisation_matches_cer():
    # Case and punctuation are stripped exactly like char_error_rate does.
    o = edit_ops("Oluwa-seun!", "oluwaseun")
    assert o["substitutions"] == o["deletions"] == o["insertions"] == 0


@pytest.mark.parametrize("ref,hyp", [
    ("james", "james"), ("emeka", "america"), ("aliyu", "ill leave you"),
    ("", "something"), ("ngozi", ""), ("bola", "boler"),
])
def test_ops_sum_equals_edit_distance(ref, hyp):
    """The decomposition is exact: S + D + I == the Levenshtein distance, so the
    three rates reconstruct CER with nothing left over."""
    o = edit_ops(ref, hyp)
    assert o["substitutions"] + o["deletions"] + o["insertions"] \
        == edit_distance(normalize(ref), normalize(hyp))


def _row(language, name, transcription):
    return {"language": language, "name": name, "transcription": transcription}


def test_profile_rates_sum_to_cer():
    rows = [_row("yoruba", "emeka", "america"), _row("igbo", "ada", "adaa")]
    p = error_profile.profile(rows)
    assert p["sub_rate"] + p["del_rate"] + p["ins_rate"] == pytest.approx(p["cer"])
    # Micro-averaged CER equals pooled errors / pooled characters.
    assert p["errors"] == p["substitutions"] + p["deletions"] + p["insertions"]


def test_profile_shares_sum_to_one_when_errors_present():
    rows = [_row("hausa", "aliyu", "ill leave you")]
    p = error_profile.profile(rows)
    assert p["sub_share"] + p["del_share"] + p["ins_share"] == pytest.approx(1.0)


def test_profile_empty_group_is_safe():
    p = error_profile.profile([])
    assert p["cer"] == 0.0 and p["errors"] == 0 and p["sub_share"] == 0.0


def test_report_has_table_and_conclusion():
    rows = [_row("english", "james", "james"),
            _row("yoruba", "emeka", "america"),
            _row("igbo", "ngozi", "nausea"),
            _row("hausa", "aliyu", "ill leave you")]
    text = error_profile.report(rows)
    assert "CER decomposition" in text
    assert "error mix (S/D/I)" in text
    assert "Why it matters" in text
