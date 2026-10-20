"""Apply Radarr quality size definitions to Whisparr via its v3 API.

Source: https://trash-guides.info/Radarr/Radarr-Quality-Settings-File-Size/
Usage:  python3 whisparr_quality_sizes.py [--url http://localhost:6969] [--dry-run]
"""

import argparse
import getpass
import json
import sys
import urllib.error
import urllib.request

# quality title -> minimum size (MB/min); preferred and max follow the Radarr guide.
MOVIE = {
    "HDTV-720p": 17.1,
    "WEBDL-720p": 12.5,
    "WEBRip-720p": 12.5,
    "Bluray-720p": 25.7,
    "HDTV-1080p": 33.8,
    "WEBDL-1080p": 12.5,
    "WEBRip-1080p": 12.5,
    "Bluray-1080p": 50.8,
    "Bluray-1080p Remux": 102,
    "HDTV-2160p": 85,
    "WEBDL-2160p": 34.5,
    "WEBRip-2160p": 34.5,
    "Bluray-2160p": 102,
    "Bluray-2160p Remux": 187.4,
}
PREFERRED = 1999
MAXIMUM = 2000


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
    ap.add_argument("--url", default="http://localhost:6969")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    key = getpass.getpass("Whisparr API key: ").strip()
    base = args.url.rstrip("/")
    wanted = MOVIE

    try:
        defs = request(base, key, "GET", "/qualitydefinition")
    except urllib.error.URLError as e:
        sys.exit(f"Failed to reach Whisparr: {e}")

    changed = 0
    for definition in defs:
        title = definition["title"]
        if title not in wanted:
            continue
        definition["minSize"] = wanted[title]
        definition["preferredSize"] = PREFERRED
        definition["maxSize"] = MAXIMUM
        print(
            f"{title}: min={definition['minSize']} " f"preferred={PREFERRED} max={MAXIMUM}"
        )
        changed += 1

    missing = set(wanted) - {definition["title"] for definition in defs}
    if missing:
        print(f"Not found in Whisparr (skipped): {', '.join(sorted(missing))}")

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
