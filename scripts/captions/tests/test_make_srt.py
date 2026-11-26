"""Tests for scripts/captions/make_srt.py (cue building, wrapping, glossary; no whisper needed)."""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import make_srt as M  # noqa: E402


def words(text, t0=0.0, step=0.3):
    return [(t0 + i * step, t0 + i * step + 0.25, w) for i, w in enumerate(text.split())]


class MakeSrtTest(unittest.TestCase):
    def test_new_cue_after_pause_and_sentence_end(self):
        W = words("Первая фраза здесь закончилась.") + words("Вторая начинается после паузы", t0=5)
        cues = M.cues_from_words(W)
        self.assertEqual(len(cues), 2)
        self.assertTrue(cues[1][2].startswith("Вторая"))

    def test_lines_fit_42_chars(self):
        long = "это довольно длинная реплика которая точно не поместится в одну строку субтитров"
        for line in M.wrap(long).split("\n"):
            self.assertLessEqual(len(line), 42)

    def test_glossary_and_timestamps(self):
        out = M.srt([[0.0, 1.5, "открываю клод код"], [61.25, 63.0, "готово"]], fixes=[["клод код", "Claude Code"]])
        self.assertIn("00:00:00,000 --> 00:00:01,500\nОткрываю Claude Code", out)
        self.assertIn("00:01:01,250 --> 00:01:03,000", out)

    def test_cue_end_clipped_to_next_start(self):
        out = M.srt([[0.0, 3.0, "раз"], [2.0, 4.0, "два"]])
        self.assertIn("00:00:00,000 --> 00:00:01,960", out)


if __name__ == "__main__":
    unittest.main()
