"""Adds a transliteration line under every Coptic lyric of a MuseScore score (.mscx), as lyric line 2.

  python3 mscx_translit.py in.mscx out.mscx
Each first-line lyric (no <no> tag) gets a sibling <Lyrics><no>1</no> with the same syllabic (so hyphens
line up), in a small brown italic, with the syllable's transliteration as Tasbeha writes it.
"""
import re, sys

T = {"ⲁ": "a", "ⲃ": "v", "ⲅ": "g", "ⲇ": "d", "ⲉ": "e", "ⲍ": "z", "ⲏ": "i", "ⲑ": "th", "ⲓ": "i", "ⲕ": "k", "ⲗ": "l",
     "ⲙ": "m", "ⲛ": "n", "ⲝ": "ks", "ⲟ": "o", "ⲡ": "p", "ⲣ": "r", "ⲥ": "s", "ⲧ": "t", "ⲩ": "i", "ⲫ": "ph", "ⲭ": "kh",
     "ⲯ": "ps", "ⲱ": "o", "ϣ": "sh", "ϥ": "f", "ϧ": "kh", "ϩ": "h", "ϫ": "j", "ϭ": "ch", "ϯ": "ti"}
VOWELS = "aeiou"
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
    if "<no>" in body:                               # already a second (or later) line
        return m.group(0)
    text = re.search(r"<text>(.*?)</text>", body, re.S)
    if not text:
        return m.group(0)
    syllabic = re.search(r"<syllabic>(.*?)</syllabic>", body)
    t = translit(re.sub(r"<[^>]+>", "", text.group(1)))
    added.append((text.group(1), t))
    ind = m.group("indent")
    extra = (f"{ind}<Lyrics>\n{ind}  <no>1</no>\n"
             + (f"{ind}  <syllabic>{syllabic.group(1)}</syllabic>\n" if syllabic else "")
             + f"{ind}  <family>Helvetica</family>\n{ind}  <size>9</size>\n{ind}  <italic>1</italic>\n"
             + f'{ind}  <color r="140" g="84" b="31" a="255"/>\n{ind}  <text>{t}</text>\n{ind}  </Lyrics>\n')
    return m.group(0) + extra


xml = pattern.sub(add, xml)
open(dst, "w", encoding="utf-8").write(xml)
print(f"{len(added)} syllables transliterated:")
print("  " + "  ".join(f"{c}→{t}" for c, t in added))
