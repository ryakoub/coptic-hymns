#!/usr/bin/env python3

import argparse
import html
import json
import math
import re
import subprocess
import urllib.request
from pathlib import Path


def fetch_page(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def clean_html_text(raw: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", raw, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_column(page: str, class_name: str) -> list[str]:
    pattern = re.compile(
        rf"<div class='col-xs-4 textcolumn {class_name}'[^>]*><p>(.*?)</p></div>",
        re.DOTALL,
    )
    return [clean_html_text(m) for m in pattern.findall(page)]


def normalize_leading_plus(text: str, keep_plus: bool) -> str:
    if keep_plus:
        return text
    return re.sub(r"^\+\s*", "", text)


def build_lyrics(english: list[str], coptic: list[str], keep_plus: bool) -> list[dict]:
    rows = []
    for en, cop in zip(english, coptic):
        en = normalize_leading_plus(en, keep_plus=keep_plus)
        cop = normalize_leading_plus(cop, keep_plus=keep_plus)
        if not en or not cop:
            continue
        rows.append(
            {
                "start": 0,
                "coptic": cop,
                "translations": {"english": en},
            }
        )
    return rows


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


def _detect_non_silent_intervals(
    audio_file: Path,
    min_silence_sec: float,
    silence_db: float,
) -> tuple[list[tuple[float, float]], float]:
    duration = _probe_duration(audio_file)
    proc = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(audio_file),
            "-af",
            f"silencedetect=noise={silence_db}dB:d={min_silence_sec}",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    starts = [float(v) for v in re.findall(r"silence_start:\s*([0-9]+(?:\.[0-9]+)?)", proc.stderr)]
    ends = [float(v) for v in re.findall(r"silence_end:\s*([0-9]+(?:\.[0-9]+)?)", proc.stderr)]

    silences = []
    for idx, start in enumerate(starts):
        if idx < len(ends):
            end = ends[idx]
            if end > start:
                silences.append((start, end))

    intervals = []
    cursor = 0.0
    for s_start, s_end in silences:
        if s_start > cursor:
            intervals.append((cursor, s_start))
        cursor = max(cursor, s_end)
    if duration > cursor:
        intervals.append((cursor, duration))

    return [(s, e) for s, e in intervals if e - s > 0.05], duration


def _merge_short_gaps(
    intervals: list[tuple[float, float]],
    join_gap_sec: float,
) -> list[tuple[float, float]]:
    if not intervals:
        return []
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        p_start, p_end = merged[-1]
        if start - p_end <= join_gap_sec:
            merged[-1] = (p_start, end)
        else:
            merged.append((start, end))
    return merged


def _drop_intro(intervals: list[tuple[float, float]], min_phrase_sec: float) -> list[tuple[float, float]]:
    for idx, (start, end) in enumerate(intervals):
        if end - start >= min_phrase_sec:
            return intervals[idx:]
    return intervals


def _token_weight(text: str) -> float:
    tokens = [t for t in text.split() if t.strip()]
    if not tokens:
        return 1.0
    chars = sum(len(t) for t in tokens)
    return max(1.0, (0.6 * len(tokens)) + (0.02 * chars))


def _assign_groups_dp(
    intervals: list[tuple[float, float]],
    weights: list[float],
) -> list[tuple[float, float]]:
    m = len(intervals)
    n = len(weights)
    if n == 0:
        return []

    if m == 0:
        return [(0.0, 0.0)] * n

    total = sum(e - s for s, e in intervals)
    weight_sum = sum(weights) or 1.0
    targets = [(w / weight_sum) * total for w in weights]

    prefix = [0.0]
    for s, e in intervals:
        prefix.append(prefix[-1] + (e - s))

    inf = float("inf")
    dp = [[inf] * (m + 1) for _ in range(n + 1)]
    back = [[-1] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0

    for i in range(1, n + 1):
        for j in range(i, m + 1):
            best = inf
            best_k = -1
            for k in range(i - 1, j):
                if dp[i - 1][k] == inf:
                    continue
                dur = prefix[j] - prefix[k]
                cost = dp[i - 1][k] + ((dur - targets[i - 1]) ** 2)
                if cost < best:
                    best = cost
                    best_k = k
            dp[i][j] = best
            back[i][j] = best_k

    groups = []
    i = n
    j = m
    while i > 0:
        k = back[i][j]
        if k < 0:
            break
        seg_start = intervals[k][0]
        seg_end = intervals[j - 1][1]
        groups.append((seg_start, seg_end))
        i -= 1
        j = k

    groups.reverse()

    if len(groups) != n:
        full_start = intervals[0][0]
        full_end = intervals[-1][1]
        span = max(0.0, full_end - full_start)
        offsets = [0.0]
        running = 0.0
        for w in weights:
            running += w
            offsets.append((running / weight_sum) * span)
        groups = []
        for idx in range(n):
            groups.append((full_start + offsets[idx], full_start + offsets[idx + 1]))

    return groups


def _resolve_mode(sync_style: str, lyrics: list[dict], hymn_style: str) -> str:
    if sync_style in {"verse", "word"}:
        return sync_style

    if hymn_style == "syllabic":
        return "word"
    if hymn_style == "melismatic":
        return "verse"

    avg_words = 0.0
    if lyrics:
        avg_words = sum(len(str(row.get("coptic", "")).split()) for row in lyrics) / len(lyrics)
    return "word" if avg_words <= 7.0 else "verse"


def _allocate_token_times(tokens: list[str], start: float, end: float) -> list[dict]:
    if not tokens:
        return []
    total_chars = sum(max(1, len(t)) for t in tokens)
    dur = max(0.0, end - start)
    out = []
    cursor = start
    for idx, token in enumerate(tokens):
        piece = (max(1, len(token)) / total_chars) * dur
        nxt = end if idx == len(tokens) - 1 else (cursor + piece)
        out.append({"text": token, "start": round(cursor, 2), "end": round(nxt, 2)})
        cursor = nxt
    return out


def _load_melisma_hints(hints_file: Path, lyric_count: int) -> dict[int, dict[int, float]]:
    payload = json.loads(hints_file.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError("Melisma hints file must be a JSON array.")

    result: dict[int, dict[int, float]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        line = item.get("line")
        if not isinstance(line, int) or line < 1 or line > lyric_count:
            continue

        row_map: dict[int, float] = {}
        boosts = item.get("boosts")
        if isinstance(boosts, dict):
            for key, value in boosts.items():
                try:
                    idx = int(key)
                    factor = float(value)
                except (TypeError, ValueError):
                    continue
                if idx >= 1 and factor > 0:
                    row_map[idx] = factor

        words = item.get("words")
        default_boost = float(item.get("boost", 1.8))
        if isinstance(words, list):
            for idx in words:
                if isinstance(idx, int) and idx >= 1 and default_boost > 0:
                    row_map[idx] = default_boost

        if row_map:
            result[line] = row_map

    return result


def _melisma_adjusted_token_times(
    tokens: list[str],
    start: float,
    end: float,
    strength: float,
    hint_boosts: dict[int, float] | None,
) -> list[dict]:
    if not tokens:
        return []

    # Base weight still tracks token size, but we boost likely melismatic words.
    raw_weights: list[float] = []
    for idx, token in enumerate(tokens):
        weight = float(max(1, len(token)))
        score = 0.0
        if idx == len(tokens) - 1:
            score += 1.2
        if re.search(r"[:;,.!?]$", token):
            score += 0.8
        if re.search(r"[\u0300-\u036f]", token):
            score += 0.4
        if len(token) >= 8:
            score += 0.3
        if "ⲱ" in token or "ϯ" in token:
            score += 0.2
        weight *= 1.0 + (max(0.0, strength) * score)

        if hint_boosts:
            boost = hint_boosts.get(idx + 1)
            if boost and boost > 0:
                weight *= boost
        raw_weights.append(weight)

    total = sum(raw_weights) or 1.0
    dur = max(0.0, end - start)
    out = []
    cursor = start
    for idx, token in enumerate(tokens):
        piece = (raw_weights[idx] / total) * dur
        nxt = end if idx == len(tokens) - 1 else (cursor + piece)
        out.append({"text": token, "start": round(cursor, 2), "end": round(nxt, 2)})
        cursor = nxt
    return out


def _load_anchor_starts(anchor_file: Path, lyric_count: int) -> list[float | None]:
    payload = json.loads(anchor_file.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError("Anchor file must be a top-level JSON array.")

    starts: list[float | None] = [None] * lyric_count
    for item in payload:
        if not isinstance(item, dict):
            continue
        line = item.get("line")
        start = item.get("start")
        if line is None or start is None:
            continue
        if not isinstance(line, int):
            raise RuntimeError("Anchor line must be an integer.")
        if line < 1 or line > lyric_count:
            raise RuntimeError(f"Anchor line {line} out of range 1..{lyric_count}")
        starts[line - 1] = float(start)

    if not any(v is not None for v in starts):
        raise RuntimeError("Anchor file has no usable start values.")
    return starts


def _interpolate_missing_starts(
    starts: list[float | None],
    weights: list[float],
    speech_start: float,
    speech_end: float,
) -> list[float]:
    anchors = [(idx, v) for idx, v in enumerate(starts) if v is not None]
    out: list[float] = [0.0] * len(starts)

    def fill_segment(a_idx: int, b_idx: int, a_t: float, b_t: float) -> None:
        span = b_idx - a_idx
        if span <= 0:
            out[a_idx] = a_t
            return
        seg_weights = weights[a_idx : b_idx + 1]
        denom = sum(seg_weights[:-1]) or float(span)
        running = 0.0
        out[a_idx] = a_t
        for i in range(a_idx + 1, b_idx + 1):
            running += seg_weights[i - a_idx - 1]
            frac = running / denom
            out[i] = a_t + ((b_t - a_t) * frac)

    first_idx, first_t = anchors[0]
    if first_idx == 0:
        out[0] = float(first_t)
    else:
        fill_segment(0, first_idx, speech_start, float(first_t))

    for (a_idx, a_t), (b_idx, b_t) in zip(anchors, anchors[1:]):
        fill_segment(a_idx, b_idx, float(a_t), float(b_t))

    last_idx, last_t = anchors[-1]
    if last_idx < len(starts) - 1:
        fill_segment(last_idx, len(starts) - 1, float(last_t), speech_end)
    else:
        out[last_idx] = float(last_t)

    return out


def _intervals_from_starts(starts: list[float], speech_end: float) -> list[tuple[float, float]]:
    intervals: list[tuple[float, float]] = []
    for idx, start in enumerate(starts):
        end = speech_end if idx == len(starts) - 1 else starts[idx + 1]
        intervals.append((start, max(start, end)))
    return intervals


def _apply_sync(
    lyrics: list[dict],
    audio_file: Path,
    sync_style: str,
    hymn_style: str,
    min_silence_sec: float,
    silence_db: float,
    join_gap_sec: float,
    anchor_file: Path | None,
    melisma_auto: bool,
    melisma_strength: float,
    melisma_hints_file: Path | None,
) -> tuple[int, int, str]:
    intervals, _ = _detect_non_silent_intervals(
        audio_file=audio_file,
        min_silence_sec=min_silence_sec,
        silence_db=silence_db,
    )
    intervals = _merge_short_gaps(intervals, join_gap_sec=join_gap_sec)
    intervals = _drop_intro(intervals, min_phrase_sec=0.6)

    mode = _resolve_mode(sync_style=sync_style, lyrics=lyrics, hymn_style=hymn_style)
    weights = [_token_weight(str(row.get("coptic", ""))) for row in lyrics]
    speech_start = intervals[0][0] if intervals else 0.0
    speech_end = intervals[-1][1] if intervals else 0.0
    melisma_hints: dict[int, dict[int, float]] = {}
    if melisma_hints_file is not None:
        melisma_hints = _load_melisma_hints(melisma_hints_file, len(lyrics))

    if anchor_file is not None:
        starts = _load_anchor_starts(anchor_file, len(lyrics))
        full_starts = _interpolate_missing_starts(
            starts=starts,
            weights=weights,
            speech_start=speech_start,
            speech_end=speech_end,
        )
        verse_intervals = _intervals_from_starts(full_starts, speech_end=speech_end)
    else:
        verse_intervals = _assign_groups_dp(intervals, weights)

    for idx, row in enumerate(lyrics):
        start, end = verse_intervals[idx]
        row["start"] = round(start, 2)
        if mode == "word":
            tokens = [t for t in str(row.get("coptic", "")).split() if t.strip()]
            if melisma_auto:
                row["words"] = _melisma_adjusted_token_times(
                    tokens=tokens,
                    start=start,
                    end=end,
                    strength=melisma_strength,
                    hint_boosts=melisma_hints.get(idx + 1),
                )
            else:
                row["words"] = _allocate_token_times(tokens, start=start, end=end)
        else:
            row.pop("words", None)

    return len(intervals), len(verse_intervals), mode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Tasbeha hymn English/Coptic lyrics into lyrics.json, with optional timestamp sync.",
    )
    parser.add_argument("url", help="Tasbeha hymn URL, for example: https://tasbeha.org/hymn_library/view/23")
    parser.add_argument("target", help="Target hymn folder path or direct lyrics.json path")
    parser.add_argument("--keep-plus", action="store_true", help="Keep leading '+' markers")

    parser.add_argument("--sync-audio", help="Optional audio file path to generate timing data")
    parser.add_argument(
        "--sync-style",
        choices=["verse", "word", "auto"],
        default="verse",
        help="How to sync text to audio",
    )
    parser.add_argument(
        "--hymn-style",
        choices=["auto", "melismatic", "syllabic"],
        default="auto",
        help="Influences auto mode: melismatic favors verse, syllabic favors word",
    )
    parser.add_argument("--min-silence", type=float, default=0.25, help="Minimum silence length in seconds")
    parser.add_argument(
        "--silence-db",
        type=float,
        default=-28.0,
        help="Silence threshold in dB for ffmpeg silencedetect",
    )
    parser.add_argument(
        "--join-gap",
        type=float,
        default=0.22,
        help="Merge neighboring sound segments when gap is less than this threshold",
    )
    parser.add_argument(
        "--anchors",
        help="Optional JSON file with known verse starts: [{\"line\":1,\"start\":6.43}]",
    )
    parser.add_argument(
        "--melisma-auto",
        action="store_true",
        help="Enable melisma-aware duration weighting for word sync mode (opt-in).",
    )
    parser.add_argument(
        "--melisma-strength",
        type=float,
        default=0.35,
        help="How strongly melisma heuristics affect word durations when --melisma-auto is enabled.",
    )
    parser.add_argument(
        "--melisma-hints",
        help="Optional JSON file with manual melisma boosts per line/word index.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    page = fetch_page(args.url)
    english = extract_column(page, "englishtext")
    coptic = extract_column(page, "coptictext_utf8")
    if not english or not coptic:
        raise SystemExit("Could not find English/Coptic hymn columns on the provided page.")

    lyrics = build_lyrics(english, coptic, keep_plus=args.keep_plus)
    if not lyrics:
        raise SystemExit("No lyric rows were extracted.")

    target_path = Path(args.target)
    if target_path.name != "lyrics.json":
        target_path = target_path / "lyrics.json"

    mode_used = "none"
    detected = 0
    mapped = 0
    if args.sync_audio:
        detected, mapped, mode_used = _apply_sync(
            lyrics=lyrics,
            audio_file=Path(args.sync_audio),
            sync_style=args.sync_style,
            hymn_style=args.hymn_style,
            min_silence_sec=args.min_silence,
            silence_db=args.silence_db,
            join_gap_sec=args.join_gap,
            anchor_file=Path(args.anchors) if args.anchors else None,
            melisma_auto=args.melisma_auto,
            melisma_strength=args.melisma_strength,
            melisma_hints_file=Path(args.melisma_hints) if args.melisma_hints else None,
        )

    target_path.write_text(json.dumps(lyrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(lyrics)} lyric rows to {target_path}")
    print(f"Extracted rows: English={len(english)}, Coptic={len(coptic)}")
    if args.sync_audio:
        print("Auto sync complete")
        print(f"Mode used: {mode_used}")
        print(f"Detected phrase intervals: {detected}")
        print(f"Mapped lyric intervals: {mapped}")


if __name__ == "__main__":
    main()
