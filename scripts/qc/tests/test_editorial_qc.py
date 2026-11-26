"""Tests for scripts/qc/editorial_qc.py on a synthetic clip — run: python3 -m unittest discover -s scripts/qc/tests
Clip: 3 s dark noisy picture + voice-like tone · 0.1 s white flash · 2 s dark · 12 s frozen grey with a 2 s silence."""
import json, os, subprocess, sys, tempfile, unittest

QC = os.path.join(os.path.dirname(__file__), "..", "editorial_qc.py")


class EditorialQcTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        v = f"{cls.d}/t.mp4"
        dark = "color=c=0x202020:s=320x180:r=30,noise=alls=40:allf=t"
        fc = (f"{dark}:d=3[a];color=c=white:s=320x180:r=30:d=0.1[b];{dark}:d=2[c];color=c=0x808080:s=320x180:r=30:d=12[e];"
              "[a][b][c][e]concat=n=4:v=1:a=0,format=yuv420p[v];"
              "sine=f=220:d=8,volume=0.3[s1];anullsrc=r=44100:cl=mono:d=2.5[s2];sine=f=220:d=4.6,volume=0.3[s3];[s1][s2][s3]concat=n=3:v=0:a=1[au]")
        # the dark parts above use filter sources with durations; build with lavfi graph
        fc = fc.replace(f"{dark}:d=3", "color=c=0x202020:s=320x180:r=30:d=3,noise=alls=40:allf=t").replace(f"{dark}:d=2", "color=c=0x202020:s=320x180:r=30:d=2,noise=alls=40:allf=t")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_complex", fc, "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-c:a", "aac", "-shortest", v], check=True)
        cls.out = f"{cls.d}/qc"
        cls.rc = subprocess.run([sys.executable, QC, v, "--out", cls.out, "--static", "8"], capture_output=True, text=True).returncode
        with open(cls.out + ".json") as f:
            cls.f = json.load(f)["findings"]

    def kinds(self, k):
        return [f for f in self.f if f["kind"] == k]

    def test_flash_found(self):
        self.assertTrue(any(2.9 <= f["t0"] <= 3.2 for f in self.kinds("flash") + self.kinds("jump")), self.f)

    def test_static_found(self):
        self.assertTrue(any(f["value"] >= 8 for f in self.kinds("static")), self.f)

    def test_pause_found(self):
        p = self.kinds("pause")
        self.assertTrue(any(abs(f["t0"] - 8.0) < 0.3 and f["value"] >= 2.0 for f in p), p)

    def test_open_findings_fail(self):
        self.assertEqual(self.rc, 1)


if __name__ == "__main__":
    unittest.main()
