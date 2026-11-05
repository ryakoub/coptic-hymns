#!/usr/bin/env python3
"""Merge the names worked out in the hymn-names sheet into catalog/hymn-names.json.

Each hymn gets two lines in the app's lists: its name (the one the church knows it by) and a second line saying
what it says, with its Coptic and Arabic names. build_catalog.py puts the name in the text's English title, the
Coptic and Arabic names in its other titles, and the second line in its "subtitle".

Usage:
  python3 tools/import_hymn_names.py "hymn-names (Psalmody).csv" --book "Holy Psalmody"
Rows are matched to texts by their Recording column: the text that recording belongs to (its info.json "text",
or the recording itself when it is its own text), else by the id column. Only rows of the given book (or all,
without --book) are taken, and with --rows only those orders (e.g. --rows 28-39,48-54).
Save the sheet from Excel as "CSV UTF-8" so the Coptic and Arabic survive.
"""
import argparse, csv, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = ROOT / "catalog" / "hymn-names.json"

def tidy(s):
    return re.sub(r"\s+", " ", (s or "").strip())

def plain(s):
    """The second line as plain words: no quotes around it, no "…" at its end."""
    s = tidy(s)
    s = re.sub(r"(\.\.\.|…)$", "", s).strip()
    if len(s) > 1 and s[0] in "\"“" and s[-1] in "\"”":
        s = s[1:-1]
    return re.sub(r"(\.\.\.|…)$", "", s).strip()

def text_of_recording():
    """Recording id -> the text it is a version of."""
    out = {}
    for f in (ROOT / "content").glob("**/info.json"):
        info = json.loads(f.read_text(encoding="utf-8"))
        out[f.parent.name] = info.get("text") or f.parent.name
    return out

def orders(spec):
    keep = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        keep.update(range(int(a), int(b or a) + 1))
    return keep

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheet")
    ap.add_argument("--book")
    ap.add_argument("--rows")
    a = ap.parse_args()
    texts = text_of_recording()
    keep = orders(a.rows) if a.rows else None
    rows = list(csv.DictReader(open(a.sheet, encoding="utf-8-sig")))
    names = json.loads(NAMES.read_text(encoding="utf-8")) if NAMES.exists() else {}
    n = 0
    for r in rows:
        if a.book and r.get("Book") != a.book:
            continue
        if keep is not None and int(r["Order"]) not in keep:
            continue
        name, line = tidy(r.get("Proposed name (big line)")), plain(r.get("Proposed second line (small)"))
        if not name:
            continue
        coptic, arabic = tidy(r.get("Coptic first words")), tidy(r.get("Arabic name"))
        # The Coptic column only when it's in Coptic letters (some rows hold the words in Latin letters, as a reminder).
        coptic = coptic if re.search(r"[\u2C80-\u2CFF\u03E2-\u03EF]", coptic) else ""
        coptic = re.sub(r"[\s:.]*(\.\.\.|…)$", "", coptic)    # the first words, without the sheet's "…" after them
        tid = texts.get(tidy(r.get("Recording")), r["id"])
        names[tid] = {"name": name, **({"says": line} if line else {}),
                          **({"coptic": coptic} if coptic else {}), **({"arabic": arabic} if arabic else {})}
        n += 1
    NAMES.write_text(json.dumps(dict(sorted(names.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{n} names taken; {len(names)} in {NAMES.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
