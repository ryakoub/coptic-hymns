#!/usr/bin/env python3
"""Build the app catalog from the hymn folders under content/ and the library in catalog/library.json.

The app works with three layers (see docs/app/data-model.md):
  text       the words, once: Coptic, translations, transliterations, line by line
  recording  one tune of a text: its audio and its own line and word timings
  library    where hymns appear: seasons, services, occasions, programs

Today each folder under content/ holds one recording with its text inside lyrics.json. This script
splits them for the app and leaves content/ and the website untouched:

  catalog/v1/index.json            library, texts and recordings, with file sizes and fingerprints
  catalog/v1/texts/<text>.json     the words of each text
  catalog/v1/timings/<rec>.json    the timings of each recording, pointing at the text's line ids

A folder becomes another tune of an existing text by naming it in info.json:
  "text": "<text id>", "tune": { "english": "Lent tune" }
and can describe its tune with "style" (major, medium, minor), "mode" (annual, festal, lenten, joyful)
and "kind" (recital, melismatic). "language": "english" (or "arabic") marks a recording sung in that
language: its word timings follow the line's sung text in it ("sung": {"english": …}), or else its translation.

A folder places itself in the library with "places": ["resurrection/liturgy", "praises/midnight-praises"]
(collection id / service or section id, as in catalog/library.json; an unambiguous part of the section
id is enough, e.g. "praises/midnight"). "order": 10 sets its position in those sections (lower first);
for a different position per place, write {"place": "praises/midnight", "order": 10}. Numbered hymns
come first in their order, then the rest alphabetically, all after any listed in library.json.

Usage:
  python3 tools/build_catalog.py            # write the catalog and print a report
  python3 tools/build_catalog.py --check    # report only, exit 1 on errors
"""
import argparse, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
LIBRARY = ROOT / "catalog" / "library.json"
OUT = ROOT / "catalog" / "v1"
BASE_URL = "https://www.copticchanter.com/"
SCHEMA = 2

COPTIC = re.compile("[Ⲁ-⳿Ϣ-ϯ]")
AUDIO_PREFERENCE = ["audio.seek.m4a", "audio.m4a", "audio.mp3"]  # same order as the web player
LINE_TEXT_KEYS = ("coptic", "translations", "transliterations", "sung", "role", "label", "static")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def audio_duration(path):
    """Seconds, via macOS afinfo; None where afinfo is unavailable."""
    try:
        out = subprocess.run(["afinfo", str(path)], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"estimated duration:\s*([\d.]+)", out)
    return round(float(m.group(1)), 2) if m else None


def site_titles():
    """id -> title from the website's hymn list (a JS object literal)."""
    src = (ROOT / "js" / "hymns-data.js").read_text(encoding="utf-8")
    start = src.index("{", src.index("window.HYMNS_DATA"))
    body = src[start: src.index("\n};", start) + 2]
    body = re.sub(r"//[^\n]*", "", body)
    body = re.sub(r"\b(id|title)\s*:", r'"\1":', body)
    body = re.sub(r",(\s*[}\]])", r"\1", body)
    data = json.loads(body)
    return {h["id"]: h["title"] for group in data.values() for level in group.values() for h in level}


def norm(s):
    return " ".join((s or "").split())


