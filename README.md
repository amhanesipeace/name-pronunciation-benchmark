# AI Name-Pronunciation Fairness Benchmark

Measuring how accurately text-to-speech (TTS) systems pronounce personal names
from African languages (**Yoruba, Igbo, Hausa**) compared to common **English**
names — to surface and quantify bias in deployed speech systems.

> **Status: v0.3 — synthesis + ASR scoring.** The pipeline synthesizes names
> with a chosen TTS engine, records a manifest, and scores pronunciation by
> transcribing the audio back with Whisper and comparing to the intended name.

## Why this matters

Screen readers, voice assistants, and automated systems mispronouncing a
person's name is a real, repeated harm — it disproportionately affects people
with names outside the English/Western mainstream. A reproducible benchmark
turns "this feels biased" into measurable evidence.

## Project layout

```
name-pronunciation-benchmark/
  data/names.csv        input dataset: names + language + provenance (+ IPA later)
  ttsbench/
    dataset.py          load names from CSV  -> list[Name]
    engines.py          TTSEngine interface + GTTSEngine (add more here)
    synth.py            run names through an engine, write audio + manifest.csv
  run.py                CLI entry point
  outputs/              generated audio + manifest (git-ignored; see below)
  requirements.txt
```

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py                              # gTTS, English voice
python run.py --engine espeak --out outputs_espeak   # espeak-ng (needs the binary)
```

Outputs land in `outputs/audio/*` with `outputs/manifest.csv` describing every
file. Use a separate `--out` dir per engine to keep runs side by side.

## Engines

| id | library / binary | key? | offline | reproducible | notes |
|----|------------------|------|---------|--------------|-------|
| `gtts`   | gTTS (pip)          | no | no  | weak   | real Google system; unofficial endpoint |
| `espeak` | espeak-ng (binary)  | no | yes | strong | deterministic; can emit IPA phonemes |

Install the espeak-ng binary separately (it is not pip-installable):

```bash
brew install espeak-ng          # macOS (needs Homebrew)
# sudo apt-get install espeak-ng   # Debian/Ubuntu
```

## Design notes (the "why")

- **Engine abstraction.** `TTSEngine` is an abstract base class; `GTTSEngine`
  is the first implementation. Swapping in an offline/open engine or a
  commercial one later is a single new subclass — the pipeline is unchanged.
- **English voice on every name (for now).** v0.1 uses one English voice for
  *all* names. That is the core bias probe: how does an English-centric TTS —
  the kind embedded in most assistants — handle African names? Native-language
  voices are a separate axis to add later.
- **Everything is logged.** The manifest records engine + version + language +
  UTC timestamp + file path per name, so runs are auditable and comparable.

## ⚠️ Reproducibility considerations

- **gTTS is not stable over time.** It calls an *unofficial* Google Translate
  endpoint whose output can change silently. Treat generated audio as a
  **primary artifact to archive**, not something you can always regenerate
  identically. Always record the date and library version (the manifest does).
- **Archive audio outside git.** `outputs/` is git-ignored because raw audio is
  large and binary. For a paper, archive a fixed snapshot (zipped release, Git
  LFS, or a data repository like **Zenodo / OSF**) and cite it.
- **Pin versions** in `requirements.txt` when you freeze an experiment.
- **Prefer open, versioned models** (Coqui/Piper/espeak-ng) or **documented
  cloud APIs** (Google Cloud TTS, Amazon Polly, Azure) for results you intend
  to publish — they can be pinned to a model/voice version.

## ⚠️ Ethical considerations

- **Names are people.** Use common given names or documented name lists, and
  cite their source. Do **not** target or profile private individuals.
- **Ground truth needs native speakers.** Scoring "correct" pronunciation
  requires a reference (IPA and/or native-speaker recordings). Source this with
  the **informed consent and credit** of native speakers; treat it as human-
  subjects data and check whether your institution's **IRB/ethics board**
  applies.
- **Frame findings to reduce harm.** The goal is to expose and fix bias, not to
  caricature languages or communities. Involve native speakers in interpretation.
- **Respect terms of service.** Heavy automated use of unofficial endpoints
  (gTTS) may violate provider ToS; use official APIs for anything at scale.
- **Metric bias.** However you eventually score pronunciation (ASR
  back-transcription, phoneme distance vs IPA, human MOS ratings), the metric
  has its *own* biases — document and justify the choice.

## Scoring

```bash
pip install faster-whisper                 # one-time (heavier dependency)
python score.py --run outputs --model base # transcribe + score a synthesis run
```

Each clip is transcribed with Whisper and compared to the intended name via
**Character Error Rate (CER)**; results are written to `<run>/scores.csv` and
summarised per language.

## Preliminary findings (v0.3, gTTS, English voice, n=16)

| language | mean CER | exact-match rate |
|----------|---------:|-----------------:|
| english  | 0.00 | 100% |
| hausa    | 0.14 | 50%  |
| igbo     | 0.37 | 0%   |
| yoruba   | 0.56 | 0%   |

**English vs African CER gap: +0.36.** Every English name transcribed perfectly;
no Yoruba or Igbo name did (e.g. *Oluwaseun* → "Alois Seyoon", *Folake* →
"for locker"). Hausa scores better mostly because *Aisha*/*Ibrahim* are common
globally. These are tiny-n, illustrative results — not yet a statistical claim.

**Metric caveat.** ASR back-transcription mixes (1) TTS pronunciation quality and
(2) how ASR-friendly the audio is. A clean English baseline (gTTS: 0.00) isolates
the name-origin effect; a robotic voice (espeak-ng) inflates error for *all*
names. Compare **within** an engine; treat the **gap** as more robust than
absolute CER. Reference-based scoring (IPA / native-speaker) is the rigorous
follow-up.

## Roadmap

1. ✅ v0.1 — synthesis + manifest (gTTS)
2. ✅ Second engine: espeak-ng (offline, deterministic, IPA-capable)
3. ✅ Scoring v1: ASR back-transcription (Whisper) + CER, summarised by language
4. Add reference pronunciations (IPA / native-speaker audio) to `data/names.csv`
5. Analysis: per-language accuracy gaps + statistics + charts
6. Expand the dataset (more names, balanced per language) with sources cited
7. Add more engines (Coqui neural; cloud APIs for real deployed systems)
```
