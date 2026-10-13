from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIO_ROOT = ROOT / "assets" / "audio"

# Downloadable source pages explicitly mark these files CC0 / public domain.
# The manifest records the original source and license for every installed alias.
ASSETS: list[dict[str, Any]] = [
    {"folder":"ambience","name":"forest_day","filename":"forest_day.mp3",
     "url":"https://bigsoundbank.com/UPLOAD/mp3/0100.mp3",
     "source":"https://bigsoundbank.com/forest-s0100.html","author":"Joseph SARDIN / LaSonotheque","license":"CC0 1.0"},
    {"folder":"ambience","name":"forest_stream","filename":"forest_stream.mp3",
     "url":"https://bigsoundbank.com/UPLOAD/mp3/2713.mp3",
     "source":"https://bigsoundbank.com/foret-et-ruisseau-1-s2713.html","author":"Pierre SIBANARCO / LaSonotheque","license":"CC0 1.0"},
    {"folder":"ambience","name":"forest_clearing","filename":"forest_clearing.mp3",
     "url":"https://bigsoundbank.com/UPLOAD/mp3/0100.mp3",
     "source":"https://bigsoundbank.com/forest-s0100.html","author":"Joseph SARDIN / LaSonotheque","license":"CC0 1.0"},
    {"folder":"sfx","name":"small_bell","filename":"small_bell.wav",
     "url":"https://opengameart.org/sites/default/files/bell_ding1.wav",
     "source":"https://opengameart.org/content/bell-dingschimes","author":"PWL","license":"CC0"},
    {"folder":"sfx","name":"magic_chime","filename":"magic_chime.wav",
     "url":"https://opengameart.org/sites/default/files/bell_ding2.wav",
     "source":"https://opengameart.org/content/bell-dingschimes","author":"PWL","license":"CC0"},
    {"folder":"sfx","name":"footsteps_grass","filename":"footsteps_grass.ogg",
     "url":"https://opengameart.org/sites/default/files/01-footstep.ogg",
     "source":"https://opengameart.org/content/footsteps-0","author":"GboxMikeFozzy","license":"CC0"},
    {"folder":"sfx","name":"footsteps_stone","filename":"footsteps_stone.ogg",
     "url":"https://opengameart.org/sites/default/files/03-footstep.ogg",
     "source":"https://opengameart.org/content/footsteps-0","author":"GboxMikeFozzy","license":"CC0"},
    {"folder":"sfx","name":"leaves_rustle","filename":"leaves_rustle.ogg",
     "url":"https://opengameart.org/sites/default/files/rustling_of_the_weeds.wav",
     "source":"https://opengameart.org/content/various-sound-effects-0","author":"Spring Spring / Julie Damsgaard","license":"CC0"},
    {"folder":"sfx","name":"stone_scrape","filename":"stone_scrape.wav",
     "url":"https://opengameart.org/sites/default/files/small_rock_impact.wav",
     "source":"https://opengameart.org/content/various-sound-effects-0","author":"Spring Spring / Julie Damsgaard","license":"CC0"},
    {"folder":"sfx","name":"water_splash","filename":"water_splash.flac",
     "url":"https://opengameart.org/sites/default/files/wave_01_cc0-11505__transitking__wavesound.flac",
     "source":"https://opengameart.org/content/water-waves","author":"transitking","license":"CC0"},
    {"folder":"sfx","name":"friends_laugh","filename":"friends_laugh.ogg",
     "url":"https://opengameart.org/sites/default/files/group_giggling.ogg",
     "source":"https://opengameart.org/content/group-giggling","author":"Nocturnal_Vanguard","license":"CC0"},
    {"folder":"sfx","name":"roots_creak","filename":"roots_creak.wav",
     "url":"https://opengameart.org/sites/default/files/rustling_of_the_weeds.wav",
     "source":"https://opengameart.org/content/various-sound-effects-0","author":"Spring Spring / Julie Damsgaard","license":"CC0"},
    {"folder":"music","name":"warm_adventure","filename":"warm_adventure.mp3",
     "url":"https://opengameart.org/sites/default/files/happy%20loop.mp3",
     "source":"https://opengameart.org/content/happy-loop","author":"wipics","license":"CC0"},
    {"folder":"music","name":"gentle_mystery","filename":"gentle_mystery.ogg",
     "url":"https://opengameart.org/sites/default/files/othercenter.ogg",
     "source":"https://opengameart.org/content/other-center","author":"zesona / Chris Murphy","license":"CC0"},
    {"folder":"music","name":"happy_ending","filename":"happy_ending.wav",
     "url":"https://opengameart.org/sites/default/files/HappyClappyLoop.wav",
     "source":"https://opengameart.org/content/happy-clappy-loop","author":"OwlishMedia","license":"CC0"},
]


def download_one(asset: dict[str, Any], force: bool = False) -> dict[str, Any]:
    folder = AUDIO_ROOT / asset["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / asset["filename"]
    if destination.exists() and destination.stat().st_size > 512 and not force:
        return {**asset, "local_path": str(destination.relative_to(ROOT)), "status": "already_present",
                "size_bytes": destination.stat().st_size}
    request = urllib.request.Request(
        asset["url"],
        headers={"User-Agent": "YouTubeME-FreeAudioInstaller/1.0", "Accept": "audio/*,application/octet-stream,*/*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Download failed for {asset['name']} from {asset['url']}: {exc}") from exc
    if len(data) < 512 or data.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        raise RuntimeError(f"Downloaded file for {asset['name']} is too small or looks like an HTML error page.")
    temp = destination.with_suffix(destination.suffix + ".part")
    temp.write_bytes(data)
    temp.replace(destination)
    return {**asset, "local_path": str(destination.relative_to(ROOT)), "status": "downloaded",
            "size_bytes": len(data)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Install a small starter pack of CC0 ambience, effects and music.")
    parser.add_argument("--force", action="store_true", help="Re-download files that already exist.")
    args = parser.parse_args()
    manifest_path = AUDIO_ROOT / "asset_manifest.json"
    records = []
    failed = []
    for asset in ASSETS:
        try:
            record = download_one(asset, force=args.force)
            records.append(record)
            print(f"[{record['status']}] {record['name']} ({record['size_bytes']:,} bytes)")
        except RuntimeError as exc:
            failed.append(str(exc))
            print(f"[FAILED] {asset['name']}: {exc}", file=sys.stderr)
    manifest_path.write_text(json.dumps({
        "created_at_unix": int(time.time()),
        "license_policy": "Each installed asset is listed with its source and stated CC0 license. Recheck source terms before commercial release.",
        "assets": records,
        "failed": failed,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Asset manifest: {manifest_path.relative_to(ROOT)}")
    if failed:
        print(f"{len(failed)} asset(s) could not be downloaded. Re-run later to retry.", file=sys.stderr)
        return 1
    print("Starter audio library is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
