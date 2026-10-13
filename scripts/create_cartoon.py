from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LLM_URL = "http://127.0.0.1:31415/v1"


class CartoonJobError(RuntimeError):
    pass


def find_executable(env_name: str, command: str, extra: list[Path] | None = None) -> str | None:
    configured = os.environ.get(env_name, "").strip().strip('"')
    if configured and Path(configured).is_file():
        return str(Path(configured).resolve())
    found = shutil.which(configured or command)
    if found:
        return found
    for path in extra or []:
        if path.is_file():
            return str(path.resolve())
    return None


def run_logged(command: list[str], cwd: Path, log_path: Path, timeout: int) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write("$ " + subprocess.list2cmdline(command) + "\n\n")
        log.flush()
        try:
            result = subprocess.run(
                command, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT,
                text=True, timeout=timeout, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CartoonJobError(f"Command failed to run: {command[0]} ({exc}). Log: {log_path}") from exc
    if result.returncode != 0:
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-3000:]
        raise CartoonJobError(f"Command returned {result.returncode}: {command[0]}\nLog: {log_path}\n{tail}")


def collect_asset_ids(screenplay: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for scene in screenplay["scenes"]:
        ids.update(effect["asset"] for effect in scene.get("sound_effects", []))
        ids.update(item["asset"] for item in scene.get("ambience", []))
        music = scene.get("music")
        if isinstance(music, dict) and music.get("asset"):
            ids.add(music["asset"])
    return ids


def ensure_audio_assets(screenplay: dict[str, Any], auto_download: bool) -> dict[str, Any]:
    from audio_timeline import _resolve_asset
    from install_audio_assets import ASSETS, download_one

    assets_root = ROOT / "assets" / "audio"
    needed = collect_asset_ids(screenplay)
    lookup = {asset["name"]: asset for asset in ASSETS}
    missing_known = [
        name for name in sorted(needed)
        if name in lookup and not (assets_root / lookup[name]["folder"] / lookup[name]["filename"]).is_file()
    ]
    unknown = sorted(needed - set(lookup))
    if unknown:
        raise CartoonJobError(
            "The screenplay references sounds not in the installed CC0 starter catalog: "
            + ", ".join(unknown)
            + ". Regenerate the screenplay or add licensed files with those identifiers."
        )
    if missing_known:
        if not auto_download:
            if not sys.stdin.isatty():
                raise CartoonJobError(
                    "Audio assets are missing. Run install_audio_assets.bat or pass --yes to download them."
                )
            answer = input(
                f"Missing {len(missing_known)} sound assets. Download the free CC0 starter pack now? [Y/n]: "
            ).strip().lower()
            if answer not in ("", "y", "yes", "да", "д"):
                raise CartoonJobError("Audio assets are required for the requested sound design.")
        records = []
        failures = []
        for asset in ASSETS:
            if asset["name"] in missing_known:
                try:
                    records.append(download_one(asset))
                except RuntimeError as exc:
                    failures.append(str(exc))
        if failures:
            raise CartoonJobError("Could not download all required audio assets:\n" + "\n".join(failures))
        manifest_path = assets_root / "asset_manifest.json"
        existing = {}
        if manifest_path.exists():
            try:
                existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {}
        by_name = {item["name"]: item for item in existing.get("assets", [])}
        by_name.update({item["name"]: item for item in records})
        manifest_path.write_text(json.dumps({
            "license_policy": "Each installed asset is listed with its source and stated license. Recheck source terms before commercial release.",
            "assets": list(by_name.values()),
            "failed": [],
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    for scene in screenplay["scenes"]:
        for effect in scene.get("sound_effects", []):
            _resolve_asset(assets_root, "sfx", effect["asset"])
        for ambience in scene.get("ambience", []):
            _resolve_asset(assets_root, "ambience", ambience["asset"])
        music = scene.get("music")
        if isinstance(music, dict) and music.get("asset"):
            _resolve_asset(assets_root, "music", music["asset"])
    return {"assets_required": sorted(needed), "auto_download_requested": auto_download}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a multi-scene Russian 3D cartoon from one natural-language brief.")
    parser.add_argument("--prompt", help="Describe the cartoon. If omitted, an interactive prompt is shown.")
    parser.add_argument("--duration", type=int, default=None, help="Runtime in seconds (default: 180).")
    parser.add_argument("--base-url", default=os.environ.get("YOUTUBEME_LLM_BASE_URL", DEFAULT_LLM_URL))
    parser.add_argument("--model", default=os.environ.get("YOUTUBEME_LLM_MODEL"))
    parser.add_argument("--yes", action="store_true", help="Automatically download missing CC0 starter audio assets.")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "ready")
    args = parser.parse_args()

    prompt = args.prompt
    if not prompt:
        print("Опиши мультфильм обычными словами. Например: «Детский мультфильм про слонёнка и трёх друзей, которые ищут волшебный колокольчик».")
        prompt = input("Твой сюжет: ").strip()
    duration = args.duration
    if duration is None:
        answer = input("Длительность в секундах [180]: ").strip()
        duration = int(answer) if answer else 180
    if not prompt:
        print("Сначала нужно описать сюжет.", file=sys.stderr)
        return 2
    if duration < 15 or duration > 1800:
        print("Длительность должна быть от 15 до 1800 секунд.", file=sys.stderr)
        return 2

    blender = find_executable("BLENDER_EXE", "blender")
    ffmpeg = find_executable("FFMPEG_EXE", "ffmpeg")
    piper = find_executable("PIPER_EXE", "piper", [ROOT / "tools" / "piper" / "piper.exe"])
    if not blender or not ffmpeg:
        print("Не найдены Blender и/или FFmpeg. Сначала запусти install_tools.bat, затем открой новое окно терминала.", file=sys.stderr)
        return 2
    if not piper:
        print("Не найден Piper. Один раз запусти install_russian_voice.bat.", file=sys.stderr)
        return 2

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = ROOT / "output" / "work" / f"cartoon_{run_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    screenplay_path = work_dir / "screenplay.json"
    try:
        from screenplay import validate_screenplay
        from screenplay_planner import plan_screenplay
        print("Этап 1/5: пишу сценарий и раскладываю историю на сцены…")
        screenplay = plan_screenplay(prompt, duration, args.base_url, args.model, timeout=240)
        errors = validate_screenplay(screenplay)
        if errors:
            raise CartoonJobError("Сценарий не прошёл проверку: " + "; ".join(errors))
        screenplay_path.write_text(json.dumps(screenplay, ensure_ascii=False, indent=2), encoding="utf-8")

        print("Этап 2/5: проверяю звуковые ресурсы и лицензии…")
        asset_report = ensure_audio_assets(screenplay, args.yes)

        for character in screenplay["cast"]:
            profile = character.get("voice_profile", "")
            if not character.get("voice_model"):
                from audio_timeline import VOICE_MODELS
                if profile not in VOICE_MODELS:
                    raise CartoonJobError(
                        f"Для персонажа {character['name']} задан неизвестный голосовой профиль {profile!r}."
                    )
                model_path = ROOT / "models" / VOICE_MODELS[profile][0]
            else:
                model_path = ROOT / "models" / character["voice_model"]
            if not model_path.is_file():
                raise CartoonJobError(
                    f"Не найдена модель голоса {model_path.name}. Запусти install_russian_voice.bat и повтори."
                )

        print("Этап 3/5: рендерю настоящие 3D-сцены в Blender (это может занять много времени)…")
        frames_root = work_dir / "frames"
        blender_script = ROOT / "scripts" / "blender_cartoon.py"
        run_logged([
            blender, "--background", "--factory-startup", "--python", str(blender_script),
            "--", "--screenplay", str(screenplay_path), "--frames-root", str(frames_root)
        ], ROOT, work_dir / "blender.log", timeout=max(1800, duration * 180))

        print("Этап 4/5: собираю видеосцены и свожу голоса, музыку и эффекты…")
        scene_videos = []
        fps = 12
        for index, scene in enumerate(screenplay["scenes"], 1):
            scene_dir = frames_root / f"scene_{index:03d}"
            segment = work_dir / f"scene_{index:03d}.mp4"
            run_logged([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-framerate", str(fps), "-start_number", "1",
                "-i", str(scene_dir / "frame_%04d.png"),
                "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "27",
                "-pix_fmt", "yuv420p", "-r", str(fps), str(segment)
            ], ROOT, work_dir / f"encode_scene_{index:03d}.log", timeout=max(300, int(scene["duration_seconds"]) * 15))
            if not segment.is_file() or segment.stat().st_size < 1000:
                raise CartoonJobError(f"Не удалось собрать видео для сцены {index}.")
            scene_videos.append(segment)

        concat_list = work_dir / "concat.txt"
        concat_list.write_text(
            "".join("file '" + str(path.resolve()).replace("\\", "/").replace("'", "'\\''") + "'\n" for path in scene_videos),
            encoding="utf-8"
        )
        silent_video = work_dir / "silent.mp4"
        run_logged([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "27",
            "-pix_fmt", "yuv420p", "-r", str(fps), "-movflags", "+faststart", str(silent_video)
        ], ROOT, work_dir / "concat.log", timeout=max(600, duration * 30))

        from audio_timeline import render_audio_timeline
        audio_path = work_dir / "soundtrack.m4a"
        audio_report = render_audio_timeline(
            screenplay, ffmpeg, piper, ROOT / "models", ROOT / "assets" / "audio",
            work_dir / "audio", audio_path
        )
        candidate = work_dir / "final.mp4"
        run_logged([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(silent_video), "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "160k", "-t", str(duration), "-movflags", "+faststart", str(candidate)
        ], ROOT, work_dir / "mux.log", timeout=max(300, duration * 10))

        ffprobe = find_executable("FFPROBE_EXE", "ffprobe")
        if not ffprobe:
            raise CartoonJobError("ffprobe не найден, поэтому нельзя проверить длительность итогового видео.")
        probe = subprocess.run([
            ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(candidate)
        ], capture_output=True, text=True, timeout=60, check=False)
        if probe.returncode != 0:
            raise CartoonJobError("ffprobe не смог проверить итоговый файл: " + probe.stderr[-1000:])
        metadata = json.loads(probe.stdout)
        video_stream = next((item for item in metadata.get("streams", []) if item.get("codec_type") == "video"), None)
        audio_stream = next((item for item in metadata.get("streams", []) if item.get("codec_type") == "audio"), None)
        actual_duration = float(metadata.get("format", {}).get("duration", 0))
        qa = {
            "passed": bool(video_stream and audio_stream and abs(actual_duration - duration) <= max(2.0, duration * 0.02)),
            "duration_seconds": round(actual_duration, 3),
            "expected_duration_seconds": duration,
            "video_present": video_stream is not None,
            "audio_present": audio_stream is not None,
            "file_size_bytes": candidate.stat().st_size if candidate.exists() else 0,
            "errors": []
        }
        if not video_stream:
            qa["errors"].append("Video stream missing")
        if not audio_stream:
            qa["errors"].append("Audio stream missing")
        if abs(actual_duration - duration) > max(2.0, duration * 0.02):
            qa["errors"].append("Final duration outside tolerance")
        manifest = {
            "project": "YouTubeME",
            "run_id": run_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt,
            "screenplay": screenplay,
            "assets": asset_report,
            "audio_report": audio_report,
            "qa": qa,
            "external_media_used": True,
            "asset_manifest_path": "assets/audio/asset_manifest.json",
            "publish_enabled": False
        }
        target_dir = args.output if qa["passed"] else ROOT / "output" / "quarantine"
        target_dir.mkdir(parents=True, exist_ok=True)
        final_path = target_dir / f"{run_id}_cartoon.mp4"
        shutil.move(str(candidate), str(final_path))
        manifest_path = target_dir / f"{run_id}_cartoon.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Проверка качества: {'PASS' if qa['passed'] else 'FAIL'}")
        print(f"Видео: {final_path}")
        print(f"Отчёт: {manifest_path}")
        if not qa["passed"]:
            print("Файл помещён в карантин. Не публикуй его без проверки.", file=sys.stderr)
            return 5
        print("Готово. Прослушай и просмотри мультфильм перед публикацией.")
        return 0
    except (RuntimeError, OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        error_path = work_dir / "error.txt"
        error_path.write_text(str(exc), encoding="utf-8")
        print(f"Создание мультфильма остановлено: {exc}", file=sys.stderr)
        print(f"Подробности: {error_path}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
