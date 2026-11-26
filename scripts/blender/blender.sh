#!/usr/bin/env bash
# Runs Blender wherever it is installed: $BLENDER, `blender` on PATH (Homebrew, Linux packages), macOS Blender.app
# from blender.org (/Applications or ~/Applications). Used by `npm run promo:3d` / `mics:3d` and doctor.sh.
#   bash scripts/blender/blender.sh -b -P scripts/blender/mics.py -- sm7b
#   bash scripts/blender/blender.sh --find      # only print the path (exit 1 if not found)
for b in "${BLENDER:-}" "$(command -v blender 2>/dev/null)" /Applications/Blender.app/Contents/MacOS/Blender \
         "$HOME/Applications/Blender.app/Contents/MacOS/Blender"; do
  if [ -n "$b" ] && [ -x "$b" ]; then
    [ "${1:-}" = "--find" ] && { echo "$b"; exit 0; }
    exec "$b" "$@"
  fi
done
[ "${1:-}" = "--find" ] && exit 1
echo "Blender не найден. Он нужен только для 3D-героев: https://www.blender.org" >&2
echo "Если он стоит в другом месте: BLENDER=/путь/к/blender npm run promo:3d" >&2
exit 127
