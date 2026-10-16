import gzip
import json
from pathlib import Path

import build_connections as b

FIX = Path(__file__).parent / "fixtures" / "opensanctions_entities.jsonl"
NOW = "2026-10-14T04:00:00Z"


def fixture_lines(url):
    assert url == b.cx.SOURCE_URL
    return FIX.read_text(encoding="utf-8").splitlines(keepends=True)


def test_fresh_build(tmp_path):
    asset, meta = tmp_path / "c.json.gz", tmp_path / "m.json"
    assert b.build(fixture_lines, asset, meta, NOW) == 0
    doc = json.loads(gzip.decompress(asset.read_bytes()))
    assert doc["updated_at"] == NOW and doc["links"] and doc["entities"]
    m = json.loads(meta.read_text())
    assert m["status"] == "fresh" and m["record_count"] == len(doc["links"])


def test_download_failure_keeps_previous(tmp_path):
    asset, meta = tmp_path / "c.json.gz", tmp_path / "m.json"

    def broken(url):
        raise OSError("timed out")

    assert b.build(broken, asset, meta, NOW) == 1
    assert not asset.exists()
    assert "timed out" in json.loads(meta.read_text())["error"]


def test_shrink_rejected(tmp_path):
    asset, meta = tmp_path / "c.json.gz", tmp_path / "m.json"
    meta.write_text(json.dumps({"record_count": 100000, "updated_at": "2026-10-13T04:00:00Z"}))
    assert b.build(fixture_lines, asset, meta, NOW) == 1
    m = json.loads(meta.read_text())
    assert "shrank" in m["error"] and m["record_count"] == 100000 and not asset.exists()


def test_missing_sample_rejected(tmp_path):
    asset, meta = tmp_path / "c.json.gz", tmp_path / "m.json"

    def no_tassos(url):
        return [l for l in fixture_lines(url) if "NK-k837moN9ssPZedvkRUrexG" not in l]

    assert b.build(no_tassos, asset, meta, NOW) == 1
    assert "sample" in json.loads(meta.read_text())["error"]


def test_corrupt_previous_meta_is_ignored(tmp_path):
    asset, meta = tmp_path / "c.json.gz", tmp_path / "m.json"
    meta.write_text("{not json")
    assert b.build(fixture_lines, asset, meta, NOW) == 0
