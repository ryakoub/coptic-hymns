#!/usr/bin/env python3
"""Copy Tasbeha's word-by-word transliteration into a hymn's lyrics.json, without touching anything else.

  python3 tools/add_transliteration.py first-hoos https://tasbeha.org/hymn_library/view/103 [--dry-run]

The hymn's Coptic words are matched to Tasbeha's across the whole hymn (verses may be grouped differently),
ignoring accents, punctuation and case. A line gets "transliterations": {"english": …} only when every one
of its words found its match, so the app can show one transliteration per Coptic word. Timings, corrections
and translations stay as they are. Lines that don't match are listed.
"""
import argparse, difflib, json, re, sys, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_hymn import fetch, parse_hymn, CONTENT, ROOT   # noqa: E402


def norm(word):
    w = unicodedata.normalize("NFD", word)
    w = "".join(c for c in w if not unicodedata.combining(c) and c not in "̀:.,;!?\"'()+·")
    return w.lower()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("hymn", help="hymn folder name, e.g. first-hoos")
    ap.add_argument("url", help="its Tasbeha page, e.g. https://tasbeha.org/hymn_library/view/103")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    hits = [p for p in CONTENT.rglob("lyrics.json") if p.parent.name == args.hymn]
    if len(hits) != 1:
        sys.exit(f"{args.hymn}: expected one folder with that name, found {len(hits)}")
    path = hits[0]
    lines = json.loads(path.read_text(encoding="utf-8"))

    _, verses, _ = parse_hymn(fetch(args.url).decode("utf-8", "replace"))
    theirs = []                                   # (normalized coptic, transliteration) per Tasbeha word
    for verse in verses:
        for l in verse:
            cw, tw = l["coptic"].split(), l["translit"].split()
            if len(cw) == len(tw):
                theirs += list(zip((norm(w) for w in cw), tw))
    if not theirs:
        sys.exit(f"{args.url}: no word-by-word transliteration found")

    ours = []                                     # (line index, normalized coptic) per word of ours
    for i, l in enumerate(lines):
        if l.get("label") or l.get("static"):
            continue
        ours += [(i, norm(w)) for w in (l.get("coptic") or "").split()]

    matcher = difflib.SequenceMatcher(None, [w for _, w in ours], [w for w, _ in theirs], autojunk=False)
    found = {}
    for a, b, n in matcher.get_matching_blocks():
        for k in range(n):
            found[a + k] = theirs[b + k][1]

    done, missed = 0, []
    pos = 0
    for i, l in enumerate(lines):
        if l.get("label") or l.get("static"):
            continue
        count = len((l.get("coptic") or "").split())
        idx = range(pos, pos + count)
        pos += count
        if count and all(k in found for k in idx):
            l.setdefault("transliterations", {})["english"] = " ".join(found[k] for k in idx)
            done += 1
        elif count:
            missed.append(i + 1)

    print(f"{args.hymn}: transliteration for {done} of {done + len(missed)} lines" + (f"; not matched: lines {missed}" if missed else ""))
    if args.dry_run or not done:
        return
    path.write_text(json.dumps(lines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
