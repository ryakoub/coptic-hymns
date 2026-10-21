#!/bin/zsh
# A MuseScore score, ready to sync: its PDF with a transliteration line, its notes' and bars' positions and times,
# and its audio as MuseScore plays it.
#
#   zsh tools/scores/prepare.sh <score.mscz or .mscx> <out folder>
#
# Writes into the folder: score.mscx (with the transliteration line), score.pdf, score.spos (notes),
# score.mpos (bars) and score.wav. The original score is not changed.
set -e
SCORE=$1 OUT=$2
[[ -f $SCORE && -n $OUT ]] || { echo "usage: zsh tools/scores/prepare.sh <score.mscz|.mscx> <out folder>"; exit 1; }
MSCORE="/Applications/MuseScore 4.app/Contents/MacOS/mscore"
[[ -x $MSCORE ]] || { echo "MuseScore 4 is needed in /Applications"; exit 1; }
HERE=${0:A:h}
mkdir -p $OUT
TMP=$(mktemp -d)
if [[ $SCORE == *.mscz ]]; then
  unzip -q -o $SCORE -d $TMP
  SRC=$(ls $TMP/*.mscx | head -1)
else
  SRC=$SCORE
fi
python3 -I $HERE/transliterate.py $SRC $OUT/score.mscx
for ext in pdf spos mpos wav; do
  $MSCORE -o $OUT/score.$ext $OUT/score.mscx >/dev/null 2>&1
done
rm -rf $TMP
ls -la $OUT
