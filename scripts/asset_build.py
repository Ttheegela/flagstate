"""Shared nightly-asset build: validate, write a gzipped JSON asset, keep yesterday's on failure.

produce() returns the asset dict and raises on any download or parse problem.
count(asset) is the size compared against the last good build (20% shrink limit).
sample_ok(asset) must be true. On any failure the asset file is not written and
meta records "kept-previous"; on success meta records "fresh".
"""
from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

SHRINK_LIMIT = 0.8


def _write_meta(path: Path, meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def build_asset(*, label, page_url, produce, count, sample_ok, sample_name, asset_path, meta_path, now=None) -> int:
    now = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    asset_path, meta_path = Path(asset_path), Path(meta_path)
    try:
        previous = json.loads(meta_path.read_text(encoding="utf-8"))
        if not isinstance(previous, dict):
            previous = {}
    except (OSError, ValueError):
        previous = {}
    base = {"label": label, "source_url": page_url, "checked_at": now}
    try:
        asset = produce()
        size = count(asset)
        if not size:
            raise ValueError("empty asset")
        prev_count = previous.get("record_count") or 0
        if prev_count and size < SHRINK_LIMIT * prev_count:
            raise ValueError(f"shrank from {prev_count} to {size}")
        if not sample_ok(asset):
            raise ValueError(f"sample check failed: {sample_name}")
    except Exception as exc:  # keep yesterday's release asset
        _write_meta(meta_path, {**base, "status": "kept-previous", "error": f"{type(exc).__name__}: {exc}",
                                "updated_at": previous.get("updated_at"), "record_count": previous.get("record_count", 0)})
        print(f"{label}: kept-previous - {type(exc).__name__}: {exc}")
        return 1
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"updated_at": now, **asset}, ensure_ascii=False, separators=(",", ":"))
    asset_path.write_bytes(gzip.compress(payload.encode("utf-8"), 9))
    _write_meta(meta_path, {**base, "status": "fresh", "updated_at": now, "record_count": size})
    print(f"{label}: fresh ({size})")
    return 0
