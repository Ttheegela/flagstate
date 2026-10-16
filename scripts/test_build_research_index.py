import re

import pytest

import build_research_index as b


@pytest.fixture(scope="module")
def entries():
    return {e["id"]: e for e in b.build()}


def test_tassos_listings(entries):
    e = entries["IMO9408695"]
    assert e["name"] == "TASSOS"
    assert e["imo"] == "9408695"
    assert e["kind"] == "Oil Tanker"
    assert e["flag"] == "Liberia"
    assert [(l["by"], l["date"], l["program"]) for l in e["listings"]] == [
        ("United States", "2025-07-30", "Iran"),
        ("European Union", "2025-10-24", "Russia"),
        ("United Kingdom", "2026-02-24", "Russia"),
    ]
    assert e["facts"][0]["text"] == (
        "Listed by the United States on 30 July 2025 (Iran), the European Union on "
        "24 October 2025 (Russia) and the United Kingdom on 24 February 2026 (Russia)."
    )


def test_tassos_names_and_history(entries):
    e = entries["IMO9408695"]
    former = {n["name"] for n in e["names"] if not n["current"]}
    assert {"Front Balder", "Bay Global", "Roxen Star", "Seasalvia"} <= former
    assert "FRONT BALDER" in e["keys"]
    assert any(ev["date"] == "2023-02" and ev["text"].startswith("Sold by Frontline") for ev in e["events"])
    assert [ev["kind"] for ev in e["events"]].count("listing") == 3
    sailed = next(f for f in e["facts"] if f["text"].startswith("Has also sailed as"))
    urls = {s["n"]: s["url"] for s in e["sources"]}
    assert all("/shadow-fleet/485" in urls[n] for n in sailed["refs"])


def test_no_program_codes_on_screen(entries):
    codes = re.compile(r"\bEO\s?\d{4,5}\b|\bSDN\b|NS-CMIC|\bSSI\b")
    for e in entries.values():
        texts = [f["text"] for f in e["facts"]] + [ev["text"] for ev in e["events"]] + [l["by"] for l in e["listings"]]
        for text in texts:
            assert not codes.search(text), (e["id"], text)


def test_every_fact_points_at_a_listed_source(entries):
    for e in entries.values():
        numbers = [s["n"] for s in e["sources"]]
        assert numbers == list(range(1, len(numbers) + 1)), e["id"]
        for fact in e["facts"]:
            assert fact["refs"], (e["id"], fact["text"])
            assert set(fact["refs"]) <= set(numbers), e["id"]


def test_all_three_datasets_present(entries):
    assert "co:sovcomflot" in entries
    assert "chip:elem" in entries
    assert any(i.startswith("org:") for i in entries)
    assert all(e["keys"] for e in entries.values())


@pytest.mark.parametrize("value,expected", [
    ("2025-07-30", "30 July 2025"),
    ("2023-02", "February 2023"),
    ("", ""),
    ("n/a", "n/a"),
])
def test_fmt_date(value, expected):
    assert b.fmt_date(value) == expected


@pytest.mark.parametrize("value,expected", [
    ("[unlisted ship manager] (Liberia)", "an unlisted ship manager (Liberia)"),
    ("the Zulu Ships Management & Operation", "the Zulu Ships Management & Operation"),
    ("[shell company] Ltd", "a shell company Ltd"),
])
def test_tidy(value, expected):
    assert b.tidy(value) == expected


def test_chip_entries_carry_official_listings_only(entries):
    chips = [e for i, e in entries.items() if i.startswith("chip:")]
    assert chips
    for e in chips:
        assert e["listings"] and all(f["text"].startswith("First listed on ") for f in e["facts"]), e["id"]


def test_chip_sources_are_official_and_page_link_only_for_firms_on_it(entries):
    rm, elem = entries["chip:rm"], entries["chip:elem"]
    assert rm["story"]["url"] == "stories/chips-into-russia/viz/listing_lag.html"
    assert [s["url"] for s in rm["sources"]] == [
        "https://ofac.treasury.gov/recent-actions/20230720", "stories/chips-into-russia/viz/listing_lag.html"]
    assert rm["facts"][0]["refs"] == [1, 2]
    assert elem["story"]["url"] == "stories/chips-into-russia/viz/index.html"
    assert [(s["url"], s["label"]) for s in elem["sources"]] == [(
        "https://www.federalregister.gov/documents/2023/12/07/2023-26935/addition-of-entities-to-the-entity-list",
        "Federal Register: Entity List additions")]
    for e in entries.values():
        if e["id"].startswith("chip:"):
            assert all("FINDINGS.md" not in s["url"] for s in e["sources"])
            assert all(r <= len(e["sources"]) for f in e["facts"] for r in f["refs"])
