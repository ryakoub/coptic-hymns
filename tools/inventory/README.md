# Hymn inventory

Builds [docs/app/hymn-inventory.md](../../docs/app/hymn-inventory.md): every hymn in the app, plus every Mahragan hymn on the youth-bishopric YouTube channel (https://www.youtube.com/@youth-bishopric), with its season and service.

```
zsh tools/inventory/scan.sh           # about 10 minutes; only when the channel has new videos
python3 tools/inventory/collect.py    # cache/ → videos.json (hymn videos only)
python3 tools/inventory/inventory.py  # → docs/app/hymn-inventory.json
python3 tools/inventory/write_md.py   # → docs/app/hymn-inventory.md
```

- `videos.json` is kept in git so the inventory can be rebuilt without scanning again; `cache/` is not.
- `parse.py` reads year, stage and level from a title and strips them to leave the hymn's name.
- `rules.py` maps hymn names to one hymn each, with its English and Arabic title, its places in `catalog/library.json`, and the folder in `content/` when the hymn is already in the app. For a hymn in the app, the inventory shows its own titles and places (its `info.json`, edited with `tools/titles.py`); the rule's only place it while it is not added yet. A name no rule matches is left out of the inventory, so after a scan check for unmatched names:

  ```
  python3 -c "import json,sys; sys.path.insert(0,'tools/inventory'); from parse import parse; from rules import classify
  [print(o['id'], o['title']) for o in parse(json.load(open('tools/inventory/videos.json'))) if not classify(o['name'])]"
  ```

- When a hymn appears more than once, the most recent video is kept, skipping those in `unavailable.txt`. YouTube often answers "not available" when it is rate limiting, so add a video there only after it fails on several tries, hours apart.
