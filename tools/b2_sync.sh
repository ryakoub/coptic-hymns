#!/bin/sh
# Uploads every recording in the coptic-hymns repo to the coptic-chanter-audio bucket, at its repo path.
# The key is in ~/.config/coptic-chanter/b2.key (key ID, then key), outside both repos.
# Skips files already there with the same size; logs one line per file; safe to run again.
cd ~/Developer/coptic-hymns || exit 1
K=~/.config/coptic-chanter/b2.key
ID=$(sed -n 1p "$K" | tr -d '[:space:]'); SECRET=$(sed -n 2p "$K" | tr -d '[:space:]')
BASE=https://coptic-chanter-audio.s3.us-east-005.backblazeb2.com
git ls-files 'content/*.m4a' 'content/*.mp3' 'content/**/*.m4a' 'content/**/*.mp3' | sort -u | while IFS= read -r P; do
  case "$P" in *.mp3) T=audio/mpeg;; *) T=audio/mp4;; esac
  ENC=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$P")
  SIZE=$(stat -f %z "$P")
  HAVE=$(curl -sS -I "$BASE/$ENC" 2>/dev/null | awk -F': ' 'tolower($1)=="content-length"{gsub("\r","",$2);print $2}')
  if [ "$HAVE" = "$SIZE" ]; then echo "skip $P"; continue; fi
  for try in 1 2 3; do
    CODE=$(curl -sS -o /dev/null -w "%{http_code}" --aws-sigv4 "aws:amz:us-east-005:s3" --user "$ID:$SECRET" \
      -H "Content-Type: $T" -H "x-amz-content-sha256: UNSIGNED-PAYLOAD" -T "$P" "$BASE/$ENC")
    [ "$CODE" = 200 ] && break; sleep 5
  done
  echo "$CODE $P"
done
echo "DONE"
