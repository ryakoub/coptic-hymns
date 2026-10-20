#!/usr/bin/env python3
"""Add a hymn from Tasbeha.org: its text (Coptic, transliteration, English, Arabic), its Coptic recording,
and optionally an English recording, ready to time with the Pencil in the Coptic Chanter app.

  python3 tools/add_hymn.py TASBEHA_HYMN_URL --list
      shows the hymn's verses and the recordings Tasbeha lists for it (with their ids)

  python3 tools/add_hymn.py TASBEHA_HYMN_URL --id second-hoos --place praises/midnight --order 50 \\
      --coptic AUDIO [--english AUDIO] [--kind recital]

AUDIO can be:
  a YouTube link                     https://www.youtube.com/watch?v=…   (downloaded with yt-dlp)
  a recording on the hymn's page     mid:10791   (an id shown by --list)
  a track on a Tasbeha album page    https://tasbeha.org/mp3/…/Part_1.html#6   (track number after #)
  a Tasbeha download link            https://tasbeha.org/media/mp3/?gd=…
  a direct audio link or a file      https://…/x.mp3   or   ~/Music/x.m4a

The hymn goes in content/hymns/<id>/ and the English recording in content/english/<id>-english/.
Lines are left untimed; time them in the app (Time words), then import with tools/import_timing.py.
Afterwards: python3 tools/build_catalog.py, and in the app repo scripts/sync-catalog.sh.
"""
import argparse, html, json, re, shutil, subprocess, sys, tempfile, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
MEDIA = "https://media.tasbeha.org/mp3/"


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def text_of(fragment):
    t = re.sub(r"<br\s*/?>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t))).strip()


def unmarked(text):
    """Tasbeha starts some lines with "+" (the other side of the choir); the lyrics keep that as "side": 1."""
    return re.sub(r"^\+\s*", "", text).strip()


# ---------- the hymn page ----------

def parse_hymn(page):
    """Titles, verses (each a list of lines with Coptic words, transliteration, English, Arabic) and recordings."""
    title_en = text_of(re.search(r'<h1 class="hp-en">(.*?)</h1>', page, re.S).group(1))
    cop = re.search(r'<span class="hp-cop[^"]*"[^>]*>(.*?)</span>', page, re.S)
    ar = re.search(r'class="hp-ar[^"]*"[^>]*>(.*?)<', page, re.S)
    titles = {"english": title_en}
    if cop: titles["coptic"] = text_of(cop.group(1))
    if ar and text_of(ar.group(1)): titles["arabic"] = text_of(ar.group(1))

    verses = []
    for para in re.split(r'<div class="sync-para"', page)[1:]:
        lines = []
        for row in re.split(r'<div class="sync-line', para)[1:]:
            coptic = [text_of(w) for w in re.findall(r'<span class="w sync-coptic[^"]*"[^>]*>(.*?)</span>', row, re.S)]
            translit = [text_of(w) for w in re.findall(r'<span class="w sync-translit"[^>]*>(.*?)</span>', row, re.S)]
            en = re.search(r'<div class="sync-english">(.*?)</div>', row, re.S)
            ar = re.search(r'<div class="sync-arabic[^"]*"[^>]*>(.*?)</div>', row, re.S)
            if coptic:
                lines.append({"marked": "+" in coptic or bool(re.match(r"^\+", " ".join(coptic))),
                              "coptic": unmarked(" ".join(w for w in coptic if w != "+")),
                              "translit": unmarked(" ".join(w for w in translit if w != "+")),
                              "english": unmarked(text_of(en.group(1))) if en else "",
                              "arabic": unmarked(text_of(ar.group(1))) if ar else ""})
        if lines:
            verses.append(lines)

    recordings = []
    for by, block in re.findall(r'<h3>(.*?)</h3><ol class="hp-recs-list">(.*?)</ol>', page, re.S):
        for li in re.findall(r'<li class="hp-rec">(.*?)</li>', block, re.S):
            mid = re.search(r'\?mid=(\d+)', li)
            title = re.search(r'class="hp-rec-title"[^>]*>(.*?)</a>', li, re.S)
            album = re.search(r'class="hp-rec-album"[^>]*>(.*?)</a>', li, re.S)
            length = re.search(r'class="hp-rec-len">([^<]*)', li)
            if mid:
                recordings.append({"mid": mid.group(1), "by": text_of(by), "title": text_of(title.group(1)) if title else "",
                                   "album": text_of(album.group(1)) if album else "", "length": length.group(1) if length else ""})
    return titles, verses, recordings


def lyrics_from(verses):
    """One lyrics line per verse; a verse of several lines keeps them as stanzas (as Aripsalin does).
    Left without start times: the app's Time words screen times them."""
    out = []
    for lines in verses:
        # Tasbeha writes instructions ("From 12 Baona to 9 Baba … is said:") as lines whose Coptic is "-":
        # they become labels, shown but not sung or timed.
        if all(not re.search(r"[Ⲁ-⳿Ϣ-ϯ]", l["coptic"]) for l in lines):
            # The app reads a label as plain text, so it takes the English (or the Arabic when there is none).
            label = " ".join(l["english"] for l in lines if l["english"]) or " ".join(l["arabic"] for l in lines if l["arabic"])
            if label:
                out.append({"label": label})
            continue
        line = {"coptic": " ".join(l["coptic"] for l in lines),
                "translations": {k: v for k, v in {"english": " ".join(l["english"] for l in lines if l["english"]),
                                                   "arabic": " ".join(l["arabic"] for l in lines if l["arabic"])}.items() if v}}
        translit = " ".join(l["translit"] for l in lines if l["translit"])
        if translit:
            line["transliterations"] = {"english": translit}
        if len(lines) > 1:
            line["stanzas"] = [{"coptic": l["coptic"]} for l in lines]
        # Tasbeha's "+" marks the verses sung by the other side of the choir.
        if any(l.get("marked") for l in lines):
            line["side"] = 1
        out.append(line)
    return out


# ---------- audio ----------

def audio_url(source, hymn_url):
    """A direct audio URL (or None for YouTube / local files) for the ways AUDIO can be given."""
    if source.startswith("mid:"):
        page = fetch(f"{hymn_url.split('?')[0]}?mid={source[4:]}").decode("utf-8", "replace")
        src = re.search(r'src="(/media/mp3/[^"]+\.mp3)"', page)
        if not src:
            sys.exit(f"recording {source}: no audio found on its page")
        return MEDIA + urllib.parse.unquote(src.group(1)[len("/media/mp3/"):])
    if "tasbeha.org/media/" in source and ("gd=" in source or "gg=" in source):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(source).query)
        path = (q.get("gd") or q.get("gg"))[0]
        return MEDIA + path.split("mp3/", 1)[-1] if path.startswith("mp3/") else MEDIA + path
    if "tasbeha.org/mp3/" in source and ".html" in source:
        page_url, _, track = source.partition("#")
        page = fetch(page_url).decode("utf-8", "replace")
        files = re.findall(r'<tr class="mediarow" data-file="([^"]+)"', page)
        if not track.isdigit() or not 1 <= int(track) <= len(files):
            names = [text_of(n) for n in re.findall(r'<td class="mediatitle[^"]*">(.*?)</td>', page, re.S)]
            sys.exit(f"{page_url}: add the track number after #, 1 to {len(files)}" + ("\n  " + "\n  ".join(f"#{i}: {n}" for i, n in enumerate(names, 1)) if names else ""))
        base = re.search(r'data-base="([^"]+)"', page)
        b = base.group(1) if base else "//media.tasbeha.org/mp3/"
        return ("https:" + b if b.startswith("//") else b) + html.unescape(files[int(track) - 1])
    if re.match(r"https?://", source) and not re.search(r"youtube\.com|youtu\.be", source):
        return source
    return None


