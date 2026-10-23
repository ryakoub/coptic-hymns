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
  python3 tools/build_catalog.py --drafts   # include hymns with notation marked "draft" (to try them locally)
"""
import argparse, datetime, hashlib, json, re, shutil, subprocess, sys
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


def sides(lines, group):
    """Which side of the choir sings each line (0 or 1), for colouring alternate verses as the website does.
    Lines with "side" given (from the books' marks) say so; otherwise verses alternate, `group` at a time
    (Aripsalin and the Psalis go by two). Headings and fixed lines have none."""
    explicit = any("side" in l for l in lines)
    out, n = [], 0
    for l in lines:
        if l.get("label") or l.get("static"):
            out.append(None)
            continue
        out.append(int(l.get("side", 0)) if explicit else (n // max(group, 1)) % 2)
        n += 1
    return out


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


def stanza_starts(line):
    """Each quarter's start: its own when given, else the time of its first word (marked or estimated).
    None when any quarter has no time, so the line simply has no quarters to light."""
    stanzas = line.get("stanzas") or []
    if not stanzas:
        return None
    starts = [s.get("start") for s in stanzas]
    if all(t is not None for t in starts):
        return starts
    words = line.get("words") or []
    written, current = [], None          # the start of each word as written (a split word starts at its first part)
    for w in words:
        if current is None:
            current = w.get("start")
        if w.get("trailingSpace") is not False:
            written.append(current)
            current = None
    k = 0
    for i, s in enumerate(stanzas):
        if starts[i] is None and k < len(written):
            starts[i] = written[k]
        k += len((s.get("coptic") or "").split())
    return starts if all(t is not None for t in starts) else None


class Build:
    def __init__(self):
        self.problems = []
        self.titles_from_site = site_titles()
        self.texts = {}        # text id -> {"meta":…, "lines": [...]}
        self.recordings = {}   # recording id -> catalog entry (without files yet)
        self.timings = {}      # recording id -> timing document
        self.out_files = {}    # relative path under catalog/v1 -> bytes
        self.places = {}       # recording id -> ["collection/section", …] from its info.json
        self.group_of = {}     # recording id -> {"english": …, "arabic": …}, its sub-folder in its sections
        self.kind_of = {}      # recording id -> its info.json "kind" (recital, melismatic, both)
        self.held_back = []    # melismatic recordings left out of their places until a score follows them

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
        side = sides(lines, int(info.get("antiphonalGroup", 1)))
        for i, l in enumerate(lines, 1):
            t = {"id": f"l{i}"}
            if side[i - 1] is not None:
                t["side"] = side[i - 1]
            for k in LINE_TEXT_KEYS:
                if l.get(k):
                    t[k] = l[k]
            # The app reads a label as plain text; an {"english", "arabic"} label would stop it opening the hymn.
            if isinstance(t.get("label"), dict):
                t["label"] = t["label"].get("english") or t["label"].get("arabic") or ""
                self.warn(tid, "a label in two languages is shown in English only")
            if l.get("stanzas"):
                t["stanzas"] = [{"coptic": s.get("coptic", "")} for s in l["stanzas"]]
            tlines.append(t)
        pending = not any(COPTIC.search(l.get("coptic", "")) for l in lines)
        titles = self.titles_for(rid, info)
        if "english" not in titles:
            self.warn(tid, "no English title")
        if pending:
            self.warn(tid, "lyrics not added yet")
        self.texts[tid] = {"id": tid, "titles": titles, "tags": info.get("tags", []), "pending": pending, "lines": tlines,
                           "links": info.get("links", []),
                           # A short introduction (what the hymn is, when it is sung), shown above its words.
                           "intro": {k: v for k, v in (info.get("intro") or {}).items() if k in ("english", "arabic") and v}}

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
            stanzas = stanza_starts(l)
            if stanzas:
                seg["stanzas"] = stanzas
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
        # "both": the hymn can be either, depending on the recording; that says nothing about this one.
        if entry.get("kind") == "both":
            del entry["kind"]
        if audio:
            entry["_audio"] = audio
        self.places[rid] = (info.get("places", []), info.get("order"))
        self.kind_of[rid] = info.get("kind")
        if info.get("group"):
            g = info["group"]
            self.group_of[rid] = {"english": g} if isinstance(g, str) else g
        self.recordings[rid] = entry

    def file(self, rel, data):
        self.out_files[rel] = data
        return {"url": f"catalog/v1/{rel}", "bytes": len(data), "sha256": sha256_bytes(data)}

    def notations(self, library):
        """Hymns with notation: content/notations/<id>/notation.json names a PDF (a score or hand-made marks),
        its recordings with the cursor's marks ([seconds, page from 1, x, y], x and y as fractions of the page),
        and "places": the collections listing it ("annual", or "annual/liturgy"). Each collection gets
        "notations": [ids]. A recording names its own "audio" file in the folder, or "recording": a hymn's
        recording id, to follow that recording's audio without another copy of it. "draft": true keeps the
        notation out of the catalog (until it is marked) unless the build is run with --drafts."""
        collections = {c["id"]: c for g in library["groups"] for c in g["collections"]}
        out = []
        for path in sorted((CONTENT / "notations").glob("*/notation.json")):
            nid, folder = path.parent.name, path.parent
            try:
                n = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                self.error(nid, f"notation.json: {e}")
                continue
            if n.get("draft") and not getattr(self, "drafts", False):
                self.warn(nid, "draft: left out of the catalog")
                continue
            pdf = folder / n.get("pdf", "notation.pdf")
            if not pdf.exists():
                self.error(nid, f"no PDF {pdf.name}")
                continue
            ref = lambda f, role: {"url": f.relative_to(ROOT).as_posix(), "role": role, "bytes": f.stat().st_size, "sha256": sha256_file(f)}
            recs = []
            for i, r in enumerate(n.get("recordings", []), 1):
                if r.get("recording"):
                    # The audio of a hymn's recording, the same file the hymn plays.
                    hymn_audio = (self.recordings.get(r["recording"]) or {}).get("_audio")
                    audio_ref = ref(hymn_audio, "audio") if hymn_audio else None
                    if not audio_ref:
                        self.error(nid, f"recording {i}: no hymn recording {r['recording']!r} with audio")
                        continue
                else:
                    audio = folder / r.get("audio", "")
                    if not r.get("audio") or not audio.exists():
                        self.error(nid, f"recording {i}: no audio file {r.get('audio')!r}")
                        continue
                    audio_ref = ref(audio, "audio")
                points = sorted(r.get("points", []))
                if any(len(p) != 4 or p[1] < 1 for p in points):
                    self.error(nid, f"recording {i}: marks are [seconds, page from 1, x, y]")
                    continue
                recs.append({"id": f"{nid}-{i}", "name": r.get("name") or f"Recording {i}",
                             **({"cantor": r["cantor"]} if r.get("cantor") else {}), "audio": audio_ref, "points": points})
            entry = {"id": nid, "titles": n.get("titles", {}), "kind": n.get("kind", "score"), "pdf": ref(pdf, "pdf"),
                     "recordings": recs, **({"credit": n["credit"]} if n.get("credit") else {}),
                     **({"cursor": n["cursor"]} if n.get("cursor") else {})}
            if "english" not in entry["titles"]:
                self.warn(nid, "notation without an English title")
            entry["version"] = sha256_bytes(json.dumps(entry, sort_keys=True, ensure_ascii=False).encode())[:16]
            for place in n.get("places", []):
                c = collections.get(place.split("/")[0])
                if c is None:
                    self.error(nid, f"places it in {place}, which is not in the library")
                    continue
                c.setdefault("notations", []).append(nid)
            out.append(entry)
        return out

    def apply_places(self, library):
        """Add each recording to the library sections its info.json names, after any listed in library.json."""
        sections = {}
        for g in library["groups"]:
            for c in g["collections"]:
                for s in c.get("sections", []):
                    sections[f"{c['id']}/{s.get('service') or s.get('id')}"] = s
        # A melismatic hymn is learned with its score: until a hymn with notation follows its recording, it stays out
        # of the seasons' lists (it is still in the catalog, and in programs that list it in library.json).
        followed = set()
        for path in (CONTENT / "notations").glob("*/notation.json"):
            try:
                n = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not n.get("draft"):
                followed |= {r["recording"] for r in n.get("recordings", []) if r.get("recording")}
        placed = {}   # section id -> [(order, title, recording)]
        in_places = {}   # recording id -> the sections its own "places" put it in (its group applies there)
        for rid, (places, default_order) in self.places.items():
            if places and self.kind_of.get(rid) == "melismatic" and rid not in followed:
                self.held_back.append(rid)
                continue
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
                in_places.setdefault(rid, set()).add(id(s))
                listed = [e if isinstance(e, str) else e.get("recording") for e in s["entries"]]
                if rid not in listed:
                    title = self.texts.get(self.recordings[rid]["text"], {}).get("titles", {})
                    placed.setdefault(id(s), (s, []))[1].append(
                        (order if order is not None else float("inf"), (title.get("english") or title.get("coptic") or rid).lower(), rid))
        # Numbered hymns in their order, then the rest alphabetically, after those listed in library.json.
        for s, items in placed.values():
            s["entries"].extend(rid for _, _, rid in sorted(items))
        # Sub-folders of a section (info.json "group"). The section keeps its whole list in "entries", so an app
        # that doesn't know about groups shows it as before. A section may name its sub-folders in library.json,
        # in order and with their titles ({"id", "titles"}): its hymns are then listed folder by folder in that
        # order (hymns in no sub-folder after them); otherwise the sub-folders come where their first hymn does.
        for s in sections.values():
            spec = [g for g in s.get("groups", []) if g.get("id")]
            rank = {g["id"]: n for n, g in enumerate(spec)}
            groups, by = [], {}

            def group_id(rid):
                g = self.group_of.get(rid)
                if not g or id(s) not in in_places.get(rid, ()):
                    return None, None
                key = g.get("english") or g.get("arabic") or ""
                return re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-") or "group", g

            if spec:
                rid_of = lambda e: e if isinstance(e, str) else e.get("recording")
                keyed = list(enumerate(s["entries"]))
                keyed.sort(key=lambda ie: (rank.get(group_id(rid_of(ie[1]))[0], len(spec)), ie[0]))
                s["entries"] = [e for _, e in keyed]
            for e in s["entries"]:
                rid = e if isinstance(e, str) else e.get("recording")
                gid, g = group_id(rid)
                if not gid:
                    continue
                if gid not in by:
                    named = spec[rank[gid]]["titles"] if gid in rank else {}
                    by[gid] = {"id": gid, "titles": named or {k: v for k, v in g.items() if k in ("english", "arabic", "coptic") and v},
                               "recordings": []}
                    groups.append(by[gid])
                by[gid]["recordings"].append(rid)
            if spec:
                unknown = [g["id"] for g in groups if g["id"] not in rank]
                if unknown:
                    self.warn("library", f"{s.get('id') or s.get('service')}: sub-folders not named in library.json: {', '.join(unknown)}")
            if groups:
                s["groups"] = groups
            else:
                s.pop("groups", None)

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
            if self.recordings[rid]["text"] not in placed_texts and rid not in self.held_back:
                self.warn(rid, "not in the library yet")
        if self.held_back:
            print(f"  NOTE  melismatic, kept out of the seasons until a score follows them: {', '.join(sorted(self.held_back))}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report only; do not write the catalog")
    ap.add_argument("--drafts", action="store_true", help='include hymns with notation marked "draft"')
    args = ap.parse_args()

    b = Build()
    b.drafts = args.drafts
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
    notations_out = b.notations(library)

    texts_out = []
    for tid, t in sorted(b.texts.items()):
        lines = [l for l in t["lines"] if not l.get("label") and not l.get("static")]
        doc = json.dumps({"id": tid, "titles": t["titles"], **({"intro": t["intro"]} if t["intro"] else {}), "lines": t["lines"]},
                         ensure_ascii=False, indent=1).encode()
        texts_out.append({"id": tid, "titles": t["titles"], "tags": t["tags"], "pending": t["pending"],
                          # Where else to hear it (another site's recording, linked rather than copied).
                          **({"links": t["links"]} if t["links"] else {}),
                          "lines": len(lines),
                          "translations": sorted({k for l in lines for k, v in (l.get("translations") or {}).items() if v}),
                          "transliterations": sorted({k for l in lines for k, v in (l.get("transliterations") or {}).items() if v}),
                          "recordings": sorted((r for r, e in b.recordings.items() if e["text"] == tid), key=lambda r: (r != tid, r)),
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
               "texts": texts_out, "recordings": recordings_out, "notations": notations_out}
    # The version changes only when content does, so the app can tell cheaply whether anything is new.
    version = sha256_bytes(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode())[:16]
    # When the content last changed, so the app takes only a newer catalog (the version is a fingerprint, not an order).
    previous = json.loads((ROOT / "catalog/v1/index.json").read_text(encoding="utf-8")) if (ROOT / "catalog/v1/index.json").exists() else {}
    updated = previous.get("updated") if previous.get("version") == version and previous.get("updated") else \
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {"version": version, "updated": updated, **payload}

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
