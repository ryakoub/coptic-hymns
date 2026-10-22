"""Adds a transliteration line under every Coptic lyric of a MuseScore score (.mscx).

  python3 mscx_translit.py in.mscx out.mscx
Each Coptic lyric gets a sibling on the next lyric line with the same syllabic (so hyphens line up), in a
small brown italic, with the syllable's transliteration as Tasbeha writes it, right under it even when there
are several verses (see LINE_RATIO).
"""
import re, sys

T = {"ⲁ": "a", "ⲃ": "v", "ⲅ": "g", "ⲇ": "d", "ⲉ": "e", "ⲍ": "z", "ⲏ": "i", "ⲑ": "th", "ⲓ": "i", "ⲕ": "k", "ⲗ": "l",
     "ⲙ": "m", "ⲛ": "n", "ⲝ": "ks", "ⲟ": "o", "ⲡ": "p", "ⲣ": "r", "ⲥ": "s", "ⲧ": "t", "ⲩ": "i", "ⲫ": "ph", "ⲭ": "kh",
     "ⲯ": "ps", "ⲱ": "o", "ϣ": "sh", "ϥ": "f", "ϧ": "kh", "ϩ": "h", "ϫ": "j", "ϭ": "ch", "ϯ": "ti"}
VOWELS = "aeiou"
# MuseScore spaces each lyric line by its own font, and a 12 pt Arial Coptic line is about one and a half 9 pt
# transliteration lines, so the transliteration of the Coptic on line n goes on line round(1.5 n) + 1:
# 0 → 1, 2 → 4 (midi_lyrics.py puts verses on lines 0, 2, 5…).
LINE_RATIO = 1.5
# Sizes (points), large enough to read on an iPad: fewer bars fit on a line, which is fine. The Coptic is in
# Arial Coptic; lyricsLineHeight leaves some room between the Coptic and its transliteration.
COPTIC_SIZE, TRANSLIT_SIZE, LINE_HEIGHT = 16, 12, 1.2      # keep the sizes 4:3, as LINE_RATIO assumes


def set_style(xml, values):
    """Sets the score's style values (in its <Style>, made if missing)."""
    if not re.search(r"<Style>", xml):
        xml = re.sub(r"(\n([ \t]*)<Division>\d+</Division>\n)", lambda m: m.group(1) + f"{m.group(2)}<Style>\n{m.group(2)}  </Style>\n", xml, count=1)
    for key, value in values.items():
        if re.search(rf"<{key}>.*?</{key}>", xml):
            xml = re.sub(rf"<{key}>.*?</{key}>", f"<{key}>{value}</{key}>", xml, count=1)
        else:
            xml = re.sub(r"(\n([ \t]*)<Style>\n)", lambda m: m.group(1) + f"{m.group(2)}  <{key}>{value}</{key}>\n", xml, count=1)
    return xml
JENKIM = "̀"


def translit(syllable):
    # A jenkim sung on its own may be written as a spacing grave (ˋ); a dot over a letter isn't said.
    s = syllable.lower().replace("\u02cb", JENKIM).replace("\u0307", "").strip(":.,; ")
    if s and set(s) <= {JENKIM}:
        return "e"                                   # a jenkim on its own is sung as a short "e"
    out, i = "", 0
    while i < len(s):
        ch = s[i]
        if ch == JENKIM:
            i += 1; continue
        jenkim = i + 1 < len(s) and s[i + 1] == JENKIM
        if s[i:i + 2] == "ⲟⲩ":
            part, step = "ou", 2
        elif ch == "ⲩ" and out[-1:] in ("a", "e"):
            part, step = "v", 1
        else:
            part, step = T.get(ch, ch), 1
        # the jenkim before a consonant is said as a short "e"
        out += ("e" + part) if jenkim and part[:1] not in VOWELS else part
        i += step
    return out


src, dst = sys.argv[1], sys.argv[2]
xml = open(src, encoding="utf-8").read()
pattern = re.compile(r"(?P<indent>[ \t]*)<Lyrics>\n(?P<body>(?:(?!</Lyrics>).)*?)</Lyrics>\n", re.S)
added = []


def add(m):
    body = m.group("body")
    no = re.search(r"<no>(\d+)</no>", body)
    no = int(no.group(1)) if no else 0
    if re.search(r"<family>Helvetica</family>", body):     # a transliteration line already
        return m.group(0)
    text = re.search(r"<text>(.*?)</text>", body, re.S)
    if not text:
        return m.group(0)
    syllabic = re.search(r"<syllabic>(.*?)</syllabic>", body)
    t = translit(re.sub(r"<[^>]+>", "", text.group(1)))
    added.append((text.group(1), t))
    ind = m.group("indent")
    extra = (f"{ind}<Lyrics>\n{ind}  <no>{round(LINE_RATIO * no) + 1}</no>\n"
             + (f"{ind}  <syllabic>{syllabic.group(1)}</syllabic>\n" if syllabic else "")
             + f"{ind}  <family>Helvetica</family>\n{ind}  <size>{TRANSLIT_SIZE}</size>\n{ind}  <italic>1</italic>\n"
             + f'{ind}  <color r="140" g="84" b="31" a="255"/>\n'
             + f'{ind}  <text>{t}</text>\n{ind}  </Lyrics>\n')
    return m.group(0) + extra


xml = pattern.sub(add, xml)
# Wider bars and room between syllables, so the larger words don't run together (fewer bars a line).
xml = set_style(xml, {"lyricsOddFontFace": "ArialCoptic", "lyricsOddFontSize": COPTIC_SIZE, "lyricsLineHeight": LINE_HEIGHT,
                      "minMeasureWidth": 14, "lyricsMinDistance": 1})
open(dst, "w", encoding="utf-8").write(xml)
print(f"{len(added)} syllables transliterated:")
print("  " + "  ".join(f"{c}→{t}" for c, t in added))
