# YouTubeME — Autonomous 3D Cartoon Studio

A free-first Windows project intended to turn one natural-language brief into a complete 3D cartoon: screenplay, consistent characters, multi-voice dialogue, sound effects, ambience, music, rendered scenes, and a final mixed video.

**Important status:** the repository now has a one-command multi-scene production path, but it has not yet been rendered end-to-end on the target laptop. The 3D characters are procedural low-poly models, and the voice engine is still Piper; this is an early working foundation, not studio-grade animation or human-level voice acting.

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

Piper and Windows SAPI are basic offline fallbacks; they can sound synthetic and do not provide professional character acting. The `create_cartoon.bat` path integrates local screenplay planning, multi-scene procedural Blender rendering, per-line character dialogue, CC0 ambience/effects/music, background ducking, final muxing, and a QA report. It uses procedural low-poly animal characters and a local LLM endpoint for screenplay planning, so it is not equivalent to a studio-quality character-animation package. Installing voice models does not by itself make narration sound human.

A first standalone audio-timeline renderer now exists at `scripts/audio_timeline.py`. It synthesizes each screenplay dialogue line separately with Piper, supports per-character model/profile assignment, places scene-local sound effects/ambience/music on the global timeline, ducks background audio under dialogue, mixes and loudness-normalizes the result, and writes a report. The integrated flow calls this renderer automatically. Audio files are installed in `assets/audio/sfx/`, `assets/audio/ambience/`, and `assets/audio/music/`. Run `install_audio_assets.bat` once to download a small starter library of CC0 effects, ambience, and music (internet required; no payment or API key). The renderer fails clearly when a referenced asset or voice model is missing rather than silently replacing it with silence.

The main remaining work is to improve the visual acting/rigs, evaluate higher-quality expressive Russian TTS options that remain free, add richer sound libraries, and verify the entire flow on the actual laptop. High-quality neural voices or generative assets may require optional external services; their actual free limits, privacy implications, licenses, and payment requirements must be checked before integration.

## Windows quick start

1. Run `install_tools.bat` if Blender and FFmpeg are not installed; reopen the terminal after installation.
2. Run `setup.bat` once.
3. Run `install_russian_voice.bat` once to install Piper and the two Russian voice models.
4. Start your local OpenAI-compatible language-model server at `http://127.0.0.1:31415/v1` (or set `YOUTUBEME_LLM_BASE_URL`).
5. Run `create_cartoon.bat`, describe the story, and enter the duration in seconds. If the starter sound pack is missing, the program offers to download the CC0 assets.
6. Find the MP4 and JSON report in `output/ready/`; failed quality checks go to `output/quarantine/`.

The one-click flow is integrated in the repository, but must still be tested end-to-end on the target laptop. It relies on a compatible local model server being active and on the installed Blender/FFmpeg/Piper tools.

## Windows quick start for the existing prototype

1. Install Blender and FFmpeg if they are not already available.
2. Optionally run `install_russian_voice.bat` to download the basic offline Piper voices.
3. Run `setup.bat` once.
4. Run `run.bat` to generate one of the currently bundled template shorts.
5. Check `output/ready/` and the accompanying manifest. Failed QA outputs go to `output/quarantine/`.

To create a screenplay from a natural-language brief through a **local OpenAI-compatible model endpoint**, run `python scripts/screenplay_planner.py --prompt "Детский мультфильм про слонёнка и трёх друзей, которые ищут волшебный колокольчик" --duration 180 --output output\screenplay.json`. By default it checks `http://127.0.0.1:31415/v1`; override with `--base-url` or `YOUTUBEME_LLM_BASE_URL`. This does not call a paid API. It requires a compatible local model server to be running.

For an audio-only test, validate the included sample with `python scripts/screenplay.py examples/elephant_friends.screenplay.json`, then run `install_audio_assets.bat` and `python scripts/audio_timeline.py examples/elephant_friends.screenplay.json` after installing the Piper voice models. The one-click launcher invokes the screenplay planner, Blender renderer, audio mixer, and final video assembly automatically.

The current prototype uses conservative render settings for a low-resource Windows laptop. A three-minute multi-scene cartoon is substantially heavier and has not been verified on the target 4 GB RAM / Celeron-class machine. Use short test renders while building out the full pipeline.

## Licensing and publishing

Project code is MIT. Third-party tools, voice models, music, sound effects, and generated assets retain their own licenses. Record provenance and review commercial-use terms before publishing. Automatic uploads remain disabled; inspect each output before posting.
