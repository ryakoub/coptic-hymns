#!/usr/bin/env python3
"""Merge word timings exported from the Coptic Chanter app into a hymn's lyrics.json.

The app exports <recording>.timing.json (Time words → Export). For each timed line this script writes
the line's "words" (text, start, end) into content/**/<recording>/lyrics.json, which the website and
the catalog builder read, and moves the line's start to its first word when that word was marked.
Everything else in lyrics.json is kept as it is.

Usage:
  python3 tools/import_timing.py ~/Downloads/first-hoos.timing.json [more files…]
  python3 tools/import_timing.py --dry-run FILE     # show what would change, write nothing

Afterwards run python3 tools/build_catalog.py, and in the app repo scripts/sync-catalog.sh.
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"


def find_folder(recording):
    hits = [p.parent for p in CONTENT.rglob("lyrics.json") if p.parent.name == recording]
    if len(hits) != 1:
        sys.exit(f"{recording}: expected one folder named {recording} under content/, found {len(hits)}")
    return hits[0]


def merge(path, dry_run):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    rec, text = doc.get("recording"), doc.get("text")
    if not rec or not isinstance(doc.get("segments"), list):
        sys.exit(f"{path}: not a timing file exported from the app")
    if text != rec:
        sys.exit(f"{path}: {rec} sings the text of {text}; importing timings for a shared text isn't supported yet")
    folder = find_folder(rec)
    lyrics_path = folder / "lyrics.json"
    lines = json.loads(lyrics_path.read_text(encoding="utf-8"))

    changed, repeats = 0, 0
    done = set()
    for seg in doc["segments"]:
        line_id = seg.get("line", "")
        if not line_id.startswith("l") or not line_id[1:].isdigit():
            sys.exit(f"{path}: unexpected line id {line_id!r}")
        i = int(line_id[1:]) - 1
        if not 0 <= i < len(lines):
            sys.exit(f"{path}: line {line_id} is beyond the {len(lines)} lines of {lyrics_path}")
        if line_id in done:
            repeats += 1          # lyrics.json has one entry per line; the first time it is sung wins
            continue
        done.add(line_id)
        words = [w for w in seg.get("words") or [] if w.get("start") is not None]
        if not words:
            continue
        out = []
        for w in seg["words"]:
            if w.get("start") is None:
                continue
            item = {"text": w["text"], "start": round(float(w["start"]), 2)}
            if w.get("end") is not None:
                item["end"] = round(float(w["end"]), 2)
            if w.get("trailingSpace") is False:
                item["trailingSpace"] = False
            out.append(item)
        missing = len(seg["words"]) - len(out)
        # The marks were made against the text the app had then. If the lyrics were corrected since,
        # importing those words would bring the old text back on the website, so skip the line.
        marked_text, joined = [], ""
        for w in seg["words"]:
            joined += w["text"]
            if w.get("trailingSpace") is not False:
                marked_text.append(joined)
                joined = ""
        if joined:
            marked_text.append(joined)
        current_text = (lines[i].get("coptic") or "").split()
        if marked_text != current_text:
            diff = next((k for k, (a, b) in enumerate(zip(marked_text, current_text)) if a != b), min(len(marked_text), len(current_text)))
            print(f"  line {i + 1}: lyrics changed since it was timed (from word {diff + 1}); skipped, re-time it after updating the app")
            continue
        if missing:
            # The website shows a line's timed words in place of its text, so a partly marked line would lose words.
            print(f"  line {i + 1}: {len(out)} of {len(seg['words'])} words marked; skipped until all are marked")
            continue
        # The website picks the active line by its start: keep it at the first word when that was marked.
        first = seg["words"][0].get("start") if seg["words"] else None
        if first is not None and round(float(first), 2) != lines[i].get("start"):
            lines[i]["start"] = round(float(first), 2)
            if lines[i].get("words") == out:
                changed += 1
                print(f"  line {i + 1}: start moved to its first word")
        if lines[i].get("words") != out:
            changed += 1
            print(f"  line {i + 1}: {len(out)} timed words")
            lines[i]["words"] = out

    if repeats:
        print(f"  {repeats} repeated line(s): kept the first time each is sung")
    if not changed:
        print(f"{rec}: nothing new")
        return
    if dry_run:
        print(f"{rec}: {changed} line(s) would change in {lyrics_path.relative_to(ROOT)} (dry run, nothing written)")
        return
    lyrics_path.write_text(json.dumps(lines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{rec}: updated {changed} line(s) in {lyrics_path.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="timing files exported from the app")
    ap.add_argument("--dry-run", action="store_true", help="show what would change without writing")
    args = ap.parse_args()
    for f in args.files:
        merge(f, args.dry_run)


if __name__ == "__main__":
    main()
