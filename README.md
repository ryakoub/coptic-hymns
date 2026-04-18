# Tools

Some helpers tools to import lyrics and attempt syncing with audio.

## Import Lyrics From Tasbeha.org

Use `tools/import_tasbeha_lyrics.py` to pull English and Coptic lyrics from a Tasbeha.org hymn page and write them into a hymn folder's `lyrics.json`.

Import lyrics only:

```bash
python3 tools/import_tasbeha_lyrics.py "https://tasbeha.org/hymn_library/view/23" "content/mahragan-keraza-2026/grades-5-6/level-1/doxology-st-mary-matins"
```

Keep leading `+` markers from Tasbeha:

```bash
python3 tools/import_tasbeha_lyrics.py "URL" "TARGET_FOLDER" --keep-plus
```

## Auto-Generate Timings

You can optionally attach timings while importing by passing the hymn audio file.

### Recommended workflow:

1. Run a first import + auto sync pass.
2. Listen and collect accurate verse start timestamps.
3. Save them in `TARGET_FOLDER/timing-anchors.json`.
4. Re-run with `--anchors` to lock verse starts.
5. Optionally switch to word sync (and melisma options) after verse starts are locked.

Available timing modes:

- `verse`: sets a `start` time for each lyric line
- `word`: adds a `words` array split by coptic word
- `auto`: chooses verse or word based on hymn style and text density

Import lyrics and detect verse timings:

```bash
python3 tools/import_tasbeha_lyrics.py "URL" "TARGET_FOLDER" --sync-audio "TARGET_FOLDER/audio.mp3" --sync-style verse
```

Import lyrics and detect word timings:

```bash
python3 tools/import_tasbeha_lyrics.py "URL" "TARGET_FOLDER" --sync-audio "TARGET_FOLDER/audio.mp3" --sync-style word
```

Import lyrics and sync with auto style hints:

```bash
python3 tools/import_tasbeha_lyrics.py "URL" "TARGET_FOLDER" --sync-audio "TARGET_FOLDER/audio.mp3" --sync-style auto --hymn-style melismatic
```

Use known verse starts (anchors) for stronger accuracy:

```bash
python3 tools/import_tasbeha_lyrics.py "URL" "TARGET_FOLDER" --sync-audio "TARGET_FOLDER/audio.mp3" --sync-style verse --anchors "TARGET_FOLDER/timing-anchors.json"
```

One-command wrapper (import and sync):

```bash
python3 tools/import_and_sync_tasbeha.py "URL" "TARGET_FOLDER" "TARGET_FOLDER/audio.mp3" --split auto --hymn-style melismatic
```

Melisma-aware word timing (opt-in, does not change default behavior):

```bash
python3 tools/import_and_sync_tasbeha.py "URL" "TARGET_FOLDER" "TARGET_FOLDER/audio.mp3" --split word --hymn-style melismatic --anchors "TARGET_FOLDER/timing-anchors.json" --melisma-auto
```

Use manual melisma hints to boost specific words:

```bash
python3 tools/import_and_sync_tasbeha.py "URL" "TARGET_FOLDER" "TARGET_FOLDER/audio.mp3" --split word --hymn-style melismatic --anchors "TARGET_FOLDER/timing-anchors.json" --melisma-auto --melisma-hints "TARGET_FOLDER/melisma-hints.json"
```

You can start from `melisma-hints.template.json`, save it as `melisma-hints.json`, then tune word boosts by line.

The new sync path uses `ffmpeg` + `ffprobe` and does not depend on `detect_pauses.py`.

Manual word-start application (reliable workflow):

Create a plain text file in this format:

```text
line 1: 4.28, 6.74, 17.68
line 2: 42.66, 44.69, 46.24
```

Then apply it to `lyrics.json` (and optionally update anchors):

```bash
python3 tools/apply_manual_word_starts.py "TARGET_FOLDER/lyrics.json" "TARGET_FOLDER/manual-word-starts.txt" --anchors "TARGET_FOLDER/timing-anchors.json" --audio "TARGET_FOLDER/audio.mp3"
```

This sets each word `start` to your provided values, sets each word `end` to the next word start, and aligns final word ends to the next verse boundary (or audio end for the last line).

### Player Sync Debug (Phone Testing)

When testing sync issues on phone, use this checklist.

1. Start local server in project root:

```bash
python3 -m http.server 8000
```

2. Find Mac LAN IP:

```bash
ipconfig getifaddr en0 || ipconfig getifaddr en1
```

3. Open on phone (same Wi-Fi):

```text
http://<LAN_IP>:8000/player.html?group=grades-3-4&level=level-1&hymn=pi-pnevma&syncDebug=1
```

Optional tuning flags:

- `syncDebug=1`: show seek telemetry overlay
- `seekDebounceMs=140`: ignore very fast repeated tap bursts
- `syncOffsetMs=0`: optional highlight delay override (default is `0`)
- Example:

