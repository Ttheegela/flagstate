"""The synthetic Scribe samples, checked offline through the pasted-transcript path."""
from pathlib import Path

import pytest

from agent import scribe

SAMPLES = Path(__file__).parent / "fixtures" / "scribe"

EXPECTED = {
    "1_news_segment": {"TASSOS": ("imo", ["Front Balder"]), "MERU": ("imo", []), "SOVCOMFLOT": ("possible", [])},
    "2_vhf_radio_call": {"MARIA": ("imo", ["Lev Yashin"]), "ENISEY": ("name", ["Federal Baffin"])},
    "3_press_briefing": {"SOVCOMFLOT": ("possible", []), "TORONTO": ("possible", ["Galloper"]),
                         "IMMANUEL": ("possible", ["Energizer"]), "AAYAT SHIP MANAGEMENT PRIVATE LIMITED": ("name", []),
                         "Admiral Group": ("name", []), "Aleksandr Valeryevich Dyukov": ("name", [])},
    "4_court_hearing": {"SKIF-V": ("imo", []), "Ali Rakhbarmadani": ("name", []), "IMO 1234567": ("imo", [])},
    "5_false_positives": {},
}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_sample(name):
    text = (SAMPLES / f"{name}.txt").read_text(encoding="utf-8")
    r = scribe.check_text(text)
    assert {e["name"]: (e["confidence"], e["heard_as"]) for e in r["entities"]} == EXPECTED[name]
    assert len(r["segments"]) == text.strip().count("\n\n") + 1


def test_every_script_has_a_recording():
    assert {p.stem for p in SAMPLES.glob("*.txt")} == {p.stem for p in SAMPLES.glob("*.mp3")} == set(EXPECTED)
