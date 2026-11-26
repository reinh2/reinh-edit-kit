# Shared helpers for 3D «heroes»: procedural Blender scenes rendered headless to a transparent PNG sequence that Remotion
# plays over any background (src/kit/Hero3D.tsx). Look of the cine style: dark glossy glass, chrome, ice-blue rims.
# Run a scene:  bash scripts/blender/blender.sh -b -P scripts/blender/<scene>.py -- <variant> [--out DIR] [--still FRAME]
# Rules from real videos: 1–3 heroes per long video, where the thought is an object (a tool, a device, a box);
# animation beats = spoken words; everything is generated here, so the renders are yours (no downloaded models).
import json, math, os, sys
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def args(default_variant):
    """(variant, out_dir or None, still frame or None) from the arguments after `--`"""
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    variant = a[0] if a and not a[0].startswith("--") else default_variant
    out = a[a.index("--out") + 1] if "--out" in a else None
    still = int(a[a.index("--still") + 1]) if "--still" in a else None
    return variant, out, still


def hex_rgba(h, a=1.0):
    """'#5B8CFF' → linear RGBA for Blender materials"""
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*lin, a)


def accent():
    try:
        return hex_rgba(json.load(open(os.path.join(ROOT, "kit.config.json")))["brand"]["accent"])
    except (OSError, KeyError, ValueError):
        return hex_rgba("#5B8CFF")


ICE = (0.65, 0.78, 1.0, 1)


def reset(fps=30, frames=90, res=(1200, 1200), samples=32):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.fps = fps
    s.frame_start, s.frame_end = 1, frames
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.render.film_transparent = True
    try:
        s.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        try:
            s.render.engine = "BLENDER_EEVEE"
        except TypeError as e:
            print("engine", e)
    ee = s.eevee
    for k, v in (("taa_render_samples", samples), ("use_raytracing", True), ("use_shadows", True)):
        if hasattr(ee, k):
            setattr(ee, k, v)
    s.render.use_motion_blur = True
    if hasattr(s.render, "motion_blur_shutter"):
        s.render.motion_blur_shutter = 0.35
    try:
        s.view_settings.view_transform = "Khronos PBR Neutral"
    except TypeError:
        pass
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.012, 0.022, 0.05, 1)
    bg.inputs[1].default_value = 0.6
    s.world = w
    return s


