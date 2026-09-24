#!/usr/bin/env python3
"""Builds source.json for Plezy from the official GitHub releases of edde746/plezy.

The file is regenerated from scratch on every run, so nothing from earlier runs
carries over. Only IPAs attached to official releases are listed, and the
newest one is downloaded and checked against GitHub's SHA-256 digest.
"""
import hashlib
import json
import os
import plistlib
import re
import sys
import tempfile
import urllib.request
import zipfile

UPSTREAM = "edde746/plezy"
ASSET = "plezy-ios.ipa"
BUNDLE_ID = "com.edde746.plezy"
KEEP_VERSIONS = 3
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source.json")
SOURCE_URL = os.environ.get("SOURCE_URL", "")


def api(path):
    req = urllib.request.Request(f"https://api.github.com/{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if token := os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def inspect_ipa(url, expected_sha, expected_size):
    """Downloads the IPA, checks its hash and returns its Info.plist."""
    sha = hashlib.sha256()
    size = 0
    with tempfile.NamedTemporaryFile(suffix=".ipa") as tmp:
        with urllib.request.urlopen(url, timeout=300) as r:
            while chunk := r.read(1 << 20):
                sha.update(chunk)
                size += len(chunk)
                tmp.write(chunk)
        tmp.flush()
        if sha.hexdigest() != expected_sha:
            fail(f"SHA-256 mismatch for {url}: {sha.hexdigest()} != {expected_sha}")
        if size != expected_size:
            fail(f"Size mismatch for {url}: {size} != {expected_size}")
        with zipfile.ZipFile(tmp.name) as z:
            name = next(
                (n for n in z.namelist() if re.fullmatch(r"Payload/[^/]+\.app/Info\.plist", n)),
                None,
            )
            if not name:
                fail("No Info.plist found in IPA")
            return plistlib.loads(z.read(name))


def main():
    owner = api(f"repos/{UPSTREAM}")["owner"]["login"]
    releases = [r for r in api(f"repos/{UPSTREAM}/releases?per_page=30")
                if not r["draft"] and not r["prerelease"]]

    versions = []
    for rel in releases:
        asset = next((a for a in rel["assets"] if a["name"] == ASSET), None)
        if not asset or not (asset.get("digest") or "").startswith("sha256:"):
            continue
        tag = rel["tag_name"]
        url = asset["browser_download_url"]
        # The link must point to the official release asset.
        if url != f"https://github.com/{UPSTREAM}/releases/download/{tag}/{ASSET}":
            fail(f"Unexpected download URL: {url}")
        sha = asset["digest"].removeprefix("sha256:")
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            fail(f"Invalid digest for {tag}: {asset['digest']}")

        entry = {
            "version": tag.lstrip("v"),
            "date": rel["published_at"][:10],
            "localizedDescription": (rel.get("body") or "").strip(),
            "downloadURL": url,
            "size": asset["size"],
            "sha256": sha,
        }
        if not versions:
            info = inspect_ipa(url, sha, asset["size"])
            if info.get("CFBundleIdentifier") != BUNDLE_ID:
                fail(f"Unexpected bundle ID: {info.get('CFBundleIdentifier')}")
            entry["version"] = info.get("CFBundleShortVersionString", entry["version"])
            entry["buildVersion"] = str(info.get("CFBundleVersion", ""))
            if min_os := info.get("MinimumOSVersion"):
                entry["minOSVersion"] = min_os
        versions.append(entry)
        if len(versions) == KEEP_VERSIONS:
            break

    if not versions:
        fail("No releases with an iOS IPA found")

    source = {
        "name": "Plezy",
        "identifier": "plezy.self-hosted-source",
        "subtitle": "Self-built source for the official Plezy IPA",
        "sourceURL": SOURCE_URL,
        "apps": [{
            "name": "Plezy",
            "bundleIdentifier": BUNDLE_ID,
            "developerName": owner,
            "subtitle": "Plex & Jellyfin client",
            "localizedDescription": f"Official IPA from github.com/{UPSTREAM}/releases, unchanged.",
            "iconURL": f"https://raw.githubusercontent.com/{UPSTREAM}/main/assets/plezy.png",
            "tintColor": "#1e2327",
            "size": versions[0]["size"],
            "versions": versions,
        }],
        "news": [],
    }
    with open(OUT, "w") as f:
        json.dump(source, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {OUT}: {', '.join(v['version'] for v in versions)}")


if __name__ == "__main__":
    main()
