from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", required=True)
    parser.add_argument("--story", required=True)
    parser.add_argument("--frames", required=True)
    return parser.parse_args(argv)


def material(name, color, metallic=0.0, roughness=0.45, emission=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if emission > 0:
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = color
            elif "Emission" in bsdf.inputs:
                bsdf.inputs["Emission"].default_value = color
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def assign(obj, mat):
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.append(mat)
    return obj


def smooth(obj):
    if obj.type == "MESH":
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def uv_sphere(name, location, scale, mat, segments=16, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    assign(obj, mat)
    smooth(obj)
    return obj


def ico_sphere(name, location, scale, mat, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    assign(obj, mat)
    return obj


def cube(name, location, scale, mat, bevel=0.12):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, mat)
    if bevel:
        modifier = obj.modifiers.new("Soft low-poly edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return obj


def cylinder_between(name, start, end, radius, mat, vertices=8):
    a, b = Vector(start), Vector(end)
    direction = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=direction.length, location=(a + b) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    assign(obj, mat)
    return obj


def text_object(name, body, location, size, mat, align="CENTER"):
    curve = bpy.data.curves.new(name, type="FONT")
    curve.body = body
    curve.size = size
    curve.align_x = align
    curve.extrude = 0.006
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (math.radians(90), 0, 0)
    assign(obj, mat)
    return obj


def keyframe_location(obj, frame, location):
    obj.location = location
    obj.keyframe_insert(data_path="location", frame=frame)


def add_area_light(name, location, energy, color, size, target=(0, 0, 1)):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.color = color
    light.data.shape = "DISK"
    light.data.size = size
    light.rotation_euler = (Vector(target) - light.location).to_track_quat("-Z", "Y").to_euler()
    return light


def build_scene(settings, story, frames_dir):
    random.seed(int(settings["video"].get("seed", 0)) or 17)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)

    width = int(settings["render"]["width"])
    height = int(settings["render"]["height"])
    fps = int(settings["video"]["fps"])
    duration = float(settings["video"]["duration_seconds"])
    frame_end = max(2, int(round(duration * fps)))
    scene = bpy.context.scene
    scene.render.engine = settings["render"].get("engine", "BLENDER_EEVEE_NEXT")
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = frame_end
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(frames_dir / "frame_")
    scene.render.use_file_extension = True
    scene.render.image_settings.compression = 15
    scene.render.use_overwrite = True
    scene.render.use_placeholder = False
    scene.view_settings.view_transform = "Standard"
    available_looks = [item.identifier for item in scene.view_settings.bl_rna.properties["look"].enum_items]
    if "Medium High Contrast" in available_looks:
        scene.view_settings.look = "Medium High Contrast"
    try:
        scene.eevee.taa_render_samples = int(settings["render"].get("samples", 8))
    except Exception:
        pass

    world = bpy.data.worlds.new("Deep-space world") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.008, 0.018, 0.06, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35

    accent = tuple(story.get("accent", [0.1, 0.7, 1.0, 1.0]))
    shell = material("Robot enamel", (0.10, 0.18, 0.30, 1), metallic=0.45, roughness=0.26)
    light_shell = material("Robot face plate", (0.58, 0.80, 0.90, 1), metallic=0.25, roughness=0.3)
    dark = material("Deep dark", (0.015, 0.035, 0.07, 1), metallic=0.2)
    glow = material("Story glow", accent, metallic=0.1, roughness=0.2, emission=1.4)
    eye = material("Bright eyes", (0.2, 0.9, 1.0, 1), metallic=0.0, roughness=0.2, emission=2.0)
    ground_mat = material("Moon dust", (0.025, 0.055, 0.11, 1), metallic=0.1, roughness=0.75)
    star_mat = material("Distant stars", (0.5, 0.72, 1.0, 1), emission=1.2)
    title_mat = material("Title white", (0.9, 0.96, 1.0, 1), emission=0.8)

    # Ground and a small circular stage.
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.12))
    ground = bpy.context.object
    ground.name = "Endless alien ground"
    assign(ground, ground_mat)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=2.2, depth=0.16, location=(0, 0, 0))
    stage = bpy.context.object
    stage.name = "Floating stage"
    assign(stage, shell)
    bevel = stage.modifiers.new("Stage rim", "BEVEL")
    bevel.width = 0.08
    bevel.segments = 2

    # Character: a deliberately low-poly original robot built entirely from primitives.
    body = cube("Robot torso", (0, 0, 1.12), (0.78, 0.58, 0.82), shell, 0.16)
    chest = cube("Robot chest plate", (0, -0.305, 1.12), (0.48, 0.08, 0.32), light_shell, 0.07)
    badge = ico_sphere("Robot chest light", (0, -0.365, 1.14), (0.10, 0.035, 0.10), glow, 2)
    head = cube("Robot head", (0, 0, 1.88), (0.92, 0.66, 0.70), light_shell, 0.20)
    face = cube("Dark face screen", (0, -0.345, 1.89), (0.68, 0.07, 0.34), dark, 0.09)
    eye_l = uv_sphere("Left eye", (-0.18, -0.40, 1.92), (0.07, 0.035, 0.09), eye, 12, 8)
    eye_r = uv_sphere("Right eye", (0.18, -0.40, 1.92), (0.07, 0.035, 0.09), eye, 12, 8)
    antenna = cylinder_between("Antenna", (0, 0, 2.20), (0, 0, 2.47), 0.035, shell)
    antenna_tip = uv_sphere("Antenna light", (0, 0, 2.50), (0.09, 0.09, 0.09), glow, 12, 8)

    arm_l = cylinder_between("Left upper arm", (-0.48, 0, 1.38), (-0.72, 0, 1.05), 0.095, shell)
    arm_r = cylinder_between("Right upper arm", (0.48, 0, 1.38), (0.72, 0, 1.05), 0.095, shell)
    hand_l = uv_sphere("Left hand", (-0.72, 0, 1.03), (0.12, 0.12, 0.12), light_shell, 12, 8)
    hand_r = uv_sphere("Right hand", (0.72, 0, 1.03), (0.12, 0.12, 0.12), light_shell, 12, 8)
    leg_l = cylinder_between("Left leg", (-0.22, 0, 0.72), (-0.24, 0, 0.28), 0.11, shell)
    leg_r = cylinder_between("Right leg", (0.22, 0, 0.72), (0.24, 0, 0.28), 0.11, shell)
    foot_l = cube("Left boot", (-0.25, -0.08, 0.20), (0.34, 0.43, 0.16), dark, 0.06)
    foot_r = cube("Right boot", (0.25, -0.08, 0.20), (0.34, 0.43, 0.16), dark, 0.06)

    # Story object is a real 3D prop, with an animated reveal.
    prop_name = story.get("prop", "orb")
    prop_z = 1.75
    prop_x = 1.25
    if prop_name == "star":
        vertices = []
        faces = []
        for i in range(10):
            angle = math.pi * i / 5.0
            radius = 0.48 if i % 2 == 0 else 0.22
            vertices.append((math.cos(angle) * radius, 0, math.sin(angle) * radius))
        vertices.extend([(x * 0.45, -0.16, z * 0.45) for x, _, z in vertices[:10]])
        for i in range(10):
            j = (i + 1) % 10
            faces.append((i, j, 10 + j, 10 + i))
        faces.append(tuple(range(10)))
        mesh = bpy.data.meshes.new("Five-point star mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        prop = bpy.data.objects.new("Floating star", mesh)
        bpy.context.collection.objects.link(prop)
        prop.location = (prop_x, 0, prop_z)
        assign(prop, glow)
        solid = prop.modifiers.new("Star thickness", "SOLIDIFY")
        solid.thickness = 0.14
        bevel_prop = prop.modifiers.new("Star edge glint", "BEVEL")
        bevel_prop.width = 0.035
        bevel_prop.segments = 2
    elif prop_name == "flower":
        cylinder_between("Flower stem", (prop_x, 0, 0.35), (prop_x, 0, 1.48), 0.045, glow)
        for side in (-1, 1):
            leaf = uv_sphere("Flower leaf", (prop_x + side * 0.18, 0, 0.83), (0.22, 0.07, 0.09), glow, 10, 6)
            leaf.rotation_euler[1] = side * 0.35
        prop = uv_sphere("Glowing flower center", (prop_x, 0, 1.55), (0.18, 0.18, 0.18), glow, 12, 8)
        for i in range(6):
            a = i * math.tau / 6
            uv_sphere("Flower petal", (prop_x + math.cos(a) * 0.24, 0, 1.55 + math.sin(a) * 0.24), (0.15, 0.09, 0.15), light_shell, 10, 6)
    elif prop_name == "crystal":
        prop = ico_sphere("Floating crystal", (prop_x, 0, prop_z), (0.38, 0.28, 0.62), glow, 1)
        prop.rotation_euler[1] = 0.2
    else:
        prop = uv_sphere("Magic orb", (prop_x, 0, prop_z), (0.42, 0.42, 0.42), glow, 16, 10)
        inner = uv_sphere("Orb core", (prop_x, -0.12, prop_z), (0.19, 0.19, 0.19), eye, 12, 8)
    if prop:
        prop.name = "Story prop"
        prop.keyframe_insert(data_path="location", frame=1)
        prop.location.z += 0.34
        prop.keyframe_insert(data_path="location", frame=max(2, frame_end // 2))
        prop.location.z -= 0.34
        prop.keyframe_insert(data_path="location", frame=frame_end)
        prop.rotation_euler.z = math.radians(-20)
        prop.keyframe_insert(data_path="rotation_euler", frame=1)
        prop.rotation_euler.z = math.radians(340)
        prop.keyframe_insert(data_path="rotation_euler", frame=frame_end)

    # Distant 3D stars, floating rocks and a ring make the environment feel dimensional.
    for i in range(38):
        x = random.uniform(-5.0, 5.0)
        y = random.uniform(1.0, 4.0)
        z = random.uniform(1.0, 6.0)
        radius = random.uniform(0.025, 0.075)
        uv_sphere(f"Background star {i:02d}", (x, y, z), (radius, radius, radius), star_mat, 8, 4)
    for i in range(7):
        x = random.uniform(-3.5, 3.5)
        z = random.uniform(0.35, 0.8)
        rock = ico_sphere(f"Floating rock {i:02d}", (x, random.uniform(0.4, 1.8), z), (0.18, 0.15, 0.13), shell, 1)
        rock.rotation_euler = (random.random(), random.random(), random.random())
    bpy.ops.mesh.primitive_torus_add(major_radius=1.35, minor_radius=0.025, major_segments=32, minor_segments=6, location=(0, 0, 0.12))
    ring = bpy.context.object
    ring.name = "Glowing stage ring"
    assign(ring, glow)

    # 3D typography, placed in front of the world rather than added as a flat video overlay.
    title = text_object("3D title", story.get("title", "A TINY STORY"), (0, -2.25, 4.25), 0.34, title_mat)
    subtitle = text_object("3D caption", story.get("caption", ""), (0, -2.25, 0.36), 0.16, title_mat)
    for obj in (title, subtitle):
        obj.keyframe_insert(data_path="location", frame=1)
        obj.location.y -= 0.10
        obj.keyframe_insert(data_path="location", frame=frame_end)

    # Lights.
    add_area_light("Cool key", (2.8, -4.0, 5.0), 550, (0.35, 0.62, 1.0), 4.0)
    add_area_light("Warm rim", (-3.0, 1.0, 3.6), 700, (1.0, 0.30, 0.12), 3.0)
    add_area_light("Top softbox", (0.0, 0.0, 6.0), 400, (0.45, 0.75, 1.0), 3.0)

    # Camera: portrait framing and a gentle, keyframed orbit.
    bpy.ops.object.camera_add(location=(0, -10.5, 3.05))
    camera = bpy.context.object
    camera.name = "Portrait camera"
    camera.data.lens = 47
    scene.camera = camera
    target = Vector((0, 0, 2.0))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.keyframe_insert(data_path="location", frame=1)
    camera.location.x = 0.55
    camera.location.z = 3.20
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.keyframe_insert(data_path="location", frame=frame_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=frame_end)

    # Character bounce and small gestures.
    for obj in (body, chest, badge, head, face, eye_l, eye_r, antenna, antenna_tip, arm_l, arm_r, hand_l, hand_r, leg_l, leg_r, foot_l, foot_r):
        base = obj.location.copy()
        obj.keyframe_insert(data_path="location", frame=1)
        obj.location.z += 0.12
        obj.keyframe_insert(data_path="location", frame=max(2, frame_end // 2))
        obj.location = base
        obj.keyframe_insert(data_path="location", frame=frame_end)
    for obj, tilt in ((arm_l, -0.45), (arm_r, 0.45), (hand_l, -0.35), (hand_r, 0.35)):
        obj.rotation_euler.y = tilt
        obj.keyframe_insert(data_path="rotation_euler", frame=1)
        obj.rotation_euler.y = -tilt
        obj.keyframe_insert(data_path="rotation_euler", frame=frame_end)
    for obj in bpy.context.scene.objects:
        if obj.animation_data and obj.animation_data.action:
            for fcurve in obj.animation_data.action.fcurves:
                for point in fcurve.keyframe_points:
                    point.interpolation = "BEZIER"

    scene.frame_set(1)
    scene.render.filepath = str(frames_dir / "frame_")
    scene.camera.data.dof.use_dof = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    # Workbench fallback is deliberately not used: the intended output uses actual lights/materials.
    bpy.ops.render.render(animation=True)


def main():
    args = parse_args()
    settings = json.loads(Path(args.settings).read_text(encoding="utf-8"))
    story = json.loads(Path(args.story).read_text(encoding="utf-8"))
    frames_dir = Path(args.frames)
    frames_dir.mkdir(parents=True, exist_ok=True)
    build_scene(settings, story, frames_dir)


if __name__ == "__main__":
    main()
