"""The notes of a score read from Fr. Abraam's PDF pages, written as a MIDI file, for a hymn without his MIDI.
Then midi_lyrics.py takes that MIDI and the same pages, as for one of his MIDI files.

  .venv/bin/python tools/scores/pdf_notes.py <book.pdf> <first page> <last page> <out.mid>

His PDFs are typeset text: noteheads, clefs, flats, dots, flags and barlines are characters of the Maestro font,
and beams are drawn shapes. A note's pitch comes from its height on the staff (treble clef) and the key
signature; its length from its head (filled, half, whole), the beams on its stem (or a flag) and a dot. Every
bar is checked against the time signature, which is taken from the bars themselves (most bars are full).

Tried on the first of the Seven Tunes against Fr. Abraam's own MIDI (October 2026): pitch right for all 540
notes, length for 96% (dotted eighth and sixteenth pairs are drawn there without their dot and half beam).
"""
import collections, struct, sys
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTChar, LTCurve, LTRect

from midi_lyrics import chars, HEADS

WHITE = [53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83, 84, 86, 88]   # F3 … E6
BOTTOM_LINE = 6                       # E4, the treble staff's bottom line, in WHITE
FLAGS = {"j", "J", "(cid:76)", "(cid:44)"}   # a single eighth's flag, at its head (the last for blue notes)
RESTS = {"(cid:168)": 1, "Ó": 2, "Œ": 1, "‰": 0.5, "∑": 4}       # beats (quarters)
ACCIDENTALS = {"b": -1, "n": 0, "#": 1}
BEATS = {"whole": 4, "half": 2, "quarter": 1, 0: 1, 1: 0.5, 2: 0.25, 3: 0.125}


def shapes(o):
    if isinstance(o, (LTCurve, LTRect)):
        yield o
    elif hasattr(o, "__iter__") and not isinstance(o, LTChar):
        for c in o:
            yield from shapes(c)


def read_page(page):
    """Each line of music: its events left to right, ("note", pitch, beats) or ("rest", beats), and barlines."""
    H = page.height
    cs = list(chars(page))
    music = max({c.fontname for c in cs}, key=lambda f: sum(1 for c in cs if c.fontname == f and c.get_text() == "="))
    ms = [c for c in cs if c.fontname == music]
    bases = sorted({round(H - c.y0, 1) for c in ms if c.get_text() == "="})
    near = lambda y: min(range(len(bases)), key=lambda i: abs(bases[i] - 6 - y))
    step = lambda c, k: round(-(H - c.y0 - bases[k]) / 2)        # staff steps up from the bottom line

    # Beams: each counted for the notes whose stems it joins (a beam ends at a stem: up-stems at a head's
    # right edge, down-stems at its left), long beams first so each stem's side is known for short ones.
    heads = [(h, near(H - h.y0), H - h.y0 - 2) for h in ms if h.get_text() in HEADS]
    beams = [(s.x0, s.x1, (2 * H - s.y0 - s.y1) / 2) for s in shapes(page) if s.height < 8 and s.width > 4]
    count, side_of = collections.Counter(), {}

    def assign(b0, b1, ym, partial):
        for side, sx in (("up", lambda h: h.x1), ("down", lambda h: h.x0)):
            cand = [(h, k) for h, k, hy in heads if (ym < hy if side == "up" else ym > hy) and abs(hy - ym) < 45
                    and b0 - 1.2 <= sx(h) <= b1 + 1.2 and (not partial or side_of.get(id(h)) == side)]
            ends = [c for c in cand if abs(sx(c[0]) - b0) < 1.8 or abs(sx(c[0]) - b1) < 1.8]
            if ends:
                for h, k in cand:
                    if k == ends[0][1]:
                        count[id(h)] += 1
                        side_of.setdefault(id(h), side)
                return
    for b0, b1, ym in sorted(beams, key=lambda b: b[0] - b[1]):
        if b1 - b0 >= 10:
            assign(b0, b1, ym, False)
    for b0, b1, ym in beams:
        if b1 - b0 < 10:
            assign(b0, b1, ym, True)

    lines = [{"events": [], "bars": [], "key": {}} for _ in bases]
    first_head = {}
    for h, k, _ in heads:
        first_head[k] = min(first_head.get(k, 1e9), h.x0)
    for c in ms:
        k = near(H - c.y0)
        t = c.get_text()
        x = c.x0
        if t == "l" and abs(H - c.y0 - bases[k]) < 1:
            lines[k]["bars"].append(x)
        elif t == "b" and x < first_head.get(k, 1e9) - 10 and x < 120:        # key signature
            lines[k]["key"][(step(c, k) + BOTTOM_LINE) % 7] = -1
        elif t in RESTS and abs(H - c.y0 - bases[k]) < 20:
            lines[k]["events"].append((x, "rest", RESTS[t]))
    # A line without its own key signature keeps the one before (the 2026 edition prints it on the first line only).
    for k in range(1, len(lines)):
        if not lines[k]["key"]:
            lines[k]["key"] = lines[k - 1]["key"]
    dots = [(c.x0, H - c.y0) for c in ms if c.get_text() == "."]
    flags = [(c.x0, H - c.y0) for c in ms if c.get_text() in FLAGS]
    marks = [(c.x0, H - c.y0, c.get_text()) for c in ms if c.get_text() in ACCIDENTALS]
    for h, k, hy in heads:
        s = step(h, k)
        pitch = WHITE[s + BOTTOM_LINE] + lines[k]["key"].get((s + BOTTOM_LINE) % 7, 0)
        acc = [a for a in marks if 2 < h.x0 - a[0] < 12 and abs(a[1] - (H - h.y0)) < 3 and a[0] > 120]
        if acc:
            pitch = WHITE[s + BOTTOM_LINE] + ACCIDENTALS[acc[0][2]]
        beams_on = count[id(h)] or (1 if any(abs(fx - h.x0) < 2 and abs(fy - (H - h.y0)) < 3 for fx, fy in flags) else 0)
        beats = BEATS.get({"˙": "half", "w": "whole"}.get(h.get_text()), BEATS[min(beams_on, 3)])
        if any(0 < dx - h.x1 < 9 and abs(dy - (H - h.y0)) < 5 for dx, dy in dots):
            beats *= 1.5
        lines[k]["events"].append(((h.x0 + h.x1) / 2, "note", pitch, beats))
    for line in lines:
        line["events"].sort(key=lambda e: e[0])
        line["bars"] = sorted(set(round(b) for b in line["bars"]))
    return lines


