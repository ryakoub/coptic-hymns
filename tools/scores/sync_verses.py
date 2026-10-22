"""Marks for a score sung part by part: you give the second where each verse starts in the recording, and each
verse is lined up on its own. A verse sung to the written tune gets a mark on every note, timed by following the
cantor's voice (its pitch, moment by moment) against the written notes; a verse sung the fast way (said quickly,
not to the tune) gets a mark on each of its syllables, timed by where the cantor starts each one.

  .venv/bin/python tools/scores/sync_verses.py <prepared folder> <recording> <out.taps.json>
        --times 6.5 9 77 147 163 178 [--fast 4 5]

<prepared folder> comes from prepare.sh. The parts of the score are found from its words: a part starts at a
syllable beginning with a capital after a full stop or colon (the first part at the first note), e.g. "Kyrie
eleison", then the four verses. --times gives the start of each part in the recording and, last, the end of
the singing; --fast lists the parts (from 1) sung the fast way. Writes Mark Sync's taps format, like align.py.

The cantor may sing in another key and octave than written: the shift is found from the voice (printed). On the
first of the Seven Tunes this put 71% of the notes where the cantor sings their exact pitch (98% within a
semitone), against 49% (85%) by matching the score's sound as align.py does.
"""
import argparse, json, os, re, subprocess, tempfile
import numpy as np
import librosa

from align import SR, STAFF_MIDDLE, page_scale, chroma, HOP as CHROMA_HOP

HOP = 256                         # 86 pitch readings a second
FPS = SR / HOP

CAPITALS = set("ⲀⲂⲄⲆⲈⲌⲎⲐⲒⲔⲖⲘⲚⲜⲞⲠⲢⲤⲦⲨⲪⲬⲮⲰϢϤϦϨϪϬϮ")
JENKIM = "̀"


def score_items(folder):
    """The score's notes in order, each with its time in the score (seconds), place on the page, first-verse
    syllable and whether it starts a bar. Rests are passed over."""
    xml = open(os.path.join(folder, "score.mscx"), encoding="utf-8").read()
    items = re.findall(r"<(Chord|Rest)>(.*?)</\1>", xml, re.S)
    spos = open(os.path.join(folder, "score.spos"), encoding="utf-8").read()
    elements = {int(m[0]): tuple(map(float, m[1:5])) + (int(m[5]),) for m in re.findall(
        r'<element id="(\d+)" x="([\d.]+)" y="([\d.]+)" sx="([\d.]+)" sy="([\d.]+)" page="(\d+)"', spos)}
    events = sorted((int(p), int(e)) for e, p in re.findall(r'<event elid="(\d+)" position="(\d+)"', spos))
    if len(events) != len(items):
        raise SystemExit(f"{len(items)} notes and rests in the score but {len(events)} in score.spos")
    mpos = open(os.path.join(folder, "score.mpos"), encoding="utf-8").read()
    bars = {int(p) for p in re.findall(r'<event elid="\d+" position="(\d+)"', mpos)}
    notes = []
    for (kind, body), (ms, elid) in zip(items, events):
        if kind != "Chord":
            continue
        syllable = None
        for lyric in re.findall(r"<Lyrics>(.*?)</Lyrics>", body, re.S):
            if "<no>" not in lyric:
                text = re.search(r"<text>(.*?)</text>", lyric, re.S)
                syllable = text.group(1) if text else None
        x, y, sx, sy, page = elements[elid]
        pitch = int(re.search(r"<pitch>(\d+)</pitch>", body).group(1))
        notes.append({"t": ms / 1000, "bar": ms in bars, "syllable": syllable, "pitch": pitch,
                      "page": page, "x": x + sx / 2, "y": y})
    return notes


def parts_of(notes):
    """Where each part starts: the first note, then a capital after a full stop or colon."""
    starts, last = [0], None
    for i, n in enumerate(notes):
        s = n["syllable"]
        if s and i and s.strip()[:1] in CAPITALS and last and last.rstrip()[-1:] in ".:":
            starts.append(i)
        if s:
            last = s
    return starts


