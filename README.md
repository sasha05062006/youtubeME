# YouTubeME — Autonomous 3D Shorts Studio

A free, local-first Windows pipeline for generating original vertical 3D cartoon Shorts without paid APIs. The first engine is procedural Blender animation: it creates real 3D scenes, renders frames, generates offline narration, assembles a vertical MP4, and runs technical/licensing QA.

## Design constraints

- **Real 3D only:** video visuals are rendered from Blender scenes; no slideshow/photo-zoom fallback.
- **Free and local:** no paid API keys, subscriptions, stock footage, or remote generation services.
- **Low-resource mode:** short clips, low-poly assets, small render resolution, and low frame rate are the defaults for a 4 GB RAM / Celeron-class laptop.
- **Safe publishing workflow:** output is reviewed locally; automatic uploading/scheduling is disabled.
- **Quality gates stay on:** invalid/empty renders, audio problems, missing metadata, and licensing violations must fail or quarantine a run rather than silently publish it.

## Quick start (Windows)

1. If Blender or FFmpeg are missing, run `install_tools.bat` once (uses Windows Package Manager and needs internet), or install them manually from https://www.blender.org/download/ and https://ffmpeg.org/download.html.
2. Close and reopen the terminal after installation so PATH refreshes; if needed, set `BLENDER_EXE`, `FFMPEG_EXE`, and `FFPROBE_EXE` in a `.env` file.
3. Run `install_russian_voice.bat` once for the offline Russian Irina/Ruslan voices (optional, downloads about 126 MB of voice models), then run `setup.bat` once.
4. Run `run.bat` and choose a topic/story, character, voice, and duration.
5. Finished MP4s appear in `output/ready/`; failed QA runs are moved to `output/quarantine/` with a report.

The setup script checks prerequisites and never installs paid tools. For better Russian narration, run `install_russian_voice.bat` once to download Piper and the optional Irina/Ruslan voice models; this needs internet for the download, but narration itself runs locally afterward. The voice models and engine have their own licenses, so review them before commercial use. If Piper is unavailable, the app attempts an installed Russian Windows speech voice.

## Current MVP behavior

- Opens a menu to choose a Russian story/topic, character, voice, and duration.
- Includes original Russian micro-stories and narration text.
- Supports robot, cat, astronaut, and dragon character variants.
- Builds and animates a low-poly 3D character, environment, props, lighting, and camera.
- Renders portrait frames with Blender in background mode.
- Adds offline narration when the local speech engine is available, then muxes and normalizes audio/video with FFmpeg.
- Writes a manifest and QA report for each output.

This is deliberately a reliable procedural 3D foundation, not a claim that a large generative video model can run on a 4 GB laptop. Heavier AI video models generally require substantially more memory and/or a GPU. See `docs/ARCHITECTURE.md`.

## Configuration

Run `run.bat` in a terminal to open the interactive menu for topic/story, character, and voice. Edit `config/settings.json` to change duration, resolution, FPS, and audio settings. Defaults are intentionally conservative. Set `publish.enabled` to `false` (default); this project does not auto-upload to social platforms.

## Troubleshooting

- `Blender not found`: install Blender or set `BLENDER_EXE` in `.env`.
- `FFmpeg not found`: install FFmpeg and add its `bin` directory to PATH.
- `No audio`: narration is optional; install/configure Piper or use Windows Speech on Windows.
- `Render too slow`: lower `render.width`, `render.height`, `render.fps`, or `video.duration_seconds` in settings.

## License

Project code: MIT. Generated procedural geometry and story templates are original project content. Third-party tools and voices retain their own licenses; check each local asset/voice license before use. No external media is included by default.
