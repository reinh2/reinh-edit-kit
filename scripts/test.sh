#!/usr/bin/env bash
# All checks of the kit: Python unit tests (ffmpeg needed), syntax of Node and shell scripts, TypeScript.
set -euo pipefail
cd "$(dirname "$0")/.."
fail=0
for d in scripts/edit/tests scripts/qc/tests scripts/audio/tests scripts/captions/tests; do
  echo "== $d"
  out=$(python3 -m unittest discover -s "$d" 2>&1) || fail=1
  echo "$out" | tail -3
done
echo "== node --check"
for f in scripts/audio/*.mjs; do node --check "$f" || fail=1; done
echo "== bash -n"
for f in scripts/ref/*.sh scripts/*.sh; do bash -n "$f" || fail=1; done
if [ -d node_modules ]; then echo "== tsc"; npx tsc || fail=1; else echo "== tsc skipped (run npm install)"; fi
[ $fail = 0 ] && echo "ALL OK" || { echo "SOME CHECKS FAILED"; exit 1; }
