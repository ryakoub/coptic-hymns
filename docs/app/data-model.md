# Coptic Chanter app: data model

Phase 0, October 2026. How hymns, tunes, the library and user data are stored, for both copticchanter.com and the iPhone/iPad app.

## Principles

1. **Words are written once.** The same text is often sung to several tunes, such as the Doxology of St. Mary in the Annual tune and the Lent tune. The words live in one place; each tune is a separate recording that points to them.
2. **Timings belong to a recording.** The same word lands at a different moment in each tune, so line and word timings are stored with the recording, never with the text.
3. **The website keeps working.** Today's `content/` folders and `lyrics.json` files stay valid. The catalog builder derives the three layers from them, and new fields are optional.
4. **Public and private never mix.** Public content comes from copticchanter.com. Private content (your PDFs, hand-made notation, your own recordings) lives only on your devices and in your own iCloud. It is never uploaded, never listed in the catalog, and never included in anything shared.
5. **Ready for Arabic.** Every piece of display text has slots for Coptic, English and Arabic. Empty slots are fine.

## The three layers

| Layer | Holds | Example |
|---|---|---|
| **Text** | The words, line by line: Coptic, translations, transliterations | Doxology of St. Mary |
| **Recording** | One tune of a text: audio, tune name, the lines it sings in order, line and word timings | Doxology of St. Mary, Lent tune |
| **Library** | Where hymns appear: seasons, services, occasions, programs. Each entry names a recording, and through it a text. | Great Lent → Raising of Incense → Doxology of St. Mary (Lent tune) |

### Text

```json
{
  "id": "aripalin",
  "titles": { "coptic": "Ⲁⲣⲓⲯⲁⲗⲓⲛ", "english": "…", "arabic": "…" },
  "lines": [
    {
      "id": "l1",
      "coptic": "Ⲁ̀ⲣⲓⲯⲁⲗⲓⲛ ⲉ̀ⲫⲏⲉ̀ⲧⲁⲩⲁϣϥ: …",
      "translations": { "english": "O sing unto Him who was crucified …", "arabic": "…" },
      "transliterations": { "arabic": "…", "english": "…" },
      "role": "people",
      "stanzas": [ { "coptic": "Ⲁ̀ⲣⲓⲯⲁⲗⲓⲛ ⲉ̀ⲫⲏⲉ̀ⲧⲁⲩⲁϣϥ:" } ]
    }
  ]
}
```

- Line ids (`l1`, `l2`, …) are stable. Recordings refer to lines by id.
- `translations` and `transliterations` hold `english` and `arabic`. `transliterations.arabic` is the Coptic written in Arabic letters, as printed in most Coptic books.
- `role` (optional) says who sings the line: `priest`, `deacon`, `people`, `north`, `south`.
- `label` lines are headings that are not sung, such as "General Funeral". A label may be a string or `{ "english": "…", "arabic": "…" }`. `static` lines are shown without timing.

### Recording

```json
{
  "recording": "aripalin-lent",
  "text": "aripalin",
  "segments": [
    { "line": "l1", "start": 8.61, "stanzas": [8.73, 13.58], "words": [ { "text": "Ⲁ̀ⲣⲓⲯⲁⲗⲓⲛ", "start": 8.73, "end": 10.1 } ] },
    { "line": "l2", "start": 31.2 },
    { "line": "l1", "start": 52.0 }
  ]
}
```

- `segments` lists what is sung, in order. A line may appear twice (a repeated verse) or not at all (a tune that skips it).
- Times are seconds from the start of the recording's audio.
- The catalog entry for a recording adds its duration, cantor and YouTube link, and names its tune. Tunes are named both ways people speak of them, so each recording may carry any of:
  - `style`: `major`, `medium`, `minor`
  - `mode`: `annual`, `festal`, `lenten`, `joyful` (more as needed)
  - `kind`: `recital`, `melismatic`
  - `tune`: a free name in each language, `{ "english": "…", "arabic": "…" }`, used when the facets don't say it well

  The app shows `tune` when present, otherwise the facets joined, such as "Festal · Major" or "Lenten · Melismatic".

### Library

Hand-edited in `catalog/library.json`. Five groups, each a list of collections; each collection has ordered sections, and each section lists entries.

| Group | Collections | Sections |
|---|---|---|
| Seasons | Annual, Nayrouz, Kiahk, Nativity, Theophany, Great Lent, Palm Sunday, Resurrection, Ascension, Pentecost, Apostles' Fast | The services: Midnight Praises, Raising of Incense, Liturgy, Special hymns. Annual has no Midnight Praises; the regular praises are their own group. |
| Feasts | Feast of the Cross, Circumcision, Wedding at Cana, Presentation of the Lord, Lazarus Saturday | The four services |
| Fasts | Jonah's Fast | The four services |
| Praises | Praises (Psalmody) | Vesper Praises, Midnight Praises, Morning Praises |
| Special seasons | Holy Week, Bright Saturday | Their own order: Holy Week by day |
| Common hymns | Common hymns | The four services |
| Occasions | Veneration (more to come) | Hymns |
| Programs | Mahragan Al-Keraza 2026 | Grade and level |

