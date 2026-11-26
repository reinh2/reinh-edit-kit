#!/usr/bin/env python3
"""Makes the example's source material, so the kit renders without anyone's footage:
  public/example/screen.mp4   synthetic screen recording (Remotion composition SampleScreen);
  public/example/voice.wav    a synthetic voice: macOS `say` (Milena), else espeak-ng, else a tone; then voice_master;
  public/example/meta.json    word times (whisper.cpp if installed, else an estimate) and the voice length.
Usage: python3 scripts/example/make_sample.py [--skip-screen]
Generated files stay local (public/example is in .gitignore): system voices are not ours to redistribute."""
import argparse, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "edit"))
import _kit  # noqa: E402
import short_cut  # noqa: E402

TEXT = ("Это пример из набора. Сначала лицо и карточка на нужном слове. "
        "Потом запись экрана, и камера сама наезжает на важную строку. В конце карточка с контактами.")
OUT = os.path.join(ROOT, "public", "example")


def sh(*cmd, **kw):
    print("→", " ".join(cmd[:4]), "…", flush=True)
    return subprocess.run(cmd, check=True, cwd=ROOT, **kw)


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout)


def synth_voice(raw):
    if shutil.which("say"):
        voices = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
        v = ["-v", "Milena"] if "Milena" in voices else []
        sh("say", *v, "-o", raw + ".aiff", TEXT)
        sh("ffmpeg", "-v", "error", "-y", "-i", raw + ".aiff", "-ar", "48000", "-ac", "1", raw)
        return "macOS say"
    if shutil.which("espeak-ng"):
        sh("espeak-ng", "-v", "ru", "-s", "150", "-w", raw + ".tmp.wav", TEXT)
        sh("ffmpeg", "-v", "error", "-y", "-i", raw + ".tmp.wav", "-ar", "48000", "-ac", "1", raw)
        return "espeak-ng"
    # no speech engine: a voice-like tone in «words», so the pipeline still runs
    sh("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=180:d=10", "-af", "volume='0.3*(0.5+0.5*sin(2*PI*3*t))':eval=frame", "-ar", "48000", "-ac", "1", raw)
    return "tone (install espeak-ng for a voice)"


def word_times(voice, d):
    c = _kit.cfg()
    model = _kit.path(c["whisperModel"])
    piece = [{"id": "S", "a": 0, "b": d, "text": TEXT}]
    tl, _ = short_cut.plan(piece, 30)
    if shutil.which("whisper-cli") and os.path.exists(model):
        tmp = tempfile.mkdtemp()
        sh("ffmpeg", "-v", "error", "-y", "-i", voice, "-ac", "1", "-ar", "16000", f"{tmp}/a.wav")
        subprocess.run(["whisper-cli", "-m", model, "-f", f"{tmp}/a.wav", "-l", c["language"], "-ojf", "-ml", "1", "-sow", "-of", f"{tmp}/w", "-np"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        W = [(s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000, s["text"].strip()) for s in json.load(open(f"{tmp}/w.json"))["transcription"]]
        return short_cut.align(tl, W), "whisper.cpp"
    # estimate: time proportional to letters, from the first to the last sound
    toks = TEXT.split()
    total = sum(len(t) + 2 for t in toks)
    t, out = 0.15, []
    span = d - 0.3
    for w in toks:
        L = span * (len(w) + 2) / total
        out.append({"w": w, "start": round(t, 3), "end": round(t + L * 0.85, 3), "seg": 0})
        t += L
    return out, "estimate (install whisper-cli + a model for real word times)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-screen", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if not a.skip_screen:
        sh("npx", "remotion", "render", "SampleScreen", os.path.join(OUT, "screen.mp4"), "--muted", "--log=error")
    raw = os.path.join(tempfile.mkdtemp(), "raw.wav")
    src = synth_voice(raw)
    voice = os.path.join(OUT, "voice.wav")
    sh(sys.executable, "scripts/audio/voice_master.py", "voice", raw, voice, "--preset", "neutral")
    d = dur(voice)
    words, how = word_times(voice, d)
    json.dump({"words": words, "voiceDur": round(d, 3)}, open(os.path.join(OUT, "meta.json"), "w"), ensure_ascii=False, indent=1)
    print(f"sample ready: voice {d:.1f} s ({src}), words: {how} → public/example/")


if __name__ == "__main__":
    main()
