# Contributing native-speaker pronunciation data

> **Status: design, not an open intake.** This describes *how* native-speaker
> reference data would be contributed and handled — the terms, the format, and
> the ethics process — so the plan is public and credible. It is **not** a live
> "upload your voice" form yet. Please **do not** send recordings through pull
> requests or email. To get involved, [open an issue](../../issues/new) saying
> which language(s) you speak; collection will begin only once the consent and
> ethics process below is in place. See also the project's
> [ethics notes](PAPER.md#5-ethical-considerations) and
> [`data/DATASHEET.md`](data/DATASHEET.md).

## Why this matters

The benchmark currently scores pronunciation with **ASR back-transcription**,
which can only tell you whether an English recognizer can recover a name — not
whether the audio matches the **correct native pronunciation**. Answering the
real question needs a native-speaker reference: for each name, how a fluent
speaker actually says it. That reference unlocks the ASR-independent phoneme
layer (`phoneme_score.py`) and the definitive version of the study. It is the
single most valuable thing the project is missing — and it is exactly the kind
of data that must be collected carefully, because **a recording of a person's
voice is personal data about a real person.**

## What a contribution would consist of

Per name, a contributor who speaks the language would provide any of:

| Field | Example | Notes |
|-------|---------|-------|
| `name` | `Oluwaseun` | must already be (or be added to) `data/names.csv` |
| `language` | `yoruba` | one of the covered languages, or a proposed new one |
| recording | a short clip of the name spoken naturally | WAV/FLAC preferred; a phone recording is fine |
| `ipa` *(optional)* | `o l u w a ʃ e u n` | space-separated phones, matching the `ipa` column schema |
| `region`/`dialect` *(optional)* | `Standard Yoruba` | pronunciation varies by region — this is signal, not noise |

A few clear recordings from one fluent speaker are more useful than many
uncertain ones. Disagreement between speakers is itself worth recording.

## Consent, credit, and licensing (agreed *before* any data is collected)

- **Informed consent.** Every contributor is told exactly what the recording is
  for (measuring and improving TTS pronunciation of names), where it will live,
  and that it may be redistributed as part of an open dataset. No recording is
  used without that explicit, documented consent.
- **Credit by default.** Contributors are acknowledged by name (or a chosen
  handle) unless they ask to remain anonymous.
- **Right to withdraw.** A contributor can ask to have their recordings removed
  at any time, and they will be removed from the distributed dataset.
- **Licensing.** Contributed audio and reference transcriptions would be released
  under **CC-BY-4.0** (attribution) — separate from the repository's MIT code
  license — so the data is openly reusable while the speaker is always credited.
- **Minors / sensitive cases.** Only adults who can give their own consent;
  no recordings of children, and no private individuals targeted or profiled.

## Ethics process

Native-speaker pronunciations are **human-subjects data**. Before any collection
begins, this will go through the appropriate **IRB / ethics review** (e.g. via a
university affiliation), with the consent language and data-handling plan above
reviewed and approved. Until then, this document is a commitment to doing it
right, not an invitation to send data.

## How to express interest now

1. [Open an issue](../../issues/new) and say which language(s) you speak and,
   if you like, which regional pronunciation.
2. That's it — no files yet. When the consent/ethics process is ready, everyone
   who expressed interest will be contacted with the proper consent form and a
   simple way to contribute.

Thank you for helping make speech systems say people's names right.
