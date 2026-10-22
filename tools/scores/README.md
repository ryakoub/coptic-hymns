# Syncing a MuseScore score with a recording

From a score's source file (MuseScore `.mscz`/`.mscx`, or MusicXML opened in MuseScore and saved), make its PDF with a line of transliteration under the Coptic, and draft marks for a recording: when each note is sung. Check the marks by ear in Mark Sync, fix the few that are off, and they become a hymn with notation in the app.

Tried on Pi Gen Misi (your own MuseScore score) with the Mahragan 2023 recording, October 2026: the automatic marks were close for most bars; 6 were fixed by ear, and smoothing by the score's rhythm made the cursor steady.

## A recording sung part by part

When the cantor sings some verses to the tune and others the fast way (as in services, for time), give the second each part starts and line them up part by part:
```
tools/scores/.venv/bin/python tools/scores/sync_verses.py <work folder> "<recording>" <work folder>/marks.taps.json --times 6.5 9 77 147 163 178 --fast 4 5
```
The parts are found from the score's words ("Kyrie eleison", then each verse). Parts sung to the tune get a mark on every note, found by following the cantor's voice (its pitch) against the written notes, in whatever key and octave he sings; parts sung fast get a mark on each syllable. Then `package.py` (step 7 below) with `--name`: the backup sets the score's small cursor and gliding to the end of each line. Give the app M4A: `ffmpeg -i in.ogg -c:a aac_at -b:a 128k out.m4a` (the app's player misreads the length of Ogg recordings).

Then a steady beat is fitted through each part sung to the tune, like a conductor's: the tempo may change from bar to bar, but within a bar the notes follow the written rhythm, so the cursor moves at an even pace (`--exact` keeps each note where the voice matching puts it instead).

Tried on the first of the Seven Tunes sung by Cantor Bola (October 2026): verses 1 and 2 to the tune, 3 and 4 fast. Note by note, 70% of the notes fall where he sings their exact pitch and 98% within a semitone (matching the score's sound, as align.py does, gave 49% and 85%), but the speed jumped from note to note; with the steady beat, speed jumps went from 42% of the notes to 1%, with 59% on the exact pitch and 92% within a semitone.

## Once

- MuseScore 4 in /Applications.
- The audio libraries, in a folder of their own (not in git):
  ```
  python3 -m venv tools/scores/.venv
  tools/scores/.venv/bin/pip install -r tools/scores/requirements.txt
  ```

## From a MIDI file and the PDF of the same score

Fr. Abraam's MIDI files have the notes but no words. His PDFs (in the collection "جميع تدوينات أبونا إبرام") have both, and their table of contents uses the same numbers as the MIDI files (e.g. "2100 07 السبع طرائق - الأولى" is on pages 1922–1923). `midi_lyrics.py` makes a MuseScore score with the notes from the MIDI and the Coptic words from the PDF, in Unicode and in Arial Coptic (it must be installed on the Mac), each syllable under its note:
```
tools/scores/.venv/bin/python tools/scores/midi_lyrics.py "<score.mid>" "<book.pdf>" <first page> <last page> <work folder>/words.mscx
```
It pairs the PDF's noteheads with the MIDI's notes, line by line, and writes nothing unless their counts agree. It prints the words by verse (in the PDF's colours) to check against the hymn's text. A key of the old Coptic font it doesn't know shows as `?` and is named: add it to `LETTERS`. Then go on with `prepare.sh` on `words.mscx` (step 1 below).

Several verses sung to the same notes (rows of words one under another) each get their own line, with its transliteration right under it. Tried on the Seven Tunes (October 2026): all seven matched note for note (173 to 773 notes each).

## For each score and recording

1. **Prepare the score** (adds the transliteration line; exports the PDF, the notes' and bars' places and times, and the score's audio):
   ```
   zsh tools/scores/prepare.sh "<score.mscz>" <work folder>
   ```
   Open `<work folder>/score.pdf` and check the transliteration line. The rules are in `transliterate.py`; a syllable can also be corrected in `score.mscx` with MuseScore, then run `prepare.sh` on that file.

2. **Find where the hymn is sung** in the recording (seconds), leaving out speech, an announcement or applause before or after it. Listening is enough: e.g. 28.5 to 101.8.

3. **Draft the marks** (one per note):
   ```
   tools/scores/.venv/bin/python tools/scores/align.py <work folder> "<recording.m4a>" <work folder>/draft.taps.json --sung 28.5 101.8
   ```
   It tries every key the cantor may sing in. A match cost around 0.15 was good; much higher means the recording may not follow this score (another tune, or parts repeated or left out).

4. **Smooth them** (each bar's first note stays; the notes in between follow the written rhythm):
   ```
   python3 tools/scores/smooth.py <work folder> <work folder>/draft.taps.json <work folder>/smoothed.taps.json
   ```

5. **Check by ear in the app** (My hymns; Mark Sync on the website works the same way): a new hymn from `score.pdf` and the recording, then **Options › Import marks…** (`smoothed.taps.json`). In Edit mode, tap a mark that is off and use **Set to playhead** (or ±0.02 / ±0.1 s). Leave marks where they are on the page: their places come from the score. Then **Options › Share marks** (Save to Files) into the work folder.

6. **Smooth again around your fixes** (the marks you changed are kept, the notes around them follow):
   ```
   python3 tools/scores/smooth.py <work folder> <work folder>/draft.taps.json "<your exported taps>.json" <work folder>/final.taps.json
   ```

7. **To try it in the app**, one hymn as a Mark Sync backup, imported in My hymns:
   ```
   python3 tools/scores/package.py <work folder>/score.pdf "<recording.m4a>" <work folder>/final.taps.json "<name>.marksync" --name "<name>"
   ```
   Importing a backup with the same id replaces the hymn, so the same `--name` updates it.

8. **To publish it** as a hymn with notation, see *Adding a music score to a hymn* in the repo's README: the PDF and the marks go in `content/notations/<id>/`, following the hymn's own recording when the app already has it.

`check_marks.swift` draws a page's marks as dots on the PDF, to check that they sit on their notes:
`swift tools/scores/check_marks.swift <score.pdf> <marks.json> <out.png> [page]` (marks.json: `{"marks": [[t, page, x, y], …]}`).

## Limits

- The places of notes come from MuseScore 4's position files, whose units differ from score to score; they are measured against score.pdf (equal left and right margins assumed). `check_marks.swift` shows whether the dots sit on the notes.
- A recording that repeats a part, skips one or sings another tune than the score needs its marks fixed by hand in those places, or a score that follows it.