def mat(name, base=(0.02, 0.035, 0.07, 1), metal=0.35, rough=0.2, coat=0.8, emit=None, estr=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = bsdf(m)
    p.inputs["Base Color"].default_value = base
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rough
    for k in ("Coat Weight", "Clearcoat"):
        if k in p.inputs:
            p.inputs[k].default_value = coat
            break
    if emit:
        p.inputs["Emission Color"].default_value = emit
        p.inputs["Emission Strength"].default_value = estr
    return m


def bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def stripes_mat(name, a, b, k=3.0, emit_a=0.0, sign=1.0, rough=0.25):
    """diagonal stripes (x + sign·z in object space) between colours a and b — the clapperboard look"""
    m = mat(name, base=a, metal=0.1, rough=rough, coat=1.0)
    nt = m.node_tree
    p = bsdf(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD" if sign > 0 else "SUBTRACT"
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = k
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "FRACT"
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.5
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs["X"], add.inputs[0]); nt.links.new(sep.outputs["Z"], add.inputs[1])
    nt.links.new(add.outputs[0], mul.inputs[0]); nt.links.new(mul.outputs[0], fr.inputs[0]); nt.links.new(fr.outputs[0], gt.inputs[0])
    nt.links.new(gt.outputs[0], mix.inputs["Factor"])
    mix.inputs["A"].default_value = a
    mix.inputs["B"].default_value = b
    nt.links.new(mix.outputs["Result"], p.inputs["Base Color"])
    if emit_a:
        nt.links.new(mix.outputs["Result"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = emit_a
    return m


def textured(m, scale=350.0, strength=0.2, distance=0.003):
    """fine noise bump on a material: moulded plastic, foam, brushed paint"""
    nt = m.node_tree
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = scale; noise.inputs["Detail"].default_value = 8
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = strength; bump.inputs["Distance"].default_value = distance
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf(m).inputs["Normal"])
    return m


_FONTS = {}


def font(family, body):
    """the kit's own web fonts (public/fonts/<family>-latin|cyrillic.woff2, FreeType reads woff2); the subset is picked
    by the text, so keep each text object one script. Without the files: Blender's built-in font (its Ж is broken)"""
    sub = "cyrillic" if any("\u0400" <= ch <= "\u04FF" for ch in body) else "latin"
    k = f"{family}-{sub}"
    if k not in _FONTS:
        p = os.path.join(ROOT, "public", "fonts", f"{k}.woff2")
        _FONTS[k] = bpy.data.fonts.load(p, check_existing=True) if os.path.exists(p) else None
    return _FONTS[k]


def text(name, body, size, loc, m, rot=(math.radians(90), 0, 0), align="LEFT", extrude=0.003, weight=0.0, family="inter"):
    """3D text; the default rot stands it up facing −Y (the camera)"""
    c = bpy.data.curves.new(name, "FONT")
    f = font(family, body)
    if f:
        c.font = f
    c.body, c.size, c.extrude, c.offset = body, size, extrude, weight
    c.align_x, c.align_y = align, "CENTER"
    o = link(bpy.data.objects.new(name, c))
    o.location, o.rotation_euler = loc, rot
    o.data.materials.append(m)
    return o


def link(o):
    bpy.context.scene.collection.objects.link(o)
    return o


def box(name, size, loc, m, bevel=0.06, seg=5):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        b = o.modifiers.new("b", "BEVEL"); b.width = bevel; b.segments = seg
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def cyl(name, r, depth, loc, m, verts=64, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, vertices=verts, rotation=rot)
    o = bpy.context.object
    o.name = name
    if bevel:
        b = o.modifiers.new("b", "BEVEL"); b.width = bevel; b.segments = 4; b.limit_method = "ANGLE"
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def empty(name, loc=(0, 0, 0)):
    o = link(bpy.data.objects.new(name, None))
    o.location = loc
    return o


def area(name, loc, rot, power, color=(1, 1, 1), size=4.0):
    l = bpy.data.lights.new(name, "AREA")
    l.energy, l.color, l.size = power, color, size
    o = link(bpy.data.objects.new(name, l))
    o.location, o.rotation_euler = loc, rot
    return o


def studio(key=800, rim=1400, fill=180):
    """key light from the front-left, two ice-blue rims from behind, a soft fill"""
    area("key", (-2, -6, 7), (math.radians(40), 0, math.radians(-15)), key, (1, 0.98, 0.95), 5)
    area("rimL", (-6, 5, 4), (math.radians(-60), math.radians(-40), 0), rim, (0.4, 0.58, 1.0), 4)
    area("rimR", (6, 5, 4), (math.radians(-60), math.radians(40), 0), rim, (0.4, 0.58, 1.0), 4)
    area("fill", (0, -9, 1), (math.radians(88), 0, 0), fill, (0.85, 0.9, 1.0), 8)


def look_at(o, target):
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(loc, target, lens=50):
    c = bpy.data.cameras.new("cam")
    c.lens = lens
    o = link(bpy.data.objects.new("cam", c))
    o.location = loc
    look_at(o, target)
    bpy.context.scene.camera = o
    return o


def key(o, frame, **kw):
    for k, v in kw.items():
        setattr(o, k, v)
        o.keyframe_insert(k, frame=frame)


def curves(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return []
    try:
        return list(ad.action.fcurves)
    except AttributeError:  # Blender 5 layered actions
        return [fc for l in ad.action.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]


def ease_all(obj, mode="EASE_IN_OUT", interp="BEZIER"):
    for fc in curves(obj):
        for kp in fc.keyframe_points:
            kp.interpolation = interp
            kp.easing = mode


def linear(obj):
    ease_all(obj, interp="LINEAR")


# ---- framing: fit the camera to objects, light metals
def bounds(root):
    bpy.context.view_layer.update()
    pts = []
    for o in [c for c in root.children_recursive if c.type == "MESH"]:
        pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def normalize(root, height=2.4, by="height"):
    """scale so the object stands `height` tall (by="max": its longest side, for objects lying on their side) with its
    base on z = 0, centred in x/y"""
    lo, hi = bounds(root)
    d = hi - lo
    k = height / max(max(d.x, d.y, d.z) if by == "max" else d.z, 1e-6)
    root.scale = (k, k, k)
    bpy.context.view_layer.update()
    lo, hi = bounds(root)
    c = (lo + hi) / 2
    root.location = (root.location.x - c.x, root.location.y - c.y, root.location.z - lo.z)


def auto_camera(roots, res, lens=70, margin=1.08, tilt=10, swing=0.0):
    """fit the box of `roots` by width and height (sensor fit AUTO: 36 mm on the long side); `swing` (rad) widens the
    width for a turntable"""
    lo = Vector((1e9, 1e9, 1e9)); hi = -lo
    for r in roots:
        a_, b_ = bounds(r)
        lo = Vector(map(min, lo, a_)); hi = Vector(map(max, hi, b_))
    c = (lo + hi) / 2
    w = max(hi.x - lo.x, hi.y - lo.y) if swing else hi.x - lo.x
    h, depth = hi.z - lo.z, hi.y - lo.y
    long_ = 18 / lens
    hf = 2 * math.atan(long_ * (1 if res[0] >= res[1] else res[0] / res[1]))
    vf = 2 * math.atan(long_ * (1 if res[1] >= res[0] else res[1] / res[0]))
    d = (max((w / 2) / math.tan(hf / 2), (h / 2) / math.tan(vf / 2)) + depth / 2) * margin
    t = math.radians(tilt)
    camera((c.x, c.y - d * math.cos(t), c.z + d * math.sin(t)), (c.x, c.y, c.z), lens)


def bright_world(strength=0.9):
    """soft grey studio sky: metals reflect light instead of the dark default; invisible (transparent film)"""
    bg = next(n for n in bpy.context.scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.55, 0.58, 0.64, 1)
    bg.inputs[1].default_value = strength



def render(out, still=None):
    """PNG sequence into `out` (0001.png …) + meta.json {frames, fps, width, height}; --still N renders one frame"""
    s = bpy.context.scene
    os.makedirs(out, exist_ok=True)
    if still is not None:
        s.frame_set(still)
        s.render.filepath = f"{out}/still_{still:04d}.png"
        bpy.ops.render.render(write_still=True)
        return
    json.dump({"frames": s.frame_end, "fps": s.render.fps, "width": s.render.resolution_x, "height": s.render.resolution_y},
              open(f"{out}/meta.json", "w"))
    s.render.filepath = f"{out}/"
    s.render.use_overwrite = False  # resume: frames already on disk are skipped
    bpy.ops.render.render(animation=True)