class Build:
    def __init__(self):
        self.problems = []
        self.titles_from_site = site_titles()
        self.texts = {}        # text id -> {"meta":…, "lines": [...]}
        self.recordings = {}   # recording id -> catalog entry (without files yet)
        self.timings = {}      # recording id -> timing document
        self.out_files = {}    # relative path under catalog/v1 -> bytes
        self.places = {}       # recording id -> ["collection/section", …] from its info.json

    def warn(self, rid, msg): self.problems.append(("warn", rid, msg))
    def error(self, rid, msg): self.problems.append(("error", rid, msg))

    def titles_for(self, rid, info):
        titles = dict(info.get("titles") or {})
        legacy = info.get("title", "")
        if legacy:
            titles.setdefault("coptic" if COPTIC.search(legacy) else "english", legacy)
        site = self.titles_from_site.get(rid, "")
        if site:
            titles.setdefault("coptic" if COPTIC.search(site) else "english", site)
        return titles

    def read_folder(self, folder):
        rid = folder.name
        info = json.loads((folder / "info.json").read_text(encoding="utf-8")) if (folder / "info.json").exists() else {}
        lines = json.loads((folder / "lyrics.json").read_text(encoding="utf-8"))
        return rid, info, lines

    def add_text(self, tid, info, lines, rid):
        """Text lines get stable ids l1, l2, … in order; timings refer to them."""
        tlines = []
        for i, l in enumerate(lines, 1):
            t = {"id": f"l{i}"}
            for k in LINE_TEXT_KEYS:
                if l.get(k):
                    t[k] = l[k]
            if l.get("stanzas"):
                t["stanzas"] = [{"coptic": s.get("coptic", "")} for s in l["stanzas"]]
            tlines.append(t)
        pending = not any(COPTIC.search(l.get("coptic", "")) for l in lines)
        titles = self.titles_for(rid, info)
        if "english" not in titles:
            self.warn(tid, "no English title")
        if pending:
            self.warn(tid, "lyrics not added yet")
        self.texts[tid] = {"id": tid, "titles": titles, "tags": info.get("tags", []), "pending": pending, "lines": tlines}

    def add_recording(self, folder, rid, info, lines):
        tid = info.get("text", rid)
        text = self.texts[tid]
        by_coptic = {}
        for t in text["lines"]:
            by_coptic.setdefault(norm(t.get("coptic")), t["id"])
        own_text = tid == rid
        segments, prev = [], -1
        sung = [l for l in lines if not l.get("label") and not l.get("static")]
        for i, l in enumerate(lines, 1):
            if l.get("label") or l.get("static") or not isinstance(l.get("start"), (int, float)):
                continue
            # A recording of a shared text may name the line directly ("line": "l3"), as timings imported
            # from the app do, especially for recordings sung in another language.
            line_id = l.get("line") if l.get("line") else f"l{i}" if own_text else by_coptic.get(norm(l.get("coptic")))
            if l.get("line") and l["line"] not in {t["id"] for t in text["lines"]}:
                self.error(rid, f"entry {i} names line {l['line']}, which is not in text {tid}")
                continue
            if not line_id:
                self.error(rid, f"line {i} is not in text {tid}")
                continue
            if l["start"] < prev:
                self.error(rid, f"line {i} starts before the line above it")
            prev = l["start"]
            seg = {"line": line_id, "start": l["start"]}
            if l.get("stanzas"):
                seg["stanzas"] = [s.get("start") for s in l["stanzas"]]
            if l.get("words"):
                ws = l["words"]
                timed = [w["start"] for w in ws if w.get("start") is not None]
                if any(b < a for a, b in zip(timed, timed[1:])):
                    self.error(rid, f"line {i}: words out of order")
                # Estimated times are for the website; the app estimates again from the marks.
                seg["words"] = [{"text": w.get("text", ""), "start": None if w.get("estimated") else w.get("start"), "end": w.get("end"),
                                 **({"trailingSpace": False} if w.get("trailingSpace") is False else {})} for w in ws]
            segments.append(seg)
        if not text["pending"] and len(segments) < len(sung):
            self.warn(rid, f"{len(sung) - len(segments)} of {len(sung)} lines have no start time")

        audio = next((folder / n for n in AUDIO_PREFERENCE if (folder / n).exists()), None)
        if audio is None:
            self.error(rid, "no audio file")
        self.timings[rid] = {"recording": rid, "text": tid, "segments": segments}
        entry = {"id": rid, "text": tid, "duration": audio_duration(audio) if audio else None,
                 "timing": {"lines": len(segments), "words": sum(1 for s in segments if s.get("words")), "of": len(sung)},
                 "source": folder.relative_to(ROOT).as_posix() + "/"}
        if info.get("tune"):
            entry["tune"] = info["tune"]
        for key in ("youtube", "antiphonalGroup", "cantor", "style", "mode", "kind", "language", "source"):
            if key in info:
                entry[key] = info[key]
        if audio:
            entry["_audio"] = audio
        self.places[rid] = (info.get("places", []), info.get("order"))
        self.recordings[rid] = entry

    def file(self, rel, data):
        self.out_files[rel] = data
        return {"url": f"catalog/v1/{rel}", "bytes": len(data), "sha256": sha256_bytes(data)}

    def apply_places(self, library):
        """Add each recording to the library sections its info.json names, after any listed in library.json."""
        sections = {}
        for g in library["groups"]:
            for c in g["collections"]:
                for s in c.get("sections", []):
                    sections[f"{c['id']}/{s.get('service') or s.get('id')}"] = s
        placed = {}   # section id -> [(order, title, recording)]
        for rid, (places, default_order) in self.places.items():
            for place in places:
                order = default_order
                if isinstance(place, dict):
                    order = place.get("order", default_order)
                    place = place.get("place", "")
                if order is not None and not isinstance(order, (int, float)):
                    self.error(rid, f"order {order!r} is not a number")
                    order = None
                s = sections.get(place) or self.short_place(place, sections, rid)
                if s is None:
                    continue
                listed = [e if isinstance(e, str) else e.get("recording") for e in s["entries"]]
                if rid not in listed:
                    title = self.texts.get(self.recordings[rid]["text"], {}).get("titles", {})
                    placed.setdefault(id(s), (s, []))[1].append(
                        (order if order is not None else float("inf"), (title.get("english") or title.get("coptic") or rid).lower(), rid))
        # Numbered hymns in their order, then the rest alphabetically, after those listed in library.json.
        for s, items in placed.values():
            s["entries"].extend(rid for _, _, rid in sorted(items))

    def short_place(self, place, sections, rid):
        """Accept an unambiguous short form: "praises/midnight" for "praises/midnight-praises"."""
        collection, _, part = place.partition("/")
        matches = [k for k in sections if k.startswith(collection + "/") and part and part in k.split("/", 1)[1]]
        if len(matches) == 1:
            return sections[matches[0]]
        if matches:
            self.error(rid, f"places it in {place}, which could be any of: {', '.join(matches)}")
        else:
            self.error(rid, f"places it in {place}, which is not in the library")
        return None

    def check_library(self, library):
        used = set()
        for g in library["groups"]:
            for c in g["collections"]:
                for s in c.get("sections", []):
                    where = f"{c['id']} / {s.get('service') or s.get('id')}"
                    for e in s.get("entries", []):
                        rid = e if isinstance(e, str) else e.get("recording")
                        tid = None if isinstance(e, str) else e.get("text")
                        if rid not in self.recordings:
                            self.error(str(rid), f"listed in {where} but no such recording")
                        elif tid and self.recordings[rid]["text"] != tid:
                            self.error(rid, f"in {where} it is listed as text {tid}, but it sings {self.recordings[rid]['text']}")
                        used.add(rid)
        placed_texts = {self.recordings[r]["text"] for r in used if r in self.recordings}
        for rid in sorted(set(self.recordings) - used):
            # Another tune or language of a placed hymn is reached from that hymn, so it needs no place of its own.
            if self.recordings[rid]["text"] not in placed_texts:
                self.warn(rid, "not in the library yet")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report only; do not write the catalog")
    args = ap.parse_args()

    b = Build()
    folders = sorted({p.parent for p in CONTENT.rglob("lyrics.json")}, key=lambda p: p.name)
    seen, parsed = {}, []
    for folder in folders:
        if folder.name in seen:
            b.error(folder.name, f"same id as {seen[folder.name]}")
            continue
        seen[folder.name] = folder.relative_to(ROOT).as_posix()
        parsed.append((folder, *b.read_folder(folder)))
    # Texts first: a folder holds its own text unless info.json points at another one.
    for folder, rid, info, lines in parsed:
        if info.get("text", rid) == rid:
            b.add_text(rid, info, lines, rid)
    for folder, rid, info, lines in parsed:
        tid = info.get("text", rid)
        if tid not in b.texts:
            b.error(rid, f"names text {tid}, which does not exist")
            continue
        b.add_recording(folder, rid, info, lines)

    library = json.loads(LIBRARY.read_text(encoding="utf-8"))
    b.apply_places(library)
    b.check_library(library)

    texts_out = []
    for tid, t in sorted(b.texts.items()):
        lines = [l for l in t["lines"] if not l.get("label") and not l.get("static")]
        doc = json.dumps({"id": tid, "titles": t["titles"], "lines": t["lines"]}, ensure_ascii=False, indent=1).encode()
        texts_out.append({"id": tid, "titles": t["titles"], "tags": t["tags"], "pending": t["pending"],
                          "lines": len(lines),
                          "translations": sorted({k for l in lines for k, v in (l.get("translations") or {}).items() if v}),
                          "transliterations": sorted({k for l in lines for k, v in (l.get("transliterations") or {}).items() if v}),
                          "recordings": sorted(r for r, e in b.recordings.items() if e["text"] == tid),
                          "file": b.file(f"texts/{tid}.json", doc)})
    recordings_out = []
    for rid, e in sorted(b.recordings.items()):
        e = dict(e)
        audio = e.pop("_audio", None)
        files = [b.file(f"timings/{rid}.json", json.dumps(b.timings[rid], ensure_ascii=False, indent=1).encode())]
        if audio:
            files.append({"url": audio.relative_to(ROOT).as_posix(), "role": "audio", "bytes": audio.stat().st_size, "sha256": sha256_file(audio)})
        files[0]["role"] = "timing"
        e["files"] = files
        recordings_out.append(e)

    payload = {"schema": SCHEMA, "baseUrl": BASE_URL, "services": library["services"], "library": library["groups"],
               "texts": texts_out, "recordings": recordings_out}
    # The version changes only when content does, so the app can tell cheaply whether anything is new.
    payload = {"version": sha256_bytes(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode())[:16], **payload}

    total = sum(f["bytes"] for r in recordings_out for f in r["files"]) + sum(t["file"]["bytes"] for t in texts_out)
    shared = [t for t in texts_out if len(t["recordings"]) > 1]
    full = sum(1 for r in recordings_out if r["timing"]["of"] and r["timing"]["words"] == r["timing"]["of"])
    some = sum(1 for r in recordings_out if r["timing"]["words"]) - full
    print(f"{len(texts_out)} texts ({len(shared)} with several tunes), {len(recordings_out)} recordings, {total / 1048576:.0f} MB in total")
    print(f"word timings: {full} recordings complete, {some} partial, {len(recordings_out) - full - some} none")
    print(f"Arabic translation: {sum(1 for t in texts_out if 'arabic' in t['translations'])} of {len(texts_out)} texts")
    for level, rid, msg in sorted(b.problems, key=lambda p: (p[0] != "error", p[2], p[1])):
        print(f"  {level.upper():5} {rid}: {msg}")

    if args.check:
        sys.exit(1 if any(p[0] == "error" for p in b.problems) else 0)
    for sub in ("texts", "timings"):
        shutil.rmtree(OUT / sub, ignore_errors=True)
    for rel, data in b.out_files.items():
        (OUT / rel).parent.mkdir(parents=True, exist_ok=True)
        (OUT / rel).write_bytes(data)
    (OUT / "index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote catalog/v1/index.json, {len(texts_out)} texts and {len(recordings_out)} timings (version {payload['version']})")


if __name__ == "__main__":
    main()
