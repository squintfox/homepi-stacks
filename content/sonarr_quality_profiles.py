"""Create/update Sonarr (v4) quality profiles and Custom Formats from the TRaSH Guides.

Guide: https://trash-guides.info/Sonarr/sonarr-setup-quality-profiles/
Profile definitions, Custom Formats and scores come from the TRaSH-Guides/Guides repo
(docs/json/sonarr). Existing Custom Formats and profiles with the same name are updated.

Usage:
  python3 sonarr_quality_profiles.py --list
  python3 sonarr_quality_profiles.py web-1080p web-2160p [--url http://localhost:8989] [--dry-run]
"""

import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO = "TRaSH-Guides/Guides"
JSON_PATH = "docs/json/sonarr"
GROUP_ID_BASE = 1000


def http(url, headers=None, method="GET", body=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else None


class Github:
    def __init__(self, branch):
        self.branch = branch

    def list_dir(self, subdir):
        url = f"https://api.github.com/repos/{REPO}/contents/{JSON_PATH}/{subdir}?ref={self.branch}"
        return [e["name"] for e in http(url) if e["name"].endswith(".json")]

    def get(self, path):
        return http(
            f"https://raw.githubusercontent.com/{REPO}/{self.branch}/{JSON_PATH}/{path}"
        )


class Sonarr:
    def __init__(self, base, key):
        self.base = base.rstrip("/") + "/api/v3"
        self.headers = {"X-Api-Key": key}

    def call(self, method, path, body=None):
        return http(self.base + path, self.headers, method, body)


def flatten_qualities(items):
    out = {}
    for item in items:
        if item.get("quality"):
            out[item["quality"]["name"]] = item["quality"]
        out.update(flatten_qualities(item.get("items") or []))
    return out


def build_items(trash_items, qualities):
    """Convert TRaSH items (highest priority first) to Sonarr items (lowest first)."""
    items, cutoff_ids, next_group = [], {}, GROUP_ID_BASE
    for entry in reversed(trash_items):
        name = entry["name"]
        if entry.get("items"):
            members = [
                {"quality": qualities[m], "items": [], "allowed": entry["allowed"]}
                for m in entry["items"]
            ]
            items.append(
                {
                    "id": next_group,
                    "name": name,
                    "items": members,
                    "allowed": entry["allowed"],
                }
            )
            cutoff_ids[name] = next_group
            next_group += 1
        else:
            q = qualities[name]
            items.append({"quality": q, "items": [], "allowed": entry["allowed"]})
            cutoff_ids[name] = q["id"]
    return items, cutoff_ids


def sync_custom_formats(sonarr, wanted, dry_run):
    cf_schema = sonarr.call("GET", "/customformat/schema")
    templates = {t["implementation"]: t for t in cf_schema}
    existing = {cf["name"]: cf for cf in sonarr.call("GET", "/customformat")}
    for cf in wanted:
        specs = []
        for s in cf["specifications"]:
            tmpl = templates.get(s["implementation"])
            if tmpl is None:
                sys.exit(
                    f"Sonarr lacks specification type {s['implementation']} (CF {cf['name']})"
                )
            names = {f["name"] for f in tmpl["fields"]}
            unknown = set(s["fields"]) - names
            if unknown:
                sys.exit(f"Unexpected fields {unknown} in CF {cf['name']}")
            fields = [
                dict(f, value=s["fields"][f["name"]]) if f["name"] in s["fields"] else f
                for f in tmpl["fields"]
            ]
            specs.append(
                {
                    "name": s["name"],
                    "implementation": s["implementation"],
                    "implementationName": tmpl.get("implementationName"),
                    "negate": s["negate"],
                    "required": s["required"],
                    "fields": fields,
                }
            )
        payload = {
            "name": cf["name"],
            "includeCustomFormatWhenRenaming": cf.get(
                "includeCustomFormatWhenRenaming", False
            ),
            "specifications": specs,
        }
        current = existing.get(cf["name"])
        verb = "update" if current else "create"
        if dry_run:
            print(f"  [dry-run] CF {verb}: {cf['name']}")
        elif current:
            payload["id"] = current["id"]
            sonarr.call("PUT", f"/customformat/{current['id']}", payload)
            print(f"  CF updated: {cf['name']}")
        else:
            sonarr.call("POST", "/customformat", payload)
            print(f"  CF created: {cf['name']}")


def apply_profile(sonarr, gh, name, cf_by_id, dry_run):
    profile = gh.get(f"quality-profiles/{name}.json")
    print(f"\n== {profile['name']} ({name}) ==")
    score_set = profile.get("trash_score_set", "default")

    needed = {
        tid: cf_by_id[tid]
        for tid in profile.get("formatItems", {}).values()
        if tid in cf_by_id
    }
    missing = [
        n for n, tid in profile.get("formatItems", {}).items() if tid not in cf_by_id
    ]
    if missing:
        print(f"  Warning: no CF definition found for: {', '.join(missing)}")
    sync_custom_formats(sonarr, list(needed.values()), dry_run)

    scores = {}
    for cf in needed.values():
        s = cf.get("trash_scores", {})
        scores[cf["name"]] = s.get(score_set, s.get("default", 0))

    if dry_run:
        for cf_name, score in scores.items():
            print(f"  score {score:>6}  {cf_name}")
        print("  [dry-run] profile not sent")
        return

    schema = sonarr.call("GET", "/qualityprofile/schema")
    qualities = flatten_qualities(schema["items"])
    items, cutoff_ids = build_items(profile["items"], qualities)
    format_items = [
        {"format": cf["id"], "name": cf["name"], "score": scores.get(cf["name"], 0)}
        for cf in sonarr.call("GET", "/customformat")
    ]

    payload = {
        "name": profile["name"],
        "upgradeAllowed": profile["upgradeAllowed"],
        "cutoff": cutoff_ids[profile["cutoff"]],
        "items": items,
        "minFormatScore": profile["minFormatScore"],
        "cutoffFormatScore": profile["cutoffFormatScore"],
        "minUpgradeFormatScore": profile.get("minUpgradeFormatScore", 1),
        "formatItems": format_items,
    }
    existing = {p["name"]: p for p in sonarr.call("GET", "/qualityprofile")}
    if profile["name"] in existing:
        payload["id"] = existing[profile["name"]]["id"]
        sonarr.call("PUT", f"/qualityprofile/{payload['id']}", payload)
        print(f"  Updated profile '{profile['name']}'")
    else:
        sonarr.call("POST", "/qualityprofile", payload)
        print(f"  Created profile '{profile['name']}'")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "profiles", nargs="*", help="TRaSH profile file names without .json, e.g. web-1080p"
    )
    ap.add_argument("--url", default="http://localhost:8989")
    ap.add_argument("--branch", default="master")
    ap.add_argument(
        "--list", action="store_true", help="List available TRaSH profiles and exit"
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    gh = Github(args.branch)
    try:
        available = [n[:-5] for n in gh.list_dir("quality-profiles")]
    except urllib.error.URLError as e:
        sys.exit(f"Failed to reach GitHub: {e}")
    if args.list:
        print("\n".join(p for p in available if p != "base-profile"))
        return
    if not args.profiles:
        ap.error("specify at least one profile (see --list)")
    unknown = [p for p in args.profiles if p not in available]
    if unknown:
        sys.exit(f"Unknown profile(s): {', '.join(unknown)}")

    key = os.environ.get("SONARR_API_KEY") or getpass.getpass("Sonarr API key: ").strip()
    sonarr = Sonarr(args.url, key)
    try:
        sonarr.call("GET", "/system/status")

        print("Fetching TRaSH Custom Format definitions...")
        with ThreadPoolExecutor(8) as pool:
            cfs = list(pool.map(lambda n: gh.get(f"cf/{n}"), gh.list_dir("cf")))
        cf_by_id = {cf["trash_id"]: cf for cf in cfs}

        for name in args.profiles:
            apply_profile(sonarr, gh, name, cf_by_id, args.dry_run)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP error {e.code} for {e.url}: {e.read().decode(errors='replace')}")
    except urllib.error.URLError as e:
        sys.exit(f"Connection failed: {e}")


if __name__ == "__main__":
    main()
