# Adding hymns from Tasbeha.org

The text (Coptic, transliteration, English, Arabic) comes from Tasbeha's hymn library. The Coptic recording can come from Tasbeha, YouTube or a file; an English recording usually comes from a Tasbeha album page.

## 1. Look at the hymn

```
python3 tools/add_hymn.py https://tasbeha.org/hymn_library/view/106 --list
```

Shows the titles, how many verses, the first lines, and the recordings Tasbeha lists for it, each with an id such as `mid:10791`.

## 2. Add it

```
python3 tools/add_hymn.py https://tasbeha.org/hymn_library/view/106 \
    --id second-hoos --place praises/midnight --order 60 --kind recital \
    --coptic mid:10791 \
    --english "https://tasbeha.org/mp3/Praises/Midnight_Praises_(Sunday)/St_Anthony_Monastery,_English_Midnight_Praises/Part_1.html#6"
```

- `--id`: the folder name (lowercase, dashes). The hymn goes in `content/hymns/<id>/`, the English recording in `content/english/<id>-english/`.
- `--place` / `--order`: where it appears in the app (see the list of places in `open-items.md`). For Midnight Praises, use Tasbeha's position × 10 (table below).
- `--coptic` / `--english`: any of
  - `mid:ID` — a recording from the hymn's own page (from `--list`)
  - an album page with the track number after `#` (leave it off to see the track list)
  - a YouTube link (downloaded with yt-dlp; if YouTube refuses with "403", run `brew upgrade yt-dlp`)
  - a Tasbeha download link, a direct audio link, or a file on the Mac

Lines start untimed.

## 3. Publish, then time it

1. `python3 tools/build_catalog.py`, commit and push (the app streams the audio from copticchanter.com).
2. In the app repo: `scripts/sync-catalog.sh`, then Run in Xcode.
3. On the iPad: open the hymn, pick Coptic or English above the play bar, tap the pencil and mark the words.
4. Export to Downloads, then `python3 tools/import_timing.py ~/Downloads/<file>.timing.json` (partly marked lines are fine: skipped words are estimated) (or ask Claude), rebuild, commit, push.

If the English singers use different words from Tasbeha's translation, correct the line's English (or add `"sung": {"english": "…"}`) before timing it.

For St. Antony Monastery recordings, Tasbeha has the sung English (https://tasbeha.org/hymn_library/cat/219). Add it before timing:

```
python3 tools/add_sung_english.py <id> https://tasbeha.org/hymn_library/view/<St. Antony page> [--dry-run --show]
```

So far: Ten Theeno 1234, First Hoos 1237, Second Hoos 1239, Third Hoos 1241, Aripsalin 1242, Fourth Hoos 1244 (next: First Hoos Lobsh 1238, Second Hoos Lobsh 1240, We follow You 1243, Commemoration 1286, Psalis 1245–1246, Theotokia 1247–1259, Litany 1260).

## Midnight Praises (Sunday), in order

From https://tasbeha.org/hymn_library/cat/216. ✓ = in the app.

| Order | Hymn | Tasbeha | |
|---|---|---|---|
| 10 | The Hymn of Ten-theno | view/92 | ✓ `ten-theeno` (YouTube, The Coptic Gate), with English (Part 1 #2). The one-verse Mahragan version stays as `ten-thinou` |
| 20 | The Hymn of the Resurrection – Tennav | view/104 | ✓ `tennav`, Ibrahim Ayad, with English |
| 30 | The Year Round Canticle | view/2539 | no recordings listed |
| 40 | The First Hoos | view/103 | ✓ `first-hoos`, with English |
| 50 | The First Hoos Lobsh | view/105 | ✓ `first-hoos-lobsh`, Ibrahim Ayad, with English |
| 60 | The Second Hoos | view/106 | ✓ `second-hoos` (YouTube, The Coptic Gate), with English |
| 70 | The Second Hoos Lobsh | view/182 | ✓ `second-hoos-lobsh`, Ibrahim Ayad, with English |
| 80 | The Third Hoos | view/108 | ✓ `third-hoos` (YouTube, The Coptic Gate), with English |
| 90 | The Third Hoos – Esmo Epchois | view/453 | ✓ `esmo-epchois`, Ibrahim Ayad |
| 100 | Psali Watos for the Three Saintly Children (Greek) — Aripsalin | view/109 | ✓ `aripalin` (Mahragan), with English (Part 1 #9) |
| 110 | Watos Hymn – Ten-oweh Ensok | view/110 | ✓ `tenoue-n-khok` (Mahragan), with English |
| 120 | The Commemoration of the Saints | view/111 | ✓ `commemoration-of-saints`, Ibrahim Ayad, with English |
| 130 | Doxology for Virgin Mary – Midnight Praise | view/25 | ✓ `doxology-virgin-midnight`, Ibrahim Ayad |
| 140 | The Fourth Hoos | view/127 | ✓ `fourth-hoos` (YouTube, The Coptic Gate), with English (Part 2 #1) |
| 150 | The First Sunday Psali | view/112 | ✓ `first-sunday-psali`, Ibrahim Ayad, with English (Part 2 #2) |
| 160 | The Second Sunday Psali | view/174 | ✓ `second-sunday-psali`, Ibrahim Ayad, with English (Part 2 #3) |
| 170 | Intro of the Theotokia (Leebon) | view/465 | ✓ `leebon`, Ibrahim Ayad |
| 180 | The Sunday Theotokia | view/476 | |
| 190 | Gospel According to St. Luke | view/138 | ✓ `gospel-luke`, Ibrahim Ayad, with English |
| 200 | The Seventh Part – Shere ne Maria | view/139 | ✓ `shere-ne-maria`, Ibrahim Ayad (English is split over Part 2 #11–12) |
| 210 | The Seventh Part – Semoti | view/452 | ✓ `semoti`, Ibrahim Ayad, with English |
| 220 | The Eighth Part – Shashf Ensop | view/140 | ✓ `shashf-ensop`, Ibrahim Ayad, with English |
| 230 | The Tenth Part – Teoi Enhekanos | view/479 | ✓ `teoi-enhekanos`, Ibrahim Ayad, with English |
| 240 | Evol Hetin – Long | view/2170 | no recordings listed |
| 250 | The Fifteenth Part – Aven Pi-arshee-erevs | view/480 | ✓ `aven-pi-arshee-erevs`, Ibrahim Ayad |
| 260 | The Sixteenth Part – Nim Ghar | view/481 | ✓ `nim-ghar`, Ibrahim Ayad, with English |
| 270 | Intro of the Difnar – Adam | view/661 | |
| 280 | The Adam Theotokias Conclusion | view/477 | ✓ `adam-theotokias-conclusion`, Ibrahim Ayad, with English |
| 290 | The Concluding Litany | view/147 | ✓ `concluding-litany`, Ibrahim Ayad, with English |
| 300 | The Morning Doxology | view/485 | ✓ `morning-doxology`, placed in **Morning Praises** (Bola Mounir, YouTube), with English |

The St. Anthony Monastery English album continues on Part 2, Part 3… pages of the same album for the later hymns.

Hymns already in the app under Mahragan (such as Ten Theeno or Tenoueh Ensok) only need `places` and `order` added to their `info.json`; adding them again would duplicate them.
