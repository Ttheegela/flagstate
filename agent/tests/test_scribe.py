import types

import pytest
from fastapi.testclient import TestClient

from agent import scribe, server

client = TestClient(server.app)


def _entity(result, name):
    return next(e for e in result["entities"] if e["name"] == name)


def test_imo_check_digit():
    assert scribe.imo_valid("9408695") and scribe.imo_valid("9187227")
    assert not scribe.imo_valid("9408696") and not scribe.imo_valid("940869") and not scribe.imo_valid("94O8695")


def test_imo_and_alias_merge_into_one_entity():
    r = scribe.check_text("The tanker Tassos, IMO 9408695, used to sail as Front Balder.")
    assert [e["name"] for e in r["entities"]] == ["TASSOS"]
    tassos = r["entities"][0]
    assert tassos["imo"] == "9408695" and tassos["confidence"] == "imo"
    assert {"United States", "United Kingdom", "European Union"} <= set(tassos["listed_by"])
    assert tassos["heard_as"] == ["Front Balder"] and len(tassos["mentions"]) == 3
    hits = [p["text"] for p in r["segments"][0]["parts"] if "entity" in p]
    assert hits == ["Tassos", "9408695", "Front Balder"]  # trailing punctuation stays outside the mark


def test_spoken_digits_become_an_imo():
    r = scribe.check_text("Next, nine one eight seven two two seven was reflagged.")
    assert _entity(r, "MERU")["mentions"][0]["segment"] == 0


def test_unknown_number_needs_imo_before_it():
    assert scribe.check_text("Call me on 1234567 tomorrow.")["entities"] == []  # valid check digit, but a phone number
    r = scribe.check_text("Please check IMO 1234567 for me.")
    assert r["entities"][0]["name"] == "IMO 1234567" and r["entities"][0]["on_record"] is False


def test_one_word_names_need_a_capital_and_a_cue():
    plain = scribe.check_text("The sun was out, Henry said trust me, Tassos smiled.")
    assert plain["entities"] == []
    assert scribe.check_text("the tanker tassos")["entities"] == []  # no capital: not a name
    cued = scribe.check_text("Today Sovcomflot PJSC denied it.")
    assert _entity(cued, "SOVCOMFLOT")["confidence"] == "possible"


def test_listed_entities_sort_first_and_transcript_follows():
    r = scribe.check_text("Check IMO 1234567. The tanker Tassos was reflagged.")
    assert [e["name"] for e in r["entities"]] == ["TASSOS", "IMO 1234567"]
    marks = [(p["text"], p["entity"]) for s in r["segments"] for p in s["parts"] if "entity" in p]
    assert marks == [("1234567", 1), ("Tassos", 0)]


def test_blank_line_starts_a_new_turn():
    r = scribe.check_text("First paragraph.\n\nSecond paragraph.\r\n\r\nThird.")
    assert [s["parts"][0]["text"] for s in r["segments"]] == ["First paragraph.", "Second paragraph.", "Third."]


def test_keyterms_respect_scribe_limits():
    terms = scribe.keyterms(["Front Balder", "front balder", "x" * 60, "a b c d e f", "Bad [name]"], limit=40)
    assert terms[0] == "Front Balder" and terms[1] == "Bad name" and len(terms) == 40
    assert len({t.casefold() for t in terms}) == len(terms)
    assert all(len(t) < 50 and len(t.split()) <= 5 and not set(t) & set("<>{}[]\\") for t in terms)


def _fake_scribe(monkeypatch, words, seen):
    class FakeSTT:
        def convert(self, **kw):
            seen.update(kw)
            return types.SimpleNamespace(text="t", language_code="eng", audio_duration_secs=9.5,
                                         words=[types.SimpleNamespace(**w) for w in words])

    class FakeClient:
        def __init__(self, api_key):
            self.speech_to_text = FakeSTT()

    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setattr(scribe, "ElevenLabs", FakeClient)


def W(text, start, speaker, kind="word"):
    return {"text": text, "type": kind, "start": start, "end": start + 0.4, "speaker_id": speaker}


WORDS = [W("The", 0.0, "speaker_0"), W(" ", 0.4, "speaker_0", "spacing"), W("tanker", 0.5, "speaker_0"),
         W(" ", 0.9, "speaker_0", "spacing"), W("Tassos?", 1.0, "speaker_0"), W(" ", 1.4, "speaker_0", "spacing"),
         W("Yes,", 2.0, "speaker_1"), W(" ", 2.4, "speaker_1", "spacing"), W("IMO", 2.5, "speaker_1"),
         W(" ", 2.9, "speaker_1", "spacing"), W("9408695.", 3.0, "speaker_1")]


def test_audio_turns_and_timestamps(monkeypatch):
    seen = {}
    _fake_scribe(monkeypatch, WORDS, seen)
    r = scribe.check_audio(b"RIFF", "clip.wav", "audio/wav", hints=["Front Balder"])
    assert seen["diarize"] is True and seen["timestamps_granularity"] == "word" and seen["keyterms"][0] == "Front Balder"
    assert seen["file"] == ("clip.wav", b"RIFF", "audio/wav") and seen["model_id"] == scribe.MODEL
    assert r["duration"] == 9.5 and r["keyterms"] == len(seen["keyterms"])
    assert [(s["speaker"], s["start"], s["end"]) for s in r["segments"]] == [("speaker_0", 0.0, 1.4), ("speaker_1", 2.0, 3.4)]
    assert [m["start"] for m in r["entities"][0]["mentions"]] == [1.0, 3.0]


def test_no_key_is_unavailable(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(scribe.ScribeUnavailable, match="no ELEVENLABS_API_KEY"):
        scribe.transcribe(b"x")


def test_route_text():
    body = client.post("/scribe/text", json={"text": "The tanker Tassos was reflagged."}).json()
    assert body["source"] == "text" and body["entities"][0]["name"] == "TASSOS"
    assert client.post("/scribe/text", json={"text": "  "}).status_code == 400


def test_route_audio(monkeypatch):
    _fake_scribe(monkeypatch, WORDS, {})
    res = client.post("/scribe", files={"file": ("clip.mp3", b"ID3", "audio/mpeg")}, data={"hints": "Front Balder, MERU"})
    assert res.status_code == 200 and res.json()["entities"][0]["name"] == "TASSOS"


def test_route_audio_rejects_bad_uploads(monkeypatch):
    assert client.post("/scribe", files={"file": ("a.txt", b"hi", "text/plain")}).status_code == 415
    assert client.post("/scribe", files={"file": ("a.mp3", b"", "audio/mpeg")}).status_code == 400
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert client.post("/scribe", files={"file": ("a.mp3", b"ID3", "audio/mpeg")}).status_code == 503
