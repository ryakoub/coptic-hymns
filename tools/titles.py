#!/usr/bin/env python3
"""Hymn titles in Coptic, English and Arabic, as one spreadsheet to review and edit.

  python3 tools/titles.py export ~/Downloads/hymn-titles.csv    # every hymn's titles now
  python3 tools/titles.py import ~/Downloads/hymn-titles.csv    # write back the cells that changed

One row per hymn text (other tunes and languages of it take their titles from it). Columns: id, where
(the hymn's folder), english, coptic, arabic. Open the file in Numbers or Excel, change any cells, and
export it as CSV again (UTF-8). Empty cells are left as they are; to clear a title, write a single "-".
The titles go into each hymn's info.json "titles"; then run tools/build_catalog.py.
"""
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
LANGS = ("english", "coptic", "arabic")


def text_folders():
    """Folders that hold a hymn's own text (not another tune or language of one), by id."""
    out = {}
    for lyrics in sorted(CONTENT.rglob("lyrics.json")):
        folder = lyrics.parent
        info_path = folder / "info.json"
        info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}
        if info.get("text", folder.name) == folder.name:
            out[folder.name] = (folder, info_path, info)
    return out


def current_titles(info):
    titles = dict(info.get("titles") or {})
    legacy = info.get("title", "")
    if legacy:
        coptic = any("Ⲁ" <= ch <= "⳿" or "Ϣ" <= ch <= "ϯ" for ch in legacy)
        titles.setdefault("coptic" if coptic else "english", legacy)
    return titles


def export(path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:      # the BOM lets Excel read Arabic and Coptic
        w = csv.writer(f)
        w.writerow(["id", "where", *LANGS])
        n = 0
        for hid, (folder, _, info) in sorted(text_folders().items(), key=lambda kv: kv[1][0].as_posix()):
            t = current_titles(info)
            w.writerow([hid, folder.parent.relative_to(CONTENT).as_posix(), *(t.get(k, "") for k in LANGS)])
            n += 1
    print(f"wrote {n} hymns to {path}")


def import_(path):
    folders = text_folders()
    changed = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            hid = (row.get("id") or "").strip()
            if hid not in folders:
                if hid:
                    print(f"  {hid}: no such hymn, skipped")
                continue
            folder, info_path, info = folders[hid]
            titles = current_titles(info)
            new = dict(titles)
            for k in LANGS:
                v = (row.get(k) or "").strip()
                if v == "-":
                    new.pop(k, None)
                elif v:
                    new[k] = v
            if new != titles:
                info["titles"] = {k: new[k] for k in LANGS if k in new}
                info.pop("title", None)
                info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                changed += 1
                print(f"  {hid}: " + "; ".join(f"{k} → {new.get(k, '(none)')}" for k in LANGS if new.get(k) != titles.get(k)))
    print(f"{changed} hymn(s) updated" + ("; now run tools/build_catalog.py" if changed else ""))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("export", "import"):
        sys.exit(__doc__)
    (export if sys.argv[1] == "export" else import_)(sys.argv[2])
