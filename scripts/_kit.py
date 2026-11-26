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


def shown(p):
    """a path for the screen: relative inside the current folder, ~/… in the home folder, the bare name for temp files"""
    p = os.path.abspath(p)
    cwd, home = os.getcwd(), os.path.expanduser("~")
    if p.startswith(cwd + os.sep):
        return os.path.relpath(p, cwd)
    if p.startswith(home + os.sep):
        return "~" + p[len(home):]
    return os.path.basename(p)


def path(p):
    """A config path relative to the repository root, unless it is absolute."""
    return p if os.path.isabs(p) else os.path.join(ROOT, p)
