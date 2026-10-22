"""A score made from Fr. Abraam's page (pdf_notes.py, midi_lyrics.py, prepare.sh) made to look like his page:
the same bars on each line, his title, maqam and source at the top and his credit at the bottom, his marks over
and under the notes (diamonds, circles, lines, pause), and his note colours. For him to check against his own.

  .venv/bin/python tools/scores/like_book.py <book.pdf> <first page> <last page> <score.mscx> <out.mscx>

Works on a score whose verses are not written out (the notes in the same order as on his page). The words stay
a little larger than his and keep their transliteration.
"""
import re, sys, unicodedata
from pdfminer.high_level import extract_pages

from midi_lyrics import chars, HEADS, coptic

# His marks (Maestro characters) and the MuseScore symbols that look like them.
MARKS = {"O": "noteheadDiamondWhite", "o": "stringsHarmonic", "-": "articTenuto", "U": "fermata", ".": "articStaccato"}
# His key signature: flats (b) and, for maqams like Bayati, half-flats (i, drawn in blue).
KEY_SIGNS = {"b": "accidentalFlat", "i": "accidentalQuarterToneFlatStein"}
LETTERS = "FGABCDEFGABCDEFGABCDE"           # the staff's steps from F3 (E4, the bottom line, is step 6)
DEGREE = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
SIZES = {"lyricsOddFontSize": 14, "minMeasureWidth": 5, "lyricsMinDistance": 0.5}
STYLE = {"titleFontFace": "ArialCoptic"}


def colour(c):
    col = c.graphicstate.ncolor
    if isinstance(col, (tuple, list)) and len(col) == 3 and any(col):
        return tuple(round(v * 255) for v in col)
    return None


def arabic(cs, H):
    """Arabic lines of the page in reading order (a PDF keeps them as they are drawn, left to right)."""
    rows = {}
    for c in cs:
        if "Arab" in c.fontname:
            rows.setdefault(round(H - c.y0), []).append(c)
    out = []
    for y, row in sorted(rows.items()):
        text = "".join(c.get_text() for c in sorted(row, key=lambda c: -c.x0))
        out.append(" ".join(unicodedata.normalize("NFKC", text).split()))
    return out


def read(pdf, first, last):
    """His notes in order (line, x) with colour and marks; each line's last note; the title and header lines."""
    notes, line_ends, title, header, key = [], [], "", [], {}
    for n, p in enumerate(extract_pages(pdf, page_numbers=range(first - 1, last))):
        H = p.height
        cs = list(chars(p))
        music = max({c.fontname for c in cs}, key=lambda f: sum(1 for c in cs if c.fontname == f and c.get_text() == "="))
        bases = sorted({round(H - c.y0, 1) for c in cs if c.fontname == music and c.get_text() == "="})
        near = lambda y: min(range(len(bases)), key=lambda i: abs(bases[i] - 6 - y))
        heads = sorted([c for c in cs if c.fontname == music and c.get_text() in HEADS],
                       key=lambda c: (near(H - c.y0), (c.x0 + c.x1) / 2))
        marks = [c for c in cs if c.fontname == music and c.get_text() in MARKS]
        for i, h in enumerate(heads):
            mine = []
            for m in marks:
                dx, dy = m.x0 - h.x0, (H - m.y0) - (H - h.y0)
                if m.get_text() == "." and not (abs(dx) < 4 and 2 < abs(dy) < 12):
                    continue                          # a dot after a note lengthens it (pdf_notes.py)
                if -3 < dx < 7 and (-26 < dy < -8 or 2 < dy < 14) and near(H - m.y0) == near(H - h.y0):
                    mine.append((MARKS[m.get_text()], "Above" if dy < 0 else "Below", colour(m)))
            notes.append({"colour": colour(h), "marks": mine})
            if i + 1 == len(heads) or near(H - heads[i + 1].y0) != near(H - h.y0):
                line_ends.append(len(notes) - 1)
        if n == 0:
            first_x = min(h.x0 for h in heads if near(H - h.y0) == 0)
            for c in cs:
                if c.fontname == music and c.get_text() in KEY_SIGNS and c.x0 < first_x - 8 and near(H - c.y0) == 0:
                    step = round(-(H - c.y0 - bases[0]) / 2) + 6
                    key[LETTERS[step]] = KEY_SIGNS[c.get_text()]
            big = sorted([c for c in cs if "Abraam" in c.fontname and c.size > 18 and H - c.y0 < bases[0] - 20],
                         key=lambda c: c.x0)
            title = coptic("".join(c.get_text() for c in big), set())
            header = [t for t in arabic([c for c in cs if H - c.y0 < bases[0]], H) if t]
    return notes, line_ends, title, header, key


