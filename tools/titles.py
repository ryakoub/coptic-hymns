#!/usr/bin/env python3
"""Every hymn's titles, places, kind and notes, as one spreadsheet to review and edit.

  python3 tools/titles.py export ~/Downloads/hymns.csv    # every recording as it is now
  python3 tools/titles.py import ~/Downloads/hymns.csv    # write back the cells that changed

One row per recording (a hymn folder). Columns:
  id, where   the folder (not editable)
  text        empty for a hymn with its own words; for another tune or language of a hymn, that hymn's id
  tune        the tune's name, shown on the hymn's tune switch (e.g. "St. Gregory Liturgy")
  kind        "recital" (quick, a syllable to a note: good for the words lighting up as they are sung) or
              "melismatic" (long notes on few words: better learned with a score or hand-made marks)
  pace        Coptic words sung per minute (not editable), a hint for kind: under 10 is melismatic, 25 and
              over recital
  english, coptic, arabic
              the titles; a tune or language takes its titles from its text, so edit them on that row
  places      where it appears, separated by ";", e.g. "annual/liturgy; holy-week/hymns"
              (collection/section, as in catalog/library.json; "praises/midnight" is short for "praises/midnight-praises").
              "annual/liturgy@30" puts it at position 30 in that place only.
  order       its position in its places, lower first (steps of 10 leave room in between)
  group       its sub-folder within its places, e.g. "Hoos" or "Hoos | الهوسات" (English | Arabic); hymns with the same
              group are shown together, in the order of the first of them
  intro, intro_arabic
              a short introduction shown above the hymn's words in the app ("About this hymn"): what it is,
              when and how it is sung (on the hymn's own row, as the titles)
  notes       your notes on the hymn and its words (kept in info.json "notes", not shown in the app yet)
Open the file in Numbers or Excel, change any cells, and export it as CSV again (UTF-8). Empty cells are left as
they are; to clear one, write a single "-". Places that are not in the library are reported and not written.
The changes go into each folder's info.json; then run tools/build_catalog.py.
"""
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
LANGS = ("english", "coptic", "arabic")
COLUMNS = ["id", "where", "text", "tune", "kind", "pace", *LANGS, "places", "order", "group", "intro", "intro_arabic", "notes"]
KINDS = ("recital", "melismatic")


def folders():
    """Every recording folder by id: (folder, info.json path, info). Hymns with notation are not recordings."""
    out = {}
    for info_path in sorted(CONTENT.rglob("info.json")):
        folder = info_path.parent
        if not (folder / "lyrics.json").exists():
            continue
        out[folder.name] = (folder, info_path, json.loads(info_path.read_text(encoding="utf-8")))
    return out


def current_titles(info):
    titles = dict(info.get("titles") or {})
    legacy = info.get("title", "")
    if legacy:
        coptic = any("Ⲁ" <= ch <= "⳿" or "Ϣ" <= ch <= "ϯ" for ch in legacy)
        titles.setdefault("coptic" if coptic else "english", legacy)
    return titles


def group_cell(info):
    g = info.get("group")
    if not g:
        return ""
    if isinstance(g, str):
        return g
    return " | ".join(v for v in (g.get("english"), g.get("arabic")) if v)


def places_cell(info):
    cells = []
    for p in info.get("places", []):
        cells.append(p if isinstance(p, str) else f"{p['place']}@{p['order']}" if p.get("order") is not None else p["place"])
    return "; ".join(cells)


def parse_places(cell):
    out = []
    for part in (x.strip() for x in cell.split(";")):
        if not part:
            continue
        place, _, order = part.partition("@")
        out.append({"place": place.strip(), "order": int(order)} if order.strip() else place.strip())
    return out


def library_places():
    """Every collection/section id, and the short forms that name one section unambiguously."""
    lib = json.loads((ROOT / "catalog/library.json").read_text(encoding="utf-8"))
    full = {f"{c['id']}/{s.get('service') or s.get('id')}" for g in lib["groups"] for c in g["collections"] for s in c["sections"]}
    return full


def known(place, full):
    if place in full:
        return True
    c, _, s = place.partition("/")
    return len([p for p in full if p.startswith(f"{c}/{s}")]) == 1


