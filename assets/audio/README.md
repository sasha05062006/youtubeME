# Local audio asset library

The audio timeline renderer expects audio files with these folder and identifier conventions:

- `assets/audio/sfx/<asset-id>.wav|flac|mp3|ogg` — one-shot sound effects.
- `assets/audio/ambience/<asset-id>.wav|flac|mp3|ogg` — loopable scene ambience.
- `assets/audio/music/<asset-id>.wav|flac|mp3|ogg` — loopable music cues.

Run `install_audio_assets.bat` on Windows (or `python scripts/install_audio_assets.py` from the project root) to download the starter CC0 library. The download is optional, uses the internet, and does not require a paid account or API key. It installs the asset IDs used by `examples/elephant_friends.screenplay.json` and writes `asset_manifest.json` with source pages, authors, and stated licenses.

The files are not committed into the Git repository; each user downloads them locally. If a source is unavailable, the installer reports the failed asset and can be rerun to retry.

Use only audio that you created yourself or that has a license compatible with your intended use. Keep a record of source URL, creator, license, and any attribution requirements for every third-party file. Do not assume that a file is free for commercial use merely because it can be downloaded for free.

Recommended production practice:
- trim one-shot effects to their useful duration;
- use clean loop points for ambience/music;
- avoid clipping and excessive reverb;
- keep dialogue clearly above ambience/music;
- audition the final mix before publishing.
