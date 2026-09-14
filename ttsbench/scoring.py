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
