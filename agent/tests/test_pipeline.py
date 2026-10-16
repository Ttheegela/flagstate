import types

import pytest

from agent import llm, pipeline, sandbox


@pytest.fixture
def offline(monkeypatch):
    """Stub the tools agent's modules and force local fallbacks for sponsors."""
    remembered = {}
    memory = types.SimpleNamespace(
        recall=lambda subject: [{"field": "flag", "value": "Liberia", "source": "s", "observed_at": "2026-10-01", "superseded_at": None}],
        remember=lambda subject, facts, source, observed_at: remembered.update({subject: facts}) or
        [{"field": "flag", "old": "Liberia", "new": facts.get("flag"), "old_observed_at": "2026-10-01"}],
    )
    browse = types.SimpleNamespace(fetch_live=lambda q, imo=None, on_live_view=None: {
        "facts": {"flag": "Cameroon"}, "sources": ["https://live.example/tassos"], "live_view_url": None, "available": True})
    mods = {"memory": memory, "browse": browse}
    monkeypatch.setattr(pipeline, "_mod", lambda name: mods.get(name))
    monkeypatch.setattr(sandbox, "run_analysis", lambda p: sandbox._local(p))
    monkeypatch.setattr(llm, "_creds_available", lambda: False)
    return mods, remembered


def test_full_pipeline(offline):
    _, remembered = offline
    seen = []
    res = pipeline.investigate("TASSOS", seen.append)
    assert [s["name"] for s in res["steps"]] == list(pipeline.STEPS)
    assert all(s["status"] == "done" for s in res["steps"]), res["steps"]
    assert len(seen) == 2 * len(pipeline.STEPS)
    assert remembered == {"IMO9408695": {"flag": "Cameroon"}}
    assert res["analysis"]["risk"] == "high" and res["analysis"]["ran_in"] == "local"
    assert res["briefing"]["text"] and res["briefing"]["claims"]
    assert res["eval"]["score"] == 1.0 and res["eval"]["label"] == "grounded"


def test_failing_step_does_not_kill_job(offline, monkeypatch):
    mods, _ = offline

    def boom(q, imo=None):
        raise RuntimeError("anchor down")

    mods["browse"] = types.SimpleNamespace(fetch_live=boom)
    del mods["memory"]
    res = pipeline.investigate("TASSOS")
    status = {s["name"]: s["status"] for s in res["steps"]}
    assert status["browse"] == "error" and status["recall"] == "skipped" and status["remember"] == "skipped"
    assert status["brief"] == "done" and res["briefing"]["text"]


def test_grounding_eval_counts_ungrounded_claims():
    ctx = {"x": "https://a.example"}
    ev = pipeline.grounding_eval({"claims": [{"text": "a", "source": "https://a.example"},
                                             {"text": "b", "source": "https://made.up"}]}, ctx)
    assert ev["score"] == 0.5 and ev["label"] == "partially_grounded"
