# 3D heroes of the promo (src/promo/Promo.tsx), procedural and rendered to transparent PNG sequences, 30 fps.
# Built like the real things (no downloaded models, no brands of others):
#   clapper  hook: a film slate - black acrylic board with painted fields (ПРОЕКТ, СЦЕНА, ДУБЛЬ…), striped sticks
#            in a chevron, a metal hinge with a bolt and rivets. It flies in, the stick winds up and snaps shut on the
#            «cut» (1.5 s), the board recoils, slow drift; 5.6 s
#   case     ending: a rugged equipment case - moulded graphite shell, seam lips, latch guards, two blue draw latches,
#            folding handle, back hinge, egg-crate foam in the lid, pluck foam with cut-outs in the base. The latches
#            flip (0.45 s), the lid opens (0.9–1.6 s), light comes up from the cut-outs and three drive cartridges
#            rise out (skills · scripts · styles) and hover; 6 s
# Usage: blender -b -P scripts/blender/promo_heroes.py -- clapper|case [--out DIR] [--still N]
#        npm run promo:3d   (both into public/promo3d/<name>/). The microphones of step 2 are real models: mics.py
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh
import bpy
from hero_common import *  # noqa

variant, out, still = args("clapper")
out = out or os.path.join(ROOT, "public", "promo3d", variant)
FPS = 30
F = lambda s: 1 + int(round(s * FPS))
R = math.radians
ACC = hex_rgba("#5B8CFF")  # the promo is the author's film: his accent; your own scenes take accent() from kit.config.json
GREEN = hex_rgba("#2FB36B")


def metal(name="metal", c=0.62, rough=0.3):
    return mat(name, base=(c, c * 1.01, c * 1.04, 1), metal=1.0, rough=rough, coat=0.1)


def paint(name="paint", c=0.86, e=0.12):
    return mat(name, base=(c, c, c * 1.02, 1), metal=0.0, rough=0.55, coat=0.0, emit=(1, 1, 1, 1), estr=e)


def hollow(objs, size, loc, parent=None):
    """cut the inside out of solid shells (a hidden box + Boolean), so foam and light inside are visible"""
    c = box("cutter", size, loc, mat("cutter"), 0)
    c.hide_render = True; c.hide_viewport = True
    if parent:
        c.parent = parent
    for o in objs:
        b = o.modifiers.new("hollow", "BOOLEAN"); b.operation = "DIFFERENCE"; b.object = c
    return c


def snap(obj, frame, mode="EASE_IN", interp="QUAD"):
    """the key that ends at `frame` accelerates into it (a fall, a snap), not an ease"""
    for fc in curves(obj):
        for kp in fc.keyframe_points:
            if abs(kp.co[0] - frame) < 0.5:
                kp.interpolation = "BEZIER"
        for a, b in zip(fc.keyframe_points, fc.keyframe_points[1:]):
            if abs(b.co[0] - frame) < 0.5:
                a.interpolation = interp; a.easing = mode


