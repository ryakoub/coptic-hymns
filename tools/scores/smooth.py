"""Steadier marks: keep each bar's first note and the marks fixed by ear, and time the notes in between by the
score's rhythm (their written lengths), so the cursor doesn't jitter from note to note.

  python3 tools/scores/smooth.py <prepared folder> <draft.taps.json> [<edited.taps.json>] <out.taps.json>

draft.taps.json comes from align.py. edited.taps.json, when given, is the same marks after fixing some in Mark
Sync or the app (Export taps, Share marks): any mark that differs from the draft counts as fixed by ear and is kept as it is.
"""
import json, os, re, sys


def events(path):
    text = open(path, encoding="utf-8").read()
    return sorted(int(p) for p in re.findall(r'<event elid="\d+" position="(\d+)"', text))


def main():
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    prepared, draft_path, out_path = sys.argv[1], sys.argv[2], sys.argv[-1]
    edited_path = sys.argv[3] if len(sys.argv) == 5 else None
    draft = json.load(open(draft_path, encoding="utf-8"))
    base = json.load(open(edited_path, encoding="utf-8")) if edited_path else draft
    auto = sorted(draft["tracks"][0]["points"], key=lambda p: p[0])
    marks = sorted(base["tracks"][0]["points"], key=lambda p: p[0])
    notes = events(os.path.join(prepared, "score.spos"))          # each note's time in the score (ms)
    bars = set(events(os.path.join(prepared, "score.mpos")))      # each bar's start (ms)
    if not (len(marks) == len(auto) == len(notes)):
        sys.exit(f"{len(marks)} marks, {len(auto)} in the draft and {len(notes)} notes: they should be one per note")

    fixed = {k for k, (a, b) in enumerate(zip(auto, marks)) if abs(a[0] - b[0]) > 0.005 or abs(a[2] - b[2]) > 0.002}
    anchors = []
    for k, ms in enumerate(notes):
        if ms in bars or k in fixed or k in (0, len(notes) - 1):
            if not anchors or marks[k][0] > marks[anchors[-1]][0]:      # anchors must go forward in time
                anchors.append(k)
    out = [list(p) for p in marks]
    for a, b in zip(anchors, anchors[1:]):
        sa, sb, ta, tb = notes[a], notes[b], marks[a][0], marks[b][0]
        for k in range(a + 1, b):
            out[k][0] = round(ta + (tb - ta) * (notes[k] - sa) / (sb - sa), 3)

    result = dict(base, tracks=[dict(base["tracks"][0], points=out)])
    json.dump(result, open(out_path, "w", encoding="utf-8"), ensure_ascii=False)
    gaps = [b[0] - a[0] for a, b in zip(out, out[1:])]
    print(f"{len(anchors)} anchors ({len(fixed)} fixed by ear); closest notes now {min(gaps):.2f}s apart")


if __name__ == "__main__":
    main()
