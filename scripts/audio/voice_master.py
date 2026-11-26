#!/usr/bin/env python3
"""Voice and master in FFmpeg — one stable, gentle standard instead of inventing a chain every time:
natural timbre, clear speech, controlled lows, even dynamics. Not maximum noise reduction, not maximum loudness.

Stages:
  voice    one mic → processed voice stem at −17 LUFS (headroom for SFX/music), with a mic preset;
  master   finished mix (video or audio) → −15 LUFS, LRA ≤ 7, true peak −1.5 dBTP, AAC-LC 320k 48 kHz stereo;
  measure  EBU R128 of a file (I, LRA, TP);
  match    EQ match of your mic to a reference recording you like (linear-phase FIR), a preset for kit.config.json;
  analyze  a raw recording of YOUR mic → level, noise floor, tonal balance against average speech, and a suggested
           preset to paste into kit.config.json («voicePresets») — see docs/MIC_CALIBRATION.md;
  presets  list the presets.

Presets — every mic, room and voice is different, so they are starting points; the final judge is your ear:
  checked by ear on real recordings (one voice, one room — still starting points for you):
    solocast   USB condenser on a desk (HyperX SoloCast): HP 70 · +2 dB shelf @ 120 · −2 dB @ 220 · +1.5 dB @ 3.5 kHz · 2.5:1
    lav        wireless lav on the chest (DJI Mic Mini 2): level → −30 LUFS · profile denoise 3 dB · HP 80 · +2 dB @ 120 ·
               −3 dB @ 800 · +5 dB @ 3.8 kHz · 2.5:1 · de-esser · pause expander ≤ −5 dB
  generic by mic type (built from the same rules, NOT checked by ear on every mic — run `analyze` and listen):
    usb-condenser, dynamic, lav-generic, headset, camera (built-in mic of a phone/camera/laptop), neutral
Profile denoise needs 2–3 s of silence somewhere in the recording (or --noise START-END).

Rules learned on real videos (keep them):
  - the compressor works on the raw level of the recording (threshold 0.10 ≈ −20 dBFS; raw speech ≈ −28…−31 LUFS), so
    only the loud words get compressed. Gain-staging to −20 LUFS first squashed all speech (LRA 4.7 → 2.4). Presets
    with a pre-level (`pre_lufs`) bring any mic gain to that raw level first with a linear gain;
  - loudness = linear gain after the chain + a 4× oversampled limiter for the short peaks; not dynamic loudnorm;
  - no tracking noise reduction by default (afftdn only with --denoise, for really noisy rooms).

Usage:
  voice_master.py voice   IN OUT --preset NAME [--channel 0] [--denoise] [--deess] [--noise START-END]
  voice_master.py master  IN OUT [--video]      (with --video: copy the picture, master the audio, +faststart)
  voice_master.py measure IN
  voice_master.py analyze IN [--channel 0] [--noise START-END] [--name my-mic]
  voice_master.py match   IN REF [--name my-mic-match] [--amount 0.75] [--denoise 3]   (EQ match to a voice you like)
  voice_master.py presets
"""
import argparse, json, math, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _kit  # noqa: E402


def fir_match(curve):
    """Linear-phase FIR EQ (firequalizer) through (Hz, dB) points — the «EQ match» of the pros (Pro-Q / RX / Ozone).
    FFmpeg 9 quirks, tested on pink noise and an impulse: scale=loglog makes the filter flat at its first entry, so the
    curve is resampled here to 1/6-octave points for the default linear-frequency scale; more than ~100 gain entries
    fails with ENOMEM; zero_phase only shifts timestamps (a WAV still comes out 50 ms late = lips out of sync), so
    atrim=start=0 drops the delay — onsets then match the input to 0.2 ms."""
    f, g = [p[0] for p in curve], [p[1] for p in curve]
    lf = [math.log2(x) for x in f]
    pts = []
    for i in range(int(math.log2(20) * 6), int(math.log2(20000) * 6) + 1):
        x = i / 6
        if x <= lf[0]:
            y = g[0]
        elif x >= lf[-1]:
            y = g[-1]
        else:
            j = next(k for k in range(len(lf) - 1) if lf[k] <= x <= lf[k + 1])
            y = g[j] + (g[j + 1] - g[j]) * (x - lf[j]) / (lf[j + 1] - lf[j])
        pts.append((round(2 ** x, 1), round(y, 2)))
    entry = ";".join(f"entry({a},{b})" for a, b in pts)
    return f"firequalizer=gain_entry='{entry}':delay=0.05:zero_phase=1,atrim=start=0"


