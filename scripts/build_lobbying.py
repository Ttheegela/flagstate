"""Nightly: pull US lobbying filings for the tracked clients and write the lobbying asset.

Writes build/lobbying.json.gz (uploaded to the data-latest release by the workflow) and
data/lobbying-meta.json (committed). Exits 1 and leaves the asset unwritten when the pull
fails, the number of filings kept falls more than 20% below the last good build, or Nord
Stream 2 no longer has a lobbying link.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import lobbying
from asset_build import build_asset

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "data" / "lobbying-clients.json"
BRIDGES = ROOT / "data" / "lobbying-bridges.json"
ASSET = ROOT / "build" / "lobbying.json.gz"
META = ROOT / "data" / "lobbying-meta.json"
PAGE_URL = "https://lda.gov/api/redoc/v1/"  # the API the filings come from
SAMPLE = "Nord Stream 2 AG has a lobbying firm"


def produce(get, sleep) -> dict:
    config = lobbying.load_config(CONFIG)
    filings = lobbying.fetch_filings(config["queries"], get=get, sleep=sleep)
    out = lobbying.extract(filings, config)
    bridges = json.loads(BRIDGES.read_text(encoding="utf-8"))
    out["bridges"] = {"links": bridges["links"], "no_lobbying_found": bridges["no_lobbying_found"]}
    out["exclude_lobbyists"] = config["exclude_lobbyists"]
    return out


def has_nord_stream_firm(asset: dict) -> bool:
    return any(e["type"] in ("hired", "lobbied_in_house") and e["source"] == "co:nord-stream-2" for e in asset["edges"])


def build(get=lobbying.get_json, sleep=time.sleep, asset_path: Path = ASSET, meta_path: Path = META, now: str | None = None) -> int:
    return build_asset(
        label="US lobbying (LDA)", page_url=PAGE_URL, produce=lambda: produce(get, sleep),
        count=lambda a: a["filings_kept"], sample_ok=has_nord_stream_firm, sample_name=SAMPLE,
        asset_path=asset_path, meta_path=meta_path, now=now,
    )


if __name__ == "__main__":
    sys.exit(build())
