# YouTubeME — Autonomous 3D Cartoon Studio

A free-first Windows project intended to turn one natural-language brief into a complete 3D cartoon: screenplay, consistent characters, multi-voice dialogue, sound effects, ambience, music, rendered scenes, and a final mixed video.

**Important status:** the repository currently contains an early procedural 3D short generator, not the complete prompt-driven cartoon studio described above. It still uses fixed micro-story templates and a single narration track. A three-minute multi-character cartoon with natural acting, distinct voices, and synchronized sound design is a target, not a feature that is already finished.

## Product target

The intended workflow is simple: describe the cartoon in ordinary language, specify the duration, and start creation. YouTubeME should then plan the story, build a cast and scene timeline, generate dialogue line by line, assign a voice profile to each character, add synchronized sound effects and music, render multiple 3D scenes, mix the audio, and run quality checks.

See [the autonomous cartoon studio MVP specification](docs/AUTONOMOUS_CARTOON_STUDIO_MVP.md) for the workflow, screenplay format, quality requirements, realistic limitations, and acceptance test.

## Current technical foundation

- Python orchestration, Blender procedural 3D rendering, and FFmpeg encoding/mixing.
- Original Russian micro-story templates for smoke tests.
- A basic single-character procedural scene with simple animation.
- Optional offline Piper or Windows SAPI narration.
- Output manifests and basic video/audio QA.
- No paid API key is required for the existing template pipeline; external generative services are not called silently.
- Automatic uploading and scheduling remain disabled.

## Voice quality warning

Piper and Windows SAPI are basic offline fallbacks; they can sound synthetic and do not provide professional character acting. The current implementation does **not** yet generate separate dialogue lines for multiple characters, expressive performances, or a full sound-effects/music timeline. Installing voice models does not by itself make narration sound human.

A first standalone audio-timeline renderer now exists at `scripts/audio_timeline.py`. It synthesizes each screenplay dialogue line separately with Piper, supports per-character model/profile assignment, places scene-local sound effects/ambience/music on the global timeline, mixes and loudness-normalizes the result, and writes a report. It is not yet wired into the existing video generator, and licensed audio files must be placed in `assets/audio/sfx/`, `assets/audio/ambience/`, and `assets/audio/music/`. The renderer fails clearly when a referenced asset or voice model is missing rather than silently replacing it with silence.

The project must still add a screenplay planner, connect the audio timeline to the video pipeline, and implement multi-scene 3D staging before it can meet the product target. High-quality neural voices or generative assets may require optional external services; their actual free limits, privacy implications, licenses, and payment requirements must be checked before integration.

## Windows quick start for the existing prototype

1. Install Blender and FFmpeg if they are not already available.
2. Optionally run `install_russian_voice.bat` to download the basic offline Piper voices.
3. Run `setup.bat` once.
4. Run `run.bat` to generate one of the currently bundled template shorts.
5. Check `output/ready/` and the accompanying manifest. Failed QA outputs go to `output/quarantine/`.

To create a screenplay from a natural-language brief through a **local OpenAI-compatible model endpoint**, run `python scripts/screenplay_planner.py --prompt "Детский мультфильм про слонёнка и трёх друзей, которые ищут волшебный колокольчик" --duration 180 --output output\screenplay.json`. By default it checks `http://127.0.0.1:31415/v1`; override with `--base-url` or `YOUTUBEME_LLM_BASE_URL`. This does not call a paid API. It requires a compatible local model server to be running.

Validate the result with `python scripts/screenplay.py output\screenplay.json`. For an audio-only screenplay test, validate the included sample with `python scripts/screenplay.py examples/elephant_friends.screenplay.json`, then run `python scripts/audio_timeline.py examples/elephant_friends.screenplay.json` after installing the listed voice models and adding the referenced licensed sound files. These are separate pipeline stages and are not yet integrated into one-click video generation. This separate audio stage is not yet integrated with the video render.

The current prototype uses conservative render settings for a low-resource Windows laptop. A three-minute multi-scene cartoon is substantially heavier and has not been verified on the target 4 GB RAM / Celeron-class machine. Use short test renders while building out the full pipeline.

## Licensing and publishing

Project code is MIT. Third-party tools, voice models, music, sound effects, and generated assets retain their own licenses. Record provenance and review commercial-use terms before publishing. Automatic uploads remain disabled; inspect each output before posting.
