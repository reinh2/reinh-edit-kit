"""Shared settings for the kit's Python scripts: reads kit.config.json from the repository root.

Every script works without the file (built-in defaults below); the file only changes defaults such as the
transcription language, the whisper.cpp model or your own voice presets. Command-line flags always win.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {
    "language": "ru",
    "whisperModel": "models/ggml-small.bin",
    "glossary": "glossary.json",
    "voicePresets": {},
}


def cfg():
    """kit.config.json merged over DEFAULTS (missing or broken file → defaults)."""
    out = dict(DEFAULTS)
    path = os.environ.get("KIT_CONFIG", os.path.join(ROOT, "kit.config.json"))
    try:
        with open(path) as f:
            out.update(json.load(f))
    except (OSError, ValueError):
        pass
    return out


def path(p):
    """A config path relative to the repository root, unless it is absolute."""
    return p if os.path.isabs(p) else os.path.join(ROOT, p)
