from pathlib import Path

import pytest

from opensanctions import listed_by, parse

DATA = (Path(__file__).parent / "fixtures" / "opensanctions.csv").read_bytes()


def by_id():
    return {e[0]: e for e in parse(DATA)}


def test_vessel_entity():
    assert by_id()["NK-k837moN9ssPZedvkRUrexG"] == [
        "NK-k837moN9ssPZedvkRUrexG", "Vessel", "9408695", "Canada, EU, UK, Switzerland, US", ["TASSOS"]]


def test_crypto_wallet_excluded():
    assert "NK-2H2gpQcac5QXNqnqCAo4Ac" not in by_id()


def test_no_programs_falls_back_to_dataset():
    assert by_id()["NK-3ESKKNkMKAVpMn9qSkndK7"][3].startswith("Polish List of Persons and Entities Subject to Sanctions")


def test_names_capped():
    e = by_id()["NK-29yBcCujk3eUQYPDa9adAv"]
    assert len(e[4]) == 6 and e[4][0] == "Umar Siddique Kathio AZMARAI" and e[3] == "US"


def test_wrong_shape():
    head, _, rest = DATA.decode().partition("\n")
    bad = (head.replace("program_ids", "programs") + "\n" + rest).encode()
    with pytest.raises(ValueError, match="missing columns"):
        parse(bad)


def test_listed_by():
    assert listed_by("XX-NEW;EU-RUS", "") == "XX, EU"
    assert listed_by("", "") == ""
