from collections import Counter
from pathlib import Path

import pytest

from lists import LISTS, PARSERS, plain_program

FIX = Path(__file__).parent / "fixtures"
FILES = {"us": "us.csv", "uk": "uk.csv", "eu": "eu.csv", "un": "un.xml"}


def load(list_id):
    return PARSERS[list_id]((FIX / FILES[list_id]).read_bytes())


def only(records, name):
    found = [r for r in records if r[0] == name]
    assert found, f"{name} not found"
    return found[0]


def test_every_record_has_seven_fields_and_a_normalised_name():
    for list_id in LISTS:
        for record in load(list_id):
            assert len(record) == 7
            assert record[1]


def test_us_tassos():
    r = only(load("us"), "TASSOS")
    assert r[1:] == ["TASSOS", "Iran", "", "54815", "9408695", ""]


def test_us_alt_names_become_their_own_records():
    refs = Counter(r[4] for r in load("us"))
    assert max(refs.values()) >= 2


def test_uk_tassos():
    r = only(load("uk"), "TASSOS")
    assert r[1:] == ["TASSOS", "Russia", "2026-02-24", "RUS3483", "9408695", ""]


def test_uk_without_banner_line_is_rejected():
    raw = (FIX / "uk.csv").read_bytes().split(b"\n", 1)[1]
    with pytest.raises(ValueError, match="Report Date"):
        PARSERS["uk"](raw)


def test_eu_entity_13():
    r = only(load("eu"), "Saddam Hussein Al-Tikriti")
    assert r[1] == "SADDAM HUSSEIN AL TIKRITI"
    assert r[2] == "Iraq"
    assert r[4] == "13"
    assert r[6].startswith("http")


def test_eu_rows_are_deduplicated_per_entity_and_name():
    keys = [(r[4], r[1]) for r in load("eu")]
    assert len(keys) == len(set(keys))


def test_un_first_individual():
    r = only(load("un"), "ERIC BADEGE")
    assert r[2] == "DR Congo"
    assert r[3] == "2012-12-31"


def test_missing_column_is_rejected():
    raw = (FIX / "us.csv").read_bytes().replace(b"alt_names", b"other_names", 1)
    with pytest.raises(ValueError, match="missing columns"):
        PARSERS["us"](raw)


def test_garbage_xml_is_rejected():
    with pytest.raises(ValueError):
        PARSERS["un"](b"<html>Service unavailable</html>")


@pytest.mark.parametrize("raw,list_id,expected", [
    ("IRAN-EO13902", "us", "Iran"),
    ("RUSSIA-EO14024; UKRAINE-EO13662", "us", "Russia, Russia/Ukraine"),
    ("SDGT", "us", "Terrorism"),
    ("CMIC-EO13959", "us", "Chinese military companies"),
    ("SDNT", "us", "Narcotics"),
    ("IRAQ2", "us", "Iraq"),
    ("XYZ-NEW", "us", "XYZ-NEW"),
    ("IRQ", "eu", "Iraq"),
    ("UKR", "eu", "Russia/Ukraine"),
    ("DRC", "un", "DR Congo"),
    ("Taliban", "un", "Taliban"),
])
def test_plain_program(raw, list_id, expected):
    assert plain_program(raw, list_id) == expected
