#!/usr/bin/env bash
# Detects hard visual changes (cuts, full-frame graphics swaps) and writes shot timing stats.
# Usage: bash scripts/ref/scene_scan.sh VIDEO OUT_DIR [THRESHOLD]
#   Writes OUT_DIR/scenes.tsv (time score), OUT_DIR/midpoints.txt (one per shot), prints stats.
# Analysis runs at 15 fps / 480 px to stay cheap; soft in-shot animations are NOT counted.
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo 'Usage: bash scripts/ref/scene_scan.sh VIDEO OUT_DIR [THRESHOLD]' >&2
  exit 2
fi
VIDEO="$1"; OUT="$2"; TH="${3:-0.18}"
[[ -f "$VIDEO" ]] || { echo "Missing video: $VIDEO" >&2; exit 1; }
mkdir -p "$OUT"
ffmpeg -hide_banner -nostats -loglevel error -i "$VIDEO" -an \
  -vf "fps=15,scale=480:-2,select='gt(scene,$TH)',metadata=print:file=$OUT/scenes.txt" -f null -
paste -d' ' <(grep -o 'pts_time:[0-9.]*' "$OUT/scenes.txt" | cut -d: -f2) \
            <(grep -o 'scene_score=[0-9.]*' "$OUT/scenes.txt" | cut -d= -f2) > "$OUT/scenes.tsv"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VIDEO")
awk -v dur="$DUR" 'BEGIN{p=0} {print (p+$1)/2; p=$1} END{print (p+dur)/2}' "$OUT/scenes.tsv" > "$OUT/midpoints.txt"
awk -v dur="$DUR" '{d=$1-p; p=$1; n++; s+=d; if(d<2)a++; else if(d<5)b++; else if(d<10)c++; else e++}
  END{d=dur-p; n++; s+=d; printf "shots=%d mean=%.2fs cuts_per_min=%.2f <2s=%d 2-5s=%d 5-10s=%d >10s=%d\n", n, s/n, (n-1)/(dur/60), a, b, c, e}' \
  "$OUT/scenes.tsv"
