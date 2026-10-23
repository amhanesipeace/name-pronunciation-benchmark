"""Tests for the error taxonomy (recovered / english_sub / garble / dropped)."""
import csv
from pathlib import Path

import pytest

from error_taxonomy import (classify, examples, load_lexicon, render_figure,
                            summarise)

ROOT = Path(__file__).resolve().parent.parent
LEX = {"for", "all", "you", "might", "america", "second", "bail", "at"}


def test_classify_recovered_on_exact_and_near():
    assert classify("Ada", "Ada", 0.0, True, LEX) == "recovered"
    assert classify("Ada", "Adah", 0.1, False, LEX) == "recovered"   # CER<=0.15


def test_classify_english_substitution():
    # majority of content words are ordinary English words
    assert classify("Olumide", "All you might", 1.0, False, LEX) == "english_sub"
    assert classify("Emeka", "America", 0.8, False, LEX) == "english_sub"


def test_classify_garble_when_novel_nonwords():
    assert classify("Oluwaseun", "Alois Seyoon", 0.78, False, LEX) == "garble"


def test_classify_dropped_on_empty():
    assert classify("Ada", "", 1.0, False, LEX) == "dropped"
    assert classify("Ada", "   .", 1.0, False, LEX) == "dropped"


def test_classify_name_tokens_dont_count_as_english():
    # A transcribed token that merely echoes the name must not be scored as the
    # recognizer "reaching for an English word": 'all' is in the lexicon, but
    # here it is the name itself, so it is excluded and the result is garble.
    assert classify("All", "all zzzq", 0.9, False, LEX) == "garble"
    # control: without the name-echo, the same English word -> english_sub
    assert classify("Zuberi", "all zzzq", 0.9, False, LEX | {"zzzq"}) == "english_sub"


def test_summarise_rates():
    rows = [
        {"name": "A", "language": "english", "cer": "0.0", "exact_match": "1",
         "transcription": "A"},
        {"name": "Olumide", "language": "yoruba", "cer": "1.0", "exact_match": "0",
         "transcription": "All you might"},
        {"name": "X", "language": "igbo", "cer": "0.9", "exact_match": "0",
         "transcription": "zzzzq"},
    ]
    s = summarise(rows, LEX)
    assert s["english"]["recovered_rate"] == 1.0
    assert s["african"]["counts"]["english_sub"] == 1
    assert s["african"]["counts"]["garble"] == 1
    assert s["african"]["english_sub_of_errors"] == pytest.approx(0.5)


def test_render_figure_writes_png(tmp_path):
    rows = [{"name": "A", "language": "english", "cer": "0.0", "exact_match": "1",
             "transcription": "A"},
            {"name": "Olumide", "language": "yoruba", "cer": "1.0",
             "exact_match": "0", "transcription": "All you might"}]
    out = render_figure(summarise(rows, LEX), tmp_path / "t.png")
    assert out.exists() and out.stat().st_size > 0


def test_lexicon_loads_and_is_large():
    lex = load_lexicon(ROOT / "data" / "common_english_words.txt")
    assert len(lex) > 5000 and "america" in lex


def test_reproducibility_english_substitution_is_real():
    """From the committed clean-baseline run: English names are near-perfectly
    recovered, African names often replaced by ordinary English words."""
    scores = ROOT / "outputs" / "scores.csv"
    if not scores.exists():
        pytest.skip("outputs/scores.csv not present")
    rows = list(csv.DictReader(open(scores, encoding="utf-8")))
    lex = load_lexicon(ROOT / "data" / "common_english_words.txt")
    s = summarise(rows, lex)
    assert s["english"]["recovered_rate"] == 1.0
    assert s["african"]["recovered_rate"] < 0.5
    assert s["african"]["english_sub_of_errors"] >= 0.2   # conservative lower bound
