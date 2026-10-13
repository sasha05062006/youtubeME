from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VOICE_MODELS = {
    "warm": ("ru_RU-irina-medium.onnx", 1.00),
    "childlike_warm": ("ru_RU-irina-medium.onnx", 1.07),
    "gentle": ("ru_RU-irina-medium.onnx", 0.94),
    "playful": ("ru_RU-ruslan-medium.onnx", 1.08),
    "youthful_playful": ("ru_RU-ruslan-medium.onnx", 1.14),
    "low_gentle": ("ru_RU-ruslan-medium.onnx", 0.88),
    "light_nervous": ("ru_RU-irina-medium.onnx", 1.12),
}


class AudioTimelineError(RuntimeError):
    pass


def build_audio_events(screenplay: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten scene-local audio cues into a global timeline."""
    events: list[dict[str, Any]] = []
    scene_offset = 0.0
    for scene in screenplay["scenes"]:
        scene_duration = float(scene["duration_seconds"])
        for line in scene.get("dialogue", []):
            events.append({
                "kind": "dialogue",
                "asset": None,
                "text": line["text"],
                "character_id": line["character_id"],
                "start_seconds": scene_offset + float(line["at_seconds"]),
                "gain_db": float(line.get("gain_db", 0)),
                "emotion": line.get("emotion", "neutral"),
            })
        for effect in scene.get("sound_effects", []):
            events.append({
                "kind": "sound_effect",
                "asset": effect["asset"],
                "start_seconds": scene_offset + float(effect["at_seconds"]),
                "gain_db": float(effect.get("gain_db", -8)),
            })
        for ambience in scene.get("ambience", []):
            events.append({
                "kind": "ambience",
                "asset": ambience["asset"],
                "start_seconds": scene_offset + float(ambience.get("start_seconds", 0)),
                "gain_db": float(ambience.get("gain_db", -22)),
                "duration_seconds": float(ambience.get("duration_seconds", max(0.0, scene_duration - float(ambience.get("start_seconds", 0))))),
            })
        music = scene.get("music")
        if isinstance(music, dict) and music.get("asset"):
            events.append({
                "kind": "music",
                "asset": music["asset"],
                "start_seconds": scene_offset + float(music.get("start_seconds", 0)),
                "gain_db": float(music.get("gain_db", -25)),
                "duration_seconds": float(music.get("duration_seconds", max(0.0, scene_duration - float(music.get("start_seconds", 0))))),
            })
        scene_offset += scene_duration
    return sorted(events, key=lambda event: event["start_seconds"])


def _resolve_asset(asset_root: Path, kind: str, name: str) -> Path:
    # Asset names are identifiers, never arbitrary paths from screenplay JSON.
    if not name or Path(name).name != name or name in {".", ".."}:
        raise AudioTimelineError(f"Invalid {kind} asset identifier: {name!r}")
    candidates = (
        asset_root / kind / f"{name}.wav",
        asset_root / kind / f"{name}.flac",
        asset_root / kind / f"{name}.mp3",
        asset_root / kind / f"{name}.ogg",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    tried = ", ".join(str(path.relative_to(asset_root)) for path in candidates)
    raise AudioTimelineError(f"Missing {kind} asset {name!r}; expected one of: {tried}")


def _run(command: list[str], timeout: int = 180, input_text: str | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, input=input_text, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AudioTimelineError(f"Could not run {command[0]}: {exc}") from exc



def build_filter_graph(clips: list[dict[str, Any]], duration: float) -> str:
    """Build a timeline mix that automatically lowers ambience/music under dialogue."""
    filters: list[str] = []
    voice_labels: list[str] = []
    background_labels: list[str] = []
    for index, clip in enumerate(clips):
        label = f"a{index}"
        delay_ms = max(0, int(round(float(clip["start_seconds"]) * 1000)))
        gain_db = float(clip.get("gain_db", 0))
        source_duration = clip.get("duration_seconds")
        trim_prefix = f"atrim=duration={float(source_duration):.3f}," if source_duration is not None else ""
        filters.append(
            f"[{index}:a]aresample=44100,volume={gain_db}dB,{trim_prefix}"
            f"asetpts=PTS-STARTPTS,adelay={delay_ms}|{delay_ms},"
            f"atrim=duration={duration}[{label}]"
        )
        if clip["kind"] == "dialogue":
            voice_labels.append(f"[{label}]")
        else:
            background_labels.append(f"[{label}]")

    if voice_labels:
        if len(voice_labels) == 1:
            filters.append(f"{voice_labels[0]}anull[voicebus]")
        else:
            filters.append(
                "".join(voice_labels) +
                f"amix=inputs={len(voice_labels)}:duration=longest:dropout_transition=0[voicebus]"
            )
    if background_labels:
        if len(background_labels) == 1:
            filters.append(f"{background_labels[0]}anull[bgbus]")
        else:
            filters.append(
                "".join(background_labels) +
                f"amix=inputs={len(background_labels)}:duration=longest:dropout_transition=1[bgbus]"
            )

    if voice_labels and background_labels:
        filters.append(
            "[bgbus][voicebus]sidechaincompress=threshold=0.025:ratio=7:"
            "attack=20:release=450:makeup=1[ducked]"
        )
        filters.append(
            f"[voicebus][ducked]amix=inputs=2:duration=longest:dropout_transition=1,"
            f"apad=whole_dur={duration},atrim=duration={duration},"
            f"loudnorm=I=-16:TP=-1.5:LRA=11[out]"
        )
    else:
        final_label = "voicebus" if voice_labels else "bgbus"
        filters.append(
            f"[{final_label}]apad=whole_dur={duration},atrim=duration={duration},"
            f"loudnorm=I=-16:TP=-1.5:LRA=11[out]"
        )
    return ";".join(filters)


def render_audio_timeline(
    screenplay: dict[str, Any],
    ffmpeg: str,
    piper: str,
    models_dir: Path,
    assets_dir: Path,
    work_dir: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Synthesize each dialogue line separately and mix it with timed local assets."""
    from screenplay import validate_screenplay

    errors = validate_screenplay(screenplay)
    if errors:
        raise AudioTimelineError("Invalid screenplay: " + "; ".join(errors))

    cast = {item["id"]: item for item in screenplay["cast"]}
    work_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    events = build_audio_events(screenplay)
    clips: list[dict[str, Any]] = []
    warnings: list[str] = []
    assigned_models: dict[str, str] = {}

    for index, event in enumerate(events):
        kind = event["kind"]
        if kind == "dialogue":
            character = cast[event["character_id"]]
            explicit_model = character.get("voice_model")
            profile = character["voice_profile"]
            profile_config = VOICE_MODELS.get(profile)
            model_name = explicit_model or (profile_config[0] if profile_config else None)
            pitch_factor = float(character.get("pitch_factor", profile_config[1] if profile_config else 1.0))
            if not model_name:
                raise AudioTimelineError(
                    f"No local voice model configured for {character['name']} "
                    f"(profile {profile!r}); set cast[].voice_model."
                )
            if Path(model_name).name != model_name or not model_name.lower().endswith(".onnx"):
                raise AudioTimelineError(f"Voice model must be an .onnx filename inside models/: {model_name!r}")
            if not 0.75 <= pitch_factor <= 1.25:
                raise AudioTimelineError(f"pitch_factor for {character['name']} must be between 0.75 and 1.25")
            model_path = (models_dir / model_name).resolve()
            if not model_path.is_file():
                raise AudioTimelineError(
                    f"Voice model for {character['name']} is missing: {model_path}. "
                    "Install a compatible Piper voice model or set cast[].voice_model."
                )
            clip_path = work_dir / f"dialogue_{index:04d}_{event['character_id']}.wav"
            result = _run([
                piper, "--model", str(model_path), "--output_file", str(clip_path)
            ], timeout=300, input_text=event["text"])
            if result.returncode != 0:
                raise AudioTimelineError(
                    f"Piper failed for {character['name']}: {result.stderr[-1200:]}"
                )
            if not clip_path.exists() or clip_path.stat().st_size <= 44:
                raise AudioTimelineError(
                    f"Piper returned no speech for {character['name']}. "
                    "Check that the Piper executable and model are compatible."
                )
            assigned_models[event["character_id"]] = model_name
            if abs(pitch_factor - 1.0) > 0.001:
                adjusted_path = work_dir / f"dialogue_{index:04d}_{event['character_id']}_voice.wav"
                atempo = 1.0 / pitch_factor
                filters = f"aresample=44100,asetrate=44100*{pitch_factor:.5f},aresample=44100,atempo={atempo:.5f}"
                adjusted = _run([
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(clip_path),
                    "-af", filters, "-c:a", "pcm_s16le", str(adjusted_path)
                ], timeout=180)
                if adjusted.returncode != 0 or not adjusted_path.exists():
                    raise AudioTimelineError(
                        f"Could not apply voice profile to {character['name']}: {adjusted.stderr[-1000:]}"
                    )
                clip_path = adjusted_path
            clips.append({**event, "path": clip_path})
        else:
            folder = {"sound_effect": "sfx", "ambience": "ambience", "music": "music"}[kind]
            path = _resolve_asset(assets_dir, folder, event["asset"])
            clips.append({**event, "path": path})

    if not clips:
        raise AudioTimelineError("Screenplay contains no dialogue, music, ambience, or sound effects.")
    model_users: dict[str, list[str]] = {}
    for character_id, model_name in assigned_models.items():
        model_users.setdefault(model_name, []).append(cast[character_id]["name"])
    for model_name, names in model_users.items():
        if len(names) > 1:
            warnings.append(
                f"{', '.join(names)} share {model_name}; pitch/tempo profiles vary the sound, "
                "but separate neural models are preferable for clearly distinct voices."
            )

    duration = float(screenplay["target_duration_seconds"])
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for clip in clips:
        if clip["kind"] in {"music", "ambience"}:
            command.extend(["-stream_loop", "-1"])
        command.extend(["-i", str(clip["path"])])

    filter_graph = build_filter_graph(clips, duration)
    command.extend([
        "-filter_complex", filter_graph,
        "-map", "[out]", "-t", str(duration),
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
        str(output_path),
    ])
    result = _run(command, timeout=max(300, int(duration * 15)))
    if result.returncode != 0 or not output_path.is_file() or output_path.stat().st_size < 1024:
        raise AudioTimelineError(f"FFmpeg audio mix failed: {result.stderr[-2000:]}")
    return {
        "output": str(output_path),
        "duration_seconds": duration,
        "dialogue_lines": sum(clip["kind"] == "dialogue" for clip in clips),
        "sound_effects": sum(clip["kind"] == "sound_effect" for clip in clips),
        "ambience_tracks": sum(clip["kind"] == "ambience" for clip in clips),
        "music_tracks": sum(clip["kind"] == "music" for clip in clips),
        "warnings": warnings,
        "voice_models": assigned_models,
        "human_quality_claim": False,
        "note": "Pitch/tempo profiles provide modest character differentiation, not human acting. Evaluate the audio before publishing.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Render screenplay dialogue and sound cues into one mixed audio track.")
    parser.add_argument("screenplay", type=Path)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    parser.add_argument("--piper", default=str(ROOT / "tools" / "piper" / "piper.exe"))
    parser.add_argument("--models-dir", type=Path, default=ROOT / "models")
    parser.add_argument("--assets-dir", type=Path, default=ROOT / "assets" / "audio")
    parser.add_argument("--work-dir", type=Path, default=ROOT / "output" / "audio_work")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "audio_preview.m4a")
    args = parser.parse_args()

    if not args.ffmpeg:
        print("FFmpeg was not found. Install it or pass --ffmpeg.", file=sys.stderr)
        return 2
    if not Path(args.piper).is_file():
        print(f"Piper executable was not found: {args.piper}", file=sys.stderr)
        return 2
    try:
        screenplay = json.loads(args.screenplay.read_text(encoding="utf-8"))
        report = render_audio_timeline(
            screenplay, args.ffmpeg, args.piper, args.models_dir, args.assets_dir,
            args.work_dir, args.output,
        )
    except (OSError, json.JSONDecodeError, AudioTimelineError, KeyError, TypeError, ValueError) as exc:
        print(f"Audio timeline failed: {exc}", file=sys.stderr)
        return 1
    report_path = args.output.with_suffix(args.output.suffix + ".json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Audio report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
