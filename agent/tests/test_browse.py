import json
from pathlib import Path

import httpx

from agent import browse

PAGE = (Path(__file__).parent / "fixtures" / "vesselfinder_9408695.html").read_text()


def _mock(monkeypatch, handler):
    monkeypatch.setenv("ANCHOR_API_KEY", "test-key")
    monkeypatch.setattr(browse, "_client", lambda key: httpx.Client(
        base_url=browse.API, headers={"anchor-api-key": key}, transport=httpx.MockTransport(handler)))


def test_no_key(monkeypatch):
    monkeypatch.delenv("ANCHOR_API_KEY", raising=False)
    out = browse.fetch_live("TASSOS", imo="9408695")
    assert out["available"] is False and out["reason"] == "no ANCHOR_API_KEY"
    assert out["facts"] == {} and out["sources"] == []


def test_parse_vesselfinder_fixture():
    f = browse.parse_vessel(PAGE)
    assert f["name"] == "TASSOS" and f["imo"] == "9408695" and f["mmsi"] == "613442805"
    assert f["flag"] == "Cameroon"  # AIS flag; particulars "Flag: Unknown" is skipped
    assert f["ship_type"] == "Crude Oil Tanker" and f["year_built"] == "2009"
    assert f["last_position_at"] == "Aug 18, 2026 21:23 UTC"
    assert "destination" not in f  # "Destination not available"


def test_web_unlocker_route(monkeypatch):
    calls = []

    def handler(req):
        calls.append(req.url.path)
        assert req.headers["anchor-api-key"] == "test-key"
        assert json.loads(req.content)["url"] == "https://www.vesselfinder.com/vessels/details/9408695"
        return httpx.Response(200, text=PAGE)

    _mock(monkeypatch, handler)
    out = browse.fetch_live("TASSOS", imo="9408695")
    assert calls == ["/v1/tools/fetch/webpage"]
    assert out["available"] and out["method"] == "web_unlocker" and out["facts"]["flag"] == "Cameroon"
    assert out["sources"] == ["https://www.vesselfinder.com/vessels/details/9408695"]


def test_ai_task_fallback_deletes_session(monkeypatch):
    calls, seen_live = [], []

    def handler(req):
        calls.append((req.method, req.url.path))
        if req.url.path == "/v1/tools/fetch/webpage":
            return httpx.Response(403, text="blocked")
        if req.url.path == "/v1/sessions":
            assert json.loads(req.content)["session"]["proxy"]["active"] is True
            return httpx.Response(200, json={"data": {"id": "s1", "cdp_url": "wss://secret", "live_view_url": "https://live/s1"}})
        if req.url.path == "/v1/tools/perform-web-task":
            assert req.url.params["sessionId"] == "s1"
            return httpx.Response(200, json={"data": {"result": json.dumps({"name": "TASSOS", "flag": "Cameroon", "manager": None})}})
        return httpx.Response(200, json={})

    _mock(monkeypatch, handler)
    out = browse.fetch_live("TASSOS", imo="9408695", on_live_view=seen_live.append)
    assert out["method"] == "ai_task" and out["facts"] == {"name": "TASSOS", "flag": "Cameroon"}
    assert out["live_view_url"] == "https://live/s1" and seen_live == ["https://live/s1"]
    assert ("DELETE", "/v1/sessions/s1") in calls
    assert "secret" not in json.dumps(out)
