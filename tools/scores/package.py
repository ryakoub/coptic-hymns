"""One hymn as a Mark Sync backup, to import in the app's My hymns (or Mark Sync): its PDF, recording and marks.

  python3 tools/scores/package.py <score.pdf> <recording> <marks.taps.json> <out.marksync> [--name NAME] [--id ID]

Importing a backup whose id is already in My hymns replaces that hymn, so keep the id to update one.
"""
import argparse, json, os, re, uuid


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf"); ap.add_argument("recording"); ap.add_argument("taps"); ap.add_argument("out")
    ap.add_argument("--name"); ap.add_argument("--id"); ap.add_argument("--folder", default="Scores")
    ap.add_argument("--cursor-size", type=float, default=0.05, help="of the page's height (a score needs a small one)")
    a = ap.parse_args()
    taps = json.load(open(a.taps, encoding="utf-8"))
    track = taps["tracks"][0]
    pdf, audio = open(a.pdf, "rb").read(), open(a.recording, "rb").read()
    name = a.name or taps.get("name") or os.path.splitext(os.path.basename(a.pdf))[0]
    audio_name = os.path.basename(a.recording)
    kind = {".m4a": "audio/mp4", ".mp4": "audio/mp4", ".ogg": "audio/ogg", ".wav": "audio/wav"}.get(
        os.path.splitext(audio_name.lower())[1], "audio/mpeg")
    project = {"id": a.id or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or str(uuid.uuid4()), "name": name,
               "folders": [a.folder], "pdfName": os.path.basename(a.pdf), "pages": taps.get("pages"),
               "pdf": {"file": 0, "name": os.path.basename(a.pdf), "type": "application/pdf"},
               "tracks": [{"id": str(uuid.uuid4()), "name": track.get("name") or name, "fileName": audio_name,
                           "startAt": track.get("startAt"), "points": track["points"],
                           "audio": {"file": 1, "name": audio_name, "type": kind}}],
               # Read by the app (Mark Sync passes over them): the cursor's size, and gliding on to each line's end.
               "cursorSize": a.cursor_size, "glideToLineEnd": True}
    manifest = json.dumps({"app": "mark-sync", "kind": "backup", "version": 1, "projects": [project],
                           "files": [{"offset": 0, "length": len(pdf)}, {"offset": len(pdf), "length": len(audio)}]},
                          ensure_ascii=False).encode()
    with open(a.out, "wb") as f:
        f.write(b"MARKSYNC-BACKUP 1\n" + str(len(manifest)).encode() + b"\n" + manifest + pdf + audio)
    print(f"{a.out}: {name}, {len(track['points'])} marks, {os.path.getsize(a.out) / 1048576:.1f} MB")


if __name__ == "__main__":
    main()
