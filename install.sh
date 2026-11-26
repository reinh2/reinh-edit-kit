#!/usr/bin/env bash
# Reinh Edit Kit - установка одной командой.
#   В папке набора:   bash install.sh
#   Без клонирования: curl -fsSL https://raw.githubusercontent.com/reinh2/reinh-edit-kit/main/install.sh | bash
# Что делает (по шагам, каждый можно пропустить флагом):
#   1. ставит недостающее: ffmpeg, whisper.cpp, Node.js, Python, git (macOS - Homebrew, Linux - apt; уже стоящее не трогает)
#   2. npm install (Remotion и зависимости)
#   3. скачивает модель Whisper (small, ≈ 466 МБ) в models/
#   4. создаёт звуки (public/sfx) и пример исходников (public/example)
#   5. подключает скиллы для Claude Code и Codex, проверяет всё (doctor) и запускает тесты
# Флаги: --yes (не спрашивать), --skip-deps, --no-model, --model NAME (small|medium|large-v3-turbo), --no-sample, --no-test,
#        --dir PATH (куда клонировать при запуске через curl, по умолчанию ~/reinh-edit-kit)
set -euo pipefail

REPO="${KIT_REPO:-https://github.com/reinh2/reinh-edit-kit.git}"
YES=0 DEPS=1 MODEL=1 MODEL_NAME=small SAMPLE=1 TEST=1 DIR="$HOME/reinh-edit-kit"
while [ $# -gt 0 ]; do
  case "$1" in
    --yes|-y) YES=1 ;; --skip-deps) DEPS=0 ;; --no-model) MODEL=0 ;; --model) MODEL_NAME="$2"; shift ;;
    --no-sample) SAMPLE=0 ;; --no-test) TEST=0 ;; --dir) DIR="$2"; shift ;;
    -h|--help) sed -n '2,13p' "$0" 2>/dev/null || true; exit 0 ;;
    *) echo "неизвестный флаг: $1"; exit 2 ;;
  esac
  shift
done

say() { printf '\n\033[1;34m==>\033[0m \033[1m%s\033[0m\n' "$*"; }
ok() { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
has() { command -v "$1" >/dev/null 2>&1; }
names() { local n out=(); for n in "$@"; do case $n in whisper) out+=("whisper.cpp") ;; node) out+=("Node.js") ;; *) out+=("$n") ;; esac; done; echo "${out[*]}"; }
ask() { # ask "вопрос" → 0 (да) / 1 (нет); с --yes всегда да; без терминала (CI, агент) - нет
  [ "$YES" = 1 ] && return 0
  local a=""
  { printf '  %s [y/N] ' "$1" > /dev/tty; } 2>/dev/null || { echo "  $1 - нет терминала для ответа, считаю «нет» (или запустите с --yes)"; return 1; }
  read -r a < /dev/tty || true  # Ctrl+D = «нет»
  [ "$a" = y ] || [ "$a" = Y ] || [ "$a" = д ] || [ "$a" = Д ]
}

# --- 0. где мы: в папке набора или запуск через curl
HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || pwd)"
if [ -f "$HERE/package.json" ] && grep -q '"reinh-edit-kit"' "$HERE/package.json" 2>/dev/null; then
  KIT="$HERE"
else
  has git || { echo "Нужен git: macOS - xcode-select --install, Linux - sudo apt install git"; exit 1; }
  if [ -d "$DIR/.git" ]; then say "Набор уже скачан: ${DIR/#$HOME/~} (обновляю)"; git -C "$DIR" pull --ff-only || true
  else say "Скачиваю набор в ${DIR/#$HOME/~}"; mkdir -p "$(dirname "$DIR")"; (cd "$(dirname "$DIR")" && git clone --depth 1 "$REPO" "$(basename "$DIR")"); fi
  KIT="$DIR"
fi
cd "$KIT"
SHOW="${KIT/#$HOME/~}"  # the folder as ~/… on screen (no user name)
OS="$(uname -s)"
echo "Reinh Edit Kit → $SHOW ($OS)"

