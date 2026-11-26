# Изменения

## 0.1.0 - черновик
- Скиллы: `kit-studio`, `kit-rough-cut`, `kit-video-edit`, `kit-audio-post`, `kit-captions`, `kit-qc`.
- Монтаж: `edl_timeline.py` (EDL → таймлайн + флаги длины планов), `short_cut.py`, `make_proxies.py`.
- Проверка: `editorial_qc.py`, `ghost_frames.py`, `cut_strips.py`, `clip_check.py`, `contact_sheet.sh`, `scene_scan.sh`.
- Звук: `voice_master.py` (пресеты по типам микрофонов, `analyze`, `match`), `mix_bed.py`, `find_offset.mjs`, `sync_pieces.mjs`, генераторы SFX.
- Субтитры: `make_srt.py`, компонент `Captions`.
- Стили анимации `light` и `cine` (`themes`, `cine`, `chapter`: засвет, главы с часами), промо-ролик в трёх вариантах.
- Установка одной командой: `install.sh`.
- Remotion: `ScreenCam`, `Captions`, `EndCard`, `OverlayCard`/`Pill`/`Bar`, пример на синтетических исходниках.