COMP = "acompressor=threshold=0.10:ratio={r}:attack=10:release=150:knee=3"
EXPANDER = "agate=threshold=0.004:ratio=2:range=0.562:attack=3:release=250:knee=2.8:detection=rms"
# two-stage dynamics of dialogue mixers: a fast peak catcher (4:1, ≈ −13 dBFS, the «1176» role) into a slow leveler
# (2:1, ≈ −23 dBFS, the «LA-2A» role); thresholds assume a −30 LUFS pre-level
TWO_STAGE = ("acompressor=threshold=0.22:ratio=4:attack=1:release=50:knee=2,"
             "acompressor=threshold=0.07:ratio=2:attack=25:release=300:knee=6")
# dynamic de-esser on 6.5 kHz: works only when sibilants are loud (a static `deesser` took 0.0 dB off a chest lav that
# has almost no sibilance energy). adynamicequalizer threshold is linear amplitude (0.01 ≈ −40 dBFS in band), range in dB
DYN_DEESS = ("adynamicequalizer=threshold=0.01:dfrequency=6500:dqfactor=1.5:tfrequency=6500:tqfactor=1.2:"
             "attack=1:release=60:ratio=4:range=6:mode=cutabove")
# chain = filters after the optional pre-level and denoise; pre_lufs = linear level before the chain; denoise = profile
# denoise strength in dB (afftdn nr, learned from the recording's own room tone)
PRESETS = {
    "solocast": dict(checked=True, note="USB condenser on a desk, 10-20 cm from the mouth",
                     chain="highpass=f=70,bass=g=2:f=120:w=0.6,equalizer=f=220:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1:g=1.5,"
                           "acompressor=threshold=0.10:ratio=2.5:attack=10:release=150:knee=3"),
    # the first by-ear choice for a DJI Mic Mini 2 lav; the same voice then preferred an EQ match to its own desk mic
    # plus TWO_STAGE + DYN_DEESS — that curve belongs to one voice and one mic pair: make yours with `match`
    "lav": dict(checked=True, pre_lufs=-30, denoise=3, note="wireless lav on the chest, 15-20 cm below the mouth",
                chain="highpass=f=80,bass=g=2:f=120:w=0.6,equalizer=f=800:t=q:w=1.4:g=-3,equalizer=f=3800:t=q:w=0.8:g=5,"
                      "acompressor=threshold=0.10:ratio=2.5:attack=10:release=150:knee=3,deesser=i=0.3:m=0.5:f=0.5," + EXPANDER),
    "usb-condenser": dict(pre_lufs=-29, note="any USB/XLR condenser in a normal room",
                          chain="highpass=f=75,bass=g=1.5:f=120:w=0.6,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1:g=1.5," + COMP.format(r=2.5)),
    "dynamic": dict(pre_lufs=-29, note="dynamic mic close to the mouth (broadcast/podcast type)",
                    chain="highpass=f=80,equalizer=f=300:t=q:w=1:g=-1.5,equalizer=f=4000:t=q:w=0.9:g=2.5,equalizer=f=9000:t=h:w=0.7:g=1.5," + COMP.format(r=2.5)),
    "lav-generic": dict(pre_lufs=-30, denoise=3, note="any lav on the chest: chest EQ, two-stage dynamics, dynamic de-esser",
                        chain="highpass=f=80,bass=g=1.5:f=120:w=0.6,equalizer=f=800:t=q:w=1.4:g=-2.5,equalizer=f=3800:t=q:w=0.8:g=4,"
                              + TWO_STAGE + "," + DYN_DEESS + "," + EXPANDER),
    "headset": dict(pre_lufs=-29, note="headset or gaming headphones mic",
                    chain="highpass=f=100,equalizer=f=250:t=q:w=1:g=1.5,equalizer=f=2500:t=q:w=1:g=-1.5,equalizer=f=6500:t=q:w=1:g=-2," + COMP.format(r=2.2)),
    "camera": dict(pre_lufs=-30, denoise=4, note="built-in mic of a phone, camera or laptop (room sound)",
                   chain="highpass=f=100,equalizer=f=350:t=q:w=1:g=-3,equalizer=f=3000:t=q:w=1:g=2.5," + COMP.format(r=2.2) + "," + EXPANDER),
    "neutral": dict(pre_lufs=-29, note="no EQ: high-pass and gentle compression only",
                    chain="highpass=f=70," + COMP.format(r=2.0)),
}

