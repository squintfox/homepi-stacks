"""Create/update Whisparr quality profiles and Custom Formats from the TRaSH *Radarr* guide.

TRaSH has no Whisparr guide, so this applies the Radarr profiles/Custom Formats
(https://trash-guides.info/Radarr/radarr-setup-quality-profiles/) to Whisparr.
Qualities Whisparr doesn't have are skipped; Custom Formats using specifications
Whisparr doesn't support are skipped with a warning.

Usage:
  python3 whisparr_quality_profiles.py --list
  python3 whisparr_quality_profiles.py hd-bluray-web [--url http://localhost:6969] [--dry-run]
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
JSON_PATH = "docs/json/radarr"
GROUP_ID_BASE = 1000

# Radarr quality name -> Whisparr (Sonarr-style) quality name, where they differ
QUALITY_ALIASES = {
    "Remux-1080p": "Bluray-1080p Remux",
    "Remux-2160p": "Bluray-2160p Remux",
}


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


class Whisparr:
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
    """Convert TRaSH items (highest priority first) to Whisparr items (lowest first).

    Returns (items, cutoff_ids, skipped). Whisparr qualities not in the TRaSH profile
    are appended as disallowed at the lowest priority.
    """
    items, cutoff_ids, skipped, used = [], {}, [], set()
    next_group = GROUP_ID_BASE
    for entry in reversed(trash_items):
        name = entry["name"]
        if entry.get("items"):
            members = []
            for m in entry["items"]:
                q = qualities.get(QUALITY_ALIASES.get(m, m))
                if q is None:
                    skipped.append(m)
                    continue
                used.add(q["name"])
                members.append({"quality": q, "items": [], "allowed": entry["allowed"]})
            if not members:
                continue
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
            q = qualities.get(QUALITY_ALIASES.get(name, name))
            if q is None:
                skipped.append(name)
                continue
            used.add(q["name"])
            items.append({"quality": q, "items": [], "allowed": entry["allowed"]})
            cutoff_ids[name] = q["id"]
    extra = [
        {"quality": q, "items": [], "allowed": False}
        for n, q in qualities.items()
        if n not in used
    ]
    return extra + items, cutoff_ids, skipped


def sync_custom_formats(whisparr, wanted, dry_run):
    templates = {
        t["implementation"]: t for t in whisparr.call("GET", "/customformat/schema")
    }
    existing = {cf["name"]: cf for cf in whisparr.call("GET", "/customformat")}
    for cf in wanted:
        specs, unsupported = [], None
        for s in cf["specifications"]:
            tmpl = templates.get(s["implementation"])
            names = {f["name"] for f in tmpl["fields"]} if tmpl else set()
            if tmpl is None or set(s["fields"]) - names:
                unsupported = s["implementation"]
                break
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
        if unsupported:
            print(f"  Skipped CF (unsupported {unsupported}): {cf['name']}")
            continue
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
            whisparr.call("PUT", f"/customformat/{current['id']}", payload)
            print(f"  CF updated: {cf['name']}")
        else:
            whisparr.call("POST", "/customformat", payload)
            print(f"  CF created: {cf['name']}")


def apply_profile(whisparr, gh, name, cf_by_id, dry_run):
    profile = gh.get(f"quality-profiles/{name}.json")
    print(f"\n== {profile['name']} ({name}) ==")
    score_set = profile.get("trash_score_set", "default")

    needed = {
        tid: cf_by_id[tid]
        for tid in profile.get("formatItems", {}).values()
        if tid in cf_by_id
    }
    sync_custom_formats(whisparr, list(needed.values()), dry_run)

    scores = {}
    for cf in needed.values():
        s = cf.get("trash_scores", {})
        scores[cf["name"]] = s.get(score_set, s.get("default", 0))

    if dry_run:
        for cf_name, score in scores.items():
            print(f"  score {score:>6}  {cf_name}")
        print("  [dry-run] profile not sent")
        return

    schema = whisparr.call("GET", "/qualityprofile/schema")
    qualities = flatten_qualities(schema["items"])
    items, cutoff_ids, skipped = build_items(profile["items"], qualities)
    if skipped:
        print(f"  Qualities not in Whisparr (skipped): {', '.join(skipped)}")

    cutoff = cutoff_ids.get(profile["cutoff"])
    if cutoff is None:
        allowed = [i for i in reversed(items) if i["allowed"]]
        if not allowed:
            sys.exit(f"No allowed qualities left for profile {name}")
        top = allowed[0]
        cutoff = top["id"] if "id" in top else top["quality"]["id"]
        print(f"  Cutoff '{profile['cutoff']}' unavailable; using highest allowed quality")

    format_items = [
        {"format": cf["id"], "name": cf["name"], "score": scores.get(cf["name"], 0)}
        for cf in whisparr.call("GET", "/customformat")
    ]

    payload = {
        "name": profile["name"],
        "upgradeAllowed": profile["upgradeAllowed"],
        "cutoff": cutoff,
        "items": items,
        "minFormatScore": profile["minFormatScore"],
        "cutoffFormatScore": profile["cutoffFormatScore"],
        "minUpgradeFormatScore": profile.get("minUpgradeFormatScore", 1),
        "formatItems": format_items,
    }
    # Only Radarr-style Whisparr builds take a language on the profile
    if "language" in schema:
        languages = {l["name"]: l for l in whisparr.call("GET", "/language")}
        language = languages.get(profile.get("language", "Original")) or languages.get(
            "Any"
        )
        if language:
            payload["language"] = language

    existing = {p["name"]: p for p in whisparr.call("GET", "/qualityprofile")}
    if profile["name"] in existing:
        payload["id"] = existing[profile["name"]]["id"]
        whisparr.call("PUT", f"/qualityprofile/{payload['id']}", payload)
        print(f"  Updated profile '{profile['name']}'")
    else:
        whisparr.call("POST", "/qualityprofile", payload)
        print(f"  Created profile '{profile['name']}'")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "profiles",
        nargs="*",
        help="TRaSH Radarr profile names without .json, e.g. hd-bluray-web",
    )
    ap.add_argument("--url", default="http://localhost:6969")
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

    key = (
        os.environ.get("WHISPARR_API_KEY") or getpass.getpass("Whisparr API key: ").strip()
    )
    whisparr = Whisparr(args.url, key)
    try:
        whisparr.call("GET", "/system/status")

        print("Fetching TRaSH Custom Format definitions...")
        with ThreadPoolExecutor(8) as pool:
            cfs = list(pool.map(lambda n: gh.get(f"cf/{n}"), gh.list_dir("cf")))
        cf_by_id = {cf["trash_id"]: cf for cf in cfs}

        for name in args.profiles:
            apply_profile(whisparr, gh, name, cf_by_id, args.dry_run)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP error {e.code} for {e.url}: {e.read().decode(errors='replace')}")
    except urllib.error.URLError as e:
        sys.exit(f"Connection failed: {e}")


if __name__ == "__main__":
    main()