# --- 1. системные программы (только недостающие)
if [ "$DEPS" = 1 ]; then
  say "1/5 Программы: ffmpeg, whisper.cpp, Node.js, Python"
  need=()
  has ffmpeg || need+=(ffmpeg)
  has whisper-cli || need+=(whisper)
  if has node; then  # Remotion: Node ^20.19, ^22.13 или 24+
    node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit((a===20&&b>=19)||(a===22&&b>=13)||a>=24?0:1)' \
      || { warn "Node.js $(node -v) не подходит (нужен 20.19+, 22.13+ или 24+)"; need+=(node); }
  else need+=(node); fi
  has python3 || need+=(python)
  if [ ${#need[@]} -eq 0 ]; then ok "всё уже установлено"
  elif [ "$OS" = Darwin ]; then
    if ! has brew; then
      if ask "Нет Homebrew (менеджер программ для macOS). Установить с brew.sh?"; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        [ -x /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"
        [ -x /usr/local/bin/brew ] && eval "$(/usr/local/bin/brew shellenv)"
      else echo "Без Homebrew поставьте вручную: $(names "${need[@]}"). Потом запустите install.sh снова."; exit 1; fi
    fi
    pk=()
    for n in "${need[@]}"; do case $n in whisper) pk+=(whisper-cpp) ;; *) pk+=("$n") ;; esac; done
    say "brew install ${pk[*]}"; brew install "${pk[@]}"
  elif has apt-get; then
    sudo apt-get update -y
    for n in "${need[@]}"; do
      case $n in
        ffmpeg) sudo apt-get install -y ffmpeg ;;
        python) sudo apt-get install -y python3 ;;
        node) warn "Node.js 22.13+ или 24+: https://nodejs.org или nvm (apt часто даёт старую версию)"; sudo apt-get install -y nodejs npm || true ;;
        whisper)
          sudo apt-get install -y git cmake build-essential
          src="$HOME/.local/src/whisper.cpp"; mkdir -p "$HOME/.local/src" "$HOME/.local/bin"
          [ -d "$src" ] || git clone --depth 1 https://github.com/ggml-org/whisper.cpp "$src"
          cmake -S "$src" -B "$src/build" -DCMAKE_BUILD_TYPE=Release >/dev/null && cmake --build "$src/build" -j --config Release
          ln -sf "$src/build/bin/whisper-cli" "$HOME/.local/bin/whisper-cli"
          case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH"; warn "добавьте в ~/.bashrc: export PATH=\"\$HOME/.local/bin:\$PATH\"" ;; esac ;;
      esac
    done
  else
    echo "Не знаю менеджер пакетов этой системы. Поставьте вручную: $(names "${need[@]}") (docs/HARDWARE.md)"; exit 1
  fi
  for c in ffmpeg node python3 whisper-cli; do has "$c" && ok "$c" || warn "$c не найден"; done
fi

# --- 2. npm
say "2/5 Пакеты Node (Remotion)"
npm install --no-audit --no-fund --no-update-notifier
ok "node_modules"

# --- 3. модель Whisper
if [ "$MODEL" = 1 ]; then
  say "3/5 Модель Whisper ($MODEL_NAME)"
  f="models/ggml-${MODEL_NAME}.bin"
  if [ -s "$f" ]; then ok "уже есть: $f"; else bash scripts/get_model.sh "$MODEL_NAME"; fi
  if [ "$MODEL_NAME" != small ]; then warn "впишите \"whisperModel\": \"$f\" в kit.config.json"; fi
fi

# --- 4. звуки и пример
say "4/5 Звуки и пример исходников"
npm run --silent sfx >/dev/null && ok "public/sfx (v1, v2, v3)"
if [ "$SAMPLE" = 1 ]; then python3 scripts/example/make_sample.py && ok "public/example"; fi

# --- 5. скиллы, проверка, тесты
say "5/5 Скиллы, проверка, тесты"
bash scripts/install_skills.sh
bash scripts/doctor.sh || warn "doctor нашёл недостающее (см. выше)"
if [ "$TEST" = 1 ]; then npm test || warn "часть тестов не прошла - напишите в Issues с выводом выше"; fi

say "Готово"
cat <<EOF
  Папка набора:      $SHOW
  Посмотреть пример: cd $SHOW && npm run render:example   (черновики в out/)
  Предпросмотр:      npm run studio
  Ваши настройки:    kit.config.json и YOUR_RULES.md
  Ваш микрофон:      python3 scripts/audio/voice_master.py analyze проба.wav
  Дальше откройте папку в агенте (Claude Code, Codex, Gemini CLI) и напишите:
                     «вот дубли в footage/<дата>, смонтируй вертикальный ролик»
EOF
