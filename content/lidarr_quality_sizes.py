"""Apply a conservative, Lidarr-default-based quality size profile via its v1 API.

Lidarr has no TRaSH Guide quality-size preset. These values follow Lidarr's
built-in definitions as a practical starting point.
Source: https://github.com/Lidarr/Lidarr/blob/develop/src/NzbDrone.Core/Qualities/Quality.cs
Usage:  python3 lidarr_quality_sizes.py [--url http://localhost:8686] [--dry-run]
"""

import argparse
import getpass
import json
import sys
import urllib.error
import urllib.request

# quality title -> (preferred size, maximum size) in Lidarr's quality scale.
# Zero minimums avoid rejecting releases based on variable album/track duration.
SETTINGS = {
    "MP3-8": (5, 10),
    "MP3-16": (15, 20),
    "MP3-24": (25, 30),
    "MP3-32": (35, 40),
    "MP3-40": (40, 45),
    "MP3-48": (50, 55),
    "MP3-56": (60, 65),
    "MP3-64": (70, 75),
    "MP3-80": (90, 95),
    "MP3-96": (95, 110),
    "MP3-112": (95, 125),
    "MP3-128": (95, 140),
    "OGG Vorbis Q5": (95, 175),
    "MP3-160": (95, 175),
    "MP3-192": (95, 210),
    "OGG Vorbis Q6": (95, 210),
    "AAC-192": (95, 210),
    "WMA": (195, 350),
    "MP3-224": (95, 245),
    "OGG Vorbis Q7": (95, 245),
    "MP3-VBR-V2": (95, 280),
    "MP3-256": (95, 280),
    "OGG Vorbis Q8": (95, 280),
    "AAC-256": (95, 280),
    "MP3-VBR-V0": (195, 350),
    "AAC-VBR": (195, 350),
    "MP3-320": (195, 350),
    "OGG Vorbis Q9": (195, 350),
    "AAC-320": (195, 350),
    "OGG Vorbis Q10": (295, 550),
    "FLAC": (895, None),
    "ALAC": (895, None),
    "APE": (895, None),
    "WavPack": (895, None),
    "FLAC 24bit": (895, None),
    "ALAC 24bit": (895, None),
    "WAV": (895, None),
}


def request(base, key, method, path, body=None):
    req = urllib.request.Request(
        f"{base}/api/v1{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"X-Api-Key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8686")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    key = getpass.getpass("Lidarr API key: ").strip()
    base = args.url.rstrip("/")

    try:
        definitions = request(base, key, "GET", "/qualitydefinition")
    except urllib.error.URLError as e:
        sys.exit(f"Failed to reach Lidarr: {e}")

    changed = 0
    for definition in definitions:
        title = definition["title"]
        if title not in SETTINGS:
            continue
        preferred, maximum = SETTINGS[title]
        definition["minSize"] = 0
        definition["preferredSize"] = preferred
        definition["maxSize"] = maximum
        max_display = "unlimited" if maximum is None else maximum
        print(f"{title}: min=0 preferred={preferred} max={max_display}")
        changed += 1

    missing = set(SETTINGS) - {definition["title"] for definition in definitions}
    if missing:
        print(f"Not found in Lidarr (skipped): {', '.join(sorted(missing))}")

    if args.dry_run:
        print("Dry run, nothing sent.")
        return
    try:
        request(base, key, "PUT", "/qualitydefinition/update", definitions)
    except urllib.error.HTTPError as e:
        sys.exit(f"Update failed: {e.code} {e.read().decode(errors='replace')}")
    print(f"Updated {changed} quality definitions.")


if __name__ == "__main__":
    main()
