import json
from pathlib import Path

import build_official_lists as b

FIX = Path(__file__).parent / "fixtures"
FILES = {"us": "us.csv", "uk": "uk.csv", "eu": "eu.csv", "un": "un.xml"}
DAY1 = "2026-10-12T04:00:00Z"
DAY2 = "2026-10-13T04:00:00Z"


def fixture_fetch(url):
    for list_id, meta in b.LISTS.items():
        if meta["download"] == url:
            return (FIX / FILES[list_id]).read_bytes()
    raise AssertionError(f"unexpected url {url}")


def read_meta(out):
    return json.loads((out / "meta.json").read_text())["lists"]


def test_all_lists_fresh(tmp_path):
    assert b.main(fixture_fetch, tmp_path, DAY1) == 0
    meta = read_meta(tmp_path)
    assert {m["status"] for m in meta.values()} == {"fresh"}
    assert meta["uk"]["updated_at"] == DAY1
    us = json.loads((tmp_path / "us.json").read_text())
    assert any(r[0] == "TASSOS" for r in us["records"])


def test_unchanged_data_leaves_list_file_identical(tmp_path):
    b.main(fixture_fetch, tmp_path, DAY1)
    before = (tmp_path / "eu.json").read_bytes()
    b.main(fixture_fetch, tmp_path, DAY2)
    assert (tmp_path / "eu.json").read_bytes() == before
    assert read_meta(tmp_path)["eu"]["checked_at"] == DAY2


def test_failed_download_keeps_previous_and_others_still_update(tmp_path):
    b.main(fixture_fetch, tmp_path, DAY1)
    before = (tmp_path / "uk.json").read_text()

    def broken(url):
        if url == b.LISTS["uk"]["download"]:
            raise OSError("timed out")
        return fixture_fetch(url)

    assert b.main(broken, tmp_path, DAY2) == 1
    meta = read_meta(tmp_path)
    assert meta["uk"]["status"] == "kept-previous"
    assert meta["uk"]["updated_at"] == DAY1
    assert "timed out" in meta["uk"]["error"]
    assert (tmp_path / "uk.json").read_text() == before
    assert meta["us"]["status"] == "fresh" and meta["us"]["updated_at"] == DAY2


def test_shrunken_list_is_rejected(tmp_path):
    b.main(fixture_fetch, tmp_path, DAY1)
    path = tmp_path / "un.json"
    doc = json.loads(path.read_text())
    doc["records"] = doc["records"] * 10
    path.write_text(json.dumps(doc))
    assert b.main(fixture_fetch, tmp_path, DAY2) == 1
    meta = read_meta(tmp_path)["un"]
    assert meta["status"] == "kept-previous"
    assert "shrank" in meta["error"]
    assert len(json.loads(path.read_text())["records"]) == len(doc["records"])


def test_wrong_shape_with_no_previous_file(tmp_path):
    def bad(url):
        if url == b.LISTS["us"]["download"]:
            return b"<html>maintenance</html>"
        return fixture_fetch(url)

    assert b.main(bad, tmp_path, DAY1) == 1
    meta = read_meta(tmp_path)["us"]
    assert meta["status"] == "kept-previous"
    assert meta["updated_at"] is None
    assert meta["record_count"] == 0
    assert not (tmp_path / "us.json").exists()


def test_corrupt_previous_files_are_treated_as_absent(tmp_path):
    (tmp_path / "un.json").write_text("{not json")
    (tmp_path / "meta.json").write_text("{not json")
    assert b.main(fixture_fetch, tmp_path, DAY1) == 0
    assert {m["status"] for m in read_meta(tmp_path).values()} == {"fresh"}
