import json

import httpx
import pytest

from agent import memory


@pytest.fixture(autouse=True)
def local_store(tmp_path, monkeypatch):
    monkeypatch.delenv("SURREAL_MEMORY_URL", raising=False)
    monkeypatch.delenv("SURREAL_MEMORY_TOKEN", raising=False)
    monkeypatch.setattr(memory, "LOCAL", tmp_path / ".memory.json")


def _supersede_roundtrip():
    first = memory.remember("TASSOS 9408695", {"flag": "Panama", "name": "TASSOS"}, "https://a", "2026-01-01T00:00:00Z")
    assert first == []  # nothing to compare against yet
    changes = memory.remember("TASSOS 9408695", {"flag": "Cameroon", "name": "tassos"}, "https://b", "2026-10-16T12:00:00Z")
    assert changes == [{"field": "flag", "old": "Panama", "new": "Cameroon", "old_observed_at": "2026-01-01T00:00:00Z"}]
    hist = memory.recall("TASSOS 9408695")
    flags = [h for h in hist if h["field"] == "flag"]
    assert [(h["value"], h["source"], h["superseded_at"]) for h in flags] == [
        ("Panama", "https://a", "2026-10-16T12:00:00Z"),
        ("Cameroon", "https://b", None),
    ]
    assert len([h for h in hist if h["field"] == "name"]) == 1  # same value (case-insensitive) not duplicated


def test_supersede_local():
    _supersede_roundtrip()
    assert memory.recall("someone else") == []


def test_supersede_agent_memory(monkeypatch):
    stored, labels_seen = [], []

    def handler(req):
        assert req.headers["Authorization"] == "Bearer tok"
        body = json.loads(req.content)
        if req.url.path == "/api/v1/flagstate/facts":
            assert body["infer"] == "none"
            stored.append(body)
            return httpx.Response(200, json={"mode": "none", "session_id": "x", "chunk_id": "c"})
        assert req.url.path == "/api/v1/flagstate/query"
        labels_seen.append(body["labels"])
        hits = [{"id": "c", "score": 1, "source": "memory_chunk", "text": s["text"]}
                for s in stored if body["labels"][0] in s["labels"]]
        return httpx.Response(200, json={"hits": hits})

    monkeypatch.setenv("SURREAL_MEMORY_URL", "https://mem.example")
    monkeypatch.setenv("SURREAL_MEMORY_TOKEN", "tok")
    real = memory._client
    monkeypatch.setattr(memory, "_client", lambda: httpx.Client(
        base_url=real().base_url, headers={"Authorization": "Bearer tok"}, transport=httpx.MockTransport(handler)))
    _supersede_roundtrip()
    assert labels_seen[0] == ["subject=tassos-9408695"]
    assert not memory.LOCAL.exists()  # remote path used, no silent fallback
