#!/bin/sh
# Download Coptic Hymns in English (CHIE) tracks from their page addresses.
#   sh tools/chie_get.sh https://www.coptichymnsinenglish.com/album/48/track/399 [more URLs…]
# Saves "CHIE <track> - <title> (<album>).<ext>" plus a .txt with the lyrics
# into ~/Downloads (or $OUT). Personal reference only; see church-content rights.
set -eu
OUT="${OUT:-$HOME/Downloads}"
[ $# -gt 0 ] || { echo "usage: $0 <track URL>…" >&2; exit 1; }
for url in "$@"; do
  track=$(printf '%s' "$url" | sed -n 's#.*/track/\([0-9]*\).*#\1#p')
  [ -n "$track" ] || { echo "not a track URL: $url" >&2; continue; }
  page=$(curl -sfL "$url") || { echo "can't open $url" >&2; continue; }
  audio=$(printf '%s' "$page" | grep -o 'https://cdn.coptichymnsinenglish.com/tracks/[A-Za-z0-9_-]*\.[a-z0-9]*' | head -1)
  [ -n "$audio" ] || { echo "no audio on $url" >&2; continue; }
  title=$(printf '%s' "$page" | sed -n 's#.*<title>\([^<]*\) · Coptic Hymns in English</title>.*#\1#p' | head -1 \
          | sed 's/&#x27;/'"'"'/g; s/&amp;/\&/g; s#[/:]#-#g')
  album=$(printf '%s' "$page" | sed 's/<[^>]*>/\n/g' | grep -v '^[[:space:]]*$' | sed -n '/^Get the app$/{n;p;q;}' \
          | sed 's/&#x27;/'"'"'/g; s/&amp;/\&/g; s#[/:]#-#g')
  name="CHIE $track - ${title:-track} (${album:-CHIE})"
  curl -sfL -o "$OUT/$name.${audio##*.}" "$audio" || { echo "download failed: $audio" >&2; continue; }
  # Lyrics: the text between "Share" and the footer's "Coptic Hymns in English".
  printf '%s' "$page" | sed 's/<[^>]*>/\n/g' | grep -v '^[[:space:]]*$' \
    | sed -n '/^Share$/,/^Coptic Hymns in English$/p' | sed '1d;$d' \
    | sed 's/&#x27;/'"'"'/g; s/&amp;/\&/g; s/&quot;/"/g' > "$OUT/$name.txt"
  [ -s "$OUT/$name.txt" ] || rm -f "$OUT/$name.txt"
  echo "saved $OUT/$name.${audio##*.}"
done
