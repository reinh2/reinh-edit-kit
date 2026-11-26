#!/usr/bin/env bash
# Downloads a whisper.cpp model from the official whisper.cpp repository on Hugging Face into models/.
# Usage: bash scripts/get_model.sh [small|medium|large-v3-turbo]   (small ≈ 466 MB: good for Russian on a laptop)
set -euo pipefail
cd "$(dirname "$0")/.."
name="${1:-small}"
case "$name" in
  tiny|base|small|medium|large-v3|large-v3-turbo|tiny.en|base.en|small.en|medium.en) ;;
  -h|--help) echo "Usage: bash scripts/get_model.sh [small|medium|large-v3-turbo|large-v3|base|tiny]   (default small)"; exit 0 ;;
  *) echo "Неизвестная модель: $name. Есть: tiny, base, small, medium, large-v3, large-v3-turbo (и .en для английского)"; exit 2 ;;
esac
mkdir -p models
url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-${name}.bin"
echo "Скачиваю $url → models/ggml-${name}.bin"
curl -L --fail -o "models/ggml-${name}.bin.part" "$url"
mv "models/ggml-${name}.bin.part" "models/ggml-${name}.bin"
echo "Готово. Если модель не small - впишите её путь в kit.config.json → whisperModel."
