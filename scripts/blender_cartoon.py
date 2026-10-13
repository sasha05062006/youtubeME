from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenplay", required=True)
    parser.add_argument("--frames-root", required=True)
    known, _ = parser.parse_known_args(bpy.app.argv[bpy.app.argv.index("--") + 1:] if "--" in bpy.app.argv else [])
    return known


def mat(name, color, roughness=0.65, metallic=0.0, emission=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if emission:
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (*color, 1)
                bsdf.inputs["Emission Strength"].default_value = emission
            elif "Emission" in bsdf.inputs:
                bsdf.inputs["Emission"].default_value = (*color, 1)
    return material


def assign(obj, material):
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        obj.data.materials.append(material)
    return obj


def sphere(name, location, scale, material, segments=16, rings=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.shade_smooth()
    assign(obj, material)
    return obj


def cone(name, location, radius, depth, material, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=radius, radius2=0.02, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = rotation
    assign(obj, material)
    return obj


def cylinder(name, location, radius, depth, material, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = rotation
    assign(obj, material)
    return obj


def clear_scene(scene):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)
    scene.camera = None


def animal_kind(character):
    text = " ".join(str(character.get(key, "")) for key in ("id", "name", "description")).lower()
    if any(word in text for word in ("elephant", "слон")):
        return "elephant"
    if any(word in text for word in ("fox", "лис")):
        return "fox"
    if any(word in text for word in ("hare", "rabbit", "зая", "крол")):
        return "hare"
    if any(word in text for word in ("bear", "медвед")):
        return "bear"
    if any(word in text for word in ("cat", "кот", "кош")):
        return "cat"
    if any(word in text for word in ("dragon", "дракон")):
        return "dragon"
    return "creature"


def build_character(character, x, y, index, mats, frame_end):
    kind = animal_kind(character)
    palette = {
        "elephant": ((0.40, 0.63, 0.78), (0.85, 0.67, 0.62)),
        "fox": ((0.95, 0.36, 0.10), (0.98, 0.84, 0.62)),
        "hare": ((0.78, 0.68, 0.57), (0.98, 0.88, 0.84)),
        "bear": ((0.48, 0.27, 0.14), (0.92, 0.73, 0.51)),
        "cat": ((0.45, 0.35, 0.64), (0.92, 0.82, 0.98)),
        "dragon": ((0.18, 0.63, 0.38), (0.98, 0.57, 0.16)),
        "creature": ((0.20 + (index * 0.13) % 0.5, 0.45, 0.72), (0.94, 0.79, 0.60)),
    }
    body_color, light_color = palette[kind]
    body_mat = mat(f"{character['id']}_body", body_color)
    light_mat = mat(f"{character['id']}_light", light_color)
    dark_mat = mats["dark"]
    eye_mat = mats["eye"]
    parts = []
    parts.append(sphere(f"{character['id']}_body", (x, y, 0.90), (0.47, 0.37, 0.55), body_mat))
    parts.append(sphere(f"{character['id']}_head", (x, y - 0.03, 1.67), (0.48, 0.42, 0.45), body_mat))
    parts.append(sphere(f"{character['id']}_muzzle", (x, y - 0.40, 1.52), (0.28, 0.16, 0.20), light_mat))
    for side in (-1, 1):
        parts.append(sphere(f"{character['id']}_eye_{side}", (x + side * 0.17, y - 0.405, 1.78), (0.075, 0.045, 0.09), eye_mat, 12, 8))
        parts.append(sphere(f"{character['id']}_foot_{side}", (x + side * 0.25, y - 0.02, 0.24), (0.19, 0.25, 0.13), dark_mat, 12, 8))
        parts.append(sphere(f"{character['id']}_ear_{side}", (x + side * 0.39, y, 1.93), (0.16, 0.12, 0.24), light_mat, 12, 8))
    if kind == "elephant":
        for j, z in enumerate((1.43, 1.26, 1.10)):
            parts.append(sphere(f"{character['id']}_trunk_{j}", (x + 0.02, y - 0.55, z), (0.12 + j * 0.01, 0.12, 0.16), body_mat, 12, 8))
        for side in (-1, 1):
            parts.append(sphere(f"{character['id']}_big_ear_{side}", (x + side * 0.47, y + 0.02, 1.65), (0.26, 0.10, 0.32), light_mat))
    elif kind == "fox":
        for side in (-1, 1):
            parts.append(cone(f"{character['id']}_pointed_ear_{side}", (x + side * 0.25, y, 2.08), 0.15, 0.42, body_mat, (side * -0.12, 0, side * -0.12)))
        parts.append(sphere(f"{character['id']}_tail", (x + 0.54, y + 0.18, 0.87), (0.38, 0.23, 0.22), body_mat))
        parts.append(sphere(f"{character['id']}_tail_tip", (x + 0.79, y + 0.16, 0.91), (0.15, 0.17, 0.15), light_mat))
        parts.append(sphere(f"{character['id']}_muzzle", (x, y - 0.48, 1.55), (0.28, 0.13, 0.15), light_mat))
    elif kind == "hare":
        for side in (-1, 1):
            parts.append(sphere(f"{character['id']}_long_ear_{side}", (x + side * 0.18, y, 2.22), (0.10, 0.11, 0.36), light_mat))
        parts.append(sphere(f"{character['id']}_tail", (x + 0.40, y + 0.18, 0.63), (0.16, 0.15, 0.16), light_mat))
    elif kind == "bear":
        for side in (-1, 1):
            parts.append(sphere(f"{character['id']}_round_ear_{side}", (x + side * 0.33, y, 2.02), (0.17, 0.14, 0.17), body_mat))
    elif kind == "cat":
        for side in (-1, 1):
            parts.append(cone(f"{character['id']}_cat_ear_{side}", (x + side * 0.25, y, 2.06), 0.15, 0.38, body_mat, (0, side * -0.10, side * -0.08)))
        parts.append(cylinder(f"{character['id']}_whisker_left", (x - 0.32, y - 0.48, 1.51), 0.012, 0.35, light_mat, (0, math.pi / 2, 0)))
        parts.append(cylinder(f"{character['id']}_whisker_right", (x + 0.32, y - 0.48, 1.51), 0.012, 0.35, light_mat, (0, math.pi / 2, 0)))
    elif kind == "dragon":
        for side in (-1, 1):
            parts.append(cone(f"{character['id']}_horn_{side}", (x + side * 0.25, y, 2.05), 0.10, 0.34, light_mat, (side * -0.12, 0, side * -0.12)))
            parts.append(sphere(f"{character['id']}_wing_{side}", (x + side * 0.54, y + 0.16, 1.16), (0.25, 0.09, 0.36), light_mat))
    # Tiny arms help the silhouettes read as friendly characters.
    for side in (-1, 1):
        parts.append(sphere(f"{character['id']}_arm_{side}", (x + side * 0.50, y - 0.05, 1.02), (0.13, 0.16, 0.30), body_mat))
    # A simple name plaque is omitted: the film should not look like a game UI.
    for obj in parts:
        base = obj.location.copy()
        obj.keyframe_insert(data_path="location", frame=1)
        obj.location.z += 0.06
        obj.keyframe_insert(data_path="location", frame=max(2, frame_end // 2))
        obj.location = base
        obj.keyframe_insert(data_path="location", frame=frame_end)
    return parts


def build_environment(scene, scene_data, frame_end, seed):
    random.seed(seed)
    location_text = (scene_data.get("location", "") + " " + scene_data.get("visual_action", "")).lower()
    is_night = any(word in location_text for word in ("ноч", "night", "пещер", "грот", "cave"))
    is_water = any(word in location_text for word in ("руч", "рек", "вод", "stream", "river"))
    sky = (0.015, 0.035, 0.10, 1) if is_night else (0.30, 0.62, 0.83, 1)
    world = bpy.data.worlds.new("Cartoon world") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = sky
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55
    ground_mat = mat("Forest ground", (0.10, 0.32, 0.15) if not is_night else (0.035, 0.08, 0.11))
    trunk_mat = mat("Tree trunk", (0.27, 0.13, 0.06))
    leaf_mat = mat("Tree leaves", (0.08, 0.38, 0.16) if not is_night else (0.035, 0.15, 0.12))
    water_mat = mat("Stream water", (0.05, 0.35, 0.75), roughness=0.18, metallic=0.12)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.04))
    assign(bpy.context.object, ground_mat)
    if is_water:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.8, 0.01))
        water = bpy.context.object
        water.name = "Blue stream"
        water.scale = (4.0, 0.65, 0.05)
        assign(water, water_mat)
    for i, x in enumerate((-4.0, -3.0, 3.0, 4.0)):
        trunk = cylinder(f"Tree trunk {i}", (x, 1.5, 1.0), 0.18, 2.0, trunk_mat)
        sphere(f"Tree canopy {i}", (x, 1.5, 2.15), (0.85, 0.65, 0.95), leaf_mat, 12, 8)
    # Scene-relevant prop: a visible golden bell when the story mentions one.
    if any(word in location_text for word in ("колоколь", "bell", "звен")):
        gold = mat("Golden bell", (0.95, 0.58, 0.08), metallic=0.45, roughness=0.22)
        bell = sphere("Story bell", (1.5, -0.1, 1.0), (0.22, 0.22, 0.25), gold)
        cylinder("Bell handle", (1.5, -0.1, 1.27), 0.07, 0.15, gold)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.17, minor_radius=0.035, location=(1.5, -0.1, 0.84))
        assign(bpy.context.object, gold)
        bell.keyframe_insert(data_path="location", frame=1)
        bell.location.z += 0.10
        bell.keyframe_insert(data_path="location", frame=max(2, frame_end // 2))
        bell.location.z -= 0.10
        bell.keyframe_insert(data_path="location", frame=frame_end)
    bpy.ops.object.light_add(type="AREA", location=(2.5, -4.5, 6.0))
    key = bpy.context.object
    key.data.energy = 520
    key.data.shape = "DISK"
    key.data.size = 5
    key.rotation_euler = (Vector((0, 0, 1.0)) - key.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.light_add(type="AREA", location=(-3.5, 1.0, 4.5))
    rim = bpy.context.object
    rim.data.energy = 700 if not is_night else 250
    rim.data.color = (0.35, 0.55, 1.0)
    rim.data.size = 3
    rim.rotation_euler = (Vector((0, 0, 1.0)) - rim.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.camera_add(location=(0, -11.0, 4.0))
    camera = bpy.context.object
    camera.name = "Story camera"
    camera.data.lens = 38
    target = Vector((0, 0.1, 1.25))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    camera.keyframe_insert(data_path="location", frame=1)
    camera.location.x = 0.20
    camera.keyframe_insert(data_path="location", frame=frame_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=frame_end)
    scene.camera.data.dof.use_dof = False


def render_screenplay(screenplay_path: Path, frames_root: Path):
    screenplay = json.loads(screenplay_path.read_text(encoding="utf-8"))
    settings = bpy.context.scene
    settings.render.engine = "BLENDER_EEVEE_NEXT"
    settings.render.resolution_x = 360
    settings.render.resolution_y = 640
    settings.render.resolution_percentage = 100
    settings.render.fps = 12
    settings.render.image_settings.file_format = "PNG"
    settings.render.image_settings.color_mode = "RGBA"
    settings.render.image_settings.color_depth = "8"
    settings.render.image_settings.compression = 15
    settings.view_settings.view_transform = "Standard"
    try:
        settings.eevee.taa_render_samples = 8
    except Exception:
        pass
    frames_root.mkdir(parents=True, exist_ok=True)
    for index, scene_data in enumerate(screenplay["scenes"], 1):
        clear_scene(settings)
        mats = {"dark": mat("Character dark details", (0.06, 0.07, 0.10)), "eye": mat("Eye highlights", (0.95, 0.98, 1.0), emission=0.15)}
        duration = float(scene_data["duration_seconds"])
        frame_end = max(2, int(round(duration * settings.render.fps)))
        settings.frame_start = 1
        settings.frame_end = frame_end
        scene_dir = frames_root / f"scene_{index:03d}"
        scene_dir.mkdir(parents=True, exist_ok=True)
        settings.render.filepath = str(scene_dir / "frame_")
        build_environment(settings, scene_data, frame_end, index)
        cast = screenplay["cast"]
        if len(cast) <= 3:
            positions = [(-1.25 + i * 1.25, -0.15) for i in range(len(cast))]
        else:
            positions = [(-1.05, -0.25), (1.05, -0.25), (-1.05, 1.0), (1.05, 1.0)]
            if len(cast) > 4:
                positions.extend([(-1.8 + i * 0.9, 1.7) for i in range(len(cast) - 4)])
        for char_index, character in enumerate(cast):
            x, y = positions[char_index] if char_index < len(positions) else (0, 1.2)
            build_character(character, x, y, char_index, mats, frame_end)
        for obj in bpy.context.scene.objects:
            if obj.animation_data and obj.animation_data.action:
                for fcurve in obj.animation_data.action.fcurves:
                    for point in fcurve.keyframe_points:
                        point.interpolation = "BEZIER"
        settings.frame_set(1)
        bpy.ops.render.render(animation=True)
        print(f"Rendered scene {index}/{len(screenplay['scenes'])}: {scene_data.get('id', index)}")


def main():
    args = parse_args()
    render_screenplay(Path(args.screenplay), Path(args.frames_root))


if __name__ == "__main__":
    main()