def all_presets():
    """built-in presets + your own from kit.config.json («voicePresets»: {name: {chain, pre_lufs?, denoise?, note?}})"""
    out = dict(PRESETS)
    for k, v in _kit.cfg().get("voicePresets", {}).items():
        if not isinstance(v, dict) or "chain" not in v:
            sys.exit(f"kit.config.json voicePresets.{k}: needs at least «chain»")
        v = dict(v)
        if v.get("match"):  # EQ match curve from `match`: the FIR goes right after the high-pass
            hp, _, rest = v["chain"].partition(",")
            v["chain"] = f"{hp},{fir_match(v['match'])},{rest}" if hp.startswith("highpass") else f"{fir_match(v['match'])},{v['chain']}"
        out[k] = {**v, "own": True}
    return out


VOICE = dict(I=-17, LRA=7, TP=-1.5)
MASTER = dict(I=-15, LRA=7, TP=-1.5)


def run(args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], capture_output=True, text=True)


def measure(path, pre=""):
    """EBU R128 of a file (optionally after a filter chain): I, LRA, true peak."""
    af = (pre + "," if pre else "") + "ebur128=peak=true"
    e = run(["-i", path, "-af", af, "-f", "null", "-"]).stderr
    g = lambda k: float(re.findall(rf"{k}:\s+(-?[\d.]+)", e)[-1])
    return {"I": g("I"), "LRA": g("LRA"), "TP": g("Peak")}


def loudnorm_two_pass(src, dst, chain, target, extra_out):
    """Pass 1 measures through `chain`, pass 2 applies loudnorm with the measured values."""
    t = target
    ln = f"loudnorm=I={t['I']}:LRA={t['LRA']}:TP={t['TP']}"
    e = run(["-i", src, "-af", f"{chain + ',' if chain else ''}{ln}:print_format=json", "-f", "null", "-"]).stderr
    m = json.loads(e[e.rindex("{"): e.rindex("}") + 1])
    ln2 = (f"{ln}:measured_I={m['input_i']}:measured_LRA={m['input_lra']}:measured_TP={m['input_tp']}"
           f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    r = run(["-y", "-i", src, "-af", f"{chain + ',' if chain else ''}{ln2}", *extra_out, dst])
    if r.returncode:
        sys.exit(r.stderr[-2000:])
    return m


def room_tone(path, pan, speech_lufs):
    """Longest pause (≥ 0.8 s) at 20 dB under the speech, shrunk by 0.2 s on each side: where the noise profile is
    learned. None if the recording has no such pause."""
    e = run(["-i", path, "-af", f"{pan},silencedetect=n={speech_lufs - 20:.1f}dB:d=0.8", "-f", "null", "-"]).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", e)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", e)]
    if len(starts) > len(ends):  # the recording ends in silence: that tail counts too
        h, m, sec = re.search(r"Duration: (\d+):(\d+):([\d.]+)", e).groups()
        ends.append(int(h) * 3600 + int(m) * 60 + float(sec))
    spans = [(max(0, s) + 0.2, t - 0.2) for s, t in zip(starts, ends)]
    spans = [s for s in spans if s[1] - s[0] >= 0.4]
    return max(spans, key=lambda s: s[1] - s[0]) if spans else None


