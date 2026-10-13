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
    "warm": "ru_RU-irina-medium.onnx",
    "childlike_warm": "ru_RU-irina-medium.onnx",
    "gentle": "ru_RU-irina-medium.onnx",
    "playful": "ru_RU-ruslan-medium.onnx",
    "youthful_playful": "ru_RU-ruslan-medium.onnx",
    "low_gentle": "ru_RU-ruslan-medium.onnx",
    "light_nervous": "ru_RU-irina-medium.onnx",
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
                "duration_seconds": float(ambience.get("duration_seconds", scene_duration)),
            })
        music = scene.get("music")
        if isinstance(music, dict) and music.get("asset"):
            events.append({
                "kind": "music",
                "asset": music["asset"],
                "start_seconds": scene_offset + float(music.get("start_seconds", 0)),
                "gain_db": float(music.get("gain_db", -25)),
                "duration_seconds": float(music.get("duration_seconds", scene_duration)),
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

    for index, event in enumerate(events):
        kind = event["kind"]
        if kind == "dialogue":
            character = cast[event["character_id"]]
            explicit_model = character.get("voice_model")
            model_name = explicit_model or VOICE_MODELS.get(character["voice_profile"])
            if not model_name:
                raise AudioTimelineError(
                    f"No local voice model configured for {character['name']} "
                    f"(profile {character['voice_profile']!r}); set cast[].voice_model."
                )
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
                    "Check that this Piper build accepts stdin text."
                )
            clips.append({**event, "path": clip_path})
        else:
            folder = {"sound_effect": "sfx", "ambience": "ambience", "music": "music"}[kind]
            path = _resolve_asset(assets_dir, folder, event["asset"])
            clips.append({**event, "path": path})

    if not clips:
        raise AudioTimelineError("Screenplay contains no dialogue, music, ambience, or sound effects.")

    duration = float(screenplay["target_duration_seconds"])
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for clip in clips:
        if clip["kind"] in {"music", "ambience"}:
            command.extend(["-stream_loop", "-1"])
        command.extend(["-i", str(clip["path"])])

    filters: list[str] = []
    labels: list[str] = []
    for index, clip in enumerate(clips):
        label = f"a{index}"
        delay_ms = max(0, int(round(float(clip["start_seconds"]) * 1000)))
        gain_db = float(clip.get("gain_db", 0))
        filters.append(
            f"[{index}:a]aresample=44100,volume={gain_db}dB,"
            f"adelay={delay_ms}|{delay_ms},atrim=duration={duration},"
            f"asetpts=PTS-STARTPTS[{label}]"
        )
        labels.append(f"[{label}]")

    filters.append(
        "".join(labels) +
        f"amix=inputs={len(labels)}:duration=longest:dropout_transition=2,"
        f"atrim=duration={duration},loudnorm=I=-16:TP=-1.5:LRA=11[out]"
    )
    command.extend([
        "-filter_complex", ";".join(filters),
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
        "human_quality_claim": False,
        "note": "Offline voice quality depends on the installed model; mixing cannot make a basic TTS voice sound like a human actor.",
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
