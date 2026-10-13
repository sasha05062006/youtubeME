from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:31415/v1"


class PlannerError(RuntimeError):
    pass


def http_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 90) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise PlannerError(
            f"Could not reach the local language-model endpoint at {url}: {exc}. "
            "Start your OpenAI-compatible local model server or pass --base-url. "
            "No paid API is called by this script."
        ) from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PlannerError(f"The model endpoint returned invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise PlannerError("The model endpoint response must be a JSON object.")
    return parsed


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^\`\`\`(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*\`\`\`$", "", text)
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise PlannerError("The model did not return a JSON screenplay.")
        try:
            result = json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise PlannerError(f"The model's screenplay JSON is malformed: {exc}") from exc
    if not isinstance(result, dict):
        raise PlannerError("The screenplay root must be a JSON object.")
    return result


def make_messages(brief: str, duration: int, previous_errors: list[str] | None = None) -> list[dict[str, str]]:
    from install_audio_assets import ASSETS
    available_assets = {
        folder: sorted(asset["name"] for asset in ASSETS if asset["folder"] == folder)
        for folder in ("sfx", "ambience", "music")
    }
    correction = ""
    if previous_errors:
        correction = "\nFix these validation errors from your previous attempt:\n- " + "\n- ".join(previous_errors)
    system = (
        "You are a professional children's animation screenwriter and sound editor. "
        "Return ONLY one valid JSON object, with no Markdown and no commentary. "
        "Write natural Russian dialogue with distinct character personalities, a clear beginning, "
        "development, emotional turning point and satisfying ending. Make dialogue fit the requested runtime. "
        "Every scene must have a positive duration_seconds; scene durations must add up to target_duration_seconds. "
        "Every dialogue line must have character_id, text, at_seconds (seconds from the start of its scene), "
        "and may include emotion and gain_db. Every character must have id, name, description, voice_profile. "
        "Allowed voice_profile values: warm, childlike_warm, gentle, playful, youthful_playful, low_gentle, light_nervous. "
        "Every scene must have id, duration_seconds, location, visual_action, camera, dialogue, sound_effects. "
        "sound_effects is a list of objects with asset (short snake_case identifier) and at_seconds. "
        "ambience is an optional list of {asset,start_seconds,gain_db}; music is an optional object "
        "{asset,start_seconds,gain_db}. Use only asset IDs from this installed CC0 catalog; never invent IDs: "
        + json.dumps(available_assets, ensure_ascii=False) + ". "
        "Do not include keys, external API instructions, HTML, or code. Keep child-safe content. "
        "JSON shape: {title,language,target_duration_seconds,style,cast:[...],scenes:[...]}. "
        "Use Russian for title, dialogue, and descriptions."
    )
    user = (
        f"Create a complete original Russian-language children's 3D cartoon screenplay. "
        f"Target runtime: exactly {duration} seconds.\n\nCreative brief:\n{brief.strip()}\n\n"
        "Plan enough scenes and dialogue to make the runtime plausible; do not stretch a short story "
        "by leaving empty scenes. Place dialogue lines at realistic scene-local times, leaving room for "
        "acting, movement, ambience and effects. Use 2-6 speaking characters unless the brief requires otherwise. "
        "Include synchronized sound effects and scene ambience/music where appropriate. "
        "Output only the complete JSON screenplay."
        + correction
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_offline_screenplay(brief: str, duration: int) -> dict[str, Any]:
    """Return the included starter story retimed to the requested duration.

    This keeps first-run use independent of any external model server. It is a
    starter template, not full AI story generation from arbitrary briefs.
    """
    sample_path = ROOT / "examples" / "elephant_friends.screenplay.json"
    try:
        screenplay = json.loads(sample_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlannerError(f"Could not load built-in offline screenplay: {exc}") from exc

    scenes = screenplay.get("scenes", [])
    total = sum(float(scene["duration_seconds"]) for scene in scenes)
    assigned = 0
    for index, scene in enumerate(scenes):
        old_duration = float(scene["duration_seconds"])
        if index == len(scenes) - 1:
            new_duration = duration - assigned
        else:
            new_duration = max(1, round(duration * old_duration / total))
            assigned += new_duration
        scene["duration_seconds"] = new_duration
        ratio = new_duration / old_duration
        for line in scene.get("dialogue", []):
            line["at_seconds"] = min(round(float(line.get("at_seconds", 0)) * ratio, 2), max(0, new_duration - 1))
        for cue in scene.get("sound_effects", []):
            cue["at_seconds"] = min(round(float(cue.get("at_seconds", 0)) * ratio, 2), max(0, new_duration - 1))
        for cue in scene.get("ambience", []):
            cue["start_seconds"] = min(round(float(cue.get("start_seconds", 0)) * ratio, 2), max(0, new_duration - 1))
            cue.pop("duration_seconds", None)
        music = scene.get("music")
        if isinstance(music, dict):
            music["start_seconds"] = min(round(float(music.get("start_seconds", 0)) * ratio, 2), max(0, new_duration - 1))

    cleaned = " ".join(brief.strip().split())
    title = re.split(r"[.!?\\n]", cleaned, maxsplit=1)[0].strip(" «»\"'")
    if title:
        screenplay["title"] = title[:90]
    screenplay["target_duration_seconds"] = duration
    screenplay["generation"] = {
        "backend": "built-in offline starter screenplay",
        "model": None,
        "note": "Retimed included elephant-friends sample; plot is not fully rewritten from the brief."
    }
    return screenplay


def plan_screenplay(
    brief: str,
    duration: int,
    base_url: str = DEFAULT_BASE_URL,
    model: str | None = None,
    timeout: int = 180,
    use_llm: bool = False,
) -> dict[str, Any]:
    if not brief.strip():
        raise PlannerError("Describe the cartoon first.")
    if duration < 15 or duration > 1800:
        raise PlannerError("Duration must be between 15 and 1800 seconds.")
    base = base_url.rstrip("/")
    selected_model = model
    from screenplay import validate_screenplay

    # The project must remain usable on a clean install without a separately
    # installed local LLM. Use the optional server only when explicitly requested.
    if not use_llm:
        screenplay = build_offline_screenplay(brief, duration)
        errors = validate_screenplay(screenplay)
        if errors:
            raise PlannerError("Built-in offline screenplay failed validation: " + "; ".join(errors))
        return screenplay

    if not selected_model:
        models_response = http_json(f"{base}/models", timeout=min(timeout, 30))
        items = models_response.get("data", [])
        if not isinstance(items, list) or not items:
            raise PlannerError(
                "The optional local endpoint did not list any models. Start a model in the server or omit --use-llm."
            )
        selected_model = str(items[0].get("id", "")).strip()
        if not selected_model:
            raise PlannerError("The first model returned by /models has no id; pass --model explicitly.")

    previous_errors: list[str] = []
    for attempt in range(2):
        response = http_json(
            f"{base}/chat/completions",
            {
                "model": selected_model,
                "messages": make_messages(brief, duration, previous_errors if attempt else None),
                "temperature": 0.7,
            },
            timeout=timeout,
        )
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise PlannerError("The local endpoint response has no choices[0].message.content field.") from exc
        screenplay = extract_json_object(str(content))
        errors = validate_screenplay(screenplay)
        from install_audio_assets import ASSETS
        available_asset_ids = {asset["name"] for asset in ASSETS}
        used_asset_ids = set()
        scenes = screenplay.get("scenes", [])
        if not isinstance(scenes, list):
            scenes = []
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            effects = scene.get("sound_effects", [])
            if not isinstance(effects, list):
                effects = []
            ambience = scene.get("ambience", [])
            if not isinstance(ambience, list):
                ambience = []
            used_asset_ids.update(
                item["asset"] for item in effects
                if isinstance(item, dict) and isinstance(item.get("asset"), str) and item["asset"]
            )
            used_asset_ids.update(
                item["asset"] for item in ambience
                if isinstance(item, dict) and isinstance(item.get("asset"), str) and item["asset"]
            )
            music = scene.get("music")
            if isinstance(music, dict) and music.get("asset"):
                used_asset_ids.add(music["asset"])
        for unknown_asset in sorted(used_asset_ids - available_asset_ids):
            errors.append(f"unknown audio asset ID {unknown_asset!r}; use only IDs from the supplied catalog")
        if not errors:
            screenplay["language"] = screenplay.get("language") or "ru"
            screenplay["target_duration_seconds"] = duration
            screenplay["generation"] = {
                "backend": "openai-compatible local endpoint",
                "base_url": base,
                "model": selected_model,
                "attempt": attempt + 1,
            }
            return screenplay
        previous_errors = errors
    raise PlannerError("The model returned an invalid screenplay after two attempts: " + "; ".join(previous_errors))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Turn a natural-language cartoon brief into a validated screenplay using a local model endpoint."
    )
    parser.add_argument("--prompt", required=True, help="Describe the cartoon in ordinary language.")
    parser.add_argument("--duration", type=int, default=180, help="Target runtime in seconds (default: 180).")
    parser.add_argument("--base-url", default=os.environ.get("YOUTUBEME_LLM_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--model", default=os.environ.get("YOUTUBEME_LLM_MODEL"))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--use-llm", action="store_true", help="Use an already-running optional OpenAI-compatible local model server.")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "screenplay.json")
    args = parser.parse_args()
    try:
        screenplay = plan_screenplay(args.prompt, args.duration, args.base_url, args.model, args.timeout, args.use_llm)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(screenplay, ensure_ascii=False, indent=2), encoding="utf-8")
    except (PlannerError, OSError, ValueError, TypeError) as exc:
        print(f"Screenplay planning failed: {exc}", file=sys.stderr)
        return 1
    print(f"Screenplay created: {args.output}")
    print(f"Title: {screenplay['title']}")
    print(f"Duration: {screenplay['target_duration_seconds']} seconds")
    print(f"Cast: {len(screenplay['cast'])}; scenes: {len(screenplay['scenes'])}")
    print(f"Planner: {screenplay.get('generation', {}).get('backend', 'unknown')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
