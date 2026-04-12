#!/usr/bin/env python3

import argparse
import json
import re
import subprocess
from pathlib import Path


LINE_RE = re.compile(r"^\s*line\s+(\d+)\s*:\s*(.+?)\s*$", re.IGNORECASE)


def _probe_duration(audio_file: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _parse_starts_file(path: Path) -> dict[int, list[float]]:
    mapping: dict[int, list[float]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = LINE_RE.match(line)
        if not match:
            raise RuntimeError(f"Invalid line format: {raw}")

        line_num = int(match.group(1))
        values = [v.strip() for v in match.group(2).split(",") if v.strip()]
        starts = [float(v) for v in values]
        if not starts:
            raise RuntimeError(f"No timestamps found in line: {raw}")
        mapping[line_num] = starts
    return mapping


def _tokenize(text: str) -> list[str]:
    return [w for w in text.split() if w.strip()]


def apply_manual_starts(
    lyrics_path: Path,
    starts_path: Path,
    anchors_path: Path | None,
    audio_path: Path | None,
) -> tuple[int, int]:
    payload = json.loads(lyrics_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError("lyrics.json must be a top-level JSON array")

    starts_map = _parse_starts_file(starts_path)

    audio_duration = None
    if audio_path is not None:
        audio_duration = _probe_duration(audio_path)

    lines_updated = 0
    words_updated = 0

    # Optional existing anchors for update/merge behavior.
    anchors_payload = []
    if anchors_path and anchors_path.exists():
        anchors_payload = json.loads(anchors_path.read_text(encoding="utf-8"))
        if not isinstance(anchors_payload, list):
            anchors_payload = []

    anchor_map: dict[int, float] = {}
    for item in anchors_payload:
        if isinstance(item, dict) and isinstance(item.get("line"), int):
            try:
                anchor_map[item["line"]] = float(item["start"])
            except Exception:
                continue

    for line_num, starts in starts_map.items():
        idx = line_num - 1
        if idx < 0 or idx >= len(payload):
            raise RuntimeError(f"Line {line_num} is out of range for lyrics length {len(payload)}")

        row = payload[idx]
        tokens = _tokenize(str(row.get("coptic", "")))
        if len(tokens) != len(starts):
            raise RuntimeError(
                f"Line {line_num} token count ({len(tokens)}) does not match provided starts ({len(starts)})"
            )

        # Determine verse end for the final word in this line.
        if idx + 1 < len(payload):
            verse_end = float(payload[idx + 1].get("start", starts[-1]))
        elif audio_duration is not None:
            verse_end = float(audio_duration)
        else:
            # Fall back to existing last-word end if present.
            existing_words = row.get("words")
            if isinstance(existing_words, list) and existing_words and isinstance(existing_words[-1], dict):
                verse_end = float(existing_words[-1].get("end", starts[-1]))
            else:
                verse_end = starts[-1]

        words = []
        for i, token in enumerate(tokens):
            w_start = starts[i]
            w_end = starts[i + 1] if i + 1 < len(starts) else verse_end
            words.append({"text": token, "start": round(w_start, 2), "end": round(max(w_start, w_end), 2)})

        row["start"] = round(starts[0], 2)
        row["words"] = words
        payload[idx] = row

        lines_updated += 1
        words_updated += len(words)
        anchor_map[line_num] = starts[0]

        # If previous line exists, align its last word end to this verse start.
        if idx > 0:
            prev_words = payload[idx - 1].get("words")
            if isinstance(prev_words, list) and prev_words:
                prev_words[-1]["end"] = round(starts[0], 2)

    lyrics_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if anchors_path is not None:
        new_anchors = [{"line": ln, "start": round(st, 2)} for ln, st in sorted(anchor_map.items())]
        anchors_path.write_text(json.dumps(new_anchors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return lines_updated, words_updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply manual per-word start timestamps to lyrics.json and optional anchors.json"
    )
    parser.add_argument("lyrics", help="Path to lyrics.json")
    parser.add_argument("starts", help="Path to txt file: line N: t1, t2, t3")
    parser.add_argument(
        "--anchors",
        help="Optional path to timing-anchors.json. Updated with first start of each modified line.",
    )
    parser.add_argument(
        "--audio",
        help="Optional audio file path used to set end time of the final word in the final line.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    lines_updated, words_updated = apply_manual_starts(
        lyrics_path=Path(args.lyrics),
        starts_path=Path(args.starts),
        anchors_path=Path(args.anchors) if args.anchors else None,
        audio_path=Path(args.audio) if args.audio else None,
    )
    print(f"Updated {lines_updated} lines and {words_updated} words")


if __name__ == "__main__":
    main()
