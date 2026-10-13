from __future__ import annotations

import argparse
import base64
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / "config" / "settings.json"

STORIES = [
    {"id":"robot_and_the_star","topic":"Космос и дружба","title":"МАЛЕНЬКИЙ РОБОТ И ЗВЕЗДА","caption":"Даже маленький поступок может изменить целый мир","narration":"В глубине космоса маленький робот встретил одинокую звезду. Он мог забрать её свет себе, но вместо этого помог ей найти дорогу домой. И тогда вся галактика стала чуточку ярче.","prop":"star","accent":[0.12,0.72,1.0,1.0]},
    {"id":"moon_garden","topic":"Волшебство и чудеса","title":"САД НА ЛУНЕ","caption":"Большие чудеса начинаются с маленького семени","narration":"На тихой стороне Луны маленький робот посадил последнее семечко. Все говорили, что здесь ничего не вырастет. Но на рассвете появился светящийся цветок, и холодный кратер превратился в самый уютный сад во Вселенной.","prop":"flower","accent":[0.35,1.0,0.52,1.0]},
    {"id":"lost_comet","topic":"Приключения","title":"ПОТЕРЯВШАЯСЯ КОМЕТА","caption":"Иногда дорогу домой помогает найти друг","narration":"Маленькая комета потеряла путь среди бесконечных звёзд. Она уже решила, что никогда не найдёт дом, но любопытный робот показал ей созвездие. Вместе они пронеслись по галактике и успели вернуться к самому красивому рассвету.","prop":"crystal","accent":[1.0,0.42,0.25,1.0]},
    {"id":"brave_bubble","topic":"Добрые истории","title":"САМОЕ СМЕЛОЕ ПУЗЫРЬКО","caption":"Быть маленьким — не значит быть слабым","narration":"Крошечный пузырёк боялся огромного океана. Волны казались ему целыми горами. Но однажды он набрался смелости и прыгнул в воду. Там его встретила добрая рыбка, и пузырёк понял: за страхом может скрываться целый удивительный мир.","prop":"bubble","accent":[0.2,0.85,1.0,1.0]},
    {"id":"cosmic_cat","topic":"Животные и юмор","title":"КОСМИЧЕСКИЙ КОТ","caption":"Любопытство может привести куда угодно","narration":"Космический кот гонялся за загадочным огоньком прямо по галактике. Он думал, что это обычная игрушка. Но огонёк оказался маяком потерявшегося корабля. Один прыжок, один счастливый хвост — и целая команда нашла дорогу домой.","prop":"orb","accent":[0.9,0.35,1.0,1.0]},
    {"id":"tiny_mountain","topic":"Мотивация","title":"САМЫЙ МАЛЕНЬКИЙ АЛЬПИНИСТ","caption":"Главное — сделать следующий шаг","narration":"Маленький робот мечтал взобраться на самую высокую гору. Он падал, скользил и снова начинал путь. Когда он наконец добрался до вершины, то понял: смелость — это не отсутствие страха. Это решение попробовать ещё раз.","prop":"crystal","accent":[1.0,0.68,0.18,1.0]}
]
CHARACTERS = {"robot":"Робот","cat":"Кот","astronaut":"Космонавт","dragon":"Дракон"}
VOICES = {"irina":"Piper — женский голос Ирина","denis":"Piper — мужской голос Денис","windows":"Русский голос Windows","silent":"Без озвучки"}


def load_settings() -> dict:
    with SETTINGS_PATH.open("r", encoding="utf-8") as handle:
        settings = json.load(handle)
    return settings


def executable_from_setting(env_name: str, configured: str, command: str) -> str | None:
    env_value = os.environ.get(env_name, "").strip().strip('"')
    candidate = env_value or configured.strip().strip('"') or shutil.which(command)
    if not candidate:
        return None
    path = Path(candidate).expanduser()
    if path.exists():
        return str(path.resolve())
    return shutil.which(candidate)


