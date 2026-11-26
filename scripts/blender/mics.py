# Popular microphones as procedural 3D heroes (no downloaded models, no logos: shapes and proportions only, built from
# primitives here). Rendered to transparent PNG turntables for Hero3D, 30 fps.
#   sm7b      Shure SM7B — broadcast dynamic: long satin body, big foam windscreen, U-yoke with side nuts
#   yeti      Blue Yeti — USB condenser: silver capsule with a grille top, red mute button, yoke on a round base
#   solocast  HyperX SoloCast — compact USB condenser: black body, grille top, red mute LED, hinge on a small stand
#   dji       DJI Mic Mini 2 — wireless lav: pebble transmitter with a magnetic cover and clip + the receiver
#   podmic    Rode PodMic — end-address dynamic: chunky black body, grille head, swing mount with a knob
#   lineup    all five in a row, one still (README / comparison board)
# Usage: blender -b -P scripts/blender/mics.py -- sm7b [--out DIR] [--still N] [--frames N]
#        npm run mics:3d   (all five turntables into public/mics3d/<name>/)
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh
import bpy
from mathutils import Vector
from hero_common import *  # noqa

variant, out, still = args("lineup")
a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FRAMES = int(a[a.index("--frames") + 1]) if "--frames" in a else 150
out = out or os.path.join(ROOT, "public", "mics3d", variant)


# ---------------------------------------------------------------- materials
def satin(name, c, metal=0.6, rough=0.42):
    return mat(name, base=(c, c, c * 1.06, 1), metal=metal, rough=rough, coat=0.15)


def black_plastic(name="black"):
    return mat(name, base=(0.018, 0.018, 0.02, 1), metal=0.0, rough=0.55, coat=0.1)


def silver(name="silver"):
    return mat(name, base=(0.62, 0.64, 0.68, 1), metal=1.0, rough=0.32, coat=0.1)


def chrome_m(name="chrome"):
    return mat(name, base=(0.85, 0.88, 0.95, 1), metal=1.0, rough=0.12, coat=0.3)


def foam(name="foam"):
    m = mat(name, base=(0.012, 0.012, 0.014, 1), metal=0.0, rough=0.95, coat=0.0)
    nt = m.node_tree
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 90; noise.inputs["Detail"].default_value = 6
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.7; bump.inputs["Distance"].default_value = 0.02
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf(m).inputs["Normal"])
    return m


def red_led(name="red", e=8):
    return mat(name, base=(0.3, 0.02, 0.02, 1), metal=0, rough=0.3, coat=0.5, emit=(1.0, 0.08, 0.06, 1), estr=e)


# ---------------------------------------------------------------- shapes
def wire_cylinder(name, r, depth, loc, m, verts=40, rings=14, th=0.012, rot=(0, 0, 0)):
    """open cylinder with dense rings → wireframe = a mic grille"""
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot, end_fill_type="NOTHING")
    o = bpy.context.object; o.name = name
    bm = bmesh.new(); bm.from_mesh(o.data)
    vert_edges = [e for e in bm.edges if (e.verts[0].co - e.verts[1].co).length > depth * 0.6]
    bmesh.ops.subdivide_edges(bm, edges=vert_edges, cuts=rings, use_grid_fill=False)
    bm.to_mesh(o.data); bm.free()
    o.modifiers.new("wire", "WIREFRAME").thickness = th
    o.data.materials.append(m)
    return o


def wire_dome(name, r, loc, m, squash=0.6, seg=40, rings=20, th=0.012, rot=(0, 0, 0), scale_axis=2):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=r, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    sc = [1, 1, 1]; sc[scale_axis] = squash; o.scale = sc
    o.modifiers.new("wire", "WIREFRAME").thickness = th
    o.data.materials.append(m)
    return o