def main():
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    pdf, first, last, src, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
    notes, line_ends, title, header, key = read(pdf, first, last)
    xml = open(src, encoding="utf-8").read()
    chords = [m for m in re.finditer(r"<Chord>.*?</Chord>", xml, re.S)
              if not re.search(r'<Spanner type="Tie">\s*<prev>', m.group(0))]
    if len(chords) != len(notes):
        sys.exit(f"{len(notes)} notes on the page but {len(chords)} in the score (verses written out?): nothing written")

    # Marks and colours, note by note (from the end, so earlier places stay put).
    for i in reversed(range(len(chords))):
        m, note = chords[i], notes[i]
        body = m.group(0)
        indent = re.search(r"\n([ \t]*)<durationType>", body).group(1)
        arts = "".join(f"{indent}<Articulation>\n{indent}  <subtype>{name}{side if name.startswith('artic') else ''}</subtype>\n"
                       + (f'{indent}  <color r="{c[0]}" g="{c[1]}" b="{c[2]}" a="255"/>\n' if c else "")
                       + f"{indent}  </Articulation>\n"
                       for name, side, c in note["marks"] if name != "fermata")
        body = re.sub(r"(<durationType>[^<]*</durationType>\n(?:[ \t]*<dots>\d</dots>\n)?)", lambda x: x.group(1) + arts, body, count=1)
        if note["colour"]:
            r, g, b = note["colour"]
            body = re.sub(r"(<Note>\n)", lambda x: x.group(1) + f'{indent}    <color r="{r}" g="{g}" b="{b}" a="255"/>\n', body)
        before = ""
        if any(name == "fermata" for name, _, _ in note["marks"]):
            before = f"{indent[:-2]}<Fermata>\n{indent}<subtype>fermataAbove</subtype>\n{indent}</Fermata>\n{indent[:-2]}"
        xml = xml[:m.start()] + before + body + xml[m.end():]

    # His line breaks: after the bar holding each line's last note.
    measures = list(re.finditer(r"<Measure>.*?</Measure>", xml, re.S))
    count, ends = 0, set()
    for j, m in enumerate(measures):
        here = len([c for c in re.findall(r"<Chord>.*?</Chord>", m.group(0), re.S)
                    if not re.search(r'<Spanner type="Tie">\s*<prev>', c)])
        if any(count <= e < count + here for e in line_ends):
            ends.add(j)
        count += here
    for j in sorted(ends, reverse=True)[1:]:              # not after the last bar
        m = measures[j]
        xml = xml[:m.end() - len("</Measure>")] + "<LayoutBreak>\n  <subtype>line</subtype>\n  </LayoutBreak>\n" + xml[m.end() - len("</Measure>"):]

    # His title, maqam and source at the top; his credit at the bottom.
    texts = [("title", title)] + [("composer" if "المقام" in t else "subtitle", t) for t in header if "المقام" in t or "المرجع" in t]
    vbox = "<VBox>\n<height>10</height>\n" + "".join(f"<Text>\n<style>{s}</style>\n<text>{t}</text>\n</Text>\n" for s, t in texts) + "</VBox>\n"
    first_measure = re.search(r'<Staff id="1">\s*\n', xml[xml.index("</Part>"):] if "</Part>" in xml else xml)
    at = (xml.index("</Part>") if "</Part>" in xml else 0) + first_measure.end()
    xml = xml[:at] + vbox + xml[at:]
    xml = re.sub(r'<metaTag name="copyright">[^<]*</metaTag>',
                 '<metaTag name="copyright">© Music Transcription: Fr. Abraam Guirguis</metaTag>', xml)
    for name, value in SIZES.items():
        xml = re.sub(rf"<{name}>[^<]*</{name}>", f"<{name}>{value}</{name}>", xml)
    for name, value in STYLE.items():
        xml = re.sub(r"(\n([ \t]*)<Style>\n)", lambda m: m.group(1) + f"{m.group(2)}  <{name}>{value}</{name}>\n", xml, count=1)

    # A key with half-flats: written as his (a custom key signature), each half-flat note carrying its sign
    # unseen, so the notes stay as the key says without a sign on each.
    if any(v != "accidentalFlat" for v in key.values()):
        defs = "".join(f'<CustDef>\n<sym>{sym}</sym>\n<def degree="{DEGREE[letter]}" xAlt="0" octAlt="0"/>\n</CustDef>\n'
                       for letter, sym in key.items())
        xml = re.sub(r"<concertKey>-?\d+</concertKey>", "<concertKey>0</concertKey>\n<custom>1</custom>\n" + defs, xml)
        tpc = {"C": 14, "D": 16, "E": 18, "F": 13, "G": 15, "A": 17, "B": 19}
        for letter, sym in key.items():
            if sym == "accidentalFlat":
                continue
            xml = re.sub(rf"(<pitch>\d+</pitch>\n(\s*)<tpc>{tpc[letter]}</tpc>\n)",
                         lambda m: m.group(1) + f"{m.group(2)}<Accidental>\n{m.group(2)}  <subtype>{sym}</subtype>\n"
                                   f"{m.group(2)}  <role>1</role>\n{m.group(2)}  <visible>0</visible>\n{m.group(2)}  </Accidental>\n", xml)
    open(out, "w", encoding="utf-8").write(xml)
    print(f"{out}: {sum(len(n['marks']) for n in notes)} marks, {sum(1 for n in notes if n['colour'])} coloured notes, "
          f"{len(ends)} lines; key {key}; title {title}; " + " | ".join(header))


if __name__ == "__main__":
    main()
