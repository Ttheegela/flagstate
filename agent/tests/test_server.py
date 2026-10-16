import time
import types

from fastapi.testclient import TestClient

from agent import pipeline, server

client = TestClient(server.app)
FAKE = {"briefing": {"text": "TASSOS is sanctioned.", "claims": []},
        "analysis": {"risk": "high", "flags": [{"flag": "on_official_list", "severity": "high", "evidence": "US list", "source": "u"}]}}


def _fake_investigate(query, on_step):
    on_step({"name": "lookup", "status": "done", "detail": "", "ms": 1})
    return {"query": query, **FAKE}


def _wait(job_id):
    for _ in range(100):
        body = client.get(f"/jobs/{job_id}").json()
        if body["status"] != "running":
            return body
        time.sleep(0.02)
    raise AssertionError("job never finished")


def test_health():
    assert client.get("/health").json()["ok"] is True


def test_tools_search():
    body = client.post("/tools/search", json={"query": "TASSOS"}).json()
    assert "TASSOS" in body["say"] and body["imo"] == "9408695"


def test_investigate_job_status_and_audio(monkeypatch):
    monkeypatch.setattr(pipeline, "investigate", _fake_investigate)
    job_id = client.post("/investigate", json={"query": "TASSOS"}).json()["job_id"]
    body = _wait(job_id)
    assert body["status"] == "done" and body["steps"][0]["name"] == "lookup"
    assert body["result"]["briefing"]["text"] == "TASSOS is sanctioned."

    status = client.post("/tools/status", json={"job_id": job_id}).json()
    assert status["say"] == "TASSOS is sanctioned." and status["top_flags"][0]["flag"] == "on_official_list"
    assert client.post("/tools/status", json={}).json()["job_id"] == job_id  # defaults to latest job

    monkeypatch.setattr(pipeline, "_mod", lambda name: types.SimpleNamespace(tts=lambda text: b"ID3fake"))
    audio = client.get(f"/jobs/{job_id}/audio")
    assert audio.status_code == 200 and audio.content == b"ID3fake"


def test_tools_investigate_returns_job(monkeypatch):
    monkeypatch.setattr(pipeline, "investigate", _fake_investigate)
    body = client.post("/tools/investigate", json={"query": "9408695"}).json()
    assert body["job_id"] and "TASSOS" in body["say"]
    _wait(body["job_id"])


def test_unknown_job_404():
    assert client.get("/jobs/nope").status_code == 404