def sphere(name, r, loc, m, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=r, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.scale = scale
    o.data.materials.append(m); bpy.ops.object.shade_smooth()
    return o


def torus(name, R, r, loc, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot, major_segments=96, minor_segments=16)
    o = bpy.context.object; o.name = name
    o.data.materials.append(m); bpy.ops.object.shade_smooth()
    return o


AX_X = (0, math.radians(90), 0)   # cylinder along X
AX_Y = (math.radians(90), 0, 0)   # cylinder along Y


def kids(root, objs):
    for o in objs:
        if o.parent is None and o is not root:
            o.parent = root


# ---------------------------------------------------------------- the microphones (1 unit ≈ 10 cm, except the DJI set ≈ 1 cm)
def build_sm7b(root):
    body_m, dark = satin("sm7b_body", 0.05), satin("sm7b_dark", 0.025, 0.4, 0.5)
    objs = [
        cyl("body", 0.31, 1.25, (0.15, 0, 0), body_m, rot=AX_X, bevel=0.03),
        cyl("rear", 0.285, 0.1, (0.82, 0, 0), dark, rot=AX_X, bevel=0.03),
        cyl("xlr", 0.09, 0.05, (0.875, 0, 0), black_plastic(), rot=AX_X),
        cyl("trim", 0.315, 0.04, (-0.43, 0, 0), chrome_m(), rot=AX_X),
        cyl("windscreen", 0.37, 0.55, (-0.70, 0, 0), foam(), rot=AX_X, verts=96),
        sphere("ws_front", 0.37, (-0.975, 0, 0), foam(), scale=(0.62, 1, 1)),
    ]
    for y in (-1, 1):
        objs += [cyl(f"nut{y}", 0.17, 0.08, (0.1, 0.38 * y, 0), dark, rot=AX_Y, bevel=0.02),
                 cyl(f"bolt{y}", 0.06, 0.1, (0.1, 0.43 * y, 0), chrome_m(), rot=AX_Y),
                 box(f"arm{y}", (0.17, 0.05, 0.66), (0.1, 0.43 * y, -0.31), dark, 0.02)]
    objs += [box("yoke_bottom", (0.17, 0.91, 0.06), (0.1, 0, -0.64), dark, 0.02),
             cyl("adapter", 0.07, 0.35, (0.1, 0, -0.83), chrome_m())]
    kids(root, objs)
    return math.radians(22)   # front (−X) turned towards the camera: the usual 3/4 hero view


def build_yeti(root):
    body_m, sil = silver("yeti_body"), silver("yeti_dark")
    bsdf(body_m).inputs["Base Color"].default_value = (0.78, 0.8, 0.84, 1)
    bsdf(sil).inputs["Base Color"].default_value = (0.42, 0.44, 0.48, 1)
    grille = chrome_m("yeti_grille")
    core = black_plastic("yeti_core")
    objs = [
        cyl("base", 0.62, 0.12, (0, 0, 0.06), sil, bevel=0.04),
        cyl("neck", 0.12, 0.3, (0, 0, 0.27), sil),
        box("yoke_bottom", (1.32, 0.16, 0.08), (0, 0, 0.44), sil, 0.03),
        box("armL", (0.08, 0.16, 1.2), (-0.62, 0, 1.0), sil, 0.03),
        box("armR", (0.08, 0.16, 1.2), (0.62, 0, 1.0), sil, 0.03),
        cyl("knobL", 0.17, 0.13, (-0.71, 0, 1.6), sil, verts=48, rot=AX_X, bevel=0.02),
        cyl("knobR", 0.17, 0.13, (0.71, 0, 1.6), sil, verts=48, rot=AX_X, bevel=0.02),
        cyl("body", 0.5, 0.72, (0, 0, 1.16), body_m, bevel=0.06),
        torus("seam", 0.505, 0.018, (0, 0, 1.52), chrome_m()),
        cyl("core", 0.48, 0.62, (0, 0, 1.83), core),
        sphere("core_top", 0.48, (0, 0, 2.14), core, scale=(1, 1, 0.55)),
        wire_cylinder("grille", 0.505, 0.62, (0, 0, 1.83), grille, verts=56, rings=18, th=0.011),
        wire_dome("grille_top", 0.505, (0, 0, 2.14), grille, squash=0.56, seg=56, rings=28, th=0.011),
        cyl("mute", 0.12, 0.05, (0, -0.5, 1.33), red_led("yeti_red", 6), rot=AX_Y),
        torus("mute_ring", 0.13, 0.015, (0, -0.505, 1.33), chrome_m(), rot=AX_Y),
        cyl("vol", 0.09, 0.08, (0, -0.5, 1.0), body_m, rot=AX_Y, bevel=0.015),
    ]
    kids(root, objs)
    return math.radians(18)


def build_solocast(root):
    blk = black_plastic("solo_black")
    satin_b = satin("solo_satin", 0.03, 0.3, 0.45)
    grille = mat("solo_grille", base=(0.08, 0.08, 0.09, 1), metal=0.8, rough=0.35)
    objs = [
        cyl("base", 0.55, 0.09, (0, 0, 0.045), satin_b, bevel=0.03),
        cyl("stem", 0.06, 0.48, (0, 0.05, 0.33), satin_b),
        box("hinge", (0.36, 0.2, 0.2), (0, 0.05, 0.66), satin_b, 0.04),
    ]
    head = empty("head", (0, 0, 0.62)); head.parent = root; head.rotation_euler = (math.radians(-8), 0, 0)
    parts = [
        cyl("body", 0.33, 0.72, (0, 0, 0.42), blk, bevel=0.05),
        cyl("core", 0.31, 0.55, (0, 0, 1.08), mat("solo_core", base=(0.005, 0.005, 0.006, 1), rough=0.8)),
        sphere("core_top", 0.31, (0, 0, 1.36), mat("solo_core2", base=(0.005, 0.005, 0.006, 1), rough=0.8), scale=(1, 1, 0.5)),
        wire_cylinder("grille", 0.335, 0.56, (0, 0, 1.08), grille, verts=44, rings=16, th=0.01),
        wire_dome("grille_top", 0.335, (0, 0, 1.36), grille, squash=0.5, seg=44, rings=22, th=0.01),
        torus("band", 0.336, 0.016, (0, 0, 0.8), satin_b),
        torus("led", 0.2, 0.014, (0, 0, 1.52), red_led("solo_red", 9)),
    ]
    for p in parts:
        p.parent = head
    kids(root, objs)
    return math.radians(20)


def build_dji(root):
    body_m = satin("dji_body", 0.035, 0.2, 0.5)
    cover = mat("dji_cover", base=(0.5, 0.66, 0.86, 1), metal=0, rough=0.3, coat=0.8)  # a coloured magnetic cover (pale blue)
    blk = black_plastic("dji_black")
    objs = [
        box("tx_body", (2.5, 0.95, 2.9), (0, 0, 1.5), body_m, 0.45, 12),
        box("tx_cover", (2.36, 0.24, 2.76), (0, -0.42, 1.5), cover, 0.4, 12),
        cyl("tx_port", 0.26, 0.06, (0, -0.56, 2.38), blk, rot=AX_Y),
        torus("tx_port_ring", 0.27, 0.025, (0, -0.57, 2.38), chrome_m(), rot=AX_Y),
        wire_dome("tx_mesh", 0.24, (0, -0.55, 2.38), mat("dji_mesh", base=(0.3, 0.3, 0.32, 1), metal=0.8, rough=0.3), squash=0.2, seg=24, rings=12, th=0.02, rot=AX_Y),
        cyl("tx_led", 0.06, 0.04, (0.8, -0.56, 0.6), mat("dji_led", base=(0, 0, 0, 1), emit=(0.3, 1, 0.5, 1), estr=8), rot=AX_Y),
        box("clip", (1.9, 0.12, 2.3), (0, 0.58, 1.65), blk, 0.25, 6),
        cyl("clip_hinge", 0.12, 1.6, (0, 0.54, 2.72), body_m, rot=AX_X),
        # receiver
        box("rx_body", (1.5, 0.7, 1.8), (2.55, 0.5, 1.15), body_m, 0.3, 8),
        box("rx_plug", (0.55, 0.22, 0.55), (2.55, 0.5, 0.05), silver("dji_plug"), 0.06, 3),
        cyl("rx_led", 0.06, 0.04, (2.55, 0.14, 1.75), mat("dji_led2", base=(0, 0, 0, 1), emit=(0.3, 1, 0.5, 1), estr=8), rot=AX_Y),
    ]
    kids(root, objs)
    return math.radians(-14)


def build_podmic(root):
    body_m = satin("pod_body", 0.03, 0.5, 0.45)
    grille = mat("pod_grille", base=(0.05, 0.05, 0.055, 1), metal=0.9, rough=0.3)
    core = mat("pod_core", base=(0.004, 0.004, 0.005, 1), rough=0.85)
    objs = [
        cyl("body", 0.33, 1.05, (0.2, 0, 0), body_m, rot=AX_X, bevel=0.03),
        sphere("rear", 0.33, (0.72, 0, 0), body_m, scale=(0.35, 1, 1)),
        cyl("core", 0.33, 0.6, (-0.62, 0, 0), core, rot=AX_X),
        sphere("core_front", 0.33, (-0.92, 0, 0), core, scale=(0.45, 1, 1)),
        wire_cylinder("grille", 0.355, 0.6, (-0.62, 0, 0), grille, verts=80, rings=28, th=0.007, rot=AX_X),
        wire_dome("grille_front", 0.355, (-0.92, 0, 0), grille, squash=0.45, seg=80, rings=40, th=0.007, rot=(0, 0, 0), scale_axis=0),
        cyl("trim", 0.36, 0.06, (-0.31, 0, 0), chrome_m(), rot=AX_X),
        cyl("knob", 0.2, 0.15, (0.25, 0.43, 0), body_m, rot=AX_Y, bevel=0.03),
        cyl("knob_cap", 0.1, 0.03, (0.25, 0.515, 0), chrome_m(), rot=AX_Y),
        box("arm", (0.2, 0.09, 0.75), (0.25, 0.43, -0.37), body_m, 0.03),
        box("arm_bottom", (0.2, 0.52, 0.09), (0.25, 0.21, -0.74), body_m, 0.03),
        cyl("thread", 0.08, 0.3, (0.25, 0, -0.9), chrome_m()),
    ]
    kids(root, objs)
    return math.radians(22)


BUILD = {"sm7b": build_sm7b, "yeti": build_yeti, "solocast": build_solocast, "dji": build_dji, "podmic": build_podmic}


# ---------------------------------------------------------------- scenes
if variant == "lineup":
    s = reset(30, 1, (2400, 900), samples=48)
    studio(key=900, rim=1600)
    bright_world()
    roots = []
    for i, name in enumerate(["yeti", "solocast", "sm7b", "podmic", "dji"]):
        r = empty(f"root_{name}")
        ang = BUILD[name](r)
        r.rotation_euler = (0, 0, ang)
        normalize(r, 2.4 if name not in ("dji",) else 1.6)
        r.location.x += (i - 2) * 3.4
        roots.append(r)
    auto_camera(roots, (2400, 900), lens=60, margin=1.05, tilt=8)
    render(out, still if still is not None else 1)
elif variant in BUILD:
    N = FRAMES
    res = (800, 1000)
    s = reset(30, N, res, samples=32)
    studio(key=900, rim=1600)
    bright_world()
    pivot = empty("pivot")          # turntable
    root = empty("root"); root.parent = pivot
    ang = BUILD[variant](root)
    root.rotation_euler = (0, 0, ang)
    normalize(root, 2.4)
    auto_camera([root], res, lens=70, margin=1.12, tilt=9, swing=math.radians(22))
    # entrance (rise + scale) and a slow swing −22° → +22°
    key(pivot, 1, scale=(0.82, 0.82, 0.82), location=(0, 0, -0.25), rotation_euler=(0, 0, math.radians(-22)))
    key(pivot, 12, scale=(1, 1, 1), location=(0, 0, 0))
    ease_all(pivot, "EASE_OUT")
    key(pivot, N, rotation_euler=(0, 0, math.radians(22)))
    for fc in curves(pivot):
        if fc.data_path == "rotation_euler":
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"; kp.easing = "EASE_IN_OUT"
    render(out, still)
else:
    sys.exit(f"unknown variant {variant}; use one of: {', '.join(BUILD)}, lineup")
