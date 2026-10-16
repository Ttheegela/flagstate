import json
from pathlib import Path

import pytest

import connections as cx

FIX = Path(__file__).parent / "fixtures" / "opensanctions_entities.jsonl"
TASSOS = "NK-k837moN9ssPZedvkRUrexG"


@pytest.fixture(scope="module")
def parsed():
    with open(FIX, encoding="utf-8") as f:
        return cx.parse(f)


def ent(parsed, eid):
    return next(e for e in parsed["entities"] if e[0] == eid)


def test_tassos_entity(parsed):
    e = ent(parsed, TASSOS)
    assert e[1] == "Vessel"
    assert e[2][0] == "TASSOS"
    assert e[3] == "9408695"
    assert {"US", "UK"} <= set(e[4])


def test_tassos_is_property_of_zulu(parsed):
    names = {e[0]: e[2][0] for e in parsed["entities"]}
    link = next(l for l in parsed["links"] if l[0] == TASSOS and names[l[1]] == "Zulu Ships Management")
    assert link[2] == "Ownership"
    assert link[3] == "Property in the interest of"
    assert set(link[4]) == {"US", "UK"}


def test_owns_controls_reads_owner_first(parsed):
    link = next(l for l in parsed["links"] if l[3] == "Owns, controls, or operates")
    owner_schema = ent(parsed, link[0])[1]
    assert owner_schema in {"Person", "Company", "Organization", "LegalEntity"}


def test_family_wording_and_latvian_translation(parsed):
    assert any(l[2] == "Family" and l[3] == "Family member of" for l in parsed["links"])
    assert any(l[3] == "Linked to (assets)" for l in parsed["links"])
    assert not any(l[3].startswith("Līdzekļi") for l in parsed["links"])


def test_every_link_endpoint_is_an_entity_and_other_schemas_are_ignored(parsed):
    ids = {e[0] for e in parsed["entities"]}
    assert all(l[0] in ids and l[1] in ids for l in parsed["links"])
    assert {e[1] for e in parsed["entities"]} <= cx.ENTITY_SCHEMAS


def line(**kw):
    return json.dumps(kw)


def test_duplicate_links_merge_authorities():
    lines = [
        line(id="A", schema="Company", caption="Alpha", datasets=["us_ofac_sdn"], properties={}),
        line(id="B", schema="Vessel", caption="Bravo", datasets=["gb_fcdo_sanctions"], properties={"imoNumber": ["1234567"]}),
        line(id="r1", schema="Ownership", caption="", datasets=["us_ofac_sdn"], properties={"owner": ["A"], "asset": ["B"], "role": ["Owned or Controlled By"]}),
        line(id="r2", schema="Ownership", caption="", datasets=["gb_fcdo_sanctions"], properties={"owner": ["A"], "asset": ["B"], "role": ["Owned or Controlled By"]}),
    ]
    out = cx.parse(lines)
    assert out["links"] == [["B", "A", "Ownership", "Owned or Controlled By", ["US", "UK"]]]
    assert [e[3] for e in out["entities"] if e[0] == "B"] == ["1234567"]


def test_empty_ownership_role_reads_owned_by():
    lines = [
        line(id="A", schema="Company", caption="Alpha", datasets=[], properties={}),
        line(id="B", schema="Company", caption="Bravo", datasets=[], properties={}),
        line(id="r", schema="Ownership", caption="", datasets=["us_ofac_sdn"], properties={"owner": ["A"], "asset": ["B"]}),
    ]
    assert cx.parse(lines)["links"] == [["B", "A", "Ownership", "Owned by", ["US"]]]


def test_bad_input_raises():
    with pytest.raises(ValueError, match="bad JSON"):
        cx.parse(["{not json"])
    with pytest.raises(ValueError, match="no FollowTheMoney"):
        cx.parse([])


def test_authorities():
    assert cx.authorities(["us_ofac_sdn", "gb_fcdo_sanctions", "us_trade_csl", "xx_new_list"]) == ["US", "UK", "XX"]
