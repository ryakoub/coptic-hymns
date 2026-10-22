"""A MuseScore score from a MIDI file and the PDF pages of the same score: the notes from the MIDI, the Coptic
words from the PDF, in Unicode, each syllable under its note. Then prepare.sh adds the transliteration line.

  venv/bin/python tools/scores/midi_lyrics.py <score.mid> <book.pdf> <first page> <last page> <out.mscx>

Made for Fr. Abraam's PDFs (Finale, with the Maestro music font and an old ASCII Coptic font): its noteheads are
text, so each one is found on the page and paired, in order, with a MIDI note. The counts must agree on every
line of music, or nothing is written. Pages count from 1.
"""
import os, re, shutil, subprocess, sys, tempfile
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTChar

MSCORE = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"
HEADS = {"ˆ", "˙", "w", "(cid:169)", "(cid:185)"}   # Maestro's noteheads as the PDF decodes them: filled, half, whole,
#                                                  and two the Seven Tunes use in bars with "+" or dots over the notes
# Written before the letter they go over: a jenkim (alone, a jenkim sung on its own note), a dot.
MARKS = {"`": "̀", "~": "̇"}
# The old Coptic font: each ASCII key stands for a Coptic letter (checked on the Seven Tunes: ; is ϯ, ] is ϣ).
LETTERS = dict(zip("abgdezhqiklmnxoprctuvyws'\\jf[];", "ⲁⲃⲅⲇⲉⲍⲏⲑⲓⲕⲗⲙⲛⲭⲟⲡⲣⲥⲧⲩⲫⲯⲱϣϧϩϫϥϭϣϯ"))
LETTERS.update({k.upper(): v.upper() for k, v in LETTERS.items() if k.isalpha()})
LETTERS.update({'"': "Ϧ", "|": "Ϩ", ">": ":", ".": ".", ":": ":", "(": "(", ")": ")"})
LYRICS_FONT = "ArialCoptic"             # installed on the Mac (ArialCoptic.ttf, as in coptic-hymns/fonts)
VERSE_LINES = [0, 2, 5, 8, 11]            # lyric line of each verse (counted from 0)
COLOURS = {"red": (126, 0, 0), "blue": (0, 0, 126)}


def chars(o):
    if isinstance(o, LTChar):
        yield o
    elif hasattr(o, "__iter__"):
        for c in o:
            yield from chars(c)


def coptic(keys, unknown):
    """Old-font text in Unicode, each mark after the letter it goes over."""
    out, mark = "", ""
    for k in keys:
        if k in MARKS:
            mark += MARKS[k]
            continue
        letter = LETTERS.get(k)
        if letter is None:
            unknown.add(k)
            letter = "?"
        out += letter + mark
        mark = ""
    # A jenkim on its own is written as a spacing grave (ˋ), which shows without a letter under it.
    return out + mark if out else mark.replace(MARKS["`"], "\u02cb")


def colour(c):
    col = c.graphicstate.ncolor
    if isinstance(col, (tuple, list)) and len(col) == 3:
        if col[0] > col[2]: return "red"
        if col[2] > col[0]: return "blue"
    return None


def read_page(page):
    """Each line of music on the page: its noteheads left to right, and its syllables with the x of their middle
    and their verse (the rows of words under a staff, from the top: several verses can share the notes)."""
    H = page.height
    cs = list(chars(page))
    music = max({c.fontname for c in cs}, key=lambda f: sum(1 for c in cs if c.fontname == f and c.get_text() == "="))
    bases = sorted({round(H - c.y0, 1) for c in cs if c.fontname == music and c.get_text() == "="})
    lines = [{"heads": [], "syllables": []} for _ in bases]
    near = lambda y: min(range(len(bases)), key=lambda k: abs(bases[k] - 6 - y))
    for c in cs:
        if c.fontname == music and c.get_text() in HEADS:
            lines[near(H - c.y0)]["heads"].append((c.x0 + c.x1) / 2)
    # Lyrics: big characters in another font, on rows from a staff's baseline down to 32 points below it.
    below = lambda c, b: -4 < H - c.y0 - b < 32
    lyric = [c for c in cs if c.fontname != music and c.size > 12 and c.get_text().isascii()
             and any(below(c, b) for b in bases)]
    rows = {}
    for c in lyric:
        k = next(k for k, b in enumerate(bases) if below(c, b))
        rows.setdefault(k, []).append(c)
    for k, staff_chars in rows.items():
        ys = sorted({round(H - c.y0, 1) for c in staff_chars})
        verse_of, verse = {}, 0
        for a, y in enumerate(ys):
            if a and y - ys[a - 1] > 5:
                verse += 1
            verse_of[y] = verse
        for v in range(verse + 1):
            row = sorted((c for c in staff_chars if verse_of[round(H - c.y0, 1)] == v), key=lambda c: c.x0)
            read_row(row, v, lines[k]["syllables"], sorted(lines[k]["heads"]))
    for line in lines:
        line["heads"].sort()
    return lines