if variant == "clapper":
    N = F(5.6)
    s = reset(FPS, N, (1200, 1000), samples=48)
    studio(key=1000, rim=1800, fill=220)
    bright_world(0.35)
    root = empty("root")
    W, H, T = 3.0, 2.4, 0.09
    acrylic = mat("acrylic", base=(0.010, 0.011, 0.014, 1), metal=0.0, rough=0.16, coat=1.0)
    pnt, lbl = paint("paint"), paint("label", 0.55, 0.05)
    acc = mat("accent", base=ACC, metal=0.0, rough=0.5, coat=0.0, emit=ACC, estr=0.5)
    parts = [box("board", (W, T, H), (0, 0, 0), acrylic, 0.035, 4)]
    fy = -T / 2 - 0.002  # painted layer on the front face
    # painted grid: 4 rows - project / roll·scene·take / director·editor / day·fps·sound
    rows = [0.56, -0.06, -0.62]
    for z in rows:
        parts.append(box(f"h{z}", (W - 0.16, 0.006, 0.028), (0, fy, z), pnt, 0))
    for x, z0, z1 in ((-0.5, -0.06, 0.56), (0.5, -0.06, 0.56), (0.0, -0.62, -0.06), (-0.5, -1.12, -0.62), (0.5, -1.12, -0.62)):
        parts.append(box(f"v{x}{z0}", (0.028, 0.006, z1 - z0), (x, fy, (z0 + z1) / 2), pnt, 0))
    ty = fy - 0.004
    def field(label, value, x0, ztop, vsize=0.26, vmat=None):
        parts.append(text(f"l_{label}", label, 0.1, (x0 + 0.08, ty, ztop - 0.1), lbl, weight=0.002, family="oswald"))
        parts.append(text(f"v_{label}", value, vsize, (x0 + 0.1, ty, ztop - 0.12 - 0.1 - vsize * 0.5), vmat or pnt, weight=0.006, family="oswald"))
    parts.append(text("l_proj", "ПРОЕКТ", 0.1, (-W / 2 + 0.16, ty, 1.04), lbl, weight=0.002, family="oswald"))
    parts.append(text("v_proj", "REINH", 0.36, (-W / 2 + 0.18, ty, 0.76), pnt, weight=0.008, family="oswald"))
    parts.append(text("v_proj2", "EDIT KIT", 0.36, (-0.4, ty, 0.76), acc, weight=0.008, family="oswald"))
    field("КАССЕТА", "A01", -1.5, 0.56)
    field("СЦЕНА", "12", -0.5, 0.56)
    field("ДУБЛЬ", "3", 0.5, 0.56, vmat=acc)
    field("РЕЖИССЁР", "вы", -1.5, -0.06, 0.26)
    field("МОНТАЖ", "агент", 0.0, -0.06, 0.26)
    field("ДЕНЬ", "01", -1.5, -0.62, 0.22)
    field("FPS", "60", -0.5, -0.62, 0.22)
    field("ЗВУК", "-15 LUFS", 0.5, -0.62, 0.22)
    # sticks: bottom one fixed on the board, the top one on a hinge; stripes form a chevron when shut
    SH, SD = 0.34, 0.12
    zb = H / 2 + SH / 2 + 0.01
    white, black = (0.88, 0.89, 0.9, 1), (0.012, 0.012, 0.014, 1)
    parts.append(box("stick_b", (W, SD, SH), (0, 0, zb), stripes_mat("sb", white, black, 2.1, sign=1, rough=0.3), 0.014, 3))
    pivot = empty("pivot", (-W / 2 + 0.02, 0, zb + SH / 2 + 0.006)); pivot.parent = root
    top = box("stick_t", (W, SD, SH), (0, 0, 0), stripes_mat("st", white, black, 2.1, sign=-1, rough=0.3), 0.014, 3)
    top.parent = pivot; top.location = (W / 2 - 0.02, 0, SH / 2 + 0.004)
    # hinge: two plates (one per stick), rivets, a bolt with a nut at the pivot
    hm = metal("hinge", 0.66, 0.28)
    parts.append(box("plate_b", (0.26, 0.012, SH - 0.04), (-W / 2 + 0.15, -SD / 2 - 0.007, zb), hm, 0.006, 2))
    pt = box("plate_t", (0.26, 0.012, SH - 0.04), (0, 0, 0), hm, 0.006, 2); pt.parent = pivot; pt.location = (0.13, -SD / 2 - 0.007, SH / 2)
    for i, z in enumerate((zb - 0.08, zb + 0.08)):
        parts.append(cyl(f"rivet_b{i}", 0.022, 0.02, (-W / 2 + 0.2, -SD / 2 - 0.014, z), metal("rv", 0.8, 0.2), 24, (R(90), 0, 0)))
        rv = cyl(f"rivet_t{i}", 0.022, 0.02, (0, 0, 0), metal("rv2", 0.8, 0.2), 24, (R(90), 0, 0)); rv.parent = pivot
        rv.location = (0.18, -SD / 2 - 0.014, SH / 2 + (i - 0.5) * 0.16)
    bolt = cyl("bolt", 0.055, SD + 0.08, (0, 0, 0), metal("bolt", 0.75, 0.18), 32, (R(90), 0, 0)); bolt.parent = pivot
    nut = cyl("nut", 0.085, 0.04, (0, 0, 0), metal("nut", 0.7, 0.25), 6, (R(90), 0, 0), bevel=0.008); nut.parent = pivot
    nut.location = (0, -SD / 2 - 0.035, 0)
    for o in parts:
        o.parent = root
    # framing on the widest pose (stick open, board turned)
    pivot.rotation_euler = (0, R(-34), 0)
    root.rotation_euler = (R(6), 0, R(-22))
    auto_camera([root], (1200, 1000), lens=55, margin=1.16, tilt=4)
    # entrance, recoil on the snap, drift
    key(root, 1, location=(0.25, 0, -3.6), rotation_euler=(R(14), R(4), R(-38)))
    key(root, F(0.6), location=(0, 0, 0), rotation_euler=(R(6), 0, R(-24)))
    key(root, F(1.5), location=(0, 0, 0), rotation_euler=(R(6), 0, R(-22)))
    key(root, F(1.6), location=(0, 0.05, -0.05), rotation_euler=(R(9), R(-1.5), R(-21)))
    key(root, F(1.85), location=(0, 0, 0), rotation_euler=(R(5.5), 0, R(-20.5)))
    key(root, N, location=(0, 0, 0.12), rotation_euler=(R(3), 0, R(-12)))
    ease_all(root, "EASE_OUT")
    # the stick: open, wind up, SNAP on the cut, small bounce
    key(pivot, 1, rotation_euler=(0, R(-26), 0))
    key(pivot, F(1.25), rotation_euler=(0, R(-34), 0))
    key(pivot, F(1.5), rotation_euler=(0, 0, 0))
    key(pivot, F(1.6), rotation_euler=(0, R(-5), 0))
    key(pivot, F(1.72), rotation_euler=(0, 0, 0))
    ease_all(pivot)
    snap(pivot, F(1.5), "EASE_IN", "CUBIC")

