"""Load the name dataset from a CSV file.

The dataset is deliberately plain CSV so it is easy to read, diff in git, and
extend by hand. Each row is one name to synthesize.

Columns:
    id        stable identifier (used in audio filenames + the manifest)
    name      the name text fed to the TTS engine
    language  yoruba | igbo | hausa | english  (the name's linguistic origin)
    origin    free-text provenance note (where the name comes from / its source)
    ipa       reference pronunciation in IPA — often blank for now; this is the
              "ground truth" we will need later to *score* pronunciations.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Name:
    id: str
    name: str
    language: str
    origin: str = ""
    ipa: str = ""


def load_names(csv_path: str | Path) -> list[Name]:
    """Read `csv_path` and return a list of Name records."""
    names: list[Name] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            text = (row.get("name") or "").strip()
            if not text:
                continue  # skip blank rows
            names.append(Name(
                id=(row.get("id") or f"n{i:03d}").strip(),
                name=text,
                language=(row.get("language") or "").strip().lower(),
                origin=(row.get("origin") or "").strip(),
                ipa=(row.get("ipa") or "").strip(),
            ))
    return names