def run_command(command: list[str], log_path: Path, timeout: int | None = None) -> subprocess.CompletedProcess:
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write("$ " + subprocess.list2cmdline(command) + "\n\n")
        log.flush()
        return subprocess.run(
            command,
            cwd=str(ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def offline_narration(text: str, destination: Path, work_dir: Path, audio_cfg: dict) -> bool:
    voice_name = str(audio_cfg.get("voice_name", "irina")).strip().lower()
    piper_executable = str(audio_cfg.get("piper_executable", "")).strip()
    piper_model = str(audio_cfg.get("piper_model", "")).strip()
    if voice_name == "windows":
        piper_model = ""
    piper_executable = os.environ.get("PIPER_EXE", piper_executable)
    piper_model = os.environ.get("PIPER_MODEL", piper_model)
    if piper_executable and piper_model:
        exe = shutil.which(piper_executable) or (piper_executable if Path(piper_executable).exists() else None)
        model = Path(piper_model).expanduser()
        if exe and model.exists():
            try:
                result = subprocess.run(
                    [str(exe), "--model", str(model), "--output_file", str(destination)],
                    input=text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=180, check=False,
                )
                if result.returncode == 0 and destination.exists() and destination.stat().st_size > 44:
                    return True
            except (OSError, subprocess.TimeoutExpired):
                pass
    if os.name != "nt":
        return False
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        return False
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    script = work_dir / "speak.ps1"
    script.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        "Add-Type -AssemblyName System.Speech\n"
        "$text = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($args[1]))\n"
        "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
        "$synth.Rate = 0\n"
        "$synth.Volume = 100\n"
        "$synth.SetOutputToWaveFile($args[0])\n"
        "$synth.Speak($text)\n"
        "$synth.Dispose()\n",
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), str(destination), encoded],
            cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False,
        )
        return result.returncode == 0 and destination.exists() and destination.stat().st_size > 44
    except (OSError, subprocess.TimeoutExpired):
        return False

def probe_video(ffprobe: str, path: Path) -> dict:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def qa_video(ffmpeg: str, ffprobe: str, video: Path, settings: dict, manifest: dict) -> dict:
    qa_cfg = settings.get("qa", {})
    report = {"passed": False, "checks": {}, "errors": []}
    if not video.exists():
        report["errors"].append("Output MP4 is missing.")
        return report
    report["checks"]["file_size_bytes"] = video.stat().st_size
    report["checks"]["minimum_file_size_bytes"] = qa_cfg.get("min_file_size_bytes", 20000)
    report["checks"]["file_size_ok"] = video.stat().st_size >= qa_cfg.get("min_file_size_bytes", 20000)
    if not report["checks"]["file_size_ok"]:
        report["errors"].append("Output file is unexpectedly small.")

    try:
        probe = probe_video(ffprobe, video)
        streams = probe.get("streams", [])
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if not video_stream:
            report["errors"].append("No video stream found.")
            return report
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        duration = float(probe.get("format", {}).get("duration", 0))
        expected_duration = float(settings["video"]["duration_seconds"])
        tolerance = float(qa_cfg.get("duration_tolerance_seconds", 2.0))
        report["checks"].update({
            "width": width,
            "height": height,
            "duration_seconds": round(duration, 3),
            "expected_duration_seconds": expected_duration,
            "vertical_video_ok": height > width,
            "duration_ok": abs(duration - expected_duration) <= tolerance,
            "audio_present": audio_stream is not None,
        })
        if qa_cfg.get("require_vertical_video", True) and height <= width:
            report["errors"].append("Video is not portrait/vertical.")
        if not report["checks"]["duration_ok"]:
            report["errors"].append("Video duration is outside the configured tolerance.")
        if settings.get("publish", {}).get("enabled", False):
            report["errors"].append("Automatic publishing must remain disabled in this MVP.")
        if manifest.get("external_media_used", True):
            report["errors"].append("Manifest indicates external media; licensing review is required.")
        if not manifest.get("asset_sources"):
            report["errors"].append("Manifest is missing asset source records.")

        if audio_stream:
            volume = subprocess.run(
                [ffmpeg, "-hide_banner", "-i", str(video), "-vn", "-af", "volumedetect", "-f", "null", "NUL"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60, check=False,
            )
            match = re.search(r"max_volume:\s*(-?(?:\d+(?:\.\d+)?|inf))\s*dB", volume.stderr)
            if match and match.group(1) != "inf":
                peak = float(match.group(1))
                limit = float(qa_cfg.get("max_volume_db", -0.1))
                report["checks"]["audio_max_volume_db"] = peak
                report["checks"]["audio_peak_limit_db"] = limit
                report["checks"]["audio_peak_ok"] = peak <= limit
                if peak > limit:
                    report["errors"].append(f"Audio peak {peak:.2f} dB exceeds limit {limit:.2f} dB.")
            elif volume.returncode != 0:
                report["errors"].append("Could not measure audio peak.")
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        report["errors"].append(f"Video probe/QA error: {exc}")

    report["passed"] = not report["errors"] and all(
        value is True for key, value in report["checks"].items()
        if key.endswith("_ok")
    )
    return report



def choose_from_menu(title: str, options: list[tuple[str, str]], default: str) -> str:
    print("\n" + title)
    for i, (key, label) in enumerate(options, 1):
        suffix = " (по умолчанию)" if key == default else ""
        print(f"  {i}. {label}{suffix}")
    while True:
        answer = input(f"Выбор [1-{len(options)}], Enter — вариант по умолчанию: ").strip()
        if not answer:
            return default
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1][0]
        print("Введите номер из списка.")


