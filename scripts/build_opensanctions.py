"""Nightly: download OpenSanctions' sanctions data and write the compact index.

Writes build/opensanctions.json.gz (uploaded to the data-latest release by the
workflow) and data/opensanctions-meta.json (committed). Exits 1 and leaves the
index unwritten when the download fails, the file has the wrong shape, the sample
ship is missing, or the entity count falls more than 20% below the last good build.
"""
from __future__ import annotations

import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import opensanctions as osx
from build_official_lists import SHRINK_LIMIT, fetch
from normalize import normalize_name

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "build" / "opensanctions.json.gz"
META = ROOT / "data" / "opensanctions-meta.json"
SAMPLE = "TASSOS"


def _write_meta(path: Path, meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def build(fetch_fn=fetch, index_path: Path = INDEX, meta_path: Path = META, now: str | None = None) -> int:
    now = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    index_path, meta_path = Path(index_path), Path(meta_path)
    try:
        previous = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    base = {"label": "OpenSanctions", "source_url": osx.PAGE_URL, "checked_at": now}
    try:
        entities = osx.parse(fetch_fn(osx.SOURCE_URL))
        if not entities:
            raise ValueError("no entities")
        prev_count = previous.get("record_count") or 0
        if prev_count and len(entities) < SHRINK_LIMIT * prev_count:
            raise ValueError(f"shrank from {prev_count} to {len(entities)} entities")
        sample = normalize_name(SAMPLE)
        if not any(normalize_name(n) == sample for e in entities for n in e[4]):
            raise ValueError(f"sample {SAMPLE!r} not found")
    except Exception as exc:  # keep yesterday's release asset
        _write_meta(meta_path, {**base, "status": "kept-previous", "error": f"{type(exc).__name__}: {exc}",
                                "updated_at": previous.get("updated_at"), "record_count": previous.get("record_count", 0)})
        print(f"opensanctions: kept-previous - {type(exc).__name__}: {exc}")
        return 1
    index_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"updated_at": now, "entities": entities}, ensure_ascii=False, separators=(",", ":"))
    index_path.write_bytes(gzip.compress(payload.encode("utf-8"), 9))
    _write_meta(meta_path, {**base, "status": "fresh", "updated_at": now, "record_count": len(entities)})
    print(f"opensanctions: fresh ({len(entities)} entities)")
    return 0


if __name__ == "__main__":
    sys.exit(build())
