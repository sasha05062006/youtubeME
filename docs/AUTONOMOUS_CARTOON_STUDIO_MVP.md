# Autonomous Cartoon Studio — MVP specification

## Product goal

YouTubeME should accept one natural-language brief and produce a complete Russian-language 3D cartoon with dialogue, character-specific voices, sound effects, music, scene changes, and a final mixed video. It must not require the user to write code, manually edit audio, or assemble scenes.

Example brief:

> Сделай детский 3D-мультфильм на 3 минуты про слонёнка и трёх друзей. Они ищут потерявшийся волшебный колокольчик в лесу. Добавь юмор, тревожный момент, дружбу и счастливый конец. Русский язык, добрые голоса, кинематографичная музыка и звуки леса.

The current procedural short generator is only a technical foundation; it does not yet meet this product goal.

## User experience

1. User enters a free-form description, target duration, language, aspect ratio, age group, and optional style notes.
2. The planner expands the brief into a coherent script with a beginning, middle, climax, and ending. It estimates dialogue length from the target duration.
3. The planner produces a validated, machine-readable screenplay: cast, character descriptions, scene timeline, dialogue lines, acting cues, camera direction, sound effects, ambience, and music cues.
4. The asset stage creates or reuses consistent 3D characters, props, and environments. Character identity must remain consistent across shots.
5. The voice stage assigns a distinct voice profile to each speaking character and narrator. It synthesizes each line separately, preserving emotion, pace, pauses, and pronunciation where the selected engine supports them.
6. The sound stage places effects and ambience on a timeline, adds music, ducks music under dialogue, and mixes/master audio without clipping.
7. The renderer creates each scene and assembles the shots into the final video.
8. Automated QA checks duration, missing lines, audio/video synchronization, clipping, silence, black frames, and missing asset/license records. Failed jobs go to quarantine with a readable report.

The normal user workflow is one brief and one **Create cartoon** action. Advanced controls are optional, not required.

## Quality requirements

### Story and dialogue
- No fixed list of story templates as the primary workflow.
- Dialogue must be attributed to a known character ID; every character has stable traits and a consistent voice assignment.
- Scene timings and dialogue must fit the requested runtime. A three-minute film must not be made by stretching an 18-second script.
- Support narrator-only, dialogue-only, and mixed narration/dialogue.
- Include emotional and performance cues in the screenplay, while gracefully degrading when a TTS engine cannot express them.

### Voices
- A single default computer voice for the whole film is not acceptable for multi-character stories.
- Every speaking role receives a separate voice profile. Voices should differ in perceived age, pitch, pace, timbre, and delivery where the engine allows it.
- Keep each line as a separate audio asset so that it can be retimed, retried, and mixed independently.
- Provide a voice preview and a clear warning if only basic offline TTS is available.
- Piper and Windows SAPI are fallback/offline voices, not a claim of professional, human-quality acting. Better voice quality may require a compatible neural TTS engine or an optional external provider. External services must be opt-in, disclose privacy/cost/limits, and never be silently called.
- Do not clone or imitate a real person's voice without the required permission.

### Sound design
- Each scene can define ambience, one-shot sound effects, music, and dialogue on a common timeline.
- Sound effects must be synchronized to actions and scene changes, not added randomly.
- Duck music under speech; keep dialogue intelligible; normalize loudness and prevent clipping.
- Only use generated, bundled, or explicitly licensed audio. Record source and license for each asset.
- A silent render must not be described as complete when the brief requires dialogue or sound design.

### 3D visuals
- Real 3D scene rendering remains the default; no slideshow fallback.
- Characters, props, lighting, camera, and environments must be scene-aware and reusable.
- The current primitive-based single-character scene is not sufficient for a multi-character three-minute cartoon. Add reusable character rigs/animation, multiple-character blocking, scene templates, and camera cuts incrementally.
- Keep a low-resource render profile for the 4 GB RAM / Celeron-class target. A longer cartoon may take hours or require a lower preview quality.

## Free-first technical strategy

- Keep orchestration and timeline/mixing local using Python, Blender, and FFmpeg.
- Use local tools for simple fallback voice generation and sound processing.
- Treat high-quality neural speech, text/script planning, and generative 3D assets as optional backends behind provider interfaces; never hardwire paid APIs into the core.
- Before enabling any external backend, document whether it is genuinely free, its usage limits, network requirement, data handling, license, and whether a payment method is required. "Free tier" does not mean unlimited or guaranteed free forever.
- On the target laptop, do not promise that modern text-to-video or large language models will run locally. Use a compact local model only if benchmarks prove it fits, or let the user explicitly opt into an external free-tier service.
- Jobs must be resumable by stage, with cached scripts, line audio, assets, rendered scenes, and logs so that a failure does not force a full rerun.

## Proposed screenplay JSON shape

```json
{
  "title": "Слонёнок и волшебный колокольчик",
  "language": "ru",
  "target_duration_seconds": 180,
  "style": "warm stylized 3D children's cartoon",
  "cast": [
    {"id": "elephant", "name": "Топа", "description": "любопытный слонёнок", "voice_profile": "childlike_warm"},
    {"id": "fox", "name": "Рыжик", "description": "быстрый и шутливый лисёнок", "voice_profile": "youthful_playful"},
    {"id": "hare", "name": "Прыг", "description": "осторожный зайчонок", "voice_profile": "light_nervous"},
    {"id": "bear", "name": "Миша", "description": "добрый медвежонок", "voice_profile": "low_gentle"}
  ],
  "scenes": [
    {
      "id": "scene_01",
      "duration_seconds": 24,
      "location": "sunlit_forest",
      "visual_action": "Друзья встречаются на лесной поляне",
      "camera": "wide establishing shot, then medium close-ups",
      "dialogue": [
        {"character_id": "elephant", "text": "Ребята, вы слышали этот звон?", "emotion": "curious", "delivery": "soft, attentive"}
      ],
      "ambience": [{"asset": "forest_day", "start_seconds": 0, "gain_db": -22}],
      "sound_effects": [{"asset": "small_bell", "at_seconds": 7.5, "gain_db": -8}],
      "music": {"mood": "wonder", "start_seconds": 0, "gain_db": -25}
    }
  ]
}
```

This is an illustrative schema, not a generated finished script. Every timeline value must be validated and adjusted to fit the target runtime.

## Implementation milestones

1. **Prompt and screenplay contract:** free-form brief input, script schema, validation, duration budgeting, cast/scene/audio cue records.
2. **Multi-voice dialogue renderer:** separate line files, voice assignment, pauses, retries, and a readable voice capability report.
3. **Sound timeline mixer:** ambience, licensed/generated effects, music ducking, loudness normalization, and sync QA.
4. **Multi-scene 3D renderer:** scene changes, several characters, reusable assets, camera cuts, and resumable rendering.
5. **End-to-end cartoon test:** one three-minute sample story, verified script, per-character dialogue, sound effects, music, render, and QA report.

## Acceptance test

A single brief requesting a three-minute children's cartoon with four friends must produce:
- a coherent script with a stable four-character cast;
- dialogue lines assigned to characters and rendered using distinct configured voice profiles;
- scene-level music/ambience and synchronized one-shot sound effects;
- multiple 3D scenes with the characters present and identifiable;
- a final video close to 180 seconds, with audible dialogue, no clipping, and an audio/video sync report;
- a manifest that records engines, models, external calls, and all asset licenses.

A passing unit test or successful short template render alone does not satisfy this acceptance test.