def read_row(row, verse, syllables, heads):
    """A row of lyric characters into syllables. Letters of a syllable sit at the font's usual spacing (in an
    italic font their boxes overlap), so a wider gap may start a new syllable; pieces that would fall under the
    same note are one syllable after all. Punctuation stays with what comes before it."""
    gaps = [round((b.x0 - a.x1) * 2) / 2 for a, b in zip(row, row[1:]) if a.get_text() not in MARKS]
    usual = max(set(gaps), key=gaps.count) if gaps else 0
    if gaps and gaps.count(usual) < 2:                # a short row: no spacing repeats, take the closest pair
        usual = min(gaps)
    row = sorted(row, key=lambda c: (round(c.x0, 1), c.get_text() not in MARKS))   # a mark before its letter
    pieces = [[row[0]]]
    for c in row[1:]:
        if (c.x0 - pieces[-1][-1].x1 <= usual + 0.75 or c.get_text() in ".:>)"
                or (pieces[-1][-1].get_text() in MARKS and c.x0 - pieces[-1][-1].x0 < 3)):  # a mark over its letter
            pieces[-1].append(c)
        else:
            pieces.append([c])
    middle = lambda g: (g[0].x0 + g[-1].x1) / 2
    note = lambda g: min(range(len(heads)), key=lambda i: abs(heads[i] - middle(g))) if heads else 0
    groups = [pieces[0]]
    for piece in pieces[1:]:
        if note(piece) == note(groups[-1]):
            groups[-1] = groups[-1] + piece
        else:
            groups.append(piece)
    for group in groups:
        text = "".join(g.get_text() for g in group).strip()
        if text:
            syllables.append((middle(group), text, colour(group[0]), verse))


def main():
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    mid, pdf, first, last, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]

    # The notes: MuseScore reads the MIDI.
    # MuseScore can stop with an error on quitting after writing the file, so the file is what counts.
    tmp = tempfile.mkdtemp()
    shutil.copy(mid, os.path.join(tmp, "score.mid"))
    subprocess.run([MSCORE, "-o", os.path.join(tmp, "score.mscx"), os.path.join(tmp, "score.mid")], capture_output=True)
    if not os.path.exists(os.path.join(tmp, "score.mscx")):
        sys.exit("MuseScore could not read the MIDI file.")
    xml = open(os.path.join(tmp, "score.mscx"), encoding="utf-8").read()
    chords = [m for m in re.finditer(r"<Chord>.*?</Chord>", xml, re.S)
              if not re.search(r'<Spanner type="Tie">\s*<prev>', m.group(0))]   # a tied note is sung once

    # The noteheads and words, page by page, line by line.
    lines = [l for p in extract_pages(pdf, page_numbers=range(first - 1, last)) for l in read_page(p)]
    heads = sum(len(l["heads"]) for l in lines)
    print(f"{len(lines)} lines of music, {heads} noteheads in the PDF; {len(chords)} notes in the MIDI")
    if heads != len(chords):
        sys.exit("The PDF and the MIDI don't have the same notes: nothing written.")

    unknown, lyrics, start = set(), {}, 0
    for n, line in enumerate(lines, 1):
        for x, keys, col, verse in line["syllables"]:
            k = min(range(len(line["heads"])), key=lambda i: abs(line["heads"][i] - x))
            if (start + k, verse) in lyrics:
                print(f"  line {n}: two syllables on one note ({lyrics[start + k, verse][0]} and {keys})")
            lyrics[start + k, verse] = (coptic(keys, unknown), col)
        start += len(line["heads"])
    if unknown:
        print("  old-font keys not known yet (shown as ?):", " ".join(sorted(unknown)))

    # Each syllable into its note, in the PDF's colour, each verse on its own lyric line with room under it for
    # its transliteration (transliterate.py, LINE_RATIO).
    parts, last_end = [], 0
    for i, m in enumerate(chords):
        verses = sorted(v for n, v in lyrics if n == i)
        if not verses:
            continue
        indent = re.search(r"\n([ \t]*)<(?:durationType|Note)", m.group(0)).group(1)
        lyric = ""
        for v in verses:
            text, col = lyrics[i, v]
            no = f"{indent}  <no>{VERSE_LINES[v]}</no>\n" if v else ""
            rgb = f'{indent}  <color r="{COLOURS[col][0]}" g="{COLOURS[col][1]}" b="{COLOURS[col][2]}" a="255"/>\n' if col else ""
            lyric += f"{indent}<Lyrics>\n{no}{rgb}{indent}  <text>{text}</text>\n{indent}  </Lyrics>\n"
        at = m.start() + m.group(0).index("<Note>")
        at = xml.rindex("\n", 0, at) + 1
        parts.append(xml[last_end:at] + lyric)
        last_end = at
    xml = "".join(parts) + xml[last_end:]
    # The Coptic (first lyric line) in Arial Coptic, the traditional-looking font the app uses too.
    xml = re.sub(r"(\n([ \t]*)<Division>\d+</Division>\n)",
                 lambda m: m.group(1) + f"{m.group(2)}<Style>\n{m.group(2)}  <lyricsOddFontFace>{LYRICS_FONT}</lyricsOddFontFace>\n"
                                        f"{m.group(2)}  <lyricsOddFontSize>12</lyricsOddFontSize>\n{m.group(2)}  </Style>\n", xml, count=1)
    open(out, "w", encoding="utf-8").write(xml)
    print(f"{out}: {len(lyrics)} syllables")
    for verse in sorted({v for _, v in lyrics}):
        for col in ("red", "blue", None):
            words = " ".join(t for (i, v), (t, c) in sorted(lyrics.items()) if v == verse and c == col)
            if words:
                print(f"  verse {verse + 1}, {col or 'black'}: {words}")


if __name__ == "__main__":
    main()
