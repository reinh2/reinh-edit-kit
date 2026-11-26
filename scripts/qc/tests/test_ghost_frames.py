"""Tests for scripts/qc/ghost_frames.py and cut_strips.py on synthetic clips (needs ffmpeg)."""
import json, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(__file__)
GF = os.path.join(HERE, "..", "ghost_frames.py")
CS = os.path.join(HERE, "..", "cut_strips.py")


def clip(path, fc):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_complex", fc, "-c:v", "libx264", "-pix_fmt", "yuv420p", path], check=True)


class GhostFramesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        # A (dark blue, 2 s) → 3 frames of a bright test pattern → C (dark red, 2 s): the 3 frames are a «phantom»
        cls.ghost = f"{cls.d}/ghost.mp4"
        clip(cls.ghost, "color=c=0x101830:s=320x180:r=30:d=2[a];testsrc2=s=320x180:r=30:d=0.1[b];color=c=0x301010:s=320x180:r=30:d=2[c];[a][b][c]concat=n=3:v=1:a=0")
        # a 1 s dissolve between the same A and C: not a phantom
        cls.fade = f"{cls.d}/fade.mp4"
        clip(cls.fade, "color=c=0x101830:s=320x180:r=30:d=3[a];color=c=0xC0C0C0:s=320x180:r=30:d=3[c];[a][c]xfade=transition=fade:duration=1:offset=2")

    def found(self, video):
        out = f"{self.d}/out_{os.path.basename(video)}"
        subprocess.run([sys.executable, GF, video, "--out", out], check=True, capture_output=True)
        return json.load(open(f"{out}/ghosts.json"))

    def test_phantom_found(self):
        f = self.found(self.ghost)
        self.assertTrue(any(1.9 <= g["t"] <= 2.2 for g in f), f)

    def test_dissolve_not_flagged(self):
        self.assertEqual(self.found(self.fade), [])

    def test_cut_strips_sheet(self):
        tl = {"fps": 30, "video": [{"from": 0, "dur": 60}, {"from": 63, "dur": 60}], "overs": []}
        p = f"{self.d}/tl.json"
        json.dump(tl, open(p, "w"))
        out = f"{self.d}/strips"
        subprocess.run([sys.executable, CS, self.ghost, p, out, "--width", "160"], check=True, capture_output=True)
        self.assertTrue(os.path.exists(f"{out}/cuts_01.jpg"))
        self.assertIn("cut at 0:02.10", open(f"{out}/cuts.txt").read())


if __name__ == "__main__":
    unittest.main()