def bars_of(lines):
    """The music bar by bar: (events, beats) for each bar."""
    out = []
    for line in lines:
        edges = line["bars"]
        if not line["events"]:
            continue
        cur = []
        for e in line["events"]:
            while edges and e[0] > edges[0] + 2:
                if cur:
                    out.append(cur)
                cur, edges = [], edges[1:]
            cur.append(e)
        if cur:
            out.append(cur)
    return [(b, sum(e[-1] for e in b)) for b in out]


def write_midi(events, path, tempo=100, beats_per_bar=4):
    """A one-track MIDI file: notes one after another (480 ticks a quarter), rests as silence."""
    def var(n):
        b = [n & 0x7F]
        while n > 0x7F:
            n >>= 7
            b.insert(0, (n & 0x7F) | 0x80)
        return bytes(b)
    track, wait = bytearray(), 0
    track += var(0) + b"\xff\x51\x03" + int(60_000_000 / tempo).to_bytes(3, "big")
    track += var(0) + b"\xff\x58\x04" + bytes([beats_per_bar, 2, 24, 8])
    for e in events:
        ticks = int(round(e[-1] * 480))
        if e[1] == "rest":
            wait += ticks
            continue
        track += var(wait) + bytes([0x90, e[2], 80]) + var(ticks) + bytes([0x80, e[2], 0])
        wait = 0
    track += var(wait) + b"\xff\x2f\x00"
    with open(path, "wb") as f:
        f.write(b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480) + b"MTrk" + struct.pack(">I", len(track)) + track)


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    pdf, first, last, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    lines = [l for p in extract_pages(pdf, page_numbers=range(first - 1, last)) for l in read_page(p)]
    bars = bars_of(lines)
    full = collections.Counter(round(b, 3) for _, b in bars).most_common(1)[0][0]
    events = []
    for i, (b, beats) in enumerate(bars):
        if i == 0 and beats < full:                 # an upbeat: the bar's rests come first
            events.append((0, "rest", full - beats))
        events += b
    notes = sum(1 for e in events if e[1] == "note")
    print(f"{notes} notes in {len(bars)} bars of {full:g} beats")
    wrong = [(i + 1, round(b, 3)) for i, (_, b) in enumerate(bars) if abs(b - full) > 1e-6 and i not in (0, len(bars) - 1)]
    if wrong:
        print(f"  bars that don't add up to {full:g} beats (bar, beats): {wrong}")
    write_midi(events, out, beats_per_bar=int(full) if full == int(full) else 4)
    print(f"{out}: written")


if __name__ == "__main__":
    main()
