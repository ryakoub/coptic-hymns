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
4. Export to Downloads, then `python3 tools/import_timing.py --fill-gaps ~/Downloads/<file>.timing.json` (or ask Claude), rebuild, commit, push.

If the English singers use different words from Tasbeha's translation, correct the line's English (or add `"sung": {"english": "…"}`) before timing it.

## Midnight Praises (Sunday), in order

From https://tasbeha.org/hymn_library/cat/216. ✓ = in the app.

| Order | Hymn | Tasbeha | |
|---|---|---|---|
| 10 | The Hymn of Ten-theno | view/92 | ✓ `ten-theeno` (YouTube, The Coptic Gate); English: Part 1 #2. The one-verse Mahragan version stays as `ten-thinou` |
| 20 | The Hymn of the Resurrection – Tennav | view/104 | |
| 30 | The Year Round Canticle | view/2539 | no recordings listed |
| 40 | The First Hoos | view/103 | ✓ `first-hoos`, with English |
| 50 | The First Hoos Lobsh | view/105 | English: Part 1 #5 |
| 60 | The Second Hoos | view/106 | ✓ `second-hoos` (YouTube, The Coptic Gate), with English |
| 70 | The Second Hoos Lobsh | view/182 | English: Part 1 #7 |
| 80 | The Third Hoos | view/108 | ✓ `third-hoos` (YouTube, The Coptic Gate), with English |
| 85 | Aripsalin (Third Hoos Lobsh) | — | ✓ `aripalin`, with English (Part 1 #9) |
| 90 | The Third Hoos – Esmo Epchois | view/453 | |
| 100 | Psali Watos for the Three Saintly Children (Greek) | view/109 | |
| 110 | Watos Hymn – Ten-oweh Ensok | view/110 | in the app as `tenoue-n-khok` (Mahragan); English: Part 1 #10 |
| 120 | The Commemoration of the Saints | view/111 | English: Part 1 #11 |
| 130 | Doxology for Virgin Mary – Midnight Praise | view/25 | |
| 140 | The Fourth Hoos | view/127 | ✓ `fourth-hoos` (YouTube, The Coptic Gate), with English (Part 2 #1) |
| 150 | The First Sunday Psali | view/112 | |
| 160 | The Second Sunday Psali | view/174 | |
| 170 | Intro of the Theotokia (Leebon) | view/465 | |
| 180 | The Sunday Theotokia | view/476 | |
| 190 | Gospel According to St. Luke | view/138 | |
| 200 | The Seventh Part – Shere ne Maria | view/139 | |
| 210 | The Seventh Part – Semoti | view/452 | |
| 220 | The Eighth Part – Shashf Ensop | view/140 | |
| 230 | The Tenth Part – Teoi Enhekanos | view/479 | |
| 240 | Evol Hetin – Long | view/2170 | no recordings listed |
| 250 | The Fifteenth Part – Aven Pi-arshee-erevs | view/480 | |
| 260 | The Sixteenth Part – Nim Ghar | view/481 | |
| 270 | Intro of the Difnar – Adam | view/661 | |
| 280 | The Adam Theotokias Conclusion | view/477 | |
| 290 | The Concluding Litany | view/147 | |
| 300 | The Morning Doxology | view/2716 | no recordings listed |

The St. Anthony Monastery English album continues on Part 2, Part 3… pages of the same album for the later hymns.

Hymns already in the app under Mahragan (such as Ten Theeno or Tenoueh Ensok) only need `places` and `order` added to their `info.json`; adding them again would duplicate them.