elif variant == "case":
    N = F(6.0)
    s = reset(FPS, N, (1000, 1000), samples=48)
    studio(key=1100, rim=1700, fill=240)
    bright_world(0.4)
    root = empty("root")
    W, D, HB, HL = 3.2, 2.2, 1.0, 0.44
    shell = textured(mat("shell", base=(0.022, 0.024, 0.028, 1), metal=0.0, rough=0.5, coat=0.15), 420, 0.25)
    rubber = textured(mat("rubber", base=(0.012, 0.012, 0.013, 1), metal=0.0, rough=0.8, coat=0.0), 260, 0.4)
    blue = mat("latch", base=ACC, metal=0.0, rough=0.35, coat=0.4)
    hm = metal("hinge", 0.6, 0.3)
    foam_m = textured(mat("foam", base=(0.03, 0.031, 0.034, 1), metal=0.0, rough=0.95, coat=0.0), 140, 0.6, 0.01)
    base = []
    base.append(box("base", (W, D, HB), (0, 0, HB / 2), shell, 0.16, 6))
    base.append(box("lip_b", (W + 0.08, D + 0.08, 0.1), (0, 0, HB - 0.07), shell, 0.04, 3))
    base.append(box("foot_l", (0.5, D - 0.3, 0.06), (-W / 2 + 0.45, 0, 0.0), rubber, 0.03, 2))
    base.append(box("foot_r", (0.5, D - 0.3, 0.06), (W / 2 - 0.45, 0, 0.0), rubber, 0.03, 2))
    hollow(base[:2], (W - 0.2, D - 0.2, HB), (0, 0, HB / 2 + 0.14), root)
    fy = -D / 2
    # latch guards (vertical ribs either side of each latch), handle mounts, folding handle
    LX = 0.98
    for sx in (-1, 1):
        for dx in (-0.36, 0.36):
            base.append(box(f"rib{sx}{dx}", (0.1, 0.14, 0.86), (sx * LX + dx, fy - 0.03, 0.5), shell, 0.04, 3))
    for x in (-0.46, 0.46):
        base.append(box(f"mount{x}", (0.18, 0.16, 0.2), (x, fy - 0.04, 0.8), shell, 0.05, 3))
        base.append(box(f"arm{x}", (0.09, 0.08, 0.36), (x, fy - 0.1, 0.6), shell, 0.03, 3))
    base.append(box("grip", (1.06, 0.16, 0.15), (0, fy - 0.12, 0.42), rubber, 0.07, 5))
    base.append(cyl("valve", 0.09, 0.05, (0, fy - 0.01, 0.14), shell, 32, (R(90), 0, 0), bevel=0.01))
    # pluck foam with three cut-outs; light comes from below the cut-outs
    foam = box("foam_b", (W - 0.24, D - 0.24, 0.5), (0, 0, HB - 0.32), foam_m, 0)
    base.append(foam)
    glows = []
    CW, CL = 0.86, 1.22
    cols = [ACC, ICE, GREEN]
    for i, c in enumerate(cols):
        x = (i - 1) * 1.0
        cut = box(f"cut{i}", (CW, CL, 0.5), (x, 0, HB - 0.07), foam_m, 0)
        cut.hide_render = True; cut.hide_viewport = True
        b = foam.modifiers.new(f"cut{i}", "BOOLEAN"); b.operation = "DIFFERENCE"; b.object = cut
        g = box(f"glow{i}", (CW - 0.04, CL - 0.04, 0.02), (x, 0, HB - 0.31), mat(f"glow{i}", base=(0.02, 0.02, 0.02, 1), metal=0, rough=0.6, coat=0, emit=c, estr=0.0), 0)
        base.append(g); glows.append(g)
        sl = bpy.data.lights.new(f"slot{i}", "POINT"); sl.color = c[:3]; sl.shadow_soft_size = 0.3
        so = link(bpy.data.objects.new(f"slot{i}", sl)); so.location = (x, 0, HB - 0.12); base.append(so)
        glows.append(sl)
    for o in base:
        o.parent = root
    # back hinge (three knuckles) and the lid on it
    for i, x in enumerate((-1.1, 0.0, 1.1)):
        k = cyl(f"knuckle{i}", 0.08, 0.6, (x, D / 2 + 0.06, HB), shell, 32, (0, R(90), 0), bevel=0.02); k.parent = root
        pin = cyl(f"pin{i}", 0.03, 0.66, (x, D / 2 + 0.06, HB), hm, 16, (0, R(90), 0)); pin.parent = root
    hinge = empty("hinge", (0, D / 2 + 0.06, HB)); hinge.parent = root
    lid = []
    lid.append(box("lid", (W, D, HL), (0, 0, HL / 2), shell, 0.16, 6))
    lid.append(box("lip_t", (W + 0.08, D + 0.08, 0.08), (0, 0, 0.06), shell, 0.04, 3))
    lid.append(box("panel", (W - 0.6, D - 0.6, 0.06), (0, 0, HL + 0.02), shell, 0.05, 3))
    for sx in (-1, 1):
        lid.append(box(f"ridge{sx}", (0.12, D - 0.5, 0.05), (sx * (W / 2 - 0.18), 0, HL - 0.01), shell, 0.04, 3))
    lid.append(box("plate", (1.3, 0.36, 0.025), (0, -D / 2 + 0.5, HL + 0.06), blue, 0.02, 3))
    lid.append(text("name", "REINH EDIT KIT", 0.16, (0, -D / 2 + 0.5, HL + 0.074), paint("name", 0.95, 0.3), rot=(0, 0, 0), align="CENTER", weight=0.01))
    lid_cut = hollow(lid[:2], (W - 0.2, D - 0.2, HL), (0, 0, HL / 2 - 0.12))
    lid.append(lid_cut)
    # egg-crate foam on the inside of the lid
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=72, y_segments=50, size=1.0)
    for v in bm.verts:
        x, y = v.co.x * (W - 0.26) / 2, v.co.y * (D - 0.26) / 2
        v.co = (x, y, -0.06 * (1 + math.sin(x * 34) * math.sin(y * 34)) / 2)
    me = bpy.data.meshes.new("eggcrate"); bm.to_mesh(me); bm.free()
    egg = link(bpy.data.objects.new("eggcrate", me)); egg.data.materials.append(foam_m)
    for p in egg.data.polygons:
        p.use_smooth = True
    egg.location = (0, 0, HL - 0.13)
    lid.append(egg)
    for o in lid:
        o.parent = hinge
        o.location.y -= D / 2 + 0.06
    # draw latches on the front: pivot at the bottom, the hook over the lid lip
    latches = []
    for sx in (-1, 1):
        lp = empty(f"latch_p{sx}", (sx * LX, fy - 0.1, 0.74)); lp.parent = root
        body = box(f"latch{sx}", (0.5, 0.08, 0.52), (0, 0, 0.26), blue, 0.035, 4); body.parent = lp
        hook = cyl(f"hook{sx}", 0.03, 0.42, (0, 0.05, 0.5), hm, 24, (0, R(90), 0)); hook.parent = lp
        for dz in (0.12, 0.38):
            ln = box(f"groove{sx}{dz}", (0.36, 0.01, 0.02), (0, -0.045, dz), rubber, 0); ln.parent = lp
        latches.append(lp)
    # drive cartridges: gunmetal body, black glass front, coloured LED strip, label
    names = ["СКИЛЛЫ", "СКРИПТЫ", "СТИЛИ"]
    carts = []
    for i, (c, nm) in enumerate(zip(cols, names)):
        cp = empty(f"cart{i}"); cp.parent = root
        bodyc = box(f"cbody{i}", (0.72, 0.2, 1.06), (0, 0, 0), metal(f"gun{i}", 0.16, 0.32), 0.06, 4); bodyc.parent = cp
        face = box(f"cface{i}", (0.6, 0.02, 0.92), (0, -0.1, 0), mat(f"cglass{i}", base=(0.01, 0.012, 0.018, 1), metal=0.2, rough=0.12, coat=1.0), 0.03, 3)
        face.parent = cp
        led = box(f"cled{i}", (0.05, 0.02, 0.78), (-0.24, -0.115, 0), mat(f"cled{i}", base=c, metal=0, rough=0.3, coat=0, emit=c, estr=6), 0.02, 2)
        led.parent = cp
        t = text(f"clabel{i}", nm, 0.08, (0.06, -0.118, 0.3), paint(f"cl{i}", 0.95, 0.4), align="CENTER", weight=0.006)
        t.parent = cp
        for k in range(4):  # capacity bars under the label
            bar = box(f"cbar{i}{k}", (0.3 - k * 0.05, 0.01, 0.028), (0.06, -0.114, 0.08 - k * 0.09), paint(f"cb{i}{k}", 0.4, 0.1), 0)
            bar.parent = cp
        carts.append(cp)
    lamp = bpy.data.lights.new("inside", "POINT"); lamp.color = ACC[:3]; lamp.shadow_soft_size = 0.9
    lo = link(bpy.data.objects.new("inside", lamp)); lo.parent = root; lo.location = (0, -0.3, 1.5)
    # framing: lid open, cartridges up
    hinge.rotation_euler = (R(-104), 0, 0)
    for i, cp in enumerate(carts):
        cp.location = ((i - 1) * 1.02, -0.45, 2.15 + (0.16 if i == 1 else 0))
    root.rotation_euler = (0, 0, R(-6))
    auto_camera([root], (1000, 1000), lens=50, margin=1.1, tilt=24)
    # latches flip, the lid opens, light comes up, the cartridges rise out of the foam
    for j, lp in enumerate(latches):
        t0 = 0.4 + j * 0.1
        key(lp, 1, rotation_euler=(0, 0, 0)); key(lp, F(t0), rotation_euler=(0, 0, 0))
        key(lp, F(t0 + 0.22), rotation_euler=(R(112), 0, 0)); key(lp, F(t0 + 0.32), rotation_euler=(R(100), 0, 0))
        ease_all(lp)
    key(hinge, 1, rotation_euler=(0, 0, 0)); key(hinge, F(0.9), rotation_euler=(0, 0, 0))
    key(hinge, F(1.6), rotation_euler=(R(-110), 0, 0)); key(hinge, F(1.75), rotation_euler=(R(-104), 0, 0))
    ease_all(hinge)
    for g in glows:  # cut-out floors glow softly, a coloured lamp in each slot lights its walls
        if isinstance(g, bpy.types.Light):
            g.energy = 0; g.keyframe_insert("energy", frame=F(1.0)); g.energy = 45; g.keyframe_insert("energy", frame=F(1.7))
            continue
        em = bsdf(g.data.materials[0]).inputs["Emission Strength"]
        em.default_value = 0; em.keyframe_insert("default_value", frame=F(1.0))
        em.default_value = 0.35; em.keyframe_insert("default_value", frame=F(1.7))
    lamp.energy = 0; lamp.keyframe_insert("energy", frame=F(1.0)); lamp.energy = 260; lamp.keyframe_insert("energy", frame=F(1.8))
    for i, cp in enumerate(carts):
        x = (i - 1) * 1.0
        t0 = 1.75 + i * 0.18
        lying = (x, 0, HB - 0.2)
        key(cp, 1, location=lying, rotation_euler=(R(-90), 0, 0)); key(cp, F(t0), location=lying, rotation_euler=(R(-90), 0, 0))
        up = ((i - 1) * 1.02, -0.45, 2.15 + (0.16 if i == 1 else 0))
        key(cp, F(t0 + 0.5), location=up, rotation_euler=(R(-14), R(-6 + 6 * i), R(10 - 10 * i)))
        key(cp, N, location=(up[0], up[1] - 0.05, up[2] + 0.16), rotation_euler=(R(-10), R(-10 + 10 * i), R(18 - 18 * i)))
        ease_all(cp, "EASE_OUT")
    key(root, 1, location=(0, 0, -0.3), scale=(0.72, 0.72, 0.72), rotation_euler=(0, 0, R(-26)))
    key(root, F(0.6), location=(0, 0, 0), scale=(1, 1, 1), rotation_euler=(0, 0, R(-12)))
    key(root, N, rotation_euler=(0, 0, R(8)))
    ease_all(root, "EASE_OUT")
else:
    sys.exit(f"unknown variant {variant}")

render(out, still)
