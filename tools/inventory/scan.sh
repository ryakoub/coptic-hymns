#!/bin/zsh
# Scans the youth-bishopric channel into tools/inventory/cache (not in git):
# every video id from the tabs and playlists, then each video's title, description, date and duration.
# Takes about 10 minutes. If YouTube refuses with "403", run `brew upgrade yt-dlp`.
cd "$(dirname "$0")" && mkdir -p cache/pl && cd cache || exit 1
CHANNEL=https://www.youtube.com/@youth-bishopric
EA=(--extractor-args "youtube:lang=ar")   # the original Arabic titles, not YouTube's translations

for tab in videos streams shorts; do
  yt-dlp $EA --flat-playlist -J "$CHANNEL/$tab" > ar_$tab.json 2>/dev/null
done
yt-dlp $EA --flat-playlist -J "$CHANNEL/playlists" > playlists.json 2>/dev/null
python3 -I -c "import json; [print(p['id']) for p in json.load(open('playlists.json'))['entries']]" > pl_ids.txt
while read -r id; do
  yt-dlp $EA --flat-playlist -J "https://www.youtube.com/playlist?list=$id" > pl/$id.json 2>/dev/null &
  while (( $(jobs | wc -l) >= 6 )); do sleep 0.3; done
done < pl_ids.txt
wait

python3 -I -c "
import json, glob
ids = []
for f in ['ar_videos.json', 'ar_streams.json', 'ar_shorts.json'] + glob.glob('pl/*.json'):
    for e in json.load(open(f)).get('entries') or []:
        if e['id'] not in ids: ids.append(e['id'])
open('all_ids.txt', 'w').write('\n'.join(ids) + '\n')
print(len(ids), 'videos')"

rm -rf chunks meta && mkdir -p chunks meta
split -l 150 all_ids.txt chunks/part_
for f in chunks/part_*; do
  sed 's|^|https://www.youtube.com/watch?v=|' $f > $f.urls
  yt-dlp $EA --skip-download --ignore-errors --no-warnings \
    -O '%(.{id,title,description,upload_date,duration,availability})j' -a $f.urls > meta/${f:t}.jsonl 2> meta/${f:t}.err &
done
wait
cat meta/*.jsonl > meta.jsonl
echo "$(wc -l < meta.jsonl) videos read; $(cat meta/*.err | grep -c ERROR) private or unavailable"
