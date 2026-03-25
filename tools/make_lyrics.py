import json, textwrap

data = """
4.75 | Verse 1 Coptic text | English meaning
21.57 | Verse 2 Coptic text | English meaning
39.40 | Verse 3 Coptic text | English meaning
57.31 | Verse 4 Coptic text | English meaning
75.13 | Verse 5 Coptic text | English meaning
93.26 | Verse 6 Coptic text | English meaning
""".strip()

out = []
for line in data.splitlines():
    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 2:
        continue
    start = float(parts[0])
    coptic = parts[1]
    english = parts[2] if len(parts) > 2 else ""
    out.append({
        "start": start,
        "coptic": coptic,
        "translations": {"english": english}
    })

print(json.dumps(out, ensure_ascii=False, indent=2))