import json
from pathlib import Path

import build_official_lists as b
import smoke_lists as s
from test_build_official_lists import fixture_fetch


def make_root(tmp_path: Path) -> Path:
    b.main(fixture_fetch, tmp_path / "data" / "lists", "2026-10-13T04:00:00Z")
    (tmp_path / "data" / "research-index.json").write_text(json.dumps({"entries": [{"name": "TASSOS"}]}))
    return tmp_path


def test_passes_on_good_data(tmp_path):
    assert s.check(make_root(tmp_path)) == []


def test_reports_missing_sample(tmp_path):
    root = make_root(tmp_path)
    path = root / "data" / "lists" / "uk.json"
    doc = json.loads(path.read_text())
    doc["records"] = [r for r in doc["records"] if r[0] != "TASSOS"]
    path.write_text(json.dumps(doc))
    assert s.check(root) == ["uk: sample 'TASSOS' not found"]


def test_reports_unreadable_file(tmp_path):
    root = make_root(tmp_path)
    (root / "data" / "lists" / "eu.json").write_text("{not json")
    problems = s.check(root)
    assert len(problems) == 1 and problems[0].startswith("eu: cannot load eu.json")


def test_reports_missing_research_index(tmp_path):
    root = make_root(tmp_path)
    (root / "data" / "research-index.json").unlink()
    assert s.check(root)[0].startswith("research-index.json:")
