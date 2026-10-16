"""Nightly: build the sanctions-connections asset from OpenSanctions' relationship data.

Writes build/connections.json.gz (uploaded to the data-latest release by the workflow)
and data/connections-meta.json (committed). Exits 1 and leaves the asset unwritten when
the download fails, the file has the wrong shape, the link count falls more than 20%
below the last good build, or TASSOS is no longer linked to Zulu Ships Management.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

import connections as cx
from asset_build import build_asset
from build_official_lists import USER_AGENT
from normalize import normalize_name

ROOT = Path(__file__).resolve().parent.parent
ASSET = ROOT / "build" / "connections.json.gz"
META = ROOT / "data" / "connections-meta.json"
SAMPLE = "TASSOS (IMO 9408695) linked to Zulu Ships Management"


def fetch_lines(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=300) as response:
        for raw in response:
            yield raw.decode("utf-8")


def tassos_linked_to_zulu(asset: dict) -> bool:
    names = {e[0]: {normalize_name(n) for n in e[2]} for e in asset["entities"]}
    ships = {e[0] for e in asset["entities"] if e[3] == "9408695"}
    target = normalize_name("Zulu Ships Management")
    for subject, obj, *_ in asset["links"]:
        if (subject in ships and target in names.get(obj, set())) or (obj in ships and target in names.get(subject, set())):
            return True
    return False


def build(lines_fn=fetch_lines, asset_path: Path = ASSET, meta_path: Path = META, now: str | None = None) -> int:
    return build_asset(
        label="OpenSanctions connections", page_url=cx.PAGE_URL,
        produce=lambda: cx.parse(lines_fn(cx.SOURCE_URL)), count=lambda a: len(a["links"]),
        sample_ok=tassos_linked_to_zulu, sample_name=SAMPLE,
        asset_path=asset_path, meta_path=meta_path, now=now,
    )


if __name__ == "__main__":
    sys.exit(build())
