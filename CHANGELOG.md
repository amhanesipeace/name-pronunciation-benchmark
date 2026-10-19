# Changelog

All notable changes to this benchmark are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and versions aim to follow
[Semantic Versioning](https://semver.org/). Dates are ISO (YYYY-MM-DD).

## [1.0.0] — 2026-10-19

First archival release: a complete, reproducible pipeline with statistical
rigour and an honest account of limitations — the snapshot intended for
citation and a Zenodo DOI.

### Added
- **Confidence intervals everywhere.** 95% percentile-bootstrap CIs (2,000
  seeded resamples) for the mean-CER gap and for Cliff's delta, pooled and
  **per language**, so every effect is reported with its uncertainty.
- **Forest plots.** `forest_plot.py` — one figure unifying all runs (gap + CI,
  coloured by significance); `per_language_forest.py` — each African language
  vs English for a single run. Both embedded in the write-ups.
- **ASR-scorer sensitivity analysis** (`sensitivity.py`): re-scoring across
  Whisper `tiny`/`base`/`small` shows the gap is not an artefact of one scorer.
- **Dataset datasheet** (`data/DATASHEET.md`), following Gebru et al.
- **Master results table** (`aggregate_results.py` → `RESULTS.md`) with
  significance columns, and a completed engine matrix (espeak at n=120).
- **Extended dataset** (120 names, 30 per language) with documented provenance;
  the headline bias replicates and strengthens (δ = +0.84, p ≈ 1×10⁻¹²).
- **Paper-style writeup** (`PAPER.md`): abstract, method, results, limitations,
  ethics.
- Pinned dependency versions for reproducibility.

### Changed
- Reconciled version strings across the repo to a single `1.0.0` release.

### Known limitations
- No native-speaker reference pronunciations yet (the phoneme-error layer is
  built and waiting for this data); ASR back-transcription is only interpretable
  when the engine has a clean English baseline. See `PAPER.md` §4.

## [0.6.0] — earlier
- Statistical significance testing: Mann-Whitney U + Cliff's delta,
  Holm-Bonferroni corrected; three-engine comparison (gTTS, espeak-ng, MMS);
  carrier-phrase synthesis that unmasks hidden bias in the neural engine;
  ASR-independent phoneme-scoring pipeline; qualitative error analysis;
  one-command Makefile; tests + CI; LICENSE + CITATION.cff.

## [0.5.0] — earlier
- Expanded the dataset to 80 names (20 per language, balanced).

## [0.4.0] — earlier
- Analysis layer: per-language CER statistics + bar chart.

## [0.3.0] — earlier
- Scoring v1: Whisper ASR back-transcription + Character Error Rate; first
  bias findings.

## [0.2.0] — earlier
- Initial benchmark: name dataset + synthesis pipeline (gTTS, espeak-ng).
