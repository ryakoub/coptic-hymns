#!/usr/bin/env python3

import argparse
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convenience wrapper: import Tasbeha lyrics and sync timestamps in one command."
    )
    parser.add_argument("url", help="Tasbeha hymn URL")
    parser.add_argument("target", help="Target hymn folder or lyrics.json path")
    parser.add_argument("audio", help="Audio file path used for syncing")
    parser.add_argument(
        "--split",
        choices=["verse", "word", "auto"],
        default="auto",
        help="Split style for syncing",
    )
    parser.add_argument(
        "--hymn-style",
        choices=["auto", "melismatic", "syllabic"],
        default="auto",
        help="Hint used when split style is auto",
    )
    parser.add_argument("--keep-plus", action="store_true", help="Keep leading '+' markers")
    parser.add_argument("--min-silence", type=float, default=0.25)
    parser.add_argument("--silence-db", type=float, default=-28.0)
    parser.add_argument("--join-gap", type=float, default=0.22)
    parser.add_argument("--anchors", help="Optional JSON anchors file with known verse starts")
    parser.add_argument("--melisma-auto", action="store_true", help="Enable melisma-aware word weighting")
    parser.add_argument("--melisma-strength", type=float, default=0.35)
    parser.add_argument("--melisma-hints", help="Optional JSON file with melisma boosts per line/word")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cmd = [
        sys.executable,
        "tools/import_tasbeha_lyrics.py",
        args.url,
        args.target,
        "--sync-audio",
        args.audio,
        "--sync-style",
        args.split,
        "--hymn-style",
        args.hymn_style,
        "--min-silence",
        str(args.min_silence),
        "--silence-db",
        str(args.silence_db),
        "--join-gap",
        str(args.join_gap),
    ]
    if args.keep_plus:
        cmd.append("--keep-plus")
    if args.anchors:
        cmd.extend(["--anchors", args.anchors])
    if args.melisma_auto:
        cmd.append("--melisma-auto")
    if args.melisma_strength != 0.35:
        cmd.extend(["--melisma-strength", str(args.melisma_strength)])
    if args.melisma_hints:
        cmd.extend(["--melisma-hints", args.melisma_hints])

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
