"""Score synthesized names by transcribing them back with ASR and comparing to
the intended name.

The idea (ASR back-transcription):
    If a TTS system mispronounces a name, an English speech recognizer will not
    transcribe it back correctly. So the transcription error, measured per name
    and averaged per language, is a signal of pronunciation bias.

Why this metric first:
    + needs NO human ground truth (fast to stand up)
    + fully automatable and reproducible

Its honest limitation (document this in any writeup):
    - it measures "how an ASR hears the TTS", so the ASR's OWN biases are folded
      in. It is a screening signal, not the final word. Reference-based scoring
      (IPA / native-speaker recordings) is the more rigorous follow-up.

We use `faster-whisper` (CTranslate2) for ASR: lighter than full PyTorch Whisper,
decodes audio without a separate ffmpeg binary, and runs fine on CPU.
"""
from __future__ import annotations

import re
from pathlib import Path


def normalize(text: str) -> str:
    """Lowercase and keep only letters/digits (drop spaces & punctuation), so
    'Oluwa-seun!' and 'oluwaseun' compare equal at the character level."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def strip_carrier(transcription: str, carrier: str) -> str:
    """Remove the carrier words from an ASR transcription, leaving the name.

    Given carrier ``"My name is {name}."`` and a heard sentence like
    ``"My name is Oluwaseon."`` this returns ``"Oluwaseon"``. It drops any
    leading/trailing words that belong to the carrier template, so what remains
    is the recognised name region, which we then score against the target.
    """
    carrier_words = {re.sub(r"[^a-z0-9]", "", w.lower())
                     for w in carrier.replace("{name}", " ").split()}
    carrier_words.discard("")
    words = [w for w in re.split(r"\s+", transcription.strip()) if w]
    kept = [w for w in words
            if re.sub(r"[^a-z0-9]", "", w.lower()) not in carrier_words]
    return " ".join(kept).strip()


def edit_distance(a: str, b: str) -> int:
    """Levenshtein edit distance (min single-char insert/delete/substitute edits
    to turn `a` into `b`). Classic dynamic-programming implementation, no deps."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1,        # deletion
                           cur[j - 1] + 1,     # insertion
                           prev[j - 1] + cost))  # substitution
        prev = cur
    return prev[-1]


def edit_ops(reference: str, hypothesis: str) -> dict:
    """Decompose the edit distance into its operation types.

    `edit_distance` returns a single number; this traces back through the DP
    table to count *how* `reference` was turned into `hypothesis`:

        substitutions  a character was heard as a different one
        deletions      a character of the name was dropped
        insertions     a character not in the name was added
        matches        a character came through unchanged

    Compares the same normalised strings as `char_error_rate`, and by
    construction ``substitutions + deletions + insertions`` equals
    `edit_distance`, so CER = (those three) / len(reference). This lets us ask
    not just *how wrong* a name is but *what kind* of error it is — e.g. are
    African names failing by dropped syllables (deletions) or wrong sounds
    (substitutions)?
    """
    ref, hyp = normalize(reference), normalize(hypothesis)
    m, n = len(ref), len(hyp)
    # Full DP table (edit_distance keeps only one row; here we need to backtrace).
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1,        # deletion
                           dp[i][j - 1] + 1,        # insertion
                           dp[i - 1][j - 1] + cost)  # substitution / match
    sub = dele = ins = match = 0
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref[i - 1] == hyp[j - 1] \
                and dp[i][j] == dp[i - 1][j - 1]:
            match += 1
            i, j = i - 1, j - 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            sub += 1
            i, j = i - 1, j - 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            dele += 1
            i -= 1
        else:  # j > 0
            ins += 1
            j -= 1
    return {"substitutions": sub, "deletions": dele, "insertions": ins,
            "matches": match, "ref_len": m}


def char_error_rate(reference: str, hypothesis: str) -> float:
    """Character Error Rate: edit distance normalised by reference length.
    0.0 = perfect; ~1.0 = completely wrong. Compares normalised strings."""
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return 0.0
    return edit_distance(ref, hyp) / len(ref)


class Transcriber:
    """A faster-whisper model, loaded once and reused for every clip."""

    def __init__(self, model_size: str = "base"):
        from faster_whisper import WhisperModel
        # int8 on CPU keeps memory + speed reasonable for short clips.
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.model_size = model_size

    def transcribe(self, audio_path: str | Path) -> str:
        # language="en": we probe how an ENGLISH recogniser hears the name,
        # matching the English TTS voice used in synthesis.
        segments, _ = self.model.transcribe(str(audio_path), language="en",
                                            beam_size=1)
        return " ".join(seg.text for seg in segments).strip()
