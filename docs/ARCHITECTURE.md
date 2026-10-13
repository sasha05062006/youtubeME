# Architecture and realistic limits

## Pipeline

1. **Story planner** chooses a bundled short English micro-story and a deterministic seed. No API calls or credentials are needed.
2. **3D scene builder** invokes Blender in background mode and builds the character, environment, props, lights, camera, and animated keyframes from Python.
3. **Frame encoder** uses FFmpeg to encode the rendered frame sequence into a vertical H.264 MP4.
4. **Offline narration** uses Windows SAPI/System.Speech when available. The pipeline can still produce a silent video if speech is unavailable; it records that condition in the manifest.
5. **Quality gate** checks the video stream, orientation, duration, file size, and audio peak when narration exists. Failed runs are quarantined rather than placed in the ready folder.
6. **Manifest** records the story, seed, generated assets, software versions, and QA results.

## Why procedural 3D first

The target machine has 4 GB RAM, a Celeron N3350, and no discrete GPU. Modern text-to-video models such as Wan require much more memory and typically a capable GPU; they are not a dependable fully-local option on this hardware. A procedural Blender scene is genuinely 3D and can be generated offline, although rendering may be slow. The MVP prioritizes repeatability and zero API cost over photorealistic generative video.

## Free and licensing rules

- The default visual assets are created procedurally at render time.
- No stock clips, music, external images, or web-scraped assets are included.
- Do not add third-party models, fonts, sounds, or voice models without recording their license in the asset manifest.
- Uploading and scheduling are disabled; a human reviews each MP4 before posting.

## Resource tuning

Start with 360x640, 12 FPS, and 12 seconds. If renders are too slow, lower FPS to 8 and duration to 8 seconds. Increase resolution only after a successful test run. Keep the Windows page file system-managed and close memory-heavy applications while rendering.
