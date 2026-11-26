# Shared helpers for 3D «heroes»: procedural Blender scenes rendered headless to a transparent PNG sequence that Remotion
# plays over any background (src/kit/Hero3D.tsx). Look of the cine style: dark glossy glass, chrome, ice-blue rims.
# Run a scene:  blender -b -P scripts/blender/<scene>.py -- <variant> [--out DIR] [--still FRAME]
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


def stripes_mat(name, a, b, k=3.0, emit_a=0.0):
    """diagonal stripes (x + z in object space) between colours a and b — the clapperboard look"""
    m = mat(name, base=a, metal=0.1, rough=0.25, coat=1.0)
    nt = m.node_tree
    p = bsdf(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"
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
