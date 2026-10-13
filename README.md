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

The project must add a screenplay planner, per-character voice profiles, line-level audio generation, a synchronized sound timeline, and multi-scene 3D staging before it can meet the product target. High-quality neural voices or generative assets may require optional external services; their actual free limits, privacy implications, licenses, and payment requirements must be checked before integration.

## Windows quick start for the existing prototype

1. Install Blender and FFmpeg if they are not already available.
2. Optionally run `install_russian_voice.bat` to download the basic offline Piper voices.
3. Run `setup.bat` once.
4. Run `run.bat` to generate one of the currently bundled template shorts.
5. Check `output/ready/` and the accompanying manifest. Failed QA outputs go to `output/quarantine/`.

The current prototype uses conservative render settings for a low-resource Windows laptop. A three-minute multi-scene cartoon is substantially heavier and has not been verified on the target 4 GB RAM / Celeron-class machine. Use short test renders while building out the full pipeline.

## Licensing and publishing

Project code is MIT. Third-party tools, voice models, music, sound effects, and generated assets retain their own licenses. Record provenance and review commercial-use terms before publishing. Automatic uploads remain disabled; inspect each output before posting.
