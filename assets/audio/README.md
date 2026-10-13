# Local audio asset library

The audio timeline renderer expects audio files with these folder and identifier conventions:

- `assets/audio/sfx/<asset-id>.wav|flac|mp3|ogg` — one-shot sound effects.
- `assets/audio/ambience/<asset-id>.wav|flac|mp3|ogg` — loopable scene ambience.
- `assets/audio/music/<asset-id>.wav|flac|mp3|ogg` — loopable music cues.

The example screenplay references assets such as `small_bell`, `forest_day`, and `warm_adventure`. Those audio files are **not bundled yet**, so the example validates as a screenplay but cannot produce a complete sound mix until matching files are added.

Use only audio that you created yourself or that has a license compatible with your intended use. Keep a record of source URL, creator, license, and any attribution requirements for every third-party file. Do not assume that a file is free for commercial use merely because it can be downloaded for free.

Recommended production practice:
- trim one-shot effects to their useful duration;
- use clean loop points for ambience/music;
- avoid clipping and excessive reverb;
- keep dialogue clearly above ambience/music;
- audition the final mix before publishing.
