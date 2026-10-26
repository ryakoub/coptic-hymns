#!/usr/bin/env python3
"""Adds the inventory's new hymns for some collections to content/hymns/, one YouTube download at a time.

  python3 tools/inventory/add_from_inventory.py annual praises [--dry-run]

Each hymn takes its words from tasbeha.json:
  "view": N      a Tasbeha page, added with tools/add_hymn.py
  "text": id     another recording (tune) of a text already in content/; its lyrics stay empty until timed
  "words": {…}   a short text given by hand
Hymns without a confirmed entry are skipped and listed. Folders that exist already are left alone.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from add_hymn import get_audio, duration  # noqa: E402

# Names for recordings that are another tune of a text, and for the first recording of such a text.
TUNES = {
    "distribution-annual-psalm-150": "With Psalm 150",
    "je-nai-nan": "Je Nai Nan only",
    "tenoueh-ensok-kiahk": "Kiahk tune",
    "ten-oosht-evol-basil": "St. Basil Liturgy",
    "ten-oosht-evol-gregory": "St. Gregory Liturgy",
    "ten-oosht-evol-vespers-matins": "Vespers and Matins",
    "gospel-response-vespers-annual": "Vespers",
    "gospel-response-matins-annual": "Matins",
    "sotees-ameen-major": "Long",
    "ti-shouri-major": "Long",
    "praxis-response-annual-major": "Long",
}
PAUSE = 8   # seconds between YouTube downloads, so YouTube doesn't start refusing


def folder_of(hid):
    found = [p.parent for p in (ROOT / "content").rglob("info.json") if p.parent.name == hid]
    return found[0] if found else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("collections", nargs="+", help="collection ids, e.g. annual praises")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    hymns = json.load(open(ROOT / "docs/app/hymn-inventory.json"))
    words = json.load(open(HERE / "tasbeha.json"))
    todo = [h for h in hymns if h["status"] == "new" and h["places"][0]["collection"] in args.collections]
    # texts before the recordings that point to them
    todo.sort(key=lambda h: "text" in words.get(h["key"], {}))
    skipped, added, failed = [], [], []
    for h in todo:
        key, w, v = h["key"], words.get(h["key"]), h["video"]
        if not w or not w.get("sure") or not (w.get("view") or w.get("text") or w.get("words")):
            skipped.append(key); continue
        if folder_of(key):
            print(f"{key}: already in content/, left alone"); continue
        if w.get("text") and not folder_of(w["text"]) and not args.dry_run:
            skipped.append(f"{key} (its text {w['text']} is missing)"); continue
        places = [p["id"] for p in h["places"]]
        print(f"{key}: {v['url']}  →  {', '.join(places)}")
        if args.dry_run:
            continue
        if added: time.sleep(PAUSE)
        if w.get("view"):
            cmd = [sys.executable, str(ROOT / "tools/add_hymn.py"), f"https://tasbeha.org/hymn_library/view/{w['view']}",
                   "--id", key, "--coptic", v["url"]] + [a for p in places for a in ("--place", p)]
            if subprocess.run(cmd).returncode != 0:
                failed.append(key); continue
            folder = ROOT / "content/hymns" / key
            info = json.load(open(folder / "info.json"))
        else:
            folder = ROOT / "content/hymns" / key
            try:
                audio = get_audio(v["url"], "", folder)
            except Exception as e:
                import shutil; shutil.rmtree(folder, ignore_errors=True)
                print(f"{key}: {e}"); failed.append(key); continue
            info = {"title": h["english"], "titles": {"english": h["english"], "arabic": h["arabic"]}, "youtube": v["url"], "places": places}
            if w.get("text"):
                info["text"] = w["text"]
                lyrics = []
            else:
                t = w["words"]
                info["titles"]["coptic"] = t["coptic"]
                lyrics = [{"coptic": t["coptic"], "translations": {"english": t["english"], "arabic": t["arabic"]},
                           "transliterations": {"english": t["transliteration"]}}]
            (folder / "lyrics.json").write_text(json.dumps(lyrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"added {folder.relative_to(ROOT)}: audio {audio.name} ({duration(audio)})")
        if key in TUNES:
            info["tune"] = {"english": TUNES[key]}
        info["mahragan"] = {k: v[k] for k in ("year", "stage", "level") if v.get(k)}
        if v.get("channel"): info["channel"] = v["channel"]
        (folder / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        added.append(key)
    print(f"\n{len(added)} added" + (f"; skipped (no confirmed words): {', '.join(skipped)}" if skipped else "")
          + (f"; FAILED: {', '.join(failed)}" if failed else ""))


if __name__ == "__main__":
    main()
