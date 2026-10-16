import json

import pytest

from agent import llm


def _converse_response(payload: dict):
    return {"output": {"message": {"content": [{"text": json.dumps(payload)}]}}}


class FakeBedrock:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    class exceptions:
        class ValidationException(Exception):
            pass

    def converse(self, modelId, **kwargs):
        self.calls.append({"modelId": modelId, **kwargs})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


BRIEFING = {"text": "TASSOS is Liberia-flagged.", "claims": [{"text": "flagged Liberia", "source": "https://a.example"}]}
CONTEXT = {"lists": [{"url": "https://a.example"}]}


def test_no_claims_skips_the_call():
    ev = llm.judge_faithfulness({"claims": []}, CONTEXT)
    assert ev == {"name": "claims_faithful", "score": 0.0, "label": "no_claims",
                  "explanation": "no claims to judge", "model": None, "available": False}


def test_no_creds_is_unavailable(monkeypatch):
    monkeypatch.setattr(llm, "_creds_available", lambda: False)
    ev = llm.judge_faithfulness(BRIEFING, CONTEXT)
    assert ev["label"] == "unavailable" and ev["score"] is None
    assert "credentials" in ev["explanation"]


def test_judge_call_parses_score_and_label(monkeypatch):
    monkeypatch.setattr(llm, "_creds_available", lambda: True)
    fake = FakeBedrock([_converse_response({"score": 0.5, "label": "partially_faithful", "explanation": "claim 1 overstates it"})])
    monkeypatch.setattr("boto3.client", lambda *a, **k: fake)
    ev = llm.judge_faithfulness(BRIEFING, CONTEXT)
    assert ev == {"name": "claims_faithful", "score": 0.5, "label": "partially_faithful",
                  "explanation": "claim 1 overstates it", "model": llm.DEFAULT_MODEL, "available": True}
    assert fake.calls[0]["modelId"] == llm.DEFAULT_MODEL


def test_judge_retries_with_inference_profile_prefix(monkeypatch):
    monkeypatch.setattr(llm, "_creds_available", lambda: True)
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-x")
    fake = FakeBedrock([FakeBedrock.exceptions.ValidationException("needs an inference profile"),
                        _converse_response({"score": 1.0, "label": "faithful", "explanation": "all good"})])
    monkeypatch.setattr("boto3.client", lambda *a, **k: fake)
    ev = llm.judge_faithfulness(BRIEFING, CONTEXT)
    assert ev["available"] and ev["model"] == "us.anthropic.claude-x"


def test_judge_failure_falls_back_to_unavailable(monkeypatch):
    monkeypatch.setattr(llm, "_creds_available", lambda: True)
    fake = FakeBedrock([RuntimeError("throttled")])
    monkeypatch.setattr("boto3.client", lambda *a, **k: fake)
    ev = llm.judge_faithfulness(BRIEFING, CONTEXT)
    assert ev["label"] == "unavailable" and ev["score"] is None
    assert "throttled" in ev["explanation"]
