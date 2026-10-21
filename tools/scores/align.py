"""Draft marks for a score: when each note is sung in a recording, found by matching MuseScore's audio of the
score with the recording (chroma features and dynamic time warping, in every transposition).

  venv/bin/python tools/scores/align.py <prepared folder> <recording> <out.taps.json> [--sung START END]

<prepared folder> comes from prepare.sh (score.wav, score.spos). --sung gives the seconds of the recording where
the hymn is sung, to leave out speech before or after it (without it, the score is looked for anywhere in the
recording). Writes Mark Sync's taps format: one mark per note, [seconds, page, x, y] with x, y as fractions of
the page, at the middle of the staff. Check and fix them in Mark Sync, then smooth.py.
"""
import argparse, json, os, re, subprocess, tempfile
import numpy as np
import librosa

SR, HOP = 22050, 512
# MuseScore 4's position files use about 4424 units an inch (measured: systems 5670 apart are 0.1165 of an 11 in
# page; checked by drawing the marks with check_marks.swift). A Letter page is 8.5 × 11 in.
UNITS_PER_INCH = 5670 / (0.1165 * 11)
STAFF_MIDDLE = 0.0125          # a note's element starts at the staff's top line; the cursor centres on the staff


def chroma(path, span=None):
    if not path.lower().endswith(".wav"):            # librosa reads WAV; ffmpeg converts the rest (m4a, mp3)
        wav = os.path.join(tempfile.mkdtemp(), "recording.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-ac", "1", "-ar", str(SR), wav], check=True)
        path = wav
    y, _ = librosa.load(path, sr=SR, mono=True, offset=span[0] if span else 0.0,
                        duration=(span[1] - span[0]) if span else None)
    c = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
    return c / (np.linalg.norm(c, axis=0, keepdims=True) + 1e-9)


def positions(path):
    text = open(path, encoding="utf-8").read()
    elements = {int(m[0]): tuple(map(float, m[1:5])) + (int(m[5]),) for m in re.findall(
        r'<element id="(\d+)" x="([\d.]+)" y="([\d.]+)" sx="([\d.]+)" sy="([\d.]+)" page="(\d+)"', text)}
    events = sorted((int(b), int(a)) for a, b in re.findall(r'<event elid="(\d+)" position="(\d+)"', text))
    return elements, events


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prepared"); ap.add_argument("recording"); ap.add_argument("out")
    ap.add_argument("--sung", nargs=2, type=float, metavar=("START", "END"))
    ap.add_argument("--page", nargs=2, type=float, default=(8.5, 11), metavar=("WIDTH_IN", "HEIGHT_IN"))
    a = ap.parse_args()

    S = chroma(os.path.join(a.prepared, "score.wav"))
    R = chroma(a.recording, a.sung)
    offset = a.sung[0] if a.sung else 0.0
    best = None
    for shift in range(12):                          # the cantor may sing in another key
        D, wp = librosa.sequence.dtw(X=S, Y=np.roll(R, shift, axis=0), metric="cosine", subseq=a.sung is None)
        cost = D[wp[0][0], wp[0][1]] / len(wp)
        if best is None or cost < best[0]:
            best = (cost, shift, wp[::-1])
    cost, shift, wp = best
    s2r = {}
    for i, j in wp:
        s2r.setdefault(int(i), int(j))

    elements, events = positions(os.path.join(a.prepared, "score.spos"))
    pw, ph = a.page[0] * UNITS_PER_INCH, a.page[1] * UNITS_PER_INCH
    marks = []
    for ms, elid in events:
        x, y, sx, sy, page = elements[elid]
        frame = min(int(round(ms / 1000 * SR / HOP)), S.shape[1] - 1)
        while frame not in s2r and frame > 0:
            frame -= 1
        t = offset + s2r.get(frame, 0) * HOP / SR
        marks.append([round(t, 3), page + 1, round((x + sx / 2) / pw, 4), round(y / ph + STAFF_MIDDLE, 4)])
    marks.sort(key=lambda m: m[0])

    name = os.path.splitext(os.path.basename(a.recording))[0]
    taps = {"app": "mark-sync", "version": 2, "name": name, "folders": [], "pdf": "score.pdf", "pages": max(m[1] for m in marks),
            "tracks": [{"name": name, "audio": os.path.basename(a.recording), "startAt": None, "points": marks}]}
    json.dump(taps, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
    gaps = [b[0] - a_[0] for a_, b in zip(marks, marks[1:])]
    print(f"transposition {shift} semitones, match cost {cost:.3f} (lower is better; about 0.15 was good)")
    print(f"{len(marks)} marks from {marks[0][0]:.1f}s to {marks[-1][0]:.1f}s; notes at the same moment: {sum(g < 0.02 for g in gaps)}")


if __name__ == "__main__":
    main()
