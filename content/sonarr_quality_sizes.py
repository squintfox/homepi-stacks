"""Apply TRaSH Guides quality size definitions to Sonarr via its v3 API.

Source: https://trash-guides.info/Sonarr/Sonarr-Quality-Settings-File-Size/
Usage:  python3 sonarr_quality_sizes.py [--url http://localhost:8989] [--profile series|anime] [--dry-run]
"""

import argparse
import getpass
import json
import sys
import urllib.error
import urllib.request

# quality title -> min size (MB/min). Max is "unlimited" (1000 in the UI) for all.
SERIES = {
    "HDTV-720p": 10,
    "HDTV-1080p": 15,
    "WEBRip-720p": 10,
    "WEBDL-720p": 10,
    "Bluray-720p": 17.1,
    "WEBRip-1080p": 15,
    "WEBDL-1080p": 15,
    "Bluray-1080p": 50.4,
    "Bluray-1080p Remux": 69.1,
    "HDTV-2160p": 25,
    "WEBRip-2160p": 25,
    "WEBDL-2160p": 25,
    "Bluray-2160p": 94.6,
    "Bluray-2160p Remux": 187.4,
}
ANIME = {
    name: 5
    for name in [
        "SDTV",
        "WEBRip-480p",
        "WEBDL-480p",
        "DVD",
        "Bluray-480p",
        "Bluray-576p",
        "HDTV-720p",
        "HDTV-1080p",
        "WEBRip-720p",
        "WEBDL-720p",
        "Bluray-720p",
        "WEBRip-1080p",
        "WEBDL-1080p",
        "Bluray-1080p",
        "Bluray-1080p Remux",
        "HDTV-2160p",
        "WEBRip-2160p",
        "WEBDL-2160p",
        "Bluray-2160p",
        "Bluray-2160p Remux",
    ]
}
PROFILES = {"series": SERIES, "anime": ANIME}
PREFERRED = 995  # as high as possible, just under the unlimited max


def request(base, key, method, path, body=None):
    req = urllib.request.Request(
        f"{base}/api/v3{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"X-Api-Key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8989")
    ap.add_argument("--profile", choices=PROFILES, default="series")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    key = getpass.getpass("Sonarr API key: ").strip()
    base = args.url.rstrip("/")
    wanted = PROFILES[args.profile]

    try:
        defs = request(base, key, "GET", "/qualitydefinition")
    except urllib.error.URLError as e:
        sys.exit(f"Failed to reach Sonarr: {e}")

    changed = 0
    for d in defs:
        title = d["title"]
        if title not in wanted:
            continue
        d["minSize"] = wanted[title]
        d["preferredSize"] = PREFERRED
        d["maxSize"] = None  # unlimited
        print(f"{title}: min={d['minSize']} preferred={PREFERRED} max=unlimited")
        changed += 1

    missing = set(wanted) - {d["title"] for d in defs}
    if missing:
        print(f"Not found in Sonarr (skipped): {', '.join(sorted(missing))}")

    if args.dry_run:
        print("Dry run, nothing sent.")
        return
    try:
        request(base, key, "PUT", "/qualitydefinition/update", defs)
    except urllib.error.HTTPError as e:
        sys.exit(f"Update failed: {e.code} {e.read().decode(errors='replace')}")
    print(f"Updated {changed} quality definitions.")


if __name__ == "__main__":
    main()