def voice(a):
    """Preset chain, then a linear gain to −17 LUFS and a 4× oversampled limiter for the remaining short peaks.
    Not dynamic loudnorm: on the first Short it squashed the speech from LRA 4.7 to 2.1 LU on top of the compressor."""
    presets = all_presets()
    if a.preset not in presets:
        sys.exit(f"unknown preset {a.preset!r}; available: {', '.join(presets)}")
    P = presets[a.preset]
    pan = f"pan=mono|c0=c{a.channel}"
    pre = measure(a.inp, pan)
    chain = [pan]
    if P.get("denoise"):
        if getattr(a, "noise", None):  # callers that import voice() may pass a namespace without --noise
            tone = tuple(float(x) for x in a.noise.split("-"))
        else:
            tone = room_tone(a.inp, pan, pre["I"])
        if tone:
            chain.append(f"asendcmd=c='{tone[0]:.2f} afftdn sn start;{tone[1]:.2f} afftdn sn stop',"
                         f"afftdn=nr={P['denoise']}:nf=-70:rf=-80:gs=8:tn=0")
            print(f"noise profile from {tone[0]:.2f}–{tone[1]:.2f} s", file=sys.stderr)
        else:
            print("no room tone ≥ 0.4 s found: profile denoise skipped (record 2–3 s of silence, or pass --noise)",
                  file=sys.stderr)
    elif a.denoise:
        chain.append("afftdn=nr=8:nf=-55:tn=1")
    if P.get("pre_lufs") is not None:
        chain.append(f"volume={P['pre_lufs'] - pre['I']:.2f}dB")
    chain.append(P["chain"])
    if a.deess:
        chain.append("deesser=i=0.4:m=0.5:f=0.5")
    chain = ",".join(chain)
    mid = measure(a.inp, chain)
    gain = VOICE["I"] - mid["I"]
    lim = 10 ** ((VOICE["TP"] - 0.4) / 20)
    # one pass: the limiter takes ~1 dB of loudness on peaky speech; pushing harder only adds limiting, and the master
    # stage sets the final level anyway
    af = f"{chain},volume={gain:.2f}dB,aresample=192000,alimiter=limit={lim:.4f}:attack=3:release=120:asc=1:level=false,aresample=48000"
    r = run(["-y", "-i", a.inp, "-af", af, "-c:a", "pcm_s24le", a.out])
    if r.returncode:
        sys.exit(r.stderr[-2000:])
    over = mid["TP"] + gain - VOICE["TP"]
    report(a.out, VOICE, f"voice/{a.preset}", {"input_i": pre["I"], "input_lra": pre["LRA"], "input_tp": pre["TP"],
                                                "normalization_type": f"linear, limiter on peaks ≤ {max(0, over):.1f} dB"})


