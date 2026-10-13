# Architecture and realistic limits

## Current implementation

The repository has two paths: the original template-short pipeline and the newer prompt-driven cartoon pipeline launched by `create_cartoon.bat`. The newer path is integrated in code but has not yet been verified by rendering a full film on the target Windows laptop. It uses a local OpenAI-compatible model endpoint and does not call a paid remote API.

### Prompt-driven path

1. `scripts/screenplay_planner.py` turns a natural-language brief into a validated Russian screenplay with a cast, scene timings, dialogue, and sound cues.
2. `scripts/blender_cartoon.py` builds and renders each scene separately, with simple primitive-based animal models and basic animation.
3. `scripts/audio_timeline.py` generates line-level Piper dialogue, places CC0 sound assets on a shared timeline, ducks background sound under dialogue, and normalizes the mix.
4. `scripts/create_cartoon.py` orchestrates planning, asset checks/download prompts, scene rendering, FFmpeg encoding/concatenation, audio mixing, final muxing, and a QA report.

The procedural models are a low-resource foundation, not polished studio animation. Piper voice profiles use a small number of base voices plus modest pitch/tempo processing; this is not equivalent to natural human voice acting.

### Original template-short path

The original template pipeline:

1. **Template story selector** chooses one of a small set of bundled Russian micro-stories. It does not yet turn an arbitrary user brief into a screenplay.
2. **3D scene builder** invokes Blender in background mode and builds a single stylized character, props, lighting, camera, and simple keyframes from Python.
3. **Frame encoder** uses FFmpeg to encode rendered frames into a vertical H.264 MP4.
4. **Basic offline narration** uses Piper when installed, or Windows SAPI as a fallback. It creates one narration track; it does not yet cast distinct voices for dialogue between multiple characters.
5. **Quality gate** checks the video stream, orientation, duration, file size, and basic audio peak when audio exists.
6. **Manifest** records story, seed, software settings, and QA results.

This current implementation is a foundation, not the finished autonomous cartoon studio.

## Target architecture

The product target is described in [AUTONOMOUS_CARTOON_STUDIO_MVP.md](AUTONOMOUS_CARTOON_STUDIO_MVP.md). The target pipeline is:

1. **Brief parser and screenplay planner (first stage added):** `scripts/screenplay_planner.py` sends a natural-language brief to a user-controlled OpenAI-compatible local endpoint (default `http://127.0.0.1:31415/v1)), asks for structured Russian screenplay JSON, validates the cast and timing, and retries once when validation fails. It does not call a paid remote API. A local model server is a prerequisite; arbitrary model output is not trusted until validated.
2. **Asset and continuity manager:** create/reuse consistent 3D characters, props, environments, and visual references across shots.
3. **Line-level voice renderer:** `scripts/audio_timeline.py` generates each dialogue line separately using Piper, assigns a configured model and pitch/tempo profile to each character, and reports when characters share a model. Profile changes are subtle processing, not a substitute for separate expressive voice models or human acting.
4. **Sound designer and timeline mixer:** the same script places scene-local sound effects, ambience, and music at their global offsets, automatically ducks the background bus under dialogue, and loudness-normalizes the mix. Audio assets must be supplied locally under `assets/audio/sfx/`, `assets/audio/ambience/`, and `assets/audio/music/`; every referenced asset must exist. Automatic music ducking and end-to-end video integration remain unfinished.
5. **Multi-scene 3D renderer (first integrated procedural stage added):** `scripts/blender_cartoon.py` builds a scene for each screenplay segment and stages up to six primitive-based animal characters, scene-specific forest/water/night elements, simple bobbing animation, lighting, and camera movement. This is a visual foundation, not a full character rig/acting system.
6. **Final assembler and QA:** combine video and audio timelines, verify duration and synchronization, detect missing dialogue and audio, inspect black/silent sections, and write a provenance/license manifest.

## Hardware and quality trade-offs

The target machine has 4 GB RAM, a Celeron N3350, and no discrete GPU. Modern text-to-video models and large local language models are not dependable on this hardware. Procedural Blender scenes can run locally, but longer multi-character films may render very slowly. Start with low-resolution previews and render one scene at a time.

High-quality neural voices, script generation, and generative 3D assets may require a separate optional backend. A free tier can have quotas, require an account or payment method, change without notice, or send prompts/audio to a third party. Such backends must be explicit opt-ins, with their price limits, data handling, and licenses documented. Do not claim unlimited, professional-quality generation from a fully offline setup unless it has been tested.

## Audio quality requirements

- Do not use one voice for every speaking character.
- Generate speech line by line and associate each line with a character ID and timing.
- Keep Piper and Windows SAPI as fallback voices, not as a guarantee of human-sounding acting.
- Mix dialogue, ambience, effects, and music on a shared timeline.
- Duck music under speech, normalize final loudness, prevent clipping, and verify synchronization.
- Track the origin and license of each music/effect/voice asset. Never silently download arbitrary media.

## Free and licensing rules

- Procedural assets generated by project code may be used by default, but third-party models and tools have their own licenses.
- Do not add third-party models, fonts, sounds, or voice models without recording their source and license.
- Uploading and scheduling remain disabled; a human reviews each MP4 before posting.

## Resource tuning

The existing prototype defaults to 360x640 and 12 FPS. Keep preview resolution and scene duration low on the target laptop. For longer cartoons, render scene-by-scene, cache successful stages, and resume after failures rather than rerendering the whole project.
