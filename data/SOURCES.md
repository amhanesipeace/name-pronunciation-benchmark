# Dataset provenance & sources

Two name lists are provided:

| file | size | role |
|------|------|------|
| `names.csv` | 80 (20 / language) | the **frozen studied set** — all published results reproduce on this |
| `names_extended.csv` | 120 (30 / language) | a **larger set for future runs** (`--names data/names_extended.csv`) |

Languages: English, Yoruba, Igbo, Hausa.

## How the names were compiled

The names are **common given names** for each language, compiled from general
knowledge and widely available name references. They are deliberately ordinary,
frequently occurring names — not the names of specific private individuals.

## ⚠️ Provenance status — read this before citing

These lists are **not yet validated by native speakers**, and specific
per-name citations are not attached. Treat them as a reasonable working sample,
**not** an authoritative corpus. Before any publication:

1. **Validate names and spellings** (including diacritics/tone marks, which this
   ASCII list omits — e.g. Yorùbá tone) with **native speakers**.
2. **Draw from documented sources** and cite them, e.g.:
   - published national/linguistic name compilations and censuses;
   - curated references such as *Behind the Name* (behindthename.com) and
     Wikipedia's lists of Yoruba / Igbo / Hausa names;
   - community-sourced pronunciation guides (e.g. Forvo) for audio references.
3. **Add reference pronunciations** to the `ipa` column. English references are
   provided (espeak-en G2P, which is correct for English); African references
   require native-speaker IPA or recordings (see `PAPER.md` §Limitations).

## The `ipa` column

- **English rows:** filled with espeak-ng's English G2P — reproducible and
  correct for English names.
- **African rows:** intentionally left blank. Using an English G2P here would
  encode the *anglicised* pronunciation, defeating the purpose; these must come
  from native speakers.

## Ethics

Names refer to people. Use common given names or documented lists; never target
or profile private individuals. Native-speaker pronunciation data is
human-subjects data — collect it with informed consent and credit. See
`PAPER.md` §Ethical considerations.
