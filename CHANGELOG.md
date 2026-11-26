# Изменения

## 0.1.0 - черновик
- Скиллы: `kit-studio`, `kit-rough-cut`, `kit-video-edit`, `kit-audio-post`, `kit-captions`, `kit-qc`.
- Монтаж: `edl_timeline.py` (EDL → таймлайн + флаги длины планов), `short_cut.py`, `make_proxies.py`.
- Проверка: `editorial_qc.py`, `ghost_frames.py`, `cut_strips.py`, `clip_check.py`, `contact_sheet.sh`, `scene_scan.sh`.
- Звук: `voice_master.py` (пресеты по типам микрофонов, `analyze`, `match`), `mix_bed.py`, `find_offset.mjs`, `sync_pieces.mjs`, генераторы SFX.
- Субтитры: `make_srt.py`, компонент `Captions`.
- Стили анимации `light` и `cine` (`themes`, `cine`, `chapter`: засвет, главы с часами), промо-ролик в трёх вариантах.
- 3D-герои из Blender: `hero_common.py`, компонент `Hero3D`; `promo_heroes.py` - хлопушка с полями «сцена» и «дубль» и кейс для техники с тремя накопителями; `mics.py` - пять популярных микрофонов (Blue Yeti, HyperX SoloCast, Shure SM7B, Rode PodMic, DJI Mic Mini 2) по реальным формам, без логотипов, плюс общий кадр `lineup`; `blender.sh` находит Blender (команда `blender`, `Blender.app` или переменная `BLENDER`).
- Установка одной командой: `install.sh` (без терминала не падает, проверяет версию Node так же, как Remotion).
- Remotion: `ScreenCam`, `Captions`, `EndCard`, `OverlayCard`/`Pill`/`Bar`, пример на синтетических исходниках.
- Remotion 4.0.547 (`npm audit`: 0 уязвимостей). У всех скриптов есть `--help`.
- Гайд по установке (`src/guide/`): композиция `Guide` из настоящих снимков окон, `npm run guide:shots`, `guide:vo`, `render:guide`; помощники съёмки окон `scripts/example/guide_capture.sh`.
- Установщик, `doctor.sh` и скрипты печатают пути как `~/…` (без имени пользователя), npm без лишних уведомлений.
