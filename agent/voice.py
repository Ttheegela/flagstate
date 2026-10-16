"""ElevenLabs text-to-speech: briefing text -> mp3 bytes."""
from __future__ import annotations

from elevenlabs.client import ElevenLabs

from agent.config import env

DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"  # "George", stock voice from the ElevenLabs quickstart
MODEL = "eleven_flash_v2_5"


class VoiceUnavailable(RuntimeError):
    """No key or ElevenLabs failed; server maps this to 503."""


def tts(text: str) -> bytes:
    key = env("ELEVENLABS_API_KEY")
    if not key:
        raise VoiceUnavailable("no ELEVENLABS_API_KEY")
    try:
        audio = ElevenLabs(api_key=key).text_to_speech.convert(
            env("ELEVENLABS_VOICE_ID", DEFAULT_VOICE), text=text, model_id=MODEL, output_format="mp3_44100_128")
        return b"".join(audio)
    except Exception as e:  # quota, bad voice id, network
        raise VoiceUnavailable(f"elevenlabs {type(e).__name__}: {str(e)[:200]}") from e
