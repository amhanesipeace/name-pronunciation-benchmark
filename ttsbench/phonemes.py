"""ASR-independent phoneme scoring.

The ASR back-transcription metric (see scoring.py) folds in the biases of a
*word-level* English recogniser. This module instead reads the **phones**
directly from the audio with a universal phoneme recogniser (allosaurus), so it
does not depend on English word recognition at all, and compares them to a
reference pronunciation via a phoneme-level edit distance (Phoneme Error Rate).

Honest limitation: a phoneme *error* metric needs a reference pronunciation.
espeak-ng has no Yoruba/Igbo/Hausa voices, so references come from the `ipa`
column of the dataset — which for African names must be supplied and validated
by **native speakers**. The recognition layer here is ready to consume that
reference the moment it exists; until then PER is only meaningful for names that
carry a trusted reference (English is provided as a working demonstration).
"""
from __future__ import annotations

import tempfile
import wave
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _recognizer():
    from allosaurus.app import read_recognizer
    return read_recognizer()


def to_wav(path: str | Path) -> str:
    """Return a 16 kHz mono WAV path for `path` (converting mp3 etc. via PyAV).
    allosaurus only accepts WAV, so non-wav inputs are transcoded to a tempfile."""
    path = str(path)
    if path.lower().endswith(".wav"):
        return path

    import av
    out = tempfile.mktemp(suffix=".wav")
    container = av.open(path)
    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    pcm = bytearray()
    for frame in container.decode(audio=0):
        for rframe in resampler.resample(frame):
            pcm += bytes(rframe.planes[0])
    for rframe in resampler.resample(None):   # flush
        if rframe:
            pcm += bytes(rframe.planes[0])
    container.close()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(bytes(pcm))
    return out


def recognize_phones(path: str | Path) -> str:
    """Recognise the phone sequence in an audio file (space-separated IPA)."""
    return _recognizer().recognize(to_wav(path))


def tokens(ipa: str) -> list[str]:
    """Split an IPA string into phone tokens. allosaurus output is already
    space-separated; a reference like 'dʒ eɪ m z' works too. As a fallback,
    a reference with no spaces is split per character."""
    parts = ipa.split()
    if len(parts) <= 1 and ipa.strip():
        return list(ipa.strip())
    return parts


def _token_edit_distance(a: list[str], b: list[str]) -> int:
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
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def phoneme_error_rate(reference_ipa: str, hypothesis_ipa: str) -> float:
    """PER = phone edit distance / reference length. 0 = perfect."""
    ref, hyp = tokens(reference_ipa), tokens(hypothesis_ipa)
    if not ref:
        return 0.0
    return _token_edit_distance(ref, hyp) / len(ref)