An entry is a recording id, or `{ "text": "…", "recording": "…" }` to make the intended text explicit:

```json
{ "service": "raising-of-incense", "entries": [ { "text": "doxology-st-mary", "recording": "doxology-st-mary-lent" } ] }
```

**Season dates.** Each season stores a date rule so a "Today" view can open the current season later. Rules are counted from the Resurrection (`{"easter": -55}` is 55 days before it) or given as a Coptic date (`{"coptic": [4, 29]}` is 29 Kiahk). `null` means the default season (Annual). The rules in `library.json` are drafts to review.

## How today's folders map to the layers

Each folder under `content/` is one recording. By default it also holds its own text (the words inside its `lyrics.json`), with the folder name as both ids.

To make a folder another tune of an existing text, add to its `info.json`:

```json
{ "text": "doxology-st-mary", "tune": { "english": "Lent tune" } }
```

The builder then matches each of its lines to the text's lines by their Coptic, and reports any line that does not match.

`info.json` also accepts `titles` (`coptic`, `english`, `arabic`), `tags`, `kind` (`recital` or `melismatic`), `style`, `mode`, `cantor` and `lyricsSource`. The legacy `title` stays for the website.

A folder can place itself in the library with `"places": ["resurrection/liturgy"]` (collection id / section, as in `catalog/library.json`). Hymns listed by hand in `library.json` keep their order there; hymns placed from `info.json` follow them. The builder reports places that don't exist.

Later, when the website reads the catalog, texts can move to their own files and `lyrics.json` can be generated from text plus timings, so lyrics are edited in exactly one place.

## Catalog

`python3 tools/build_catalog.py` reads `content/` and `catalog/library.json` and writes:

| File | Contents |
|---|---|
| `catalog/v1/index.json` | Services, the library, every text and recording with sizes and fingerprints |
| `catalog/v1/texts/<text>.json` | The words of one text |
| `catalog/v1/timings/<recording>.json` | The segments of one recording |

- `version` changes only when content changes, so the app can check for updates cheaply.
- Every file is listed with `url` (relative to `baseUrl`), `bytes` and `sha256`, so the app can show sizes and download only what changed.
- Texts report which translations and transliterations they have; recordings report how many lines and words are timed. The app can show this before downloading anything.
- The builder reports problems: lines out of order, lines that are not in their text, missing audio, library entries that point nowhere, and recordings not yet in the library. `--check` reports without writing.

## On the device

| Data | Where | Synced |
|---|---|---|
| Downloaded public texts, timings and audio | App storage, re-downloadable | No |
| Favorites, recently played, settings, chosen tune per hymn | App database | Your iCloud (later phase) |
| Timing edits made with the Pencil | App database, as drafts per recording | Your iCloud; exportable for the website |
| Your own hymns and recordings | App storage | Your iCloud |
| Private attachments: PDF slides, hand-made notation dots, score maps | App storage | Your iCloud only |

### Rules for private content

- Never written to the catalog or to copticchanter.com.
- Never included in exports meant for others. A timing export contains times and line ids, never PDFs or audio you added.
- A shared copy of a hymn may include its public files and your timing edits, but not its private attachments.

## Planned: recordings sung in English or Arabic

Not built yet. Praises and doxologies are often sung in Coptic, English and Arabic, each with its own audio. The model leaves room for this:

- A recording would add `"language": "coptic" | "english" | "arabic"` (Coptic when missing, as today). Its word timings would follow the words of that language.
- Text lines would add `sung` slots (`"sung": { "english": "…", "arabic": "…" }`) for the singable version, which often differs from the literal `translations`.
- Recordings in every language keep pointing at the same line ids, so line-by-line sync carries across languages; word timings stay per recording.
- The hymn screen would offer a language picker beside the tune picker, showing only languages that have recordings.

Until then, keep line ids stable and keep timings per recording, so this can be added without changing existing files.

## Open items

1. English titles for the 17 hymns that have only a Coptic title.
2. Review of season and service names, and the Arabic names in `catalog/library.json`.
3. Known tune pairs among the existing hymns, to link with `"text"` in `info.json`.
4. The season and service for each Mahragan 2026 hymn.
5. Lyrics for `conclusion-canon-resurrection`, `ke-ypertou` and `verses-cymbals-resurrection`, which have audio but no words yet.

Fonts: the app ships ArialCoptic (traditional, the default) and Noto Sans Coptic (modern), matching the website's font setting. Church fonts, audio and icon artwork are cleared for this non-profit app.