def get_audio(source, hymn_url, folder):
    """Downloads or copies the audio into folder as audio.m4a or audio.mp3; returns the file."""
    folder.mkdir(parents=True, exist_ok=True)
    if re.search(r"youtube\.com|youtu\.be", source):
        if not shutil.which("yt-dlp"):
            sys.exit("yt-dlp is needed for YouTube links: brew install yt-dlp")
        out = folder / "audio.m4a"
        # Take YouTube's own AAC stream as it is (format 140). Re-encoding (yt-dlp -x turns the Opus stream into
        # AAC with ffmpeg's built-in encoder) adds audible blips to chant; only when a video has no m4a stream is it
        # converted, with Apple's encoder at a high bitrate.
        # "bestaudio[ext=m4a]" ranks the original language first, so auto-dubbed tracks YouTube adds are skipped.
        r = subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", "bestaudio[ext=m4a]", "-o", str(out), source])
        if r.returncode != 0 or not out.exists():
            raw = folder / "audio.source"
            subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", "bestaudio", "-o", str(raw), source], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-vn", "-c:a", "aac_at", "-b:a", "192k", str(out)], check=True)
            raw.unlink()
        return out
    url = audio_url(source, hymn_url)
    if url:
        data = fetch(urllib.parse.quote(url, safe=":/?&=%#,()"))
        if data[:3] != b"ID3" and data[:2] not in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2") and b"ftyp" not in data[:16]:
            sys.exit(f"{url}: that is not an audio file (the server sent something else)")
        ext = "m4a" if b"ftyp" in data[:16] else "mp3"
        out = folder / f"audio.{ext}"
        out.write_bytes(data)
        return out
    path = Path(source).expanduser()
    if not path.exists():
        sys.exit(f"{source}: no such file, and not a link this tool knows")
    out = folder / ("audio.m4a" if path.suffix.lower() in (".m4a", ".mp4", ".aac") else "audio.mp3")
    shutil.copy(path, out)
    return out