```text
http://<LAN_IP>:8000/player.html?group=grades-3-4&level=level-1&hymn=pi-pnevma&syncDebug=1&seekDebounceMs=180&syncOffsetMs=250
```

If `target` and `current` look equal but heard audio is still behind on a specific device/browser, test `syncOffsetMs` in small steps (e.g. `80`, `120`).

## Seek-Friendly Audio Files

For better random-seek accuracy on browsers, player prefers `audio.seek.m4a` when present and falls back to `audio.mp3` automatically.

Companion file naming:

- `audio.mp3` (existing source)
- `audio.seek.m4a` (preferred for playback when available)

Create one companion file:

```bash
ffmpeg -y -i "TARGET_FOLDER/audio.mp3" -c:a aac -b:a 128k "TARGET_FOLDER/audio.seek.m4a"
```

Recommended stress test pattern:

1. Tap first word (or first verse)
2. Tap last word (or last verse)
3. Repeat 10-20 times quickly
4. Record overlay values for `target`, `landed`, `drift`, and `delta`

If testing does not reflect latest code, close and reopen the phone tab after each `player.js` version bump in `player.html`.

# Hymns

These are the hymns with added lyrics (some level of audio-lyric sync)

## KG

### Level-1

- [x] Concluding Canon for Feast of the Cross
- [x] Sotees Ameen (Fast)
- [x] Psalm Response, Resurrection

### Level-2

- [x] Ere Po Esmo (May Their Holy Blessing)
- [x] Liturgy Gospel Response, Annual
- [x] Hiten for Archangel Michael, Feast of Resurrection

## GRADES-1-2

### Level-1

- [x] Procession Refrain, Feast of the Cross
- [x] This Is the Day
- [x] Blessed, Pentecost

### Level-2

- [x] The Thought of Man
- [x] St. Mark Doxology (First One)
- [x] Liturgy Gospel Response, Resurrection

## GRADES-3-4

### Level-1

- [x] Gospel Response of the Feast of the Cross
- [x] The Golden Censer
- [x] Ⲡⲓⲡ̀ⲛⲉⲩⲙⲁ
- [x] ⲧⲟⲛ ⲥⲩⲛⲁ
- [x] Doxology of St. Mary Vespers

### Level-2

- [x] The Second Doxology of the Apostles
- [x] Psalm 150, 4th Hoos
- [x] Paralex of Resurrection
- [x] Distribution Refrain for Resurrection

## GRADES-5-6

### Level-1

- [x] Verse of Cymbals for Feast of the Cross
- [x] Doxology of St. Mary, Matins
- [x] Praxis Response, Annual
- [x] Doxology of Resurrection
- [x] Conclusion of Midnight Praises

### Level-2

- [x] Doxology of Heavenly Orders
- [x] Anaphora Responses of St. Basil and St. Gregory Liturgies
- [x] Verse of Cymbals for Resurrection
- [x] Praxis Response for Resurrection

## MS

### Level-1

- [x] Refrain of Third Hour, Pentecost
- [x] Praxis Response, Feast of the Cross
- [x] The Hymn of the Blessing
- [x] Lobsh of First Hoos
- [x] Christ Is Risen

### Level-2

- [x] Paralex, Shere Ne Maria
- [x] Ⲁⲣⲓⲯⲁⲗⲓⲛ
- [x] Aspasmos Adam, Resurrection

## HS

### Level-1

- [x] Ⲡⲓⲱⲓⲕ
- [x] First Hoos
- [x] Second Doxology of Resurrection
- [x] Ⲡⲓⲭⲣⲓⲥⲧⲟⲥ Ⲁϥⲧⲟⲛϥ
- [x] Ⲧⲟⲩ Ⲗⲓⲑⲟⲩ

### Level-2

- [x] Ⲧⲉⲛⲟⲩⲉϩ Ⲛ̀ⲥⲱⲕ
- [x] Ⲕⲁⲧⲁ Ⲛⲓⲭⲟⲣⲟⲥ
- [x] Joyful Ⲁⲅⲓⲟⲥ, Major

## COLLEGE & UP

### Level-1

- [x] Ⲁⲣⲓϩⲟⲩⲟ Ϭⲁⲥϥ from 3rd Hoos
- [x] Hossana Intro to Doxologies & 1st Doxology
- [x] ⲭ̀ⲣⲓⲥⲧⲟⲥ ⲁ̀ⲛⲁⲗⲩⲙⲯⲓⲥ
- [ ] Ⲉⲑⲃⲉ Ϯⲁⲛⲁⲥⲧⲁⲥⲓⲥ

### Level-2

- [X] Ⲱ̀ⲛⲓⲙ Ⲛⲁⲓ Ⲥⲩⲙⲫⲱⲛⲓⲁ
- [x] Ⲧⲉⲛ Ⲑⲏⲛⲟⲩ
- [X] Ⲫⲁⲓ Ⲉⲧⲁϥⲉⲛϥ
- [ ] Ⲟⲩⲕⲁⲧⲏⲭⲏⲥⲓⲥ
