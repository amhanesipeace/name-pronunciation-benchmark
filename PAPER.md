# Measuring Name-Pronunciation Bias in Text-to-Speech Systems for African Names

**Peace Amhanesi** · [github.com/amhanesipeace/name-pronunciation-benchmark](https://github.com/amhanesipeace/name-pronunciation-benchmark)

*A short, self-contained writeup of the benchmark. Preliminary work: small n,
automatic scoring; see Limitations.*

## Abstract

Mispronouncing a person's name is a small but repeated harm that falls hardest
on people whose names lie outside the English/Western mainstream. We build an
open, reproducible benchmark that quantifies how accurately text-to-speech (TTS)
systems render personal names from three African languages — **Yoruba, Igbo, and
Hausa** — relative to common **English** names. Using ASR back-transcription and
a non-parametric significance test on n=80 names, we find that a widely used
system (Google's gTTS) pronounces African names **significantly and substantially
worse** than English names (Cliff's δ = +0.82, p ≈ 9×10⁻⁹). We further show that
**evaluation methodology determines whether the bias is even visible**: a neural
system (Meta MMS) appears unbiased under a naive isolated-word test only because
that test is *saturated*; a carrier-sentence protocol reveals a large, significant
gap (δ = +0.70). We release the dataset, pipeline, statistics, an ASR-independent
phoneme-scoring layer, and an honest account of what such a benchmark cannot yet
do without native-speaker reference data.

## 1. Motivation

Screen readers, voice assistants, and automated announcements routinely
mispronounce non-Western names. Anecdote is common; measurement is rare. A
reproducible benchmark turns "this feels biased" into evidence that can be
tracked and acted on.

## 2. Method

- **Dataset.** 80 given names, balanced 20 each across English, Yoruba, Igbo,
  Hausa (`data/names.csv`). Provenance is documented and currently *not*
  native-speaker-validated (see Limitations).
- **Engines.** gTTS (Google), espeak-ng (formant), Meta MMS (neural), and an
  API-gated ElevenLabs engine. For a like-for-like probe, each speaks every name
  with an **English** voice — the common case in deployed English-language
  assistants.
- **Primary metric — ASR back-transcription.** Each clip is transcribed with
  Whisper; we score **Character Error Rate (CER)** between the intended name and
  the transcription. Rationale: if a TTS mispronounces a name, an English
  recognizer cannot recover it — no human ground truth required.
- **Carrier protocol.** Names are optionally spoken inside "My name is *X*." so
  neural engines produce natural connected speech instead of mangling lone words.
- **Phoneme layer (ASR-independent).** A universal phoneme recognizer
  (allosaurus) reads phones directly from audio; Phoneme Error Rate is computed
  against a reference `ipa` column.
- **Statistics.** Non-parametric **Mann-Whitney U** (CER is bounded/skewed) with
  **Cliff's delta** effect size and **Holm-Bonferroni** correction across the
  three per-language comparisons.

## 3. Results

1. **A mainstream system is measurably biased.** gTTS: English CER 0.01 vs
   African 0.37; gap significant and large (δ = +0.82, p ≈ 9×10⁻⁹). Every
   per-language gap is significant after correction.
2. **Methodology decides visibility.** MMS under isolated words looks unbiased
   (0.87 vs 0.90, "gap" +0.04) — a saturation artifact. Under the carrier
   protocol the real gap emerges: 0.21 vs 0.61 (δ = +0.70, p ≈ 1.5×10⁻⁶). gTTS
   remains significantly biased under the fairer test (δ = +0.75).
3. **Coverage precedes quality.** Meta's "massively multilingual" MMS ships
   Yoruba and Hausa voices but **no Igbo voice** — some languages are excluded
   before pronunciation quality is even a question.
4. **What it sounds like.** African names are turned into unrelated English
   words: *Aliyu* → "I'll leave you", *Emeka* → "America", *Oluwaseun* → "Alois
   Seyoon", *Folake* → "For Locker".

## 4. Limitations

- **No native-speaker reference.** The rigorous question — how close is the audio
  to the *correct native* pronunciation — needs native-speaker IPA or recordings.
  espeak-ng has no Yoruba/Igbo/Hausa voices, so references cannot be
  auto-generated; the phoneme layer is built and waiting for this data.
- **ASR metric is not neutral.** Back-transcription folds in the recognizer's own
  biases and is only interpretable when the engine has a clean English baseline.
- **Recognizer noise.** The universal phoneme recognizer is unreliable on short
  single-word clips, so PER is not yet a dependable standalone metric.
- **Scale and provenance.** Small n; names compiled from general knowledge, not a
  cited, validated corpus.
- **English-voice-only, three engines.** Native-language voices and commercial
  systems (Polly, Azure, Google Cloud, ElevenLabs) are largely untested.

## 5. Ethical considerations

- **Names are people.** Only common given names are used; no private individuals
  are targeted or profiled.
- **Ground truth is human-subjects data.** Native-speaker pronunciations must be
  collected with **informed consent and credit**, and treated under the relevant
  **IRB/ethics** process.
- **Framing to reduce harm.** The aim is to expose and fix bias, not to caricature
  languages or communities; native speakers should be involved in interpretation.
- **Metric humility.** Every scoring choice carries its own bias; we report
  methods and limitations openly rather than a single headline number.

## 6. Future work

Native-speaker reference pronunciations (unlocking the phoneme metric and the
definitive study); native-language voices; commercial-system benchmarking; a
larger, source-cited dataset; and public archiving (Zenodo/OSF) for a DOI.