def follow_voice(part, end_t, voice, voiced, rec_a, rec_b, offset):
    """When each note of a part is sung: the written pitches (shifted by offset), frame by frame, matched to the
    cantor's pitch by dynamic time warping. Frames without a sung pitch match anything equally. Returns the
    times and the average cost (lower is closer)."""
    t0 = part[0]["t"]
    grid = np.arange(t0, end_t, 1 / FPS)
    which = np.searchsorted([n["t"] for n in part], grid, side="right") - 1
    written = np.array([part[w]["pitch"] - offset for w in which], float)
    a, b = int(rec_a * FPS), int(rec_b * FPS)
    sung, on = np.nan_to_num(voice[a:b]), voiced[a:b]
    cost = np.minimum(np.abs(written[:, None] - sung[None, :]), 3.0) / 3.0
    cost[:, ~on] = 0.5
    D, wp = librosa.sequence.dtw(C=cost)
    first = {}
    for i, j in wp[::-1]:
        first.setdefault(int(i), int(j))
    times = []
    for n in part:
        f = min(int(round((n["t"] - t0) * FPS)), len(grid) - 1)
        while f not in first and f > 0:
            f -= 1
        times.append(rec_a + first.get(f, 0) / FPS)
    return times, D[-1, -1] / len(wp)


def follow_sound(part, end_t, S, R, rec_a, rec_b, shift):
    """For a choir, where there is no single voice to follow: the score's sound (score.wav) matched to the
    recording by harmony (chroma), as align.py does, part by part. Returns the times and the average cost."""
    f = lambda t: int(round(t * SR / CHROMA_HOP))
    sa, sb = f(part[0]["t"]), min(f(end_t), S.shape[1])
    D, wp = librosa.sequence.dtw(X=S[:, sa:sb], Y=np.roll(R[:, f(rec_a):f(rec_b)], shift, axis=0), metric="cosine")
    first = {}
    for i, j in wp[::-1]:
        first.setdefault(int(i), int(j))
    times = []
    for n in part:
        i = min(f(n["t"]) - sa, sb - sa - 1)
        while i not in first and i > 0:
            i -= 1
        times.append(rec_a + first.get(i, 0) * CHROMA_HOP / SR)
    return times, D[-1, -1] / len(wp)


def steady_tempo(times, part, smoothness=0.05):
    """A steady pace through the part, as a conductor would beat it: a smooth curve from written time to sung
    time, fitted to the notes so that the few the voice matching got wrong count little. The curve bends where
    the cantor clearly holds a tone longer or hurries, and stays even elsewhere, so the cursor moves without
    note to note jumps. smoothness: higher is steadier, lower follows the cantor more closely. 0.05 balanced
    both on Bola's Tunes 1 and 2 and Ibrahim's Tune 1 (speed jumps over 50% at 1–2% of the notes; 84–95% of
    the notes within a semitone of the sung pitch)."""
    from scipy.interpolate import make_smoothing_spline
    if len(part) < 8:
        return times
    x = np.array([n["t"] for n in part]) + np.arange(len(part)) * 1e-6    # notes sung together, kept in order
    y = np.array(times)
    w = np.ones_like(y)
    for _ in range(4):
        curve = make_smoothing_spline(x, y, w=w, lam=smoothness)
        w = 1 / (1 + ((y - curve(x)) / 0.15) ** 2)           # far from the curve: probably a matching error
    return [float(t) for t in np.maximum.accumulate(curve(x))]


def keep_apart(times, part, gap=0.06):
    """Notes the matching put (almost) at the same moment: spaced by the written rhythm between the notes before
    and after them, so the cursor doesn't jump."""
    out, k = list(times), 1
    while k < len(out):
        if out[k] - out[k - 1] >= gap:
            k += 1
            continue
        e = k
        while e < len(out) and out[e] - out[k - 1] < gap * (e - k + 1):
            e += 1
        a, b = k - 1, min(e, len(out) - 1)
        if b > a and out[b] > out[a] and part[b]["t"] > part[a]["t"]:
            for m in range(a + 1, b):
                out[m] = out[a] + (out[b] - out[a]) * (part[m]["t"] - part[a]["t"]) / (part[b]["t"] - part[a]["t"])
        k = e + 1
    return out


