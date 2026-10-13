from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate_screenplay(data: dict[str, Any]) -> list[str]:
    """Validate the stable screenplay contract before voice/render stages run."""
    errors: list[str] = []
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("title must be a non-empty string")

    target = data.get("target_duration_seconds")
    if not isinstance(target, (int, float)) or isinstance(target, bool) or target <= 0:
        errors.append("target_duration_seconds must be a positive number")
        target = 0

    cast = data.get("cast")
    if not isinstance(cast, list) or not cast:
        errors.append("cast must be a non-empty list")
        cast = []

    character_ids: set[str] = set()
    for index, character in enumerate(cast):
        if not isinstance(character, dict):
            errors.append(f"cast[{index}] must be an object")
            continue
        character_id = character.get("id")
        if not isinstance(character_id, str) or not character_id.strip():
            errors.append(f"cast[{index}].id must be a non-empty string")
            continue
        if character_id in character_ids:
            errors.append(f"duplicate character id: {character_id}")
        character_ids.add(character_id)
        for required in ("name", "description", "voice_profile"):
            if not isinstance(character.get(required), str) or not character[required].strip():
                errors.append(f"cast[{index}].{required} must be a non-empty string")

    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes must be a non-empty list")
        scenes = []

    scene_ids: set[str] = set()
    total_scene_duration = 0.0
    for index, scene in enumerate(scenes):
        prefix = f"scenes[{index}]"
        if not isinstance(scene, dict):
            errors.append(f"{prefix} must be an object")
            continue
        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not scene_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string")
        elif scene_id in scene_ids:
            errors.append(f"duplicate scene id: {scene_id}")
        else:
            scene_ids.add(scene_id)

        duration = scene.get("duration_seconds")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
            errors.append(f"{prefix}.duration_seconds must be positive")
            duration = 0
        total_scene_duration += float(duration)

        for required in ("location", "visual_action", "camera"):
            if not isinstance(scene.get(required), str) or not scene[required].strip():
                errors.append(f"{prefix}.{required} must be a non-empty string")

        dialogue = scene.get("dialogue", [])
        if not isinstance(dialogue, list):
            errors.append(f"{prefix}.dialogue must be a list")
            dialogue = []
        for line_index, line in enumerate(dialogue):
            line_prefix = f"{prefix}.dialogue[{line_index}]"
            if not isinstance(line, dict):
                errors.append(f"{line_prefix} must be an object")
                continue
            character_id = line.get("character_id")
            if character_id not in character_ids:
                errors.append(f"{line_prefix} references unknown character_id: {character_id}")
            if not isinstance(line.get("text"), str) or not line["text"].strip():
                errors.append(f"{line_prefix}.text must be a non-empty string")
            at_seconds = line.get("at_seconds")
            if not isinstance(at_seconds, (int, float)) or isinstance(at_seconds, bool):
                errors.append(f"{line_prefix}.at_seconds must be numeric")
            elif at_seconds < 0 or at_seconds > duration:
                errors.append(f"{line_prefix}.at_seconds must be within the scene duration")

        effects = scene.get("sound_effects", [])
        if not isinstance(effects, list):
            errors.append(f"{prefix}.sound_effects must be a list")
            effects = []
        for effect_index, effect in enumerate(effects):
            effect_prefix = f"{prefix}.sound_effects[{effect_index}]"
            if not isinstance(effect, dict):
                errors.append(f"{effect_prefix} must be an object")
                continue
            asset = effect.get("asset")
            if not isinstance(asset, str) or not asset.strip():
                errors.append(f"{effect_prefix}.asset must be a non-empty string")
            at_seconds = effect.get("at_seconds")
            if not isinstance(at_seconds, (int, float)) or isinstance(at_seconds, bool):
                errors.append(f"{effect_prefix}.at_seconds must be numeric")
            elif at_seconds < 0 or at_seconds > duration:
                errors.append(f"{effect_prefix}.at_seconds must be within the scene duration")
            gain = effect.get("gain_db", -8)
            if not isinstance(gain, (int, float)) or isinstance(gain, bool):
                errors.append(f"{effect_prefix}.gain_db must be numeric")

        ambience = scene.get("ambience", [])
        if not isinstance(ambience, list):
            errors.append(f"{prefix}.ambience must be a list")
            ambience = []
        for ambience_index, cue in enumerate(ambience):
            cue_prefix = f"{prefix}.ambience[{ambience_index}]"
            if not isinstance(cue, dict):
                errors.append(f"{cue_prefix} must be an object")
                continue
            if not isinstance(cue.get("asset"), str) or not cue["asset"].strip():
                errors.append(f"{cue_prefix}.asset must be a non-empty string")
            start = cue.get("start_seconds", 0)
            if not isinstance(start, (int, float)) or isinstance(start, bool) or start < 0 or start > duration:
                errors.append(f"{cue_prefix}.start_seconds must be within the scene duration")
            cue_duration = cue.get("duration_seconds", duration)
            if not isinstance(cue_duration, (int, float)) or isinstance(cue_duration, bool) or cue_duration <= 0:
                errors.append(f"{cue_prefix}.duration_seconds must be positive")
            gain = cue.get("gain_db", -22)
            if not isinstance(gain, (int, float)) or isinstance(gain, bool):
                errors.append(f"{cue_prefix}.gain_db must be numeric")

        music = scene.get("music")
        if music is not None:
            if not isinstance(music, dict):
                errors.append(f"{prefix}.music must be an object")
            else:
                if not isinstance(music.get("asset"), str) or not music["asset"].strip():
                    errors.append(f"{prefix}.music.asset must be a non-empty string")
                start = music.get("start_seconds", 0)
                if not isinstance(start, (int, float)) or isinstance(start, bool) or start < 0 or start > duration:
                    errors.append(f"{prefix}.music.start_seconds must be within the scene duration")
                gain = music.get("gain_db", -25)
                if not isinstance(gain, (int, float)) or isinstance(gain, bool):
                    errors.append(f"{prefix}.music.gain_db must be numeric")

    if target and scenes:
        tolerance = max(5.0, float(target) * 0.05)
        if abs(total_scene_duration - float(target)) > tolerance:
            errors.append(
                f"scene duration total ({total_scene_duration:g}s) differs from target "
                f"({float(target):g}s) by more than {tolerance:g}s"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a YouTubeME screenplay JSON file.")
    parser.add_argument("screenplay", type=Path, help="Path to screenplay JSON")
    args = parser.parse_args()
    try:
        data = json.loads(args.screenplay.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read screenplay: {exc}")
        return 2
    if not isinstance(data, dict):
        print("Screenplay root must be a JSON object.")
        return 2

    errors = validate_screenplay(data)
    if errors:
        print("Screenplay validation: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    duration = sum(float(scene["duration_seconds"]) for scene in data["scenes"])
    lines = sum(len(scene.get("dialogue", [])) for scene in data["scenes"])
    effects = sum(len(scene.get("sound_effects", [])) for scene in data["scenes"])
    print("Screenplay validation: PASS")
    print(f"Title: {data['title']}")
    print(f"Target duration: {data['target_duration_seconds']}s")
    print(f"Scene duration total: {duration:g}s")
    print(f"Cast: {len(data['cast'])}; dialogue lines: {lines}; sound effects: {effects}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
