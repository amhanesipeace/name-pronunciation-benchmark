# Datasheet — name-pronunciation fairness dataset

Following *Datasheets for Datasets* (Gebru et al., 2021,
[arXiv:1803.09010](https://arxiv.org/abs/1803.09010)). This documents the name
lists in `data/names.csv` (80, frozen) and `data/names_extended.csv` (120). It
complements the provenance notes in [`SOURCES.md`](SOURCES.md) and the ethics and
limitations sections of [`../PAPER.md`](../PAPER.md).

---

## Motivation

**For what purpose was the dataset created?**
To benchmark fairness in text-to-speech (TTS) pronunciation: it provides parallel
sets of common given names across English and three African languages (Yoruba,
Igbo, Hausa) so a system's pronunciation competence can be compared across groups
on equal footing. It exists because no small, ready-made, openly licensed set for
this comparison was available.

**Who created it and for whom?**
Compiled by Peace Amhanesi as an independent research project. It is a research
and educational resource, released openly.

**Who funded it?** No external funding; a self-directed project.

## Composition

**What do the instances represent?**
Each instance is a **given name** (a text string), not a person. Fields:
`id`, `name`, `language`, `origin`, `ipa`.

**How many instances are there?**
- `names.csv`: **80** — 20 each for English, Yoruba, Igbo, Hausa. This is the
  **frozen** studied set; all published results reproduce on it.
- `names_extended.csv`: **120** — 30 per language, for larger future runs.

**Is it a sample or a complete set?**
A small, deliberately ordinary **sample** of frequently occurring given names per
language — explicitly **not** an exhaustive or authoritative corpus.

**What data does each instance consist of?**
Processed text: the name in Latin script, a language label, an origin note, and
(for English rows only) a reference IPA pronunciation.

**Is any information missing?**
Yes, by design and as a known limitation:
- The `ipa` column is **blank for all African-language rows** — an English
  grapheme-to-phoneme tool would encode the *anglicised* pronunciation and defeat
  the dataset's purpose; correct references require native speakers.
- Names are stored in **ASCII without tone marks / diacritics** (e.g. Yorùbá
  tone), which carry meaning in these languages.

**Are there labels?** `language` and `origin`, assigned by the compiler. English
`ipa` labels come from espeak-ng's English G2P (reproducible and correct for
English).

**Does the dataset contain data that might be offensive, or identify
individuals?**
No. Instances are **common given names**, not records about specific people, and
contain no personal, sensitive, or contact information. Names are not those of
specific private individuals.

**Known quality caveat:** the lists are **not yet validated by native speakers**
and lack per-name source citations. Treat them as a reasonable working sample,
not ground truth (see `SOURCES.md`, "Provenance status").

## Collection process

**How were the names collected?**
Compiled from general knowledge and widely available public name references
(e.g. community name sites, encyclopaedic name lists). No human subjects were
involved and no personal data was gathered; the names are generic given names.

**Over what time frame?** Assembled in 2025–2026 during development of the
benchmark.

**Were ethical review processes conducted?**
Not required at this stage, as no human-subjects data was collected. The planned
next step — native-speaker pronunciation references — *would* be human-subjects
data and should be collected under informed consent and, where applicable, IRB
review (see `PAPER.md`, "Ethical considerations").

## Preprocessing / cleaning / labeling

Names were recorded in Latin script and grouped by language. English reference
pronunciations were generated with espeak-ng's English G2P. No other
transformation was applied; raw lists are the CSV files themselves. African IPA
references were intentionally left empty rather than machine-filled.

## Uses

**What is the dataset intended for?**
Measuring and studying pronunciation disparities in TTS/ASR pipelines; teaching
fairness evaluation methodology.

**What should it *not* be used for?**
- Identifying, profiling, or targeting individuals or communities.
- As an authoritative linguistic corpus or a canonical list of "correct" names.
- Drawing universal claims: results establish gaps for the **specific systems
  tested**, not all speech systems.

**What (if anything) should users know to avoid harms?**
Native-speaker validation and documented sourcing are required before any
publication built on these lists; the missing tone marks and blank African IPA
must be addressed with native speakers rather than automated tools.

## Distribution

Distributed publicly on GitHub as part of the benchmark repository under the
project's MIT license, with a `CITATION.cff` for attribution. No third-party IP
or usage restrictions beyond the license apply.

## Maintenance

**Who maintains it?** Peace Amhanesi, via the GitHub repository (issues/PRs
welcome).

**Will it be updated?**
- `names.csv` is kept **frozen** so published results remain reproducible.
- `names_extended.csv` and the `ipa` column may grow — in particular, adding
  native-speaker-validated names, diacritics, and African reference
  pronunciations — with changes recorded in version control.

**How can others contribute or flag issues?**
Through GitHub issues and pull requests; native-speaker corrections to spellings,
tone marks, and pronunciations are especially valued.
