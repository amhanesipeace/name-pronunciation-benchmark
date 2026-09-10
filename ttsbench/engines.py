"""Text-to-speech engines behind a single common interface.

Design goal: the rest of the benchmark should not care *which* TTS system it is
talking to. Adding a new system (Coqui, Piper, espeak-ng, Amazon Polly, Google
Cloud TTS, ...) means writing one more small subclass of `TTSEngine` — nothing
else in the pipeline changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSEngine(ABC):
    """Abstract base class every TTS backend implements."""

    #: short, stable id used in filenames and the manifest (e.g. "gtts")
    name: str = "base"
    #: file extension of the audio this engine produces (e.g. "mp3", "wav")
    audio_ext: str = "wav"

    @abstractmethod
    def synthesize(self, text: str, out_path: Path) -> None:
        """Render `text` to speech and write the audio to `out_path`."""
        raise NotImplementedError

    @property
    def version(self) -> str:
        """Version string recorded in the manifest (for reproducibility)."""
        return "unknown"

    def describe(self) -> dict:
        """Metadata about this engine/config, copied into every manifest row."""
        return {"engine": self.name, "engine_version": self.version}


class GTTSEngine(TTSEngine):
    """Google Translate TTS via the `gTTS` library.

    Why we start here:
      + free, no API key, tiny install
      + reflects a real, widely used Google system

    Caveats you must document in any writeup:
      - it calls an UNOFFICIAL Google Translate endpoint (can change or break,
        and heavy automated use is a terms-of-service grey area)
      - it needs an internet connection
      - output can drift over time, so it is only "reproducible" if you ARCHIVE
        the generated audio and record the date + library version (we do both).
    """

    name = "gtts"
    audio_ext = "mp3"

    def __init__(self, lang: str = "en", tld: str = "com", slow: bool = False):
        # lang="en" is deliberate for the first experiment: we make ONE
        # English voice pronounce every name, English and African alike, to
        # measure how an English-centric TTS handles African names. Native-
        # language voices are a separate axis we can add later.
        self.lang = lang
        self.tld = tld      # Google domain, e.g. "com", "co.uk" — affects accent
        self.slow = slow

    def synthesize(self, text: str, out_path: Path) -> None:
        # Imported lazily so `import ttsbench` works even if gTTS isn't installed.
        from gtts import gTTS
        gTTS(text=text, lang=self.lang, tld=self.tld, slow=self.slow).save(str(out_path))

    @property
    def version(self) -> str:
        try:
            from importlib.metadata import version
            return f"gTTS-{version('gTTS')}"
        except Exception:
            return "gTTS-unknown"

    def describe(self) -> dict:
        meta = super().describe()
        meta.update({"tts_lang": self.lang, "tld": self.tld, "slow": self.slow})
        return meta


class EspeakNgEngine(TTSEngine):
    """espeak-ng, an open-source formant/phoneme synthesizer, via its CLI.

    Why add this:
      + fully OFFLINE and DETERMINISTIC (same input -> same audio every time)
      + open-source and cross-platform -> strong reproducibility for a benchmark
      + can also emit IPA phonemes (see `phonemize`) -> useful ground-truth aid

    Requirement: the `espeak-ng` binary must be installed and on PATH.
      macOS:  brew install espeak-ng
      Debian/Ubuntu: sudo apt-get install espeak-ng

    Caveat: espeak-ng uses formant synthesis, so it sounds robotic. That is
    fine (even helpful) for a benchmark: it is consistent and transparent about
    the phonemes it chose, unlike a neural voice that "smooths over" mistakes.
    """

    name = "espeak"
    audio_ext = "wav"

    def __init__(self, lang: str = "en", speed: int = 160, binary: str = "espeak-ng"):
        # lang maps to an espeak-ng voice code (e.g. "en"). As with gTTS, v0.1
        # uses the English voice on every name for the core bias probe.
        self.lang = lang
        self.speed = speed              # words per minute
        self.binary = binary
        self._version: str | None = None

    def _run(self, args: list[str], **kwargs):
        import subprocess
        try:
            return subprocess.run([self.binary, *args], check=True,
                                  capture_output=True, text=True, **kwargs)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"'{self.binary}' not found. Install it (macOS: "
                f"'brew install espeak-ng') and ensure it is on your PATH."
            ) from exc

    def synthesize(self, text: str, out_path: Path) -> None:
        # -v voice, -s speed, -w write to WAV file; text passed as its own arg
        # (no shell) so names with punctuation/spaces are handled safely.
        self._run(["-v", self.lang, "-s", str(self.speed), "-w", str(out_path), text])

    def phonemize(self, text: str) -> str:
        """Return espeak-ng's IPA phoneme transcription of `text` (no audio).

        Handy later: gives a consistent phoneme string you can compare against
        a reference pronunciation. Not part of synthesis; a bonus utility.
        """
        # -q: quiet (no audio), --ipa: print IPA phonemes to stdout
        result = self._run(["-v", self.lang, "-q", "--ipa", text])
        return result.stdout.strip()

    @property
    def version(self) -> str:
        if self._version is None:
            try:
                out = self._run(["--version"]).stdout.strip()
                self._version = f"espeak-ng-{out.split()[3]}" if out else "espeak-ng-unknown"
            except Exception:
                self._version = "espeak-ng-unknown"
        return self._version

    def describe(self) -> dict:
        meta = super().describe()
        meta.update({"tts_lang": self.lang, "speed": self.speed})
        return meta


# Registry so the CLI can select an engine by name. Add new engines here.
ENGINES = {
    "gtts": GTTSEngine,
    "espeak": EspeakNgEngine,
}
