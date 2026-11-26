# 3D heroes of the promo (src/promo/Promo.tsx), procedural and rendered to transparent PNG sequences, 30 fps:
#   clapper  hook: a glass clapperboard flies in, the striped clapper snaps shut on the «cut» (1.5 s), slow drift; 5.6 s
#   case     ending: the kit's hard case, the lid opens (0.9–1.6 s), light inside, three blocks pop out
#            (skills · scripts · styles) and hover; 6 s
# Usage: blender -b -P scripts/blender/promo_heroes.py -- clapper|case [--out DIR] [--still N]
#        npm run promo:3d   (both into public/promo3d/<name>/). The microphones of step 2 are real models: mics.py
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from hero_common import *  # noqa

variant, out, still = args("clapper")
out = out or os.path.join(ROOT, "public", "promo3d", variant)
FPS = 30
F = lambda s: 1 + int(round(s * FPS))
ACC = hex_rgba("#5B8CFF")  # the promo is the author's film: his accent; your own scenes take accent() from kit.config.json
glass = lambda: mat("glass", base=(0.03, 0.05, 0.1, 1), metal=0.3, rough=0.12, coat=1.0)
chrome = lambda: mat("chrome", base=(0.85, 0.88, 0.95, 1), metal=1.0, rough=0.12, coat=0.3)
glow = lambda name, c, e: mat(name, base=(0.05, 0.05, 0.05, 1), metal=0, rough=0.4, coat=0, emit=c, estr=e)

if variant == "clapper":
    N = F(5.6)
    s = reset(FPS, N, (1200, 1000))
    studio()
    root = empty("root", (0, 0, 0))
    board = box("board", (3.2, 0.16, 2.3), (0, 0, 0), glass(), 0.08)
    board.parent = root
    line_m = glow("line", ICE, 1.6)
    for i, (w, z) in enumerate(((2.4, 0.62), (1.7, 0.12), (2.2, -0.38), (1.2, -0.82))):
        ln = box(f"ln{i}", (w, 0.02, 0.07), (-1.35 + w / 2, -0.09, z), line_m, 0.02, 2)
        ln.parent = root
    bar = box("bar", (3.2, 0.18, 0.42), (0, 0, 1.36), stripes_mat("stripes", (0.92, 0.94, 0.98, 1), (0.03, 0.04, 0.08, 1), 2.2), 0.04)
    bar.parent = root
    pivot = empty("pivot", (-1.6, 0, 1.58))
    pivot.parent = root
    clap = box("clap", (3.2, 0.18, 0.42), (0, 0, 0), stripes_mat("stripes2", (0.03, 0.04, 0.08, 1), (0.92, 0.94, 0.98, 1), 2.2), 0.04)
    clap.parent = pivot
    clap.location = (1.6, 0, 0.22)
    hinge = cyl("hinge", 0.12, 0.3, (0, 0, 0), chrome(), rot=(math.radians(90), 0, 0))
    hinge.parent = pivot
    hinge.location = (0, 0, 0)
    dot = cyl("dot", 0.09, 0.04, (1.25, -0.1, -0.82), glow("acc", ACC, 6), rot=(math.radians(90), 0, 0))
    dot.parent = root
    # entrance, drift
    key(root, 1, location=(0, 0, -4.2), rotation_euler=(math.radians(8), 0, math.radians(-14)))
    key(root, F(0.55), location=(0, 0, 0), rotation_euler=(math.radians(2), 0, math.radians(-6)))
    key(root, N, location=(0, 0, 0.15), rotation_euler=(math.radians(-1), 0, math.radians(7)))
    ease_all(root, "EASE_OUT")
    # clapper: open, open a bit more, SNAP on the cut, small bounce
    key(pivot, 1, rotation_euler=(0, math.radians(-24), 0))
    key(pivot, F(1.3), rotation_euler=(0, math.radians(-31), 0))
    key(pivot, F(1.5), rotation_euler=(0, 0, 0))
    key(pivot, F(1.62), rotation_euler=(0, math.radians(-4), 0))
    key(pivot, F(1.75), rotation_euler=(0, 0, 0))
    ease_all(pivot)
    for fc in curves(pivot):  # the snap itself is an accelerating fall, not an ease
        for kp in fc.keyframe_points:
            if abs(kp.co[0] - F(1.5)) < 0.5:
                kp.interpolation = "BEZIER"; kp.easing = "EASE_IN"
            if abs(kp.co[0] - F(1.3)) < 0.5:
                kp.interpolation = "QUAD"; kp.easing = "EASE_IN"
    camera((0, -11.5, 1.2), (0, 0, 0.75), 50)

