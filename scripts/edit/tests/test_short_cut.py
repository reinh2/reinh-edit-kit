"""Tests for scripts/edit/short_cut.py (planning and word alignment; no ffmpeg/whisper needed)."""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import short_cut as S  # noqa: E402


class ShortCutTest(unittest.TestCase):
    def test_plan_is_frame_exact_with_gaps(self):
        tl, total = S.plan([{"id": "a", "a": 1.0, "b": 2.51, "text": "x"}, {"id": "b", "a": 0, "b": 1, "gap": 0.2, "text": "y"}], 30)
        self.assertEqual((tl[0]["t0"], tl[0]["t1"]), (0.0, round(45 / 30, 4)))
        self.assertAlmostEqual(tl[1]["t0"], 1.5)
        self.assertAlmostEqual(total, 1.5 + 1 + 0.2)

    def test_align_keeps_times_and_fixes_spelling(self):
        tl, _ = S.plan([{"id": "a", "a": 0, "b": 2, "text": "Привет, Claude Code"}], 30)
        W = [(0.1, 0.5, "привет"), (0.6, 0.9, "клод"), (1.0, 1.4, "код"), (1.5, 1.6, "[музыка]")]
        w = S.align(tl, W)
        self.assertEqual([x["w"] for x in w], ["Привет,", "Claude", "Code"])
        self.assertEqual([x["start"] for x in w], [0.1, 0.6, 1.0])

    def test_align_spreads_missed_words(self):
        tl, _ = S.plan([{"id": "a", "a": 0, "b": 3, "text": "раз два три четыре"}], 30)
        w = S.align(tl, [(0.0, 0.4, "раз"), (2.0, 2.4, "четыре")])
        self.assertEqual([x["w"] for x in w], ["раз", "два", "три", "четыре"])
        self.assertTrue(0.4 <= w[1]["start"] < w[2]["start"] < 2.0)


if __name__ == "__main__":
    unittest.main()
