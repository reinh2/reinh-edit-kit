"""Tests for scripts/audio/voice_master.py on a synthetic «voice» (filtered noise in syllables with pauses).
Run: python3 -m unittest discover -s scripts/audio/tests   (needs ffmpeg)"""
import json, os, subprocess, sys, tempfile, unittest

VM = os.path.join(os.path.dirname(__file__), "..", "voice_master.py")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import voice_master as V  # noqa: E402


def run(*args, env=None):
    r = subprocess.run([sys.executable, VM, *args], capture_output=True, text=True, env=env)
    if r.returncode:
        raise AssertionError(r.stderr[-1500:])
    return r


class VoiceMasterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.src = f"{cls.d}/raw.wav"
        # 3 s room tone, then 6 s of «syllables» (pink noise band-limited to speech, gated at 4 Hz), raw level ≈ −27 LUFS, room tone ≈ −54 dBFS
        fc = ("anoisesrc=c=pink:d=9:a=0.1:r=48000,highpass=f=120,lowpass=f=6000[n];"
              "anoisesrc=c=white:d=9:a=0.0006:r=48000[room];"
              "[n]volume='if(gt(t,3),0.5+0.5*sin(2*PI*4*t),0)':eval=frame[s];[s][room]amix=inputs=2:normalize=0,volume=6")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_complex", fc, "-ac", "1", "-c:a", "pcm_s24le", cls.src], check=True)

    def test_every_builtin_preset_hits_voice_target(self):
        for name in ("solocast", "lav", "usb-condenser", "dynamic", "lav-generic", "headset", "camera", "neutral"):
            out = f"{self.d}/v_{name}.wav"
            r = run("voice", self.src, out, "--preset", name)
            m = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertLess(abs(m["out"]["I"] - V.VOICE["I"]), 1.6, (name, m))
            self.assertLessEqual(m["out"]["TP"], V.VOICE["TP"] + 0.3, (name, m))

    def test_master_hits_delivery_target(self):
        out = f"{self.d}/master.m4a"
        r = run("master", self.src, out)
        m = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertLess(abs(m["out"]["I"] - V.MASTER["I"]), 1.0, m)
        self.assertLessEqual(m["out"]["TP"], V.MASTER["TP"] + 0.3, m)

    def test_analyze_suggests_a_usable_preset(self):
        r = run("analyze", self.src, "--name", "test-mic")
        rep = json.loads(r.stdout)
        self.assertIsNotNone(rep["room_tone_s"])
        self.assertGreater(rep["speech_over_noise_db"], 10)
        preset = rep["suggested"]["test-mic"]
        cfg = f"{self.d}/kit.config.json"
        json.dump({"voicePresets": {"test-mic": preset}}, open(cfg, "w"))
        env = {**os.environ, "KIT_CONFIG": cfg}
        r2 = run("voice", self.src, f"{self.d}/own.wav", "--preset", "test-mic", env=env)
        self.assertTrue(json.loads(r2.stdout.strip().splitlines()[-1])["ok"])

    def test_unknown_preset_fails_with_list(self):
        r = subprocess.run([sys.executable, VM, "voice", self.src, f"{self.d}/x.wav", "--preset", "nope"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("available", r.stderr)



class MatchTest(unittest.TestCase):
    def test_curve_is_level_free_and_limited(self):
        src = {f: -40.0 for f in V.THIRD}
        ref = {f: -30.0 + (6 if f >= 3150 else 0) + (10 if f < 100 else 0) for f in V.THIRD}
        c = dict((f, g) for f, g in V.match_curve(src, ref))
        self.assertLess(abs(c[1000]), 1.0)          # +10 dB of level is not an EQ
        self.assertGreater(c[5000], 3.0)            # the missing presence comes back (75 %)
        self.assertLessEqual(c[63], 1.5)            # no big low boost

    def test_match_preset_renders(self):
        d = tempfile.mkdtemp()
        ref, dull = f"{d}/ref.wav", f"{d}/dull.wav"
        base = "anoisesrc=c=pink:d=6:a=0.1:r=48000,volume='0.5+0.5*sin(2*PI*4*t)':eval=frame"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_complex", base, "-ac", "1", ref], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_complex", base + ",lowpass=f=2500", "-ac", "1", dull], check=True)
        rep = json.loads(run("match", dull, ref, "--name", "m").stdout)
        preset = rep["suggested"]["m"]
        self.assertGreater(dict(map(tuple, preset["match"]))[5000], 2.0)
        cfg = f"{d}/kit.config.json"
        json.dump({"voicePresets": {"m": preset}}, open(cfg, "w"))
        r = run("voice", dull, f"{d}/out.wav", "--preset", "m", env={**os.environ, "KIT_CONFIG": cfg})
        self.assertTrue(json.loads(r.stdout.strip().splitlines()[-1])["ok"])


if __name__ == "__main__":
    unittest.main()
