"""Tests for scripts/edit/edl_timeline.py — run: python3 -m unittest discover -s scripts/edit/tests"""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import edl_timeline as T  # noqa: E402


def make(edl, base):
    d = tempfile.mkdtemp()
    os.makedirs(f"{d}/projects/t")
    json.dump({"segments": base}, open(f"{d}/projects/t/base.json", "w"))
    p = f"{d}/projects/t/edl.json"
    json.dump(edl, open(p, "w"))
    return p


BASE = [{"id": "F", "obs": "10-00-00", "in_s": 100, "dur": 40, "phone": "x", "phone_in": 0},
        {"id": "S", "obs": "10-00-00", "in_s": 200, "dur": 20, "phone": "x", "phone_in": 0}]


def edl(**kw):
    e = {"base": "projects/t/base.json", "fps": 60, "handle": 0.8, "faceZoom": [1.0, 1.14], "lcut": 0.3, "clockStart": "10:00:00",
         "pieces": [{"id": "F", "kind": "face", "clips": [[0, 5, "a"], [6, 10, "b"]], "punch": [[3, "p"]]},
                    {"id": "S", "kind": "screen", "clips": [[1, 5, "c"]], "cams": [[1, 960, 540, 1920, 0], [3, 1000, 500, 900, 0.6]]}],
         "gaps": [], "overs": [{"piece": "F", "at": 7.0, "d": 1.0, "el": "Card"}]}
    e.update(kw)
    return e


class TimelineTest(unittest.TestCase):
    def test_frames_and_total(self):
        tl, _ = T.build(make(edl(), BASE))
        self.assertEqual(tl["total"], 5 * 60 + 4 * 60 + 4 * 60)
        self.assertEqual([a["startFrom"] for a in tl["audio"]], [48, 6 * 60 + 48, 60 + 48])  # handle 0.8 s = 48 frames

    def test_jump_cut_and_punch_change_framing(self):
        tl, _ = T.build(make(edl(), BASE))
        face = [v for v in tl["video"] if v["kind"] == "face"]
        self.assertEqual([round(v["zoom"], 2) for v in face], [1.0, 1.14, 1.0])  # 0–3, punch at 3, jump cut at 6

    def test_lcut_screen_takes_over_early(self):
        tl, _ = T.build(make(edl(), BASE))
        face, scr = tl["video"][-2], tl["video"][-1]
        self.assertTrue(scr.get("lcut"))
        self.assertEqual(face["from"] + face["dur"], scr["from"])
        self.assertAlmostEqual(scr["local"], 0.7)
        self.assertEqual(scr["from"], 9 * 60 - 18)

    def test_no_lcut_across_an_insert(self):
        tl, _ = T.build(make(edl(gaps=[{"after": "F", "d": 2.0, "el": "Chapter X"}]), BASE))
        self.assertFalse(any(v.get("lcut") for v in tl["video"]))
        self.assertEqual(tl["total"], (5 + 4 + 2 + 4) * 60)

    def test_over_anchored_to_local_time(self):
        tl, _ = T.build(make(edl(), BASE))
        self.assertEqual(tl["overs"][0]["from"], 5 * 60 + 60)  # local 7.0 = 1 s into the second clip

    def test_over_to_beats_overlay_across_a_jump_cut(self):
        # v3: `to` measures the output length across the removed 5–6 s gap; beats map local word times to insert seconds
        e = edl(overs=[{"piece": "F", "at": 4.0, "to": 8.0, "el": "Ins", "beats": {"w": 7.0, "gap": 5.5}, "overlay": True}])
        tl, _ = T.build(make(e, BASE))
        o = tl["overs"][0]
        self.assertEqual((o["from"], o["dur"]), (4 * 60, 3 * 60))  # 4–5 (1 s) + 6–8 (2 s)
        self.assertEqual(o["props"]["b"], {"w": 2.0, "gap": 1.0})  # a time inside the gap maps to the next clip
        self.assertTrue(o["overlay"])
        self.assertFalse(any(s["kind"] == "over" for s in T.shots(tl)))  # an overlay keeps the face shot

    def test_slow_push_list_splits_at_bounds(self):
        e = edl()
        e["pieces"][0]["push"] = [[0, 2, 1.0, 1.1, "push-in"]]
        tl, _ = T.build(make(e, BASE))
        f = [v for v in tl["video"] if v["kind"] == "face"]
        self.assertEqual((f[0]["dur"], f[0]["zoom"], f[0]["zoom1"]), (120, 1.0, 1.1))  # 0–2 s pushes to 1.1
        self.assertEqual((f[1]["zoom"], f[1]["zoom1"]), (1.0, 1.0))  # after the push the framing holds (no toggle)

    def test_media_folder(self):
        tl, _ = T.build(make(edl(media="x/v3"), BASE))
        self.assertTrue(all(a["src"].startswith("x/v3/") for a in tl["audio"]))

    def test_flags_long_face_and_held_screen(self):
        e = edl()
        e["pieces"][0]["clips"] = [[0, 15, "long"]]
        e["pieces"][0]["punch"] = []
        e["pieces"][1]["cams"] = [[1, 1000, 500, 900, 0]]
        e["pieces"][1]["clips"] = [[1, 11, "held"]]
        e["overs"] = []
        tl, _ = T.build(make(e, BASE))
        flags = [f for _, f in T.check(tl)[1]]
        self.assertTrue(any("held 14.7" in f for f in flags), flags)  # 15 s − 0.3 s L-cut
        self.assertTrue(any("held 10.3" in f for f in flags), flags)  # 10 s + 0.3 s L-cut

    def test_clean_edit_has_no_flags(self):
        tl, _ = T.build(make(edl(), BASE))
        self.assertEqual(T.check(tl)[1], [])


if __name__ == "__main__":
    unittest.main()
