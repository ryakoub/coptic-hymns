#!/usr/bin/env python3
"""Add the English as sung in a recording (e.g. St. Antony Monastery's) to a hymn, as each line's "sung" English.

  python3 tools/add_sung_english.py first-hoos https://tasbeha.org/hymn_library/view/1237 [--dry-run]

Tasbeha's page for the sung version has the Coptic with the sung English under each line. Its lines are
matched to the hymn's by their Coptic words (verses may be grouped differently), and the English of the
lines matching each verse becomes that verse's "sung": {"english": …}. The literal translation stays in
"translations". The app shows the sung English and times English recordings against it.
Only lines whose sung English differs from the translation are written. --dry-run shows the differences.
"""
import argparse, difflib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_hymn import fetch, parse_hymn, CONTENT, ROOT   # noqa: E402
from add_transliteration import norm                    # noqa: E402


def words_only(text):
    return [w.strip(".,;:!?\"'“”‘’()").lower() for w in text.split() if w.strip(".,;:!?\"'“”‘’()")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("hymn")
    ap.add_argument("url")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", action="store_true", help="print each changed line, old and new")
    args = ap.parse_args()

    hits = [p for p in CONTENT.rglob("lyrics.json") if p.parent.name == args.hymn]
    if len(hits) != 1:
        sys.exit(f"{args.hymn}: expected one folder with that name, found {len(hits)}")
    path = hits[0]
    lines = json.loads(path.read_text(encoding="utf-8"))

    _, verses, _ = parse_hymn(fetch(args.url).decode("utf-8", "replace"))
    theirs = [l for v in verses for l in v]                       # their lines, in order
    their_words = [(k, norm(w)) for k, l in enumerate(theirs) for w in l["coptic"].split()]
    our_words = [(i, norm(w)) for i, l in enumerate(lines) if not (l.get("label") or l.get("static"))
                 for w in (l.get("coptic") or "").split()]

    m = difflib.SequenceMatcher(None, [w for _, w in our_words], [w for _, w in their_words], autojunk=False)
    votes = {}                                                    # their line -> {our line: matched words}
    for a, b, n in m.get_matching_blocks():
        for k in range(n):
            ours, theirs_line = our_words[a + k][0], their_words[b + k][0]
            votes.setdefault(theirs_line, {}).setdefault(ours, 0)
            votes[theirs_line][ours] += 1

    sung = {}                                                     # our line -> their English, in order
    for k, l in enumerate(theirs):
        if k in votes and l["english"]:
            ours = max(votes[k], key=votes[k].get)
            sung.setdefault(ours, []).append(l["english"])

    changed, same, missing = [], 0, []
    for i, l in enumerate(lines):
        if l.get("label") or l.get("static"):
            continue
        if i not in sung:
            missing.append(i + 1)
            continue
        text = " ".join(sung[i])
        current = (l.get("translations") or {}).get("english", "")
        # Differences of punctuation alone don't count (and would unsettle existing timings).
        if words_only(text) == words_only(current):
            same += 1
            l.get("sung", {}).pop("english", None)
            continue
        if (l.get("sung") or {}).get("english") != text:
            changed.append((i + 1, current, text))
            l.setdefault("sung", {})["english"] = text

    print(f"{args.hymn}: {len(changed)} lines get the sung English, {same} already match"
          + (f", no sung English found for lines {missing}" if missing else ""))
    if args.show:
        for n, old, new in changed:
            print(f"  line {n}:\n    translation: {old}\n    sung:        {new}")
    if args.dry_run or not changed:
        return
    for l in lines:
        if "sung" in l and not l["sung"]:
            del l["sung"]
    path.write_text(json.dumps(lines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