def duration(path):
    try:
        out = subprocess.run(["afinfo", str(path)], capture_output=True, text=True).stdout
        m = re.search(r"estimated duration:\s*([\d.]+)", out)
        s = float(m.group(1))
        return f"{int(s // 60)}:{int(s % 60):02d}"
    except Exception:
        return "?"


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="Tasbeha hymn page, e.g. https://tasbeha.org/hymn_library/view/106")
    ap.add_argument("--list", action="store_true", help="show the hymn's text and recordings, change nothing")
    ap.add_argument("--id", help="folder name for the hymn, e.g. second-hoos")
    ap.add_argument("--place", action="append", default=[], help="library place, e.g. praises/midnight (repeatable)")
    ap.add_argument("--order", type=int, help="position within its places, e.g. 50")
    ap.add_argument("--kind", choices=["recital", "melismatic"])
    ap.add_argument("--coptic", help="the Coptic recording (see AUDIO above)")
    ap.add_argument("--english", help="an English recording (see AUDIO above)")
    ap.add_argument("--youtube", help="a YouTube link to keep with the hymn (for the website)")
    args = ap.parse_args()

    page = fetch(args.url).decode("utf-8", "replace")
    titles, verses, recordings = parse_hymn(page)
    if args.list:
        print(f"{titles.get('english')} | {titles.get('coptic', '')} | {titles.get('arabic', '')}")
        print(f"{len(verses)} verses, {sum(len(v) for v in verses)} lines")
        for lines in verses[:2]:
            print("  " + lines[0]["coptic"][:70] + "\n    " + lines[0]["english"][:70] + "\n    " + lines[0]["arabic"][:70])
        print("Recordings (use --coptic mid:ID or --english mid:ID):")
        for r in recordings:
            print(f"  mid:{r['mid']:<6} {r['by'][:34]:<34} {r['title'][:40]:<40} {r['length']}")
        if not recordings:
            print("  none listed; use a YouTube link, an album page track or a file")
        return

    if not args.id or not args.coptic:
        sys.exit("--id and --coptic are needed to add the hymn (or use --list to look first)")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", args.id):
        sys.exit("--id: use lowercase letters, digits and dashes, e.g. second-hoos")
    clash = [p.parent for p in CONTENT.rglob("lyrics.json") if p.parent.name in (args.id, f"{args.id}-english")]
    if clash:
        sys.exit(f"{args.id}: a hymn folder with that name exists already: {clash[0].relative_to(ROOT)}")
    if not verses:
        sys.exit(f"{args.url}: no text found on the page")

    folder = CONTENT / "hymns" / args.id
    folder.mkdir(parents=True)
    try:
        info = {"title": titles.get("english", args.id), "titles": titles, "source": args.url.split("?")[0]}
        if args.place: info["places"] = args.place
        if args.order is not None: info["order"] = args.order
        if args.kind: info["kind"] = args.kind
        if args.youtube or re.search(r"youtube\.com|youtu\.be", args.coptic):
            info["youtube"] = args.youtube or args.coptic
        coptic = get_audio(args.coptic, args.url, folder)
        (folder / "lyrics.json").write_text(json.dumps(lyrics_from(verses), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (folder / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"added {folder.relative_to(ROOT)}: {len(verses)} verses, Coptic audio {coptic.name} ({duration(coptic)})")
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise

    if args.english:
        efolder = CONTENT / "english" / f"{args.id}-english"
        try:
            english = get_audio(args.english, args.url, efolder)
            einfo = {"title": f"{titles.get('english', args.id)} (English)", "titles": {"english": f"{titles.get('english', args.id)} (English)"},
                     "text": args.id, "language": "english", "source": args.english.split("#")[0]}
            (efolder / "info.json").write_text(json.dumps(einfo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (efolder / "lyrics.json").write_text("[]\n", encoding="utf-8")
            print(f"added {efolder.relative_to(ROOT)}: English audio {english.name} ({duration(english)})")
        except BaseException:
            shutil.rmtree(efolder, ignore_errors=True)
            raise
    print("next: python3 tools/build_catalog.py, then time it in the app")


if __name__ == "__main__":
    main()
