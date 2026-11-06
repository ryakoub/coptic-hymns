#!/bin/sh
# Uploads the recordings in the coptic-hymns repo that the coptic-chanter-audio bucket doesn't have yet (or has
# at another size), at their repo paths. The key is in ~/.config/coptic-chanter/b2.key (key ID, then key).
# It lists the bucket once (one request per 1,000 files) instead of asking about each file: per-file checks are
# Backblaze "Class B transactions", capped at 2,500 a day free, and going over the cap stops ALL downloads
# (Nov 6, 2026). Safe to run again.
cd ~/Developer/coptic-hymns || exit 1
K=~/.config/coptic-chanter/b2.key
ID=$(sed -n 1p "$K" | tr -d '[:space:]'); SECRET=$(sed -n 2p "$K" | tr -d '[:space:]')
BASE=https://coptic-chanter-audio.s3.us-east-005.backblazeb2.com
TMP=$(mktemp -d)
TOKEN=""
: > "$TMP/have"
while :; do
  Q="list-type=2&max-keys=1000"; [ -n "$TOKEN" ] && Q="$Q&continuation-token=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$TOKEN")"
  curl -s --aws-sigv4 "aws:amz:us-east-005:s3" --user "$ID:$SECRET" -H "x-amz-content-sha256: UNSIGNED-PAYLOAD" "$BASE/?$Q" > "$TMP/page.xml" || { echo "listing failed"; exit 1; }
  grep -q "<Error>" "$TMP/page.xml" && { cat "$TMP/page.xml"; exit 1; }
  TOKEN=$(python3 - "$TMP/page.xml" "$TMP/have" <<'PY'
import sys, xml.etree.ElementTree as ET
ns = {'s': 'http://s3.amazonaws.com/doc/2006-03-01/'}
root = ET.parse(sys.argv[1]).getroot()
with open(sys.argv[2], 'a') as out:
    for c in root.findall('s:Contents', ns):
        out.write(f"{c.find('s:Size', ns).text} {c.find('s:Key', ns).text}\n")
t = root.find('s:NextContinuationToken', ns)
print(t.text if root.findtext('s:IsTruncated', '', ns) == 'true' and t is not None else '')
PY
)
  [ -z "$TOKEN" ] && break
done
echo "$(wc -l < "$TMP/have" | tr -d ' ') files in the bucket"
git ls-files 'content/*.m4a' 'content/*.mp3' | while read P; do
  SIZE=$(stat -f %z "$P")
  grep -qxF "$SIZE $P" "$TMP/have" && continue
  case "$P" in *.mp3) T=audio/mpeg;; *) T=audio/mp4;; esac
  ENC=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$P")
  for TRY in 1 2 3; do
    CODE=$(curl -s -o /dev/null -w "%{http_code}" --aws-sigv4 "aws:amz:us-east-005:s3" --user "$ID:$SECRET" \
      -H "Content-Type: $T" -H "x-amz-content-sha256: UNSIGNED-PAYLOAD" -T "$P" "$BASE/$ENC")
    [ "$CODE" = 200 ] && break
  done
  echo "$CODE $P"
done
rm -rf "$TMP"; echo DONE
