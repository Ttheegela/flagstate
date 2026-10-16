import pytest

from agent import voice


def test_no_key_raises(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(voice.VoiceUnavailable, match="no ELEVENLABS_API_KEY"):
        voice.tts("hello")


def test_returns_mp3_bytes(monkeypatch):
    seen = {}

    class FakeTTS:
        def convert(self, voice_id, *, text, model_id, output_format):
            seen.update(voice_id=voice_id, text=text, model_id=model_id)
            return iter([b"ID3", b"\x00mp3"])

    class FakeClient:
        def __init__(self, api_key):
            self.text_to_speech = FakeTTS()

    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
    monkeypatch.setattr(voice, "ElevenLabs", FakeClient)
    assert voice.tts("TASSOS changed flag") == b"ID3\x00mp3"
    assert seen == {"voice_id": voice.DEFAULT_VOICE, "text": "TASSOS changed flag", "model_id": "eleven_flash_v2_5"}


def test_api_error_maps_to_unavailable(monkeypatch):
    class Boom:
        def __init__(self, api_key):
            raise RuntimeError("quota")

    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setattr(voice, "ElevenLabs", Boom)
    with pytest.raises(voice.VoiceUnavailable):
        voice.tts("x")
