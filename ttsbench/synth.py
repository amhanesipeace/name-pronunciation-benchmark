"""Run a list of names through a TTS engine and record a reproducible manifest.

The manifest (a CSV) is the scientific core of the benchmark: it captures WHAT
was generated, by WHICH engine/version, WHEN, and WHERE the audio lives — so a
run can be audited, reproduced, and later scored.
"""
from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path

from .dataset import Name
from .engines import TTSEngine

# Column order for the manifest CSV.
MANIFEST_FIELDS = [
    "id", "name", "language", "origin",
    "engine", "engine_version", "tts_lang",
    "audio_path", "audio_format", "timestamp_utc", "status", "error",
]


def _slug(text: str) -> str:
    """Filesystem-safe version of a name, e.g. 'Oluwaseun' -> 'oluwaseun'."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def synthesize_all(names: list[Name], engine: TTSEngine,
                   output_dir: str | Path) -> tuple[Path, list[dict]]:
    """Synthesize every name; write audio files + a manifest.csv. Returns
    (manifest_path, rows). Failures are recorded per-row, not fatal, so one
    bad name never aborts the whole run."""
    output_dir = Path(output_dir)
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    engine_meta = engine.describe()
    rows: list[dict] = []

    for name in names:
        filename = f"{name.id}_{name.language}_{_slug(name.name)}.{engine.audio_ext}"
        out_path = audio_dir / filename
        row = {
            "id": name.id,
            "name": name.name,
            "language": name.language,
            "origin": name.origin,
            "engine": engine_meta.get("engine", ""),
            "engine_version": engine_meta.get("engine_version", ""),
            "tts_lang": engine_meta.get("tts_lang", ""),
            "audio_path": str(out_path.relative_to(output_dir)),
            "audio_format": engine.audio_ext,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "ok",
            "error": "",
        }
        try:
            engine.synthesize(name.name, out_path)
            print(f"  ok  {name.name:<24} -> {row['audio_path']}")
        except Exception as exc:
            row["status"] = "error"
            row["error"] = f"{type(exc).__name__}: {exc}"
            print(f"  ERR {name.name:<24} {row['error']}")
        rows.append(row)

    manifest_path = output_dir / "manifest.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return manifest_path, rows