def run_wizard(args):
    story_options = [(s["id"], s["topic"] + " — " + s["title"]) for s in STORIES]
    args.story = args.story or choose_from_menu("1/3. Выбери тему и сюжет:", story_options, STORIES[0]["id"])
    args.character = args.character or choose_from_menu("2/3. Выбери персонажа:", list(CHARACTERS.items()), "robot")
    args.voice = args.voice or choose_from_menu("3/3. Выбери голос:", list(VOICES.items()), "irina")
    settings = load_settings()
    settings.setdefault("audio", {})["enabled"] = args.voice != "silent"
    settings["audio"]["voice_name"] = args.voice
    if args.voice in ("irina", "denis"):
        model_name = "ru_RU-irina-medium.onnx" if args.voice == "irina" else "ru_RU-denis-medium.onnx"
        settings["audio"]["piper_model"] = str(ROOT / "models" / model_name)
    elif args.voice == "windows":
        settings["audio"]["piper_model"] = ""
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    return args


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an original procedural 3D vertical short.")
    parser.add_argument("--seed", type=int, default=None, help="Repeatable story/scene seed.")
    parser.add_argument("--story", choices=[s["id"] for s in STORIES], help="Use a specific bundled story.")
    parser.add_argument("--list-stories", action="store_true", help="List bundled story templates and exit.")
    parser.add_argument("--character", choices=list(CHARACTERS), help="Main character.")
    parser.add_argument("--voice", choices=list(VOICES), help="Narration voice.")
    parser.add_argument("--no-menu", action="store_true", help="Run without interactive prompts.")
    args = parser.parse_args()

    if args.list_stories:
        for story in STORIES:
            print(f'{story["id"]}: {story["title"]}')
        return 0

    load_dotenv()
    if not args.no_menu and sys.stdin.isatty():
        args = run_wizard(args)
    args.story = args.story or STORIES[0]["id"]
    args.character = args.character or "robot"
    args.voice = args.voice or "irina"
    settings = load_settings()
    settings.setdefault("audio", {})["enabled"] = args.voice != "silent"
    settings["audio"]["voice_name"] = args.voice
    blender = executable_from_setting("BLENDER_EXE", "", "blender")
    ffmpeg = executable_from_setting("FFMPEG_EXE", "", "ffmpeg")
    ffprobe = executable_from_setting("FFPROBE_EXE", "", "ffprobe")
    missing = [name for name, value in (("Blender", blender), ("FFmpeg", ffmpeg), ("ffprobe", ffprobe)) if not value]
    if missing:
        print("Missing required free tools: " + ", ".join(missing))
        print("Install Blender and FFmpeg, add them to PATH, or set BLENDER_EXE / FFMPEG_EXE / FFPROBE_EXE.")
        print("No video was generated; this pipeline never substitutes slides for 3D.")
        return 2

    seed = args.seed if args.seed is not None else int(settings["video"].get("seed", 0))
    if seed == 0:
        seed = int(time.time_ns() % 2_000_000_000)
    rng = random.Random(seed)
    story = next((s for s in STORIES if s["id"] == args.story), None)
    if story is None:
        print("Unknown story selection.")
        return 2
    story["character"] = args.character
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(seed)
    work_dir = ROOT / "output" / "work" / run_id
    frames_dir = work_dir / "frames"
    ready_dir = ROOT / "output" / "ready"
    quarantine_dir = ROOT / "output" / "quarantine"
    for folder in (frames_dir, ready_dir, quarantine_dir):
        folder.mkdir(parents=True, exist_ok=True)

    settings["video"]["seed"] = seed
    story_path = work_dir / "story.json"
    story_path.write_text(json.dumps(story, indent=2), encoding="utf-8")
    settings_path = work_dir / "settings.json"
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    blender_log = work_dir / "blender.log"
    blender_script = ROOT / "scripts" / "blender_scene.py"
    command = [
        blender, "--background", "--factory-startup", "--python", str(blender_script), "--",
        "--settings", str(settings_path), "--story", str(story_path), "--frames", str(frames_dir),
    ]
    print(f'Generating real 3D scene: {story["title"]} (seed {seed})')
    render = run_command(command, blender_log, timeout=max(900, int(settings["video"]["duration_seconds"]) * 240))
    if render.returncode != 0:
        print(f"Blender render failed; inspect {blender_log}")
        return 3

    fps = int(settings["video"]["fps"])
    silent_video = work_dir / "silent.mp4"
    encode_log = work_dir / "encode.log"
    encode = run_command([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", str(fps), "-start_number", "1", "-i", str(frames_dir / "frame_%04d.png"),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "27", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(silent_video),
    ], encode_log, timeout=600)
    if encode.returncode != 0 or not silent_video.exists():
        print(f"FFmpeg frame encoding failed; inspect {encode_log}")
        return 4

    candidate = work_dir / "final.mp4"
    audio_path = work_dir / "narration.wav"
    audio_cfg = settings.get("audio", {})
    narration_ok = audio_cfg.get("enabled", True) and offline_narration(story["narration"], audio_path, work_dir, audio_cfg)
    if narration_ok:
        mux_log = work_dir / "mux.log"
        mux = run_command([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(silent_video), "-i", str(audio_path),
            "-filter:a", f'loudnorm=I={audio_cfg.get("target_lufs", -16)}:TP={audio_cfg.get("true_peak_db", -1.5)}:LRA=11,apad',
            "-t", str(settings["video"]["duration_seconds"]), "-c:v", "copy", "-c:a", "aac", "-b:a", "96k",
            "-shortest", "-movflags", "+faststart", str(candidate),
        ], mux_log, timeout=300)
        if mux.returncode != 0 or not candidate.exists():
            print(f"Audio mux failed; inspect {mux_log}; retaining silent render for QA.")
            shutil.copy2(silent_video, candidate)
            narration_ok = False
    else:
        shutil.copy2(silent_video, candidate)

    manifest = {
        "project": "YouTubeME",
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "story_id": story["id"],
        "title": story["title"],
        "narration_text": story["narration"],
        "character": args.character,
        "voice": args.voice,
        "topic": story.get("topic", ""),
        "seed": seed,
        "settings": settings,
        "blender_executable": blender,
        "ffmpeg_executable": ffmpeg,
        "narration_generated": narration_ok,
        "external_media_used": False,
        "asset_sources": [{"type": "procedural_3d", "source": "generated locally by scripts/blender_scene.py", "license": "project-generated"}],
        "publish_enabled": False,
    }
    report = qa_video(ffmpeg, ffprobe, candidate, settings, manifest) if settings.get("qa", {}).get("enabled", True) else {"passed": True, "checks": {"qa_disabled": True}, "errors": []}
    manifest["qa"] = report
    manifest["narration_note"] = "Offline narration generated." if narration_ok else "No configured offline voice was available; output is silent."
    target_dir = ready_dir if report["passed"] else quarantine_dir
    final_path = target_dir / f"{run_id}_{story['id']}.mp4"
    shutil.move(str(candidate), str(final_path))
    manifest_path = target_dir / f"{run_id}_{story['id']}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"QA: {'PASS' if report['passed'] else 'FAIL'}")
    print(f"Video: {final_path.relative_to(ROOT)}")
    print(f"Manifest: {manifest_path.relative_to(ROOT)}")
    if not narration_ok and args.voice != "silent":
        print("Note: voice model/executable not found. Configure Piper or select an installed Windows voice.")
    if not report["passed"]:
        for error in report.get("errors", []):
            print("QA ERROR:", error)
        print("The file was quarantined and is not marked ready for publishing.")
        return 5
    print("Done. Review the MP4 before uploading it to TikTok or YouTube Shorts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
