import gzip
import json
from pathlib import Path

import build_lobbying as b

FIX = json.loads((Path(__file__).parent / "fixtures" / "lda_nord_stream_2.json").read_text(encoding="utf-8"))
NOW = "2026-10-14T04:00:00Z"


def fake_get(url):
    # Every query returns the same Nord Stream 2 page with no next link.
    return {**FIX, "next": None}


def no_sleep(seconds):
    pass


def test_fresh_build(tmp_path):
    asset, meta = tmp_path / "l.json.gz", tmp_path / "m.json"
    assert b.build(fake_get, no_sleep, asset, meta, NOW) == 0
    doc = json.loads(gzip.decompress(asset.read_bytes()))
    assert any(e["type"] in ("hired", "lobbied_in_house") and e["source"] == "co:nord-stream-2" for e in doc["edges"])
    assert len(doc["bridges"]["links"]) == 18
    assert "Sovcomflot" in doc["bridges"]["no_lobbying_found"]
    assert doc["exclude_lobbyists"] == []
    m = json.loads(meta.read_text())
    assert m["status"] == "fresh" and m["record_count"] == doc["filings_kept"]


def test_fetch_failure_keeps_previous(tmp_path):
    asset, meta = tmp_path / "l.json.gz", tmp_path / "m.json"

    def broken(url):
        raise RuntimeError("giving up on " + url)

    assert b.build(broken, no_sleep, asset, meta, NOW) == 1
    assert not asset.exists()
    assert "giving up" in json.loads(meta.read_text())["error"]


def test_shrink_rejected(tmp_path):
    asset, meta = tmp_path / "l.json.gz", tmp_path / "m.json"
    meta.write_text(json.dumps({"record_count": 100000}))
    assert b.build(fake_get, no_sleep, asset, meta, NOW) == 1
    assert "shrank" in json.loads(meta.read_text())["error"]


def test_missing_sample_rejected(tmp_path):
    asset, meta = tmp_path / "l.json.gz", tmp_path / "m.json"

    def other_client(url):
        page = json.loads(json.dumps(FIX))
        for r in page["results"]:
            r["client"]["name"] = "HUAWEI TECHNOLOGIES USA"
        return {**page, "next": None}

    assert b.build(other_client, no_sleep, asset, meta, NOW) == 1
    assert "sample" in json.loads(meta.read_text())["error"]