def master(a):
    """The mix is already even (voice stem + SFX), so the master only needs a level change. loudnorm falls back to its
    dynamic mode whenever measured peak + gain would pass the ceiling, and that squashes the whole mix (LRA 3.6 → 2.4 on
    the first Short). So: pass 1 measures; if peaks would overshoot by ≤ 3 dB, apply a linear gain and let a 4×
    oversampled limiter shave just those peaks; otherwise use two-pass loudnorm."""
    out = ["-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "320k"]
    if a.video:
        out = ["-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", *out, "-movflags", "+faststart"]
    pre = measure(a.inp)
    gain = MASTER["I"] - pre["I"]
    over = pre["TP"] + gain - MASTER["TP"]
    if over <= 3:
        lim = 10 ** ((MASTER["TP"] - 0.4) / 20)
        af = f"volume={gain:.2f}dB,aresample=192000,alimiter=limit={lim:.4f}:attack=3:release=120:asc=1:level=false,aresample=48000"
        r = run(["-y", "-i", a.inp, "-af", af, *out, a.out])
        if r.returncode:
            sys.exit(r.stderr[-2000:])
        m = {"input_i": pre["I"], "input_lra": pre["LRA"], "input_tp": pre["TP"], "normalization_type": f"linear +{gain:.1f} dB, limiter on peaks ≤ {max(0, over):.1f} dB"}
    else:
        m = loudnorm_two_pass(a.inp, a.out, "", MASTER, out)
    report(a.out, MASTER, "master", m)


def report(path, target, label, m):
    r = measure(path)
    tol = 1.5 if target is VOICE else 1  # the voice stem only needs headroom; the master is exact
    ok = abs(r["I"] - target["I"]) <= tol and r["TP"] <= target["TP"] + 0.3 and r["LRA"] <= target["LRA"] + 1  # LRA 4–7 is judged on the cut, not on raw takes
    print(json.dumps({"file": path, "stage": label, "in": {"I": m["input_i"], "LRA": m["input_lra"], "TP": m["input_tp"]},
                      "out": r, "target": target, "ok": ok, "mode": m.get("normalization_type")}, ensure_ascii=False))


# Long-term average speech spectrum (Byrne et al., 1994, third-octave levels at octave centres, dB): the «average voice»
# that `analyze` compares your recording with. A guide for the first EQ guess, not a target to force a voice into.
LTASS = {63: 38.6, 125: 57.7, 250: 59.7, 500: 62.6, 1000: 53.1, 2000: 49.2, 4000: 47.8, 8000: 44.7}


def band_levels(path, pan, speech_lufs):
    """mean level per octave band over speech only (pauses removed), dB; two cascaded 2-pole band-passes per band"""
    gate = f"silenceremove=stop_periods=-1:stop_duration=0.25:stop_threshold={speech_lufs - 18:.1f}dB"
    out = {}
    for f in LTASS:
        e = run(["-i", path, "-af", f"{pan},{gate},bandpass=f={f}:width_type=o:w=1,bandpass=f={f}:width_type=o:w=1,volumedetect", "-f", "null", "-"]).stderr
        out[f] = float(re.findall(r"mean_volume: (-?[\d.]+)", e)[-1])
    return out


def span_level(path, pan, span):
    e = run(["-ss", f"{span[0]:.2f}", "-t", f"{span[1] - span[0]:.2f}", "-i", path, "-af", f"{pan},volumedetect", "-f", "null", "-"]).stderr
    return float(re.findall(r"mean_volume: (-?[\d.]+)", e)[-1])


def suggest(dev, snr, raw):
    """EQ / denoise guess from band deviations (dB vs the average voice), SNR and raw loudness → (preset dict, notes)"""
    notes, eq = [], []
    hp = 100 if dev[63] > 6 else 90 if dev[63] > 3 else 75
    if hp > 75:
        notes.append(f"много низкого гула (+{dev[63]:.0f} дБ на 63 Гц): срез низов {hp} Гц; проверьте вибрации стола и кондиционер")
    if dev[125] < -3 and hp <= 75:  # never boost the lows we are cutting a rumble under
        eq.append("bass=g=2:f=120:w=0.6"); notes.append("тонкий низ: мягкая полка +2 дБ на 120 Гц")
    elif dev[125] > 4:
        eq.append("bass=g=-2:f=120:w=0.6"); notes.append("гудящий низ (эффект близости): полка -2 дБ на 120 Гц")
    if dev[250] > 2:
        g = min(dev[250], 4); eq.append(f"equalizer=f=250:t=q:w=1:g={-g:.1f}"); notes.append(f"мутность 250 Гц: -{g:.1f} дБ")
    if dev[1000] > 2.5:
        g = min(dev[1000], 3.5); eq.append(f"equalizer=f=800:t=q:w=1.2:g={-g:.1f}"); notes.append(f"«коробка» 800 Гц - 1 кГц: -{g:.1f} дБ")
    pres = (dev[2000] + dev[4000]) / 2
    if pres < -2:
        g = min(-pres, 5); eq.append(f"equalizer=f=3500:t=q:w=0.9:g={g:.1f}"); notes.append(f"глухо, мало разборчивости: +{g:.1f} дБ на 3.5 кГц")
    elif pres > 3:
        g = min(pres, 3); eq.append(f"equalizer=f=3500:t=q:w=0.9:g={-g:.1f}"); notes.append(f"резко на 2-4 кГц: -{g:.1f} дБ")
    deess = dev[8000] > 4
    if deess:
        notes.append("яркие шипящие: включён мягкий де-эссер")
    chain = [f"highpass=f={hp}", *eq, COMP.format(r=2.5)]
    if deess:
        chain.append("deesser=i=0.3:m=0.5:f=0.5")
    preset = {"pre_lufs": -29, "chain": ",".join(chain), "note": "suggested by analyze — check by ear"}
    if snr is None:
        notes.append("в записи нет паузы ≥ 0.8 с: шум не измерен; запишите 2-3 с тишины")
    elif snr < 20:
        notes.append(f"шум очень высокий (речь над шумом {snr:.0f} дБ): обработка не спасёт, микрофон ближе ко рту, тише комната")
        preset["denoise"] = 6
    elif snr < 32:
        preset["denoise"] = 5; notes.append(f"заметный шум (речь над шумом {snr:.0f} дБ): шумодав по снимку тишины 5 дБ")
    elif snr < 42:
        preset["denoise"] = 3; notes.append(f"лёгкий шум (речь над шумом {snr:.0f} дБ): шумодав по снимку тишины 3 дБ")
    if preset.get("denoise"):
        preset["chain"] += "," + EXPANDER
    if raw > -14:
        notes.append(f"запись очень громкая ({raw:.0f} LUFS): уменьшите усиление микрофона, иначе возможен клиппинг")
    elif raw < -40:
        notes.append(f"запись очень тихая ({raw:.0f} LUFS): прибавьте усиление микрофона, иначе поднимется шум")
    return preset, notes


def analyze(a):
    pan = f"pan=mono|c0=c{a.channel}"
    pre = measure(a.inp, pan)
    tone = tuple(float(x) for x in a.noise.split("-")) if a.noise else room_tone(a.inp, pan, pre["I"])
    noise = span_level(a.inp, pan, tone) if tone else None
    bands = band_levels(a.inp, pan, pre["I"])
    diff = {f: bands[f] - LTASS[f] for f in LTASS}
    mid = sorted(diff[f] for f in (250, 500, 1000, 2000))
    ref = (mid[1] + mid[2]) / 2
    dev = {f: round(diff[f] - ref, 1) for f in LTASS}
    speech = max(bands.values())  # rough: loudest band mean ≈ speech level in the gate
    sp = run(["-i", a.inp, "-af", f"{pan},volumedetect", "-f", "null", "-"]).stderr
    mean_all = float(re.findall(r"mean_volume: (-?[\d.]+)", sp)[-1])
    snr = round(mean_all - noise, 1) if noise is not None else None
    preset, notes = suggest(dev, snr, pre["I"])
    rep = {"file": a.inp, "raw": pre, "noise_db": noise, "speech_over_noise_db": snr, "room_tone_s": tone,
           "tone_vs_average_voice_db": dev, "suggested": {a.name: preset}, "notes": notes, "_speech_band_peak": speech}
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    print("\nВставьте «suggested» в kit.config.json → «voicePresets», затем:\n"
          f"  python3 scripts/audio/voice_master.py voice {a.inp} work/test_{a.name}.wav --preset {a.name}\n"
          "и сравните на слух с исходником и с соседним пресетом (docs/MIC_CALIBRATION.md).", file=sys.stderr)
    return rep


THIRD = [50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000,
         5000, 6300, 8000, 10000, 12500, 16000]


def third_octave(path, pan, lufs):
    """speech-only level per 1/3 octave, dB"""
    gate = f"silenceremove=stop_periods=-1:stop_duration=0.25:stop_threshold={lufs - 18:.1f}dB"
    out = {}
    for f in THIRD:
        bp = f"bandpass=f={f}:width_type=o:w=0.33"
        e = run(["-i", path, "-af", f"{pan},{gate},{bp},{bp},volumedetect", "-f", "null", "-"]).stderr
        out[f] = float(re.findall(r"mean_volume: (-?[\d.]+)", e)[-1])
    return out


def match_curve(src, ref, amount=0.75, lf_boost=1.5, limit=9.0):
    """EQ that moves `src` towards `ref` (dicts Hz → dB): level-free (mean of 200 Hz–5 kHz = 0), 3-point smoothing,
    `amount` of the difference (100 % sounds forced), low-frequency boosts ≤ lf_boost dB (they boost rumble too)."""
    d = {f: ref[f] - src[f] for f in THIRD}
    mid = [d[f] for f in THIRD if 200 <= f <= 5000]
    m = sum(mid) / len(mid)
    d = {f: v - m for f, v in d.items()}
    sm = []
    for i, f in enumerate(THIRD):
        w = [d[THIRD[j]] for j in range(max(0, i - 1), min(len(THIRD), i + 2))]
        sm.append(sum(w) / len(w))
    out = []
    for f, v in zip(THIRD, sm):
        g = max(-limit, min(limit, v * amount))
        if f < 100:
            g = min(g, lf_boost)
        out.append([f, round(g, 2)])
    return out


def match(a):
    """EQ match of your mic (IN) to a reference recording you like (REF): best with the same words recorded by both mics
    at once; different texts work too, less precisely. Prints a preset for kit.config.json «voicePresets»."""
    pan = f"pan=mono|c0=c{a.channel}"
    pi, pr = measure(a.inp, pan), measure(a.ref, "pan=mono|c0=c0")
    src = third_octave(a.inp, pan, pi["I"])
    ref = third_octave(a.ref, "pan=mono|c0=c0", pr["I"])
    curve = match_curve(src, ref, amount=a.amount)
    preset = {"pre_lufs": -30, "match": curve, "chain": "highpass=f=70," + TWO_STAGE + "," + DYN_DEESS,
              "note": f"EQ match to {os.path.basename(a.ref)} ({int(a.amount * 100)} %) — check by ear"}
    if a.denoise:
        preset["denoise"] = a.denoise
        preset["chain"] += "," + EXPANDER
    rms = (sum(g * g for _, g in curve) / len(curve)) ** 0.5
    print(json.dumps({"file": a.inp, "reference": a.ref, "curve_rms_db": round(rms, 2), "suggested": {a.name: preset}}, ensure_ascii=False, indent=1))
    print("\nВставьте «suggested» в kit.config.json → «voicePresets» и сравните на слух с эталоном (docs/MIC_CALIBRATION.md).", file=sys.stderr)
    return curve


def list_presets():
    for k, v in all_presets().items():
        tag = "свой" if v.get("own") else "проверен на слух" if v.get("checked") else "общий"
        print(f"{k:14} [{tag}] {v.get('note', '')}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("voice"); v.add_argument("inp"); v.add_argument("out")
    v.add_argument("--preset", required=True, help="see `voice_master.py presets`"); v.add_argument("--channel", type=int, default=0)
    v.add_argument("--denoise", action="store_true"); v.add_argument("--deess", action="store_true")
    v.add_argument("--noise", help="room tone for the profile denoiser, seconds START-END (default: longest pause)")
    mm = sub.add_parser("master"); mm.add_argument("inp"); mm.add_argument("out"); mm.add_argument("--video", action="store_true")
    me = sub.add_parser("measure"); me.add_argument("inp")
    an = sub.add_parser("analyze"); an.add_argument("inp"); an.add_argument("--channel", type=int, default=0)
    an.add_argument("--noise", help="room tone START-END, s"); an.add_argument("--name", default="my-mic")
    mt = sub.add_parser("match"); mt.add_argument("inp"); mt.add_argument("ref"); mt.add_argument("--channel", type=int, default=0)
    mt.add_argument("--name", default="my-mic-match"); mt.add_argument("--amount", type=float, default=0.75)
    mt.add_argument("--denoise", type=int, default=0, help="add profile denoise of N dB (needs room tone in the recording)")
    sub.add_parser("presets")
    a = p.parse_args()
    if a.cmd == "voice":
        voice(a)
    elif a.cmd == "master":
        master(a)
    elif a.cmd == "analyze":
        analyze(a)
    elif a.cmd == "match":
        match(a)
    elif a.cmd == "presets":
        list_presets()
    else:
        print(json.dumps(measure(a.inp)))
