#!/usr/bin/env bash
# Links the kit's skills for coding agents and prints the official installs of the Remotion and auto-editor skills.
#   .claude/skills/kit-*  → Claude Code      .agents/skills/kit-*  → Codex and other agents reading .agents/skills
# The links are already in the repository; run this after moving the folder or to add the skills to another project:
#   bash scripts/install_skills.sh [/path/to/other/project]
set -euo pipefail
kit="$(cd "$(dirname "$0")/.." && pwd)"
dest="${1:-$kit}"
for d in .claude/skills .agents/skills; do
  mkdir -p "$dest/$d"
  for s in "$kit"/skills/kit-*; do
    n=$(basename "$s")
    if [ "$dest" = "$kit" ]; then ln -sfn "../../skills/$n" "$dest/$d/$n"; else ln -sfn "$s" "$dest/$d/$n"; fi
  done
done
echo "Скиллы набора подключены в $dest (.claude/skills, .agents/skills)."
echo
echo "Официальные скиллы (ставятся отдельно, от их авторов):"
echo "  npx skills add remotion-dev/skills      # Remotion: анимации, субтитры, рендер"
echo "  npx skills add WyattBlue/auto-editor    # auto-editor: резка по тишине, экспорт в монтажные программы"
