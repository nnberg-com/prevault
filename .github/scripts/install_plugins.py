#!/usr/bin/env python3

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


PLUGINS_DIR = Path(".obsidian/plugins")
COMMUNITY_PLUGINS_FILE = Path(".obsidian/community-plugins.json")

REGISTRY_URL = (
    "https://raw.githubusercontent.com/"
    "obsidianmd/obsidian-releases/master/community-plugins.json"
)

GITHUB_API = "https://api.github.com"

PLUGIN_FILES = ("manifest.json", "main.js", "styles.css")


def request(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "prevault-build",
    }

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return urllib.request.Request(url, headers=headers)


def get_json(url):
    with urllib.request.urlopen(request(url)) as response:
        return json.load(response)


def download(url, destination):
    with urllib.request.urlopen(request(url)) as response:
        destination.write_bytes(response.read())


def main():
    if not PLUGINS_DIR.is_dir():
        print(f"Plugin directory not found: {PLUGINS_DIR}", file=sys.stderr)
        return 1

    plugin_ids = sorted(
        path.name
        for path in PLUGINS_DIR.iterdir()
        if path.is_dir()
    )

    print(f"Plugins: {', '.join(plugin_ids)}")

    registry = get_json(REGISTRY_URL)

    plugins_by_id = {
        plugin["id"]: plugin
        for plugin in registry
    }

    installed_plugin_ids = []

    for plugin_id in plugin_ids:
        print()
        print(f"Installing {plugin_id}")

        plugin = plugins_by_id.get(plugin_id)

        if plugin is None:
            print(
                f"Plugin not found in Obsidian registry: {plugin_id}",
                file=sys.stderr,
            )
            continue

        repo = plugin["repo"]
        print(f"  Repository: {repo}")

        release = get_json(
            f"{GITHUB_API}/repos/{repo}/releases/latest"
        )

        print(f"  Release: {release['tag_name']}")

        assets = {
            asset["name"]: asset["browser_download_url"]
            for asset in release["assets"]
        }

        plugin_dir = PLUGINS_DIR / plugin_id

        for filename in PLUGIN_FILES:
            url = assets.get(filename)

            if url is None:
                if filename == "styles.css":
                    print("  styles.css: not present")
                    continue

                print(
                    f"Required release asset missing: "
                    f"{repo} / {filename}",
                    file=sys.stderr,
                )
                return 1

            print(f"  Downloading {filename}")
            download(url, plugin_dir / filename)

        installed_plugin_ids.append(plugin_id)

    COMMUNITY_PLUGINS_FILE.write_text(
        json.dumps(installed_plugin_ids, indent=2) + "\n",
        encoding="utf-8",
    )

    print()
    print(f"Wrote {COMMUNITY_PLUGINS_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
