"""Download the four official lists and write data/lists/<id>.json plus meta.json.

A list that fails (download error, wrong shape, empty, or more than 20% smaller
than the committed copy) keeps its previous file and is marked "kept-previous".
Exits 1 when any list failed so the nightly workflow can open an issue.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from lists import LISTS, PARSERS

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "lists"
SHRINK_LIMIT = 0.8
USER_AGENT = "Flagstate/1.0 (+https://github.com/Ttheegela/flagstate)"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def build_one(list_id: str, fetch_fn, out_dir: Path, now: str, previous_meta: dict) -> dict:
    path = out_dir / f"{list_id}.json"
    try:
        prev_records = json.loads(path.read_text(encoding="utf-8"))["records"]
    except (OSError, ValueError, KeyError, TypeError):  # missing or corrupt previous file counts as absent
        prev_records = None
    base = {"label": LISTS[list_id]["label"], "source_url": LISTS[list_id]["page"], "checked_at": now}
    try:
        records = PARSERS[list_id](fetch_fn(LISTS[list_id]["download"]))
        if not records:
            raise ValueError("no records")
        if prev_records and len(records) < SHRINK_LIMIT * len(prev_records):
            raise ValueError(f"shrank from {len(prev_records)} to {len(records)} records")
    except Exception as exc:  # any failure keeps yesterday's file for this list only
        return {
            **base,
            "status": "kept-previous",
            "error": f"{type(exc).__name__}: {exc}",
            "updated_at": previous_meta.get(list_id, {}).get("updated_at"),
            "record_count": len(prev_records or []),
        }
    text = json.dumps({"list": list_id, "records": records}, ensure_ascii=False, separators=(",", ":"))
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        _write_atomic(path, text)
    return {**base, "status": "fresh", "updated_at": now, "record_count": len(records)}


def main(fetch_fn=fetch, out_dir: Path = OUT_DIR, now: str | None = None) -> int:
    now = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = out_dir / "meta.json"
    try:
        previous = json.loads(meta_path.read_text(encoding="utf-8"))["lists"]
    except (OSError, ValueError, KeyError, TypeError):
        previous = {}
    lists = {list_id: build_one(list_id, fetch_fn, out_dir, now, previous) for list_id in LISTS}
    _write_atomic(meta_path, json.dumps({"lists": lists}, indent=2) + "\n")
    for list_id, meta in lists.items():
        detail = f" - {meta['error']}" if meta.get("error") else ""
        print(f"{list_id}: {meta['status']} ({meta['record_count']} records){detail}")
    return 1 if any(m["status"] != "fresh" for m in lists.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