def spread_repeats(times, part):
    """Notes repeating the same pitch can't be told apart by pitch: within a run of them, keep when the run
    starts and when the next pitch comes, and space the notes between by the written rhythm."""
    out, k = list(times), 0
    while k < len(part):
        e = k
        while e + 1 < len(part) and part[e + 1]["pitch"] == part[k]["pitch"]:
            e += 1
        if e > k and e + 1 < len(part) and times[e + 1] > times[k]:
            span_s, span_r = part[e + 1]["t"] - part[k]["t"], times[e + 1] - times[k]
            for m in range(k + 1, e + 1):
                out[m] = times[k] + span_r * (part[m]["t"] - part[k]["t"]) / span_s
        k = e + 1
    return out


def fast_part(y, rec_a, rec_b, syllables):
    """Syllables said quickly: spread over the part by their length, then each moved to the nearest start of a
    sound the cantor makes (within 0.2 s), keeping their order."""
    weights = [max(1, len(s.replace(JENKIM, "").strip(".:"))) for s in syllables]
    total = sum(weights) + 1
    times, acc = [], 0
    for w in weights:
        times.append(rec_a + (rec_b - rec_a) * acc / total)
        acc += w
    seg = y[int(rec_a * SR):int(rec_b * SR)]
    onsets = rec_a + librosa.onset.onset_detect(y=seg, sr=SR, hop_length=HOP, units="time", backtrack=True)
    out, floor = [], rec_a
    for t in times:
        near = [o for o in onsets if abs(o - t) <= 0.2 and o > floor + 0.05]
        t2 = min(near, key=lambda o: abs(o - t)) if near else max(t, floor + 0.05)
        out.append(round(t2, 3))
        floor = t2
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prepared"); ap.add_argument("recording"); ap.add_argument("out")
    ap.add_argument("--times", nargs="+", type=float, required=True)
    ap.add_argument("--fast", nargs="*", type=int, default=[])
    ap.add_argument("--exact", action="store_true", help="each note where the voice matching puts it, not a steady tempo")
    ap.add_argument("--choir", action="store_true", help="follow the harmony, not one voice (found by itself too)")
    ap.add_argument("--smoothness", type=float, default=0.05, help="higher: steadier; lower: follows held tones more")
    a = ap.parse_args()

    notes = score_items(a.prepared)
    starts = parts_of(notes)
    if len(starts) != len(a.times) - 1:
        raise SystemExit(f"The score has {len(starts)} parts (starting with " +
                         ", ".join(notes[s]["syllable"] or "?" for s in starts) +
                         f") but --times gives {len(a.times) - 1}: give each part's start and then the end.")
    print("parts:", ", ".join(f"{k + 1} {notes[s]['syllable']} at {a.times[k]}s" + (" (fast)" if k + 1 in a.fast else "")
                              for k, s in enumerate(starts)))

    wav = os.path.join(tempfile.mkdtemp(), "recording.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.recording, "-ac", "1", "-ar", str(SR), wav], check=True)
    y, _ = librosa.load(wav, sr=SR, mono=True)
    f0, voiced, _ = librosa.pyin(y, fmin=65, fmax=1047, sr=SR, frame_length=4096, hop_length=HOP)
    voice = librosa.hz_to_midi(f0)
    bounds = starts + [len(notes)]
    ends = [notes[b]["t"] if b < len(notes) else notes[-1]["t"] + 1 for b in bounds[1:]]

    sung = [k for k in range(len(starts)) if k + 1 not in a.fast]
    k0 = max(sung, key=lambda k: bounds[k + 1] - bounds[k])
    heard = np.concatenate([voiced[int(a.times[k] * FPS):int(a.times[k + 1] * FPS)] for k in sung])
    choir = a.choir or heard.mean() < 0.4
    if choir:
        # No single voice to follow (a choir, or voices in harmony): match by the sound's harmony instead.
        S, R = chroma(os.path.join(a.prepared, "score.wav")), chroma(wav)
        part0 = notes[bounds[k0]:bounds[k0 + 1]]
        shift = min(range(12), key=lambda sh: follow_sound(part0, ends[k0], S, R, a.times[k0], a.times[k0 + 1], sh)[1])
        print(f"a choir (one clear voice {heard.mean():.0%} of the time): following the harmony, transposed {shift}")
    else:
        # The cantor's key and octave: start from the difference of the middle pitches, try a few semitones round it.
        sung_mid = np.nanmedian(np.concatenate([voice[int(a.times[k] * FPS):int(a.times[k + 1] * FPS)] for k in sung]))
        written_mid = np.median([n["pitch"] for k in sung for n in notes[bounds[k]:bounds[k + 1]]])
        guess = int(round(written_mid - sung_mid))
        offset = min(range(guess - 2, guess + 3), key=lambda o: follow_voice(
            notes[bounds[k0]:bounds[k0 + 1]], ends[k0], voice, voiced, a.times[k0], a.times[k0 + 1], o)[1])
        # His tuning: a cantor may sit a little sharp or flat of the written pitches all through. Measured on the
        # notes as first matched, then everything is matched again with it (exact semitones made the start of
        # Tune 2 rush through ten notes in a second).
        part0 = notes[bounds[k0]:bounds[k0 + 1]]
        first, _ = follow_voice(part0, ends[k0], voice, voiced, a.times[k0], a.times[k0 + 1], offset)
        diffs = []
        for i, n in enumerate(part0[:-1]):
            seg = voice[int(first[i] * FPS):int(first[i + 1] * FPS)]
            seg = seg[np.isfinite(seg)]
            if len(seg):
                d = np.median(seg) - (n["pitch"] - offset)
                if abs(d) < 1.5:
                    diffs.append(d)
        offset = offset - float(np.median(diffs)) if diffs else offset
        print(f"the cantor sings {offset:.2f} semitones below the written notes")

    scale, w, h = page_scale(a.prepared)
    pw, ph = scale * w, scale * h
    marks = []
    for k in range(len(starts)):
        part = notes[bounds[k]:bounds[k + 1]]
        if k + 1 in a.fast:
            sy = [n for n in part if n["syllable"]]
            times = fast_part(y, a.times[k], a.times[k + 1], [n["syllable"] for n in sy])
            chosen = list(zip(sy, times))
            print(f"  part {k + 1}: {len(sy)} syllables, sung fast")
        else:
            times, cost = (follow_sound(part, ends[k], S, R, a.times[k], a.times[k + 1], shift) if choir else
                           follow_voice(part, ends[k], voice, voiced, a.times[k], a.times[k + 1], offset))
            times = keep_apart(spread_repeats(times, part) if a.exact else steady_tempo(times, part, a.smoothness), part)
            chosen = list(zip(part, times))
            print(f"  part {k + 1}: {len(part)} notes, match cost {cost:.3f}")
        for n, t in chosen:
            marks.append([round(t, 3), n["page"] + 1, round(n["x"] / pw, 4), round(n["y"] / ph + STAFF_MIDDLE, 4)])
    marks.sort(key=lambda q: q[0])

    name = os.path.splitext(os.path.basename(a.recording))[0]
    taps = {"app": "mark-sync", "version": 2, "name": name, "folders": [], "pdf": "score.pdf",
            "pages": max(q[1] for q in marks),
            "tracks": [{"name": name, "audio": os.path.basename(a.recording), "startAt": None, "points": marks}]}
    json.dump(taps, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
    gaps = [b[0] - q[0] for q, b in zip(marks, marks[1:])]
    print(f"{len(marks)} marks from {marks[0][0]:.1f}s to {marks[-1][0]:.1f}s; closest {min(gaps):.2f}s apart")


if __name__ == "__main__":
    main()
