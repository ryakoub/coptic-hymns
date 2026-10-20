"""Builds docs/app/hymn-inventory.json: channel hymns (most recent version kept) plus the hymns already in the app."""
import glob, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rules import classify
from parse import parse

SITE = os.path.normpath(os.path.join(HERE, '../..'))
parsed = parse(json.load(open(os.path.join(HERE, 'videos.json'))))

# what's in content/ now
existing = {}
for f in sorted(glob.glob(os.path.join(SITE, 'content/**/info.json'), recursive=True)):
    d = json.load(open(f)); folder = os.path.dirname(f)
    t = d.get('titles', {})
    existing[os.path.basename(folder)] = dict(id=os.path.basename(folder), ar=t.get('arabic', ''), en=t.get('english') or d.get('title', ''),
                                              places=d.get('places', []), text=d.get('text', ''))
library = json.load(open(os.path.join(SITE, 'catalog/library.json')))
coll = {c['id']: c for g in library['groups'] for c in g['collections']}
services = {s['id']: s['titles'] for s in library['services']}

def place_label(p):
    c, s = p.split('/')
    # a section is a service or has its own id and titles; "midnight" is short for "midnight-praises"
    secs = {(x.get('service') or x['id']): (services.get(x.get('service')) or x.get('titles') or {}) for x in coll[c]['sections']}
    key = s if s in secs else next(k for k in secs if k.startswith(s))
    st = secs[key]
    ct = coll[c]['titles']
    return {'collection': c, 'english': f"{ct['english']} · {st['english']}", 'arabic': f"{ct['arabic']} · {st.get('arabic', st['english'])}"}

groups = defaultdict(list)
info = {}
for o in parsed:
    c = classify(o['name'])
    if not c: continue
    groups[c['key']].append(o)
    info[c['key']] = c

# YouTube's "not available" is usually rate limiting, so only videos listed in unavailable.txt count as unplayable.
UNAVAILABLE = {l.strip() for l in open(os.path.join(HERE, 'unavailable.txt')) if l.strip() and not l.startswith('#')}
def playable(o): return o['id'] not in UNAVAILABLE
FALLBACKS = {k: v for k, v in json.load(open(os.path.join(HERE, 'fallbacks.json'))).items() if not k.startswith('_')}
# Same year and upload day (2025 went up in one day): prefer the school stages, youngest first, then the video id.
STAGE_ORDER = ['kg', 'grades-1-2', 'grades-3-4', 'grades-5-6', 'ms', 'hs', 'college', 'graduates', 'servants',
               'cana-family', 'simeon-elders', 'adult-learners', 'didymus', 'special-needs', None]
def recency(o): return (o['year'] or 0, o['date'] or '', -STAGE_ORDER.index(o['stage']), o['id'])

hymns = []
for key, vids in groups.items():
    c = info[key]
    vids.sort(key=recency, reverse=True)
    best = next((v for v in vids if playable(v)), vids[0])
    # in the app: the folder the rule names, or one named after the hymn (added from this inventory)
    in_app = c['existing'] if c['existing'] in existing else key if key in existing else None
    video = dict(id=best['id'], url=f"https://www.youtube.com/watch?v={best['id']}", title=best['title'], year=best['year'],
                 stage=best['stage'], level=best['level'], uploaded=best['date'], duration=best['duration'], playable=playable(best))
    if not playable(best) and key in FALLBACKS:
        f = FALLBACKS[key]
        video = dict(id=f['id'], url=f"https://www.youtube.com/watch?v={f['id']}", title=f['title'], year=f['year'], stage=f['stage'],
                     level=f['level'], uploaded=None, duration=None, playable=True, channel=f['channel'])
    # A hymn in the app shows its own titles and places (its info.json, edited with tools/titles.py);
    # the rules only place hymns not added yet.
    english, arabic, places = c['english'], c['arabic'], c['places']
    if in_app:
        e = existing[in_app]
        english, arabic = e['en'] or english, e['ar'] or arabic
        places = [p if isinstance(p, str) else p['place'] for p in e['places']] or places
    hymns.append(dict(
        key=key, english=english, arabic=arabic, places=[place_label(p) | {'id': p} for p in places],
        status='in app' if in_app else 'new', app_id=in_app, note=c['note'],
        video=video,
        newest_unplayable=[dict(id=v['id'], year=v['year']) for v in vids if recency(v) > recency(best) and not playable(v)],
        other_versions=[dict(id=v['id'], year=v['year'], stage=v['stage'], level=v['level']) for v in vids if v is not best],
    ))

# hymns in the app that the channel doesn't have
matched = {h['app_id'] for h in hymns if h['app_id']}
for r in existing.values():
    if r['id'] in matched or r['text']: continue          # English recordings are tunes of a text already listed
    pl = [p if isinstance(p, str) else p['place'] for p in r['places']]
    hymns.append(dict(key=r['id'], english=r['en'], arabic=r['ar'], places=[place_label(p) | {'id': p} for p in pl],
                      status='in app', app_id=r['id'], note='not on the youth-bishopric channel', video=None,
                      newest_unplayable=[], other_versions=[]))

order = [c['id'] for g in library['groups'] for c in g['collections']]
hymns.sort(key=lambda h: (order.index(h['places'][0]['collection']) if h['places'] else 99, h['places'][0]['id'] if h['places'] else '', h['english']))
json.dump(hymns, open(os.path.join(SITE, 'docs/app/hymn-inventory.json'), 'w'), ensure_ascii=False, indent=1)

from collections import Counter
print('hymns', len(hymns), Counter(h['status'] for h in hymns))
print('new, by collection:', Counter(h['places'][0]['collection'] for h in hymns if h['status'] == 'new'))
print('new with check:', sum(1 for h in hymns if h['status'] == 'new' and 'check' in h['note']))
print('new whose best video is unplayable:', [h['key'] for h in hymns if h['status'] == 'new' and not h['video']['playable']])
print('in app but channel has newer unplayable:', sum(1 for h in hymns if h['newest_unplayable']))
