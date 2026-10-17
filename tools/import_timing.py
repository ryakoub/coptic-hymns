#!/usr/bin/env python3
"""Merge word timings exported from the Coptic Chanter app into a hymn's lyrics.json.

The app exports <recording>.timing.json (Time words → Export). For each timed line this script writes
the line's "words" (text, start, end) into content/**/<recording>/lyrics.json, which the website and
the catalog builder read, and moves the line's start to its first word when that word was marked.
Everything else in lyrics.json is kept as it is.

Usage:
  python3 tools/import_timing.py ~/Downloads/first-hoos.timing.json [more files…]
  python3 tools/import_timing.py --dry-run FILE     # show what would change, write nothing

Lines can be partly marked: the words left unmarked get estimated times (tools/word_estimates.py, the same
way the app does it), written with "estimated": true. The website uses them; the catalog builder leaves
them out for the app, which estimates again from the marks.

Afterwards run python3 tools/build_catalog.py, and in the app repo scripts/sync-catalog.sh.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from word_estimates import estimate   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"


def find_folder(recording):
    hits = [p.parent for p in CONTENT.rglob("lyrics.json") if p.parent.name == recording]
    if len(hits) != 1:
        sys.exit(f"{recording}: expected one folder named {recording} under content/, found {len(hits)}")
    return hits[0]


def written_words(words):
    """Words as written: a word with "trailingSpace": false joins the next."""
    result, joined = [], ""
    for w in words:
        joined += w["text"]
        if w.get("trailingSpace") is not False:
            result.append(joined)
            joined = ""
    if joined:
        result.append(joined)
    return result


def line_words(line, language):
    """What a recording in `language` sings for a text line, word by word."""
    if language == "coptic":
        return (line.get("coptic") or "").split()
    return ((line.get("sung") or {}).get(language) or (line.get("translations") or {}).get(language) or "").split()


def merge_shared(path, doc, dry_run):
    """A recording of another hymn's text (another tune or language): its timings go in its own lyrics.json
    as entries naming the line ({"line": "l3", "start": …, "words": […]}); the text's lyrics are untouched."""
    rec, text = doc["recording"], doc["text"]
    folder, text_folder = find_folder(rec), find_folder(text)
    info = json.loads((folder / "info.json").read_text(encoding="utf-8")) if (folder / "info.json").exists() else {}
    language = info.get("language", "coptic")
    text_lines = json.loads((text_folder / "lyrics.json").read_text(encoding="utf-8"))
    lyrics_path = folder / "lyrics.json"
    entries = json.loads(lyrics_path.read_text(encoding="utf-8")) if lyrics_path.exists() else []
    by_line = {e["line"]: e for e in entries if e.get("line")}
    changed = 0
    for seg in doc["segments"]:
        line_id = seg.get("line", "")
        i = int(line_id[1:]) - 1 if line_id[1:].isdigit() else -1
        if not 0 <= i < len(text_lines):
            sys.exit(f"{path}: line {line_id} is not in {text}")
        if not any(w.get("start") is not None and not w.get("estimated") for w in seg.get("words") or []):
            continue
        out = [word_item(w) for w in seg["words"]]
        timed = [w["start"] for w in out if "start" in w]
        if any(b < a for a, b in zip(timed, timed[1:])):
            print(f"  line {i + 1}: marks out of order; skipped, re-mark it in the app")
            continue
        if written_words(out) != line_words(text_lines[i], language):
            print(f"  line {i + 1}: its words don't spell its {language} text; skipped (re-time it after updating the app)")
            continue
        entry = {"line": line_id, "start": timed[0], "words": out}
        if by_line.get(line_id) != entry:
            by_line[line_id] = entry
            changed += 1
            print(f"  line {i + 1}: {describe(out)}")
    if not changed:
        print(f"{rec}: nothing new")
        return
    if dry_run:
        print(f"{rec}: {changed} line(s) would change in {lyrics_path.relative_to(ROOT)} (dry run, nothing written)")
        return
    merged = sorted(by_line.values(), key=lambda e: e["start"])
    lyrics_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{rec}: updated {changed} line(s) in {lyrics_path.relative_to(ROOT)} ({language})")


def word_item(w):
    item = {"text": w["text"]}
    if w.get("start") is not None:
        item["start"] = round(float(w["start"]), 2)
        if w.get("estimated"):
            item["estimated"] = True
    if w.get("end") is not None and not w.get("estimated"):
        item["end"] = round(float(w["end"]), 2)
    if w.get("trailingSpace") is False:
        item["trailingSpace"] = False
    return item


def describe(words):
    marked = sum(1 for w in words if "start" in w and not w.get("estimated"))
    return f"{len(words)} timed words" if marked == len(words) else f"{marked} of {len(words)} words marked, the rest estimated"


def merge(path, dry_run):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    rec, text = doc.get("recording"), doc.get("text")
    if not rec or not isinstance(doc.get("segments"), list):
        sys.exit(f"{path}: not a timing file exported from the app")
    # Untimed lines the app placed at the far end (never marked) are not part of the recording's order.
    doc["segments"] = [seg for seg in doc["segments"] if seg.get("start", 0) < 1e9]
    estimate(doc["segments"])
    if text != rec:
        return merge_shared(path, doc, dry_run)
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
        if not any(w.get("start") is not None and not w.get("estimated") for w in seg.get("words") or []):
            continue
        out = [word_item(w) for w in seg["words"]]
        timed = [w["start"] for w in out if "start" in w]
        if any(b < a for a, b in zip(timed, timed[1:])):
            print(f"  line {i + 1}: marks out of order; skipped, re-mark it in the app")
            continue
        # The website shows a line's timed words in place of its text, so import a line only when its
        # words spell out its current lyrics exactly (lyrics corrected after timing would bring old words back).
        current_text = (lines[i].get("coptic") or "").split()
        line_text = written_words(out)
        if line_text != current_text:
            diff = next((k for k, (a, b) in enumerate(zip(line_text, current_text)) if a != b), min(len(line_text), len(current_text)))
            print(f"  line {i + 1}: its words differ from the lyrics from word {diff + 1}; skipped, re-time it after updating the app")
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
            print(f"  line {i + 1}: {describe(out)}")
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
