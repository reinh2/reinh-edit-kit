#!/usr/bin/env bash
# Builds labelled-by-index contact sheets from a list of timestamps (read-only on the source).
# Usage: bash scripts/ref/contact_sheet.sh VIDEO TIMES_FILE OUT_DIR [COLS] [ROWS] [WIDTH]
#   TIMES_FILE: one timestamp in seconds per line (e.g. shot midpoints from scene_scan.sh).
#   Writes OUT_DIR/frames/NNN.jpg, OUT_DIR/sheet_K.jpg and OUT_DIR/index.tsv (cell -> timestamp).
# ffmpeg here has no drawtext, so timestamps live in index.tsv, ordered left-to-right, top-to-bottom.
set -euo pipefail
if [[ $# -lt 3 ]]; then
  echo 'Usage: bash scripts/ref/contact_sheet.sh VIDEO TIMES_FILE OUT_DIR [COLS] [ROWS] [WIDTH]' >&2
  exit 2
fi
VIDEO="$1"; TIMES="$2"; OUT="$3"; COLS="${4:-5}"; ROWS="${5:-4}"; W="${6:-384}"
[[ -f "$VIDEO" ]] || { echo "Missing video: $VIDEO" >&2; exit 1; }
[[ -f "$TIMES" ]] || { echo "Missing times file: $TIMES" >&2; exit 1; }
mkdir -p "$OUT/frames"
: > "$OUT/index.tsv"
PER=$((COLS * ROWS))
i=0
while read -r t; do
  [[ -z "$t" ]] && continue
  f=$(printf '%03d' "$i")
  ffmpeg -hide_banner -loglevel error -y -ss "$t" -i "$VIDEO" -frames:v 1 -vf "scale=$W:-2" -q:v 4 "$OUT/frames/$f.jpg" </dev/null
  printf '%s\tsheet_%d\tcell_%d\t%s\n' "$f" $((i / PER)) $((i % PER + 1)) "$t" >> "$OUT/index.tsv"
  i=$((i + 1))
done < "$TIMES"
n=$(( (i + PER - 1) / PER ))
for ((k = 0; k < n; k++)); do
  ffmpeg -hide_banner -loglevel error -y -framerate 1 -start_number $((k * PER)) -i "$OUT/frames/%03d.jpg" \
    -frames:v 1 -vf "tile=${COLS}x${ROWS}:padding=4:color=white" -q:v 3 "$OUT/sheet_$k.jpg" </dev/null
done
echo "frames=$i sheets=$n -> $OUT"
