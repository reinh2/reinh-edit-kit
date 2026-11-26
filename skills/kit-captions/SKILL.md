---
name: kit-captions
description: 'Captions: local whisper.cpp word timestamps of the final mix, glossary fixes of tech terms (glossary.json), word-by-word captions of up to 3 words for vertical videos (src/kit/Captions.tsx) and a separate .srt for every video (make_srt.py); no burn-in for long videos. Use for "субтитры", "титры", "captions", "srt".'
---

# Субтитры

1. **Слова - по финальному монтажу**, не по исходникам: `python3 scripts/captions/make_srt.py <финал.mp4> exports/<ролик>/<имя>.srt` (язык и модель - `kit.config.json`). Если слова уже есть (`short_cut.py` → `words.json`) - `--words words.json`.
2. **Глоссарий** `glossary.json`: термины, имена, бренды (`[регулярное выражение, как писать]`). Пополнять после каждого ролика. Числа - цифрами.
3. **Вертикальный ролик:** компонент `Captions` - страницы до 3 слов (`kit.config.json` «captions»), новая страница после пунктуации и на новом куске EDL, текущее слово акцентом, скрывать на полноэкранных вставках (`hide`). Позицию сверить с интерфейсом площадки: низ кадра закрывают кнопки и подпись.
4. **Длинный ролик:** не вжигать; отдать `.srt` (строки ≤ 42 символов, 1-2 строки, 1-6 с).
5. **QC:** прослушать 3 случайных куска по 10 с - каждое слово совпадает с речью, подсветка вовремя (±2 кадра), нет «висящих» слов. Whisper растягивает слова на паузах: концы реплик в `.srt` обрезаны до начала следующей, но читать результат глазами обязательно.
