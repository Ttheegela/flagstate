"""Regenerate the .mp3 recordings from the .txt scripts with ElevenLabs TTS, one voice per speaker.
Speaker labels are not spoken, so Scribe has to tell the speakers apart by voice.

    agent/.venv/bin/python agent/tests/fixtures/scribe/make_audio.py   # from the repo root, needs ELEVENLABS_API_KEY
"""
from pathlib import Path

from elevenlabs.client import ElevenLabs

from agent.config import env

HERE = Path(__file__).resolve().parent
VOICES = ["JBFqnCBsd6RMkjVDRZzb", "21m00Tcm4TlvDq8ikWAM", "pNInz6obpgDQGcFmaJgB", "EXAVITQu4vr4xnAAsxzK"]  # George, Rachel, Adam, Bella


def main():
    client = ElevenLabs(api_key=env("ELEVENLABS_API_KEY"))
    for script in sorted(HERE.glob("*.txt")):
        turns = [t.split(":", 1) for t in script.read_text(encoding="utf-8").strip().split("\n\n")]
        roles = list(dict.fromkeys(role.strip() for role, _ in turns))
        audio = b"".join(
            b"".join(client.text_to_speech.convert(VOICES[roles.index(role.strip()) % len(VOICES)], text=text.strip(),
                                                   model_id="eleven_multilingual_v2", output_format="mp3_44100_128"))
            for role, text in turns)
        script.with_suffix(".mp3").write_bytes(audio)
        print(script.with_suffix(".mp3").name, f"{len(audio) // 1024} KB", roles)


if __name__ == "__main__":
    main()