def paces():
    """Coptic words per minute of each recording with its own words, from the catalog's durations."""
    try:
        index = json.loads((ROOT / "catalog/v1/index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    durations = {r["id"]: r.get("duration") for r in index.get("recordings", [])}
    out = {}
    for hid, (folder, _, info) in folders().items():
        if info.get("text") or not durations.get(hid):
            continue
        lines = json.loads((folder / "lyrics.json").read_text(encoding="utf-8"))
        words = sum(len(l.get("coptic", "").split()) for l in lines if l.get("coptic") and not l.get("label"))
        if words:
            out[hid] = round(words / (durations[hid] / 60), 1)
    return out


def export(path):
    pace = paces()
    with open(path, "w", newline="", encoding="utf-8-sig") as f:      # the BOM lets Excel read Arabic and Coptic
        w = csv.writer(f)
        w.writerow(COLUMNS)
        rows = sorted(folders().items(), key=lambda kv: (kv[1][2].get("text", kv[0]), "text" in kv[1][2], kv[0]))
        for hid, (folder, _, info) in rows:
            t = current_titles(info)
            w.writerow([hid, folder.parent.relative_to(CONTENT).as_posix(), info.get("text", ""),
                        (info.get("tune") or {}).get("english", ""), info.get("kind", ""), pace.get(hid, ""),
                        *(t.get(k, "") for k in LANGS), places_cell(info), info.get("order", ""), group_cell(info),
                        (info.get("intro") or {}).get("english", ""), (info.get("intro") or {}).get("arabic", ""), info.get("notes", "")])
    print(f"wrote {len(rows)} recordings to {path}")


def import_(path):
    all_folders = folders()
    full = library_places()
    changed = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            hid = (row.get("id") or "").strip()
            if hid not in all_folders:
                if hid:
                    print(f"  {hid}: no such hymn, skipped")
                continue
            folder, info_path, info = all_folders[hid]
            before = json.dumps(info, ensure_ascii=False, sort_keys=True)
            notes = []

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
                if new.get("english"):
                    info["title"] = new["english"]          # the website still reads "title"
                notes += [f"{k} → {new.get(k, '(none)')}" for k in LANGS if new.get(k) != titles.get(k)]

            tune = (row.get("tune") or "").strip()
            if tune == "-":
                info.pop("tune", None)
            elif tune and tune != (info.get("tune") or {}).get("english"):
                info["tune"] = {**(info.get("tune") or {}), "english": tune}
                notes.append(f"tune → {tune}")

            kind = (row.get("kind") or "").strip().lower()
            if kind == "-":
                info.pop("kind", None)
            elif kind and kind != info.get("kind"):
                if kind in KINDS:
                    info["kind"] = kind
                    notes.append(f"kind → {kind}")
                else:
                    print(f"  {hid}: kind {kind!r} is not recital or melismatic, left as it was")

            group = (row.get("group") or "").strip()
            if group == "-":
                info.pop("group", None)
            elif group and group != group_cell(info):
                english, _, arabic = (x.strip() for x in group.partition("|"))
                info["group"] = {k: v for k, v in (("english", english), ("arabic", arabic)) if v}
                notes.append(f"group → {group}")

            intro = dict(info.get("intro") or {})
            for col, lang in (("intro", "english"), ("intro_arabic", "arabic")):
                v = (row.get(col) or "").strip()
                if v == "-":
                    intro.pop(lang, None)
                elif v:
                    intro[lang] = v
            if intro != (info.get("intro") or {}):
                if intro: info["intro"] = intro
                else: info.pop("intro", None)
                notes.append("intro updated")

            note = (row.get("notes") or "").strip()
            if note == "-":
                info.pop("notes", None)
            elif note and note != info.get("notes"):
                info["notes"] = note
                notes.append("notes updated")

            cell = (row.get("places") or "").strip()
            if cell == "-":
                info.pop("places", None)
            elif cell and cell != places_cell(info):
                places = parse_places(cell)
                bad = [p if isinstance(p, str) else p["place"] for p in places]
                bad = [p for p in bad if not known(p, full)]
                if bad:
                    print(f"  {hid}: not in the library, places left as they were: {', '.join(bad)}")
                else:
                    info["places"] = places
                    notes.append(f"places → {cell}")

            order = (row.get("order") or "").strip()
            if order == "-":
                info.pop("order", None)
            elif order and order != str(info.get("order", "")):
                if order.lstrip("-").isdigit():
                    info["order"] = int(order)
                    notes.append(f"order → {order}")
                else:
                    print(f"  {hid}: order {order!r} is not a number, left as it was")

            if json.dumps(info, ensure_ascii=False, sort_keys=True) != before:
                info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                changed += 1
                print(f"  {hid}: " + "; ".join(notes))
    print(f"{changed} hymn(s) updated" + ("; now run tools/build_catalog.py" if changed else ""))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("export", "import"):
        sys.exit(__doc__)
    (export if sys.argv[1] == "export" else import_)(sys.argv[2])