elif variant == "case":
    N = F(6.0)
    s = reset(FPS, N, (1000, 1000))
    studio(key=900)
    root = empty("root", (0, 0, 0))
    body = box("body", (3.0, 2.0, 1.1), (0, 0, 0), glass(), 0.1); body.parent = root
    band = box("band", (3.02, 2.02, 0.05), (0, 0, 0.3), glow("band", ACC, 3), 0.02, 2); band.parent = root
    for x in (-0.85, 0.85):
        latch = box(f"latch{x}", (0.36, 0.1, 0.24), (x, -1.03, 0.42), chrome(), 0.03); latch.parent = root
    inner = box("inner", (2.7, 1.7, 0.05), (0, 0, 0.53), mat("innerm", base=(0.05, 0.05, 0.05, 1), emit=ACC, estr=0.0), 0.01, 1); inner.parent = root
    hinge = empty("hinge", (0, 1.0, 0.55)); hinge.parent = root
    lid = box("lid", (3.0, 2.0, 0.34), (0, 0, 0), glass(), 0.1); lid.parent = hinge; lid.location = (0, -1.0, 0.17)
    foam = box("foam", (2.7, 1.7, 0.06), (0, 0, 0), mat("foam", base=(0.015, 0.018, 0.03, 1), metal=0, rough=0.95, coat=0), 0.02, 2)
    foam.parent = hinge; foam.location = (0, -1.0, -0.02)
    lidband = box("lidband", (3.02, 2.02, 0.04), (0, 0, 0), glow("lidband", ICE, 1.4), 0.02, 2); lidband.parent = hinge; lidband.location = (0, -1.0, 0.05)
    lamp = bpy.data.lights.new("inside", "POINT"); lamp.color = ACC[:3]; lamp.shadow_soft_size = 0.8
    lo = link(bpy.data.objects.new("inside", lamp)); lo.parent = root; lo.location = (0, 0, 1.0)
    # the lid opens, light comes up, three blocks pop out
    key(hinge, 1, rotation_euler=(0, 0, 0)); key(hinge, F(0.9), rotation_euler=(0, 0, 0))
    key(hinge, F(1.6), rotation_euler=(math.radians(-108), 0, 0)); key(hinge, F(1.75), rotation_euler=(math.radians(-102), 0, 0))
    ease_all(hinge)
    em = bsdf(inner.data.materials[0]).inputs["Emission Strength"]
    em.default_value = 0; em.keyframe_insert("default_value", frame=F(1.0))
    em.default_value = 1.6; em.keyframe_insert("default_value", frame=F(1.7))
    lamp.energy = 0; lamp.keyframe_insert("energy", frame=F(1.0)); lamp.energy = 350; lamp.keyframe_insert("energy", frame=F(1.8))
    cols = [ACC, ICE, hex_rgba("#2FB36B")]
    for i, c in enumerate(cols):
        b = box(f"block{i}", (0.62, 0.62, 0.62), (0, 0, 0), mat(f"bm{i}", base=c, metal=0.2, rough=0.18, coat=1.0, emit=c, estr=0.6), 0.14, 6)
        b.parent = root
        x = (i - 1) * 1.05
        t0 = 1.75 + i * 0.18
        key(b, 1, location=(x, 0, 0.1), rotation_euler=(0, 0, 0), scale=(0.6, 0.6, 0.6))
        key(b, F(t0), location=(x, 0, 0.1), scale=(0.6, 0.6, 0.6))
        key(b, F(t0 + 0.45), location=(x, -0.2, 1.75 + (0.18 if i == 1 else 0)), rotation_euler=(math.radians(18), math.radians(-12 + 12 * i), math.radians(25)), scale=(1, 1, 1))
        key(b, N, location=(x, -0.25, 1.95 + (0.18 if i == 1 else 0)), rotation_euler=(math.radians(28), math.radians(-24 + 24 * i), math.radians(70)))
        ease_all(b, "EASE_OUT")
    key(root, 1, location=(0, 0, -1.2), scale=(0.8, 0.8, 0.8), rotation_euler=(0, 0, math.radians(-16)))
    key(root, F(0.6), location=(0, 0, 0), scale=(1, 1, 1), rotation_euler=(0, 0, math.radians(-10)))
    key(root, N, rotation_euler=(0, 0, math.radians(10)))
    ease_all(root, "EASE_OUT")
    camera((0, -8.2, 4.0), (0, 0, 0.85), 50)
else:
    sys.exit(f"unknown variant {variant}")

render(out, still)
