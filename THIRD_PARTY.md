# Сторонние компоненты

Код набора - MIT (`LICENSE`). В репозитории есть и чужие файлы со своими лицензиями:

| Что | Где | Лицензия |
|---|---|---|
| Шрифт Inter (подмножества кириллица + латиница) | `public/fonts/inter-*.woff2` | SIL Open Font License 1.1, `public/fonts/Inter-OFL.txt` |
| Шрифт JetBrains Mono (подмножества) | `public/fonts/jbmono-*.woff2` | SIL Open Font License 1.1, `public/fonts/JetBrainsMono-OFL.txt` |
| Шрифт Oswald (подмножества) | `public/fonts/oswald-*.woff2` | SIL Open Font License 1.1, `public/fonts/Oswald-OFL.txt` |
| Значки Lucide: все в `EndCard`, в промо - `send`, `mic`, `user` (остальные нарисованы для набора) | `src/kit/EndCard.tsx`, `src/promo/Promo.tsx` | ISC, `licenses/Lucide-LICENSE.txt` |

Ставятся отдельно и **не входят** в репозиторий:
| Что | Лицензия | Важно |
|---|---|---|
| [Remotion](https://www.remotion.dev) | Remotion License | **бесплатно для частных лиц и компаний до 3 человек**; компаниям больше - нужна платная лицензия Remotion ([remotion.dev/license](https://www.remotion.dev/license)) |
| [FFmpeg](https://ffmpeg.org) | LGPL/GPL (зависит от сборки) | |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) и модели Whisper | MIT | |
| [Blender](https://www.blender.org) | GPL | необязательно, только для 3D-героев |
| [auto-editor](https://github.com/WyattBlue/auto-editor) | Unlicense | необязательно |
| Скиллы `remotion-dev/skills`, `WyattBlue/auto-editor` | у авторов | ставятся командой `npx skills add` |

Звуки `public/sfx/` создаются генераторами набора (`npm run sfx`) и распространяются как код (MIT). Пример `public/example/` создаётся на вашем компьютере (`npm run sample`, голос - системный синтез речи) и в репозиторий не попадает. Музыки в наборе нет: `docs/MUSIC_AND_SFX.md`.
