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
HEADS = {"ˆ", "˙", "w"}                 # Maestro's filled, half and whole noteheads (as the PDF decodes them)
# Written before the letter they go over: a jenkim (alone, a jenkim sung on its own note), a dot.
MARKS = {"`": "̀", "~": "̇"}
# The old Coptic font: each ASCII key stands for a Coptic letter (checked on the Seven Tunes: ; is ϯ, ] is ϣ).
LETTERS = dict(zip("abgdezhqiklmnxoprctuvyws'\\jf[];", "ⲁⲃⲅⲇⲉⲍⲏⲑⲓⲕⲗⲙⲛⲭⲟⲡⲣⲥⲧⲩⲫⲯⲱϣϧϩϫϥϭϣϯ"))
LETTERS.update({k.upper(): v.upper() for k, v in LETTERS.items() if k.isalpha()})
LETTERS.update({">": ":", ".": ".", ":": ":"})
LYRICS_FONT = "ArialCoptic"             # installed on the Mac (ArialCoptic.ttf, as in coptic-hymns/fonts)
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
    """Each line of music on the page: its noteheads left to right, and its syllables with the x of their middle."""
    H = page.height
    cs = list(chars(page))
    music = max({c.fontname for c in cs}, key=lambda f: sum(1 for c in cs if c.fontname == f and c.get_text() == "="))
    bases = sorted({round(H - c.y0, 1) for c in cs if c.fontname == music and c.get_text() == "="})
    lines = [{"heads": [], "syllables": []} for _ in bases]
    near = lambda y: min(range(len(bases)), key=lambda k: abs(bases[k] - 6 - y))
    for c in cs:
        if c.fontname == music and c.get_text() in HEADS:
            lines[near(H - c.y0)]["heads"].append((c.x0 + c.x1) / 2)
    # Lyrics: big characters in another font on a row level with a staff's baseline.
    lyric = [c for c in cs if c.fontname != music and c.size > 12 and c.get_text().isascii()
             and min(abs(H - c.y0 - b) for b in bases) < 4]
    rows = {}
    for c in lyric:
        rows.setdefault(min(range(len(bases)), key=lambda k: abs(bases[k] - (H - c.y0))), []).append(c)
    for k, row in rows.items():
        row.sort(key=lambda c: c.x0)
        group = [row[0]]
        for c in row[1:] + [None]:
            if c is not None and c.x0 - group[-1].x1 <= 2.5:
                group.append(c)
                continue
            text = "".join(g.get_text() for g in group).strip()
            if text:
                lines[k]["syllables"].append(((group[0].x0 + group[-1].x1) / 2, text, colour(group[0])))
            if c is not None:
                group = [c]
    for line in lines:
        line["heads"].sort()
    return lines


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
        for x, keys, col in line["syllables"]:
            k = min(range(len(line["heads"])), key=lambda i: abs(line["heads"][i] - x))
            if start + k in lyrics:
                print(f"  line {n}: two syllables on one note ({lyrics[start + k][0]} and {keys})")
            lyrics[start + k] = (coptic(keys, unknown), col)
        start += len(line["heads"])
    if unknown:
        print("  old-font keys not known yet (shown as ?):", " ".join(sorted(unknown)))

    # Each syllable into its note, as the first lyric line, in the PDF's colour.
    parts, last_end = [], 0
    for i, m in enumerate(chords):
        if i not in lyrics:
            continue
        text, col = lyrics[i]
        indent = re.search(r"\n([ \t]*)<(?:durationType|Note)", m.group(0)).group(1)
        rgb = f'{indent}  <color r="{COLOURS[col][0]}" g="{COLOURS[col][1]}" b="{COLOURS[col][2]}" a="255"/>\n' if col else ""
        lyric = f"{indent}<Lyrics>\n{rgb}{indent}  <text>{text}</text>\n{indent}  </Lyrics>\n"
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
    for col in ("red", "blue", None):
        words = " ".join(t for i, (t, c) in sorted(lyrics.items()) if c == col)
        if words:
            print(f"  {col or 'black'}: {words}")


if __name__ == "__main__":
    main()
