#!/usr/bin/env bash
# Checks what the kit needs and prints how to install what is missing. Changes nothing.
cd "$(dirname "$0")/.."
ok=0
check() { if command -v "$1" >/dev/null 2>&1; then echo "✓ $1  $($2 2>&1 | head -1)"; else echo "✗ $1 - $3"; ok=1; fi; }
mac=$([ "$(uname)" = Darwin ] && echo 1 || echo 0)
inst() { [ "$mac" = 1 ] && echo "brew install $1" || echo "sudo apt install $2"; }
check ffmpeg "ffmpeg -version" "$(inst ffmpeg ffmpeg)"
check ffprobe "ffprobe -version" "входит в ffmpeg"
check python3 "python3 --version" "$(inst python python3) (нужен 3.10+)"
check node "node --version" "https://nodejs.org (20.19+ или 22.13+)"
check whisper-cli "echo whisper.cpp" "$(inst whisper-cpp whisper-cpp) или сборка https://github.com/ggml-org/whisper.cpp"
check auto-editor "auto-editor --version" "необязательно: pip install auto-editor"
if command -v blender >/dev/null 2>&1 || [ -x /Applications/Blender.app/Contents/MacOS/Blender ]; then echo "✓ blender (3D-герои)"; else echo "• blender не найден - нужен только для 3D-героев: https://www.blender.org"; fi
model=$(python3 -c "import sys; sys.path.insert(0,'scripts'); import _kit; print(_kit.path(_kit.cfg()['whisperModel']))")
if [ -f "$model" ]; then echo "✓ модель Whisper: $model"; else echo "✗ модель Whisper: $model - bash scripts/get_model.sh"; ok=1; fi
[ -d node_modules ] && echo "✓ node_modules" || { echo "✗ node_modules - npm install"; ok=1; }
[ -d public/sfx/v2 ] && echo "✓ звуки public/sfx" || echo "• звуки ещё не созданы - npm run sfx"
if ffmpeg -hide_banner -filters 2>/dev/null | grep -q " firequalizer " && ffmpeg -hide_banner -filters 2>/dev/null | grep -q " adynamicequalizer "; then echo "✓ ffmpeg: firequalizer, adynamicequalizer"; else echo "✗ в вашем ffmpeg нет firequalizer или adynamicequalizer - обновите ffmpeg (нужен 6.1+)"; ok=1; fi
[ $ok = 0 ] && echo "Всё готово." || echo "Установите отмеченное ✗ и запустите снова."
exit $ok
