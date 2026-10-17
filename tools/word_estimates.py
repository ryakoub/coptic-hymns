"""Times for words left unmarked, the same way the app works them out (CopticChanter/Model/WordEstimates.swift).

Only some words need marking (say the first of each quarter). Between two marked words the time is shared
out by syllables, so "a" or "in" gets a moment and a long word more. After a line's last mark, words follow
at the pace sung so far, never past the next line. Words sung before with the same melody (a refrain) take
the timing of the time they were marked in full. Lines with no marked words are left as they are.

Estimated words get "estimated": true. The website uses their times; the catalog builder leaves them out
for the app, which estimates again from the marks.
"""

VOWELS = set("aeiouyⲁⲉⲏⲓⲟⲩⲱ")
JINKIM = "̀"
PUNCTUATION = set(".,:;!?·«»\"“”")


def syllables(text):
    """A rough syllable count: groups of vowels, plus a jinkim on a consonant (ⲛ̀ is a syllable of its own)."""
    count, previous_vowel = 0, False
    for ch in text.lower():
        if ch == JINKIM:
            if not previous_vowel:
                count += 1
            continue
        vowel = ch in VOWELS
        if vowel and not previous_vowel:
            count += 1
        previous_vowel = vowel
    return max(count, 1)


def refrain_key(text):
    return "".join(ch for ch in text.lower() if ch not in PUNCTUATION)


def _starts(words):
    return [w.get("start") if not w.get("estimated") else None for w in words]


def typical_pace(segments):
    """Seconds per syllable between neighbouring marked words, the median over the recording."""
    paces = []
    for seg in segments:
        words = seg.get("words") or []
        starts = _starts(words)
        marked = [i for i, t in enumerate(starts) if t is not None]
        for a, b in zip(marked, marked[1:]):
            dt = starts[b] - starts[a]
            if dt > 0:
                paces.append(dt / sum(syllables(w["text"]) for w in words[a:b]))
    return sorted(paces)[len(paces) // 2] if paces else None


def refrain_times(texts, outside, segments, keys, marks):
    """Hand-marked times of these words in another line, the nearest earlier one first."""
    if len(texts) < 2:
        return None
    wanted = [refrain_key(t) for t in texts]
    order = list(range(min(outside, len(segments)) - 1, -1, -1)) + list(range(outside + 1, len(segments)))
    for i in order:
        line_keys, starts = keys[i], marks[i]
        for start in range(len(line_keys) - len(wanted) + 1):
            if line_keys[start] != wanted[0] or line_keys[start:start + len(wanted)] != wanted:
                continue
            times = starts[start:start + len(wanted)]
            if all(t is not None for t in times) and all(a < b for a, b in zip(times, times[1:])):
                return times
    return None


def estimate(segments):
    """Fill in "start" (with "estimated": true) for unmarked words of partly marked lines, in place.
    `segments` are the app's segments: {"line", "start", "words": [{"text", "start"?}, …]}, in sung order.
    Returns how many words were estimated."""
    pace = typical_pace(segments)
    keys = [[refrain_key(w["text"]) for w in seg.get("words") or []] for seg in segments]
    marks = [_starts(seg.get("words") or []) for seg in segments]
    count = 0
    for s, seg in enumerate(segments):
        words = seg.get("words") or []
        for w in words:
            if w.get("estimated"):
                w.pop("start", None)
                w.pop("estimated", None)
        marked = [i for i, w in enumerate(words) if w.get("start") is not None]
        if not marked or len(marked) == len(words):
            continue
        weights = [syllables(w["text"]) for w in words]

        def weight(a, b):
            return sum(weights[a:b])

        def put(k, t):
            nonlocal count
            words[k]["start"] = round(t, 3)
            words[k]["estimated"] = True
            count += 1

        spans = [(words[b]["start"] - words[a]["start"], weight(a, b)) for a, b in zip(marked, marked[1:])
                 if words[b]["start"] > words[a]["start"]]
        line_pace = sum(d for d, _ in spans) / sum(w for _, w in spans) if spans else pace
        next_start = segments[s + 1]["start"] if s + 1 < len(segments) else None

        first = marked[0]
        if first > 0:
            first_t = words[first]["start"]
            if seg["start"] < first_t - 0.05:
                floor = seg["start"]
            elif s > 0:
                prev = [w.get("start") for w in segments[s - 1].get("words") or [] if w.get("start") is not None]
                floor = (max(prev) if prev else segments[s - 1]["start"]) + 0.05
            else:
                floor = 0
            begin = max(floor, first_t - (line_pace or 0.3) * weight(0, first))
            if begin < first_t:
                for k in range(first):
                    put(k, begin + (first_t - begin) * weight(0, k) / weight(0, first))

        for a, b in zip(marked, marked[1:]):
            if b <= a + 1:
                continue
            ta, tb = words[a]["start"], words[b]["start"]
            if tb <= ta:
                continue
            sung = refrain_times([w["text"] for w in words[a:b + 1]], s, segments, keys, marks)
            for k in range(a + 1, b):
                if sung:
                    put(k, ta + (tb - ta) * (sung[k - a] - sung[0]) / (sung[-1] - sung[0]))
                else:
                    put(k, ta + (tb - ta) * weight(a, k) / weight(a, b))

        last = marked[-1]
        if last + 1 < len(words):
            ta = words[last]["start"]
            sung = refrain_times([w["text"] for w in words[last:]], s, segments, keys, marks)
            if sung:
                length = sung[-1] - sung[0]
                room = (next_start - ta) * 0.95 if next_start is not None else float("inf")
                scale = room / length if length > room else 1
                if room > 0:
                    for k in range(last + 1, len(words)):
                        put(k, ta + (sung[k - last] - sung[0]) * scale)
            else:
                total = weight(last, len(words))
                per = line_pace or 0.3
                if next_start is not None and next_start > ta and per * total > next_start - ta:
                    per = (next_start - ta) / total
                if next_start is None or next_start > ta:
                    for k in range(last + 1, len(words)):
                        put(k, ta + per * weight(last, k))
    return count
