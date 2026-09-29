"""Tests for the scoring helpers (pure functions; no ASR model needed)."""
from ttsbench.scoring import (normalize, edit_distance, char_error_rate,
                              strip_carrier)


def test_normalize_strips_case_and_punctuation():
    assert normalize("Oluwa-seun!") == "oluwaseun"
    assert normalize("  James. ") == "james"
    assert normalize("") == ""


def test_edit_distance():
    assert edit_distance("cat", "cat") == 0
    assert edit_distance("cat", "cut") == 1        # substitution
    assert edit_distance("cat", "cats") == 1       # insertion
    assert edit_distance("", "abc") == 3


def test_char_error_rate_perfect_and_wrong():
    assert char_error_rate("James", "James") == 0.0
    assert char_error_rate("James", "james!") == 0.0     # normalised first
    # completely different string -> high CER
    assert char_error_rate("Ngozi", "xyz") > 0.5


def test_char_error_rate_empty_reference():
    assert char_error_rate("", "anything") == 0.0


def test_strip_carrier_isolates_name():
    c = "My name is {name}."
    assert strip_carrier("My name is Oluwaseon.", c) == "Oluwaseon."
    assert strip_carrier("my name is James", c) == "James"
    # multi-word recognised name is preserved
    assert strip_carrier("My name is a boob a car", c) == "a boob a car"


def test_strip_carrier_no_carrier_words():
    # a bare transcription with none of the carrier words is returned as-is
    assert strip_carrier("Folake", "My name is {name}.") == "Folake"
