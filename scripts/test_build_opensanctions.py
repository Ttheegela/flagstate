import gzip
import json
from pathlib import Path

import build_opensanctions as b

DATA = (Path(__file__).parent / "fixtures" / "opensanctions.csv").read_bytes()
TASSOS_ID = "NK-k837moN9ssPZedvkRUrexG"
TASSOS = [TASSOS_ID, "Vessel", "9408695", "Canada, EU, UK, Switzerland, US", ["TASSOS"]]


def run(tmp_path, fetch_fn):
    code = b.build(fetch_fn, tmp_path / "idx.json.gz", tmp_path / "meta.json", now="2026-10-14T04:00:00Z")
    meta = json.loads((tmp_path / "meta.json").read_text())
    return code, meta


def test_fresh(tmp_path):
    code, meta = run(tmp_path, lambda url: DATA)
    doc = json.loads(gzip.decompress((tmp_path / "idx.json.gz").read_bytes()))
    assert code == 0 and set(doc) == {"updated_at", "entities"} and TASSOS in doc["entities"]
    assert meta["status"] == "fresh" and meta["record_count"] == len(doc["entities"])


def test_download_failure(tmp_path):
    def boom(url):
        raise OSError("network down")
    code, meta = run(tmp_path, boom)
    assert code == 1 and not (tmp_path / "idx.json.gz").exists()
    assert meta["status"] == "kept-previous" and "network down" in meta["error"]


def test_shrink(tmp_path):
    (tmp_path / "meta.json").write_text(json.dumps({"record_count": 10 * 6, "updated_at": "x"}))
    code, meta = run(tmp_path, lambda url: DATA)
    assert code == 1 and "shrank" in meta["error"] and not (tmp_path / "idx.json.gz").exists()


def test_sample_missing(tmp_path):
    lines = [l for l in DATA.decode().splitlines(keepends=True) if TASSOS_ID not in l]
    code, meta = run(tmp_path, lambda url: "".join(lines).encode())
    assert code == 1 and "sample" in meta["error"]


def test_corrupt_previous_meta(tmp_path):
    (tmp_path / "meta.json").write_text("{not json")
    code, meta = run(tmp_path, lambda url: DATA)
    assert code == 0 and meta["status"] == "fresh"
