"""Turns the scan in cache/ into videos.json: the channel's hymn videos (talks, results and choir songs left out)."""
import glob, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache')

src = {}
def add(e, where):
    src.setdefault(e['id'], {'title': e.get('title'), 'src': []})['src'].append(where)
for tab in ['videos', 'streams', 'shorts']:
    for e in json.load(open(os.path.join(CACHE, f'ar_{tab}.json'))).get('entries') or []: add(e, tab)
for f in glob.glob(os.path.join(CACHE, 'pl/*.json')):
    d = json.load(open(f))
    for e in d.get('entries') or []: add(e, 'pl:' + d['id'])

meta = {}
for line in open(os.path.join(CACHE, 'meta.jsonl')):
    d = json.loads(line); meta[d['id']] = d

pls = {p['id']: p['title'] for p in json.load(open(os.path.join(CACHE, 'playlists.json')))['entries']}
hymn_playlists = {k for k, v in pls.items() if re.search('لحان|ألحان', v)}
# words that name a hymn or a part of a service
TYPE = re.compile('لحن|ألحان|الحان|مرد|ذكصولوج|طرح|مديح|هوس|مزمور|ابصالي|إبصالي|أبصالي|اسبسمس|اسبزمس|إسبسمس|هيتين|هيتيني|هيتتين|هيتني|القطعة|قطعة|ارباع|أرباع|مردات|ختام|تسبحة|ثيئوطوكي|ثيؤطوكي|مقدمة|الليلويا|هلليلويا|أجيوس|اجيوس|قسمة|توزيع|الناقوس|محير|برلكس|بارلكس|مزامير|ابركسيس|إبركسيس')
# talks, contests, results, choirs and other events
NOT = re.compile('ترنيم|مسابقة|الفائز|فائز|نتيجة|تصفيات|كلمة|شعار|مباركة|القناة الرسمية|كورال|حفل|عشرون عام|موضوع|إعلان|اعلان|البحوث|فاعليات|مؤتمر|^قبطى|لمهرجان الكرازة المرقسية$')

videos = []
for vid, s in src.items():
    m = meta.get(vid) or {'id': vid, 'title': s['title'], 'description': '', 'upload_date': None, 'duration': None,
                          'availability': 'unplayable'}       # private, or blocked outside its region
    t = m['title'] or ''
    if not t or NOT.search(t): continue
    in_hymn_playlist = any(x[3:] in hymn_playlists for x in s['src'] if x.startswith('pl:'))
    if not (in_hymn_playlist or TYPE.search(t)): continue
    playlist = next((pls[x[3:]] for x in s['src'] if x.startswith('pl:') and x[3:] in pls), None)
    videos.append(dict(id=vid, title=t, upload_date=m['upload_date'], duration=m['duration'],
                       availability=m.get('availability') or 'unplayable', playlist=playlist))

videos.sort(key=lambda v: (v['upload_date'] or '', v['id']))
json.dump(videos, open(os.path.join(HERE, 'videos.json'), 'w'), ensure_ascii=False, indent=0)
print(len(src), 'videos on the channel,', len(videos), 'hymn videos')
