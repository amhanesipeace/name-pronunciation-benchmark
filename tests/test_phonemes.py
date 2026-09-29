"""Tests for phoneme tokenisation + PER (no allosaurus/audio needed).

These cover the pure logic; the recogniser itself (allosaurus) is exercised
manually, not in CI, since it downloads a model and needs audio.
"""
from ttsbench.phonemes import tokens, phoneme_error_rate


def test_tokens_space_separated():
    assert tokens("d ʒ eɪ m z") == ["d", "ʒ", "eɪ", "m", "z"]


def test_tokens_fallback_to_chars_when_unspaced():
    assert tokens("dʒmz") == ["d", "ʒ", "m", "z"]


def test_tokens_empty():
    assert tokens("") == []


def test_per_perfect():
    assert phoneme_error_rate("d ʒ eɪ m z", "d ʒ eɪ m z") == 0.0


def test_per_one_substitution():
    # 1 differing phone out of 5 reference phones
    assert phoneme_error_rate("d ʒ eɪ m z", "d ʒ eɪ n z") == 1 / 5


def test_per_empty_reference():
    assert phoneme_error_rate("", "a b c") == 0.0
