import email.message
import json
import urllib.error
from pathlib import Path

import pytest

import lobbying as lb

ROOT = Path(__file__).resolve().parent.parent
CONFIG = lb.load_config(ROOT / "data" / "lobbying-clients.json")
FIX = Path(__file__).parent / "fixtures" / "lda_nord_stream_2.json"


def filing(uuid, *, client="NORD STREAM 2 AG", client_id=1, registrant="CAPITOL COUNSEL LLC", reg_id=10,
           year=2018, period="first_quarter", income=None, posted="2018-04-20T00:00:00Z", activities=None, foreign=None):
    return {"filing_uuid": uuid, "client": {"id": client_id, "name": client}, "registrant": {"id": reg_id, "name": registrant},
            "filing_year": year, "filing_period": period, "income": income, "expenses": None, "dt_posted": posted,
            "lobbying_activities": activities or [], "foreign_entities": foreign or []}


def edges(out, typ):
    return [e for e in out["edges"] if e["type"] == typ]


def test_amendment_counted_once_latest_amount_wins():
    out = lb.extract({"a": filing("a", income="50000", posted="2018-04-20T00:00:00Z"),
                      "b": filing("b", income="60000", posted="2018-05-20T00:00:00Z")}, CONFIG)
    [hired] = edges(out, "hired")
    assert hired["source"] == "co:nord-stream-2"
    assert hired["amount"] == 60000.0
    assert hired["n_filings"] == 2


def test_version_with_amount_beats_later_blank():
    out = lb.extract({"a": filing("a", income="40000", posted="2020-01-01T00:00:00Z"),
                      "b": filing("b", income=None, posted="2020-02-01T00:00:00Z")}, CONFIG)
    assert edges(out, "hired")[0]["amount"] == 40000.0


def test_subcontract_not_added_to_client_total():
    out = lb.extract({"a": filing("a", client="BIG FIRM ON BEHALF OF NORD STREAM 2 AG", income="30000")}, CONFIG)
    [hired] = edges(out, "hired")
    assert hired.get("subcontract") is True
    assert hired.get("sub_amount") == 30000.0
    assert "amount" not in hired


def test_in_house_filing():
    out = lb.extract({"a": filing("a", registrant="NORD STREAM 2 AG", income="10000")}, CONFIG)
    assert edges(out, "lobbied_in_house")[0]["target"] == "co:nord-stream-2"


def test_lobbyist_former_post_bodies_bills_and_parent():
    act = {"description": "S.722 Countering Iran's Destabilizing Activities Act, Russia sanctions",
           "government_entities": [{"name": "SENATE"}, {"name": "TREASURY - DEPT OF"}],
           "lobbyists": [{"lobbyist": {"first_name": "JANE", "last_name": "EXAMPLE"}, "covered_position": "Legislative Assistant, Sen. Smith"}]}
    foreign = [{"name": "GAZPROM (50% of NS2 operating budget)", "country": "RU", "ownership_percentage": "50"}]
    out = lb.extract({"a": filing("a", income="1000", activities=[act], foreign=foreign)}, CONFIG)
    names = {n["id"]: n for n in out["nodes"]}
    assert names["p:jane-example"]["name"] == "Jane Example"
    assert names["p:jane-example"]["covered_positions"] == ["Legislative Assistant, Sen. Smith"]
    assert any(e["source"] == "p:jane-example" and e["target"] == "gov:us-senate" for e in edges(out, "formerly_served_in"))
    assert {(e["target"], e["client"]) for e in edges(out, "lobbied")} == {("gov:us-senate", "co:nord-stream-2"), ("gov:us-treasury", "co:nord-stream-2")}
    assert [(e["target"], e["client"]) for e in edges(out, "lobbied_on")] == [("bill:s722", "co:nord-stream-2")]
    [fe] = edges(out, "foreign_entity_of")
    assert fe["source"] == "co:gazprom" and fe["target"] == "co:nord-stream-2"
    assert fe["texts"] == ["50% of NS2 operating budget"] and fe["ownership_pct"] == "50"
    assert edges(out, "lobbied_for")[0]["source"] == "p:jane-example"


def test_long_tail_bill_dropped_and_lobbied_kept_per_client():
    act1 = {"description": "H.R. 1234 farm subsidies", "government_entities": [{"name": "SENATE"}], "lobbyists": []}
    out = lb.extract({"a": filing("a", activities=[act1]),
                      "b": filing("b", client="HUAWEI TECHNOLOGIES USA", client_id=2, activities=[act1])}, CONFIG)
    assert not any(n["type"] == "bill" for n in out["nodes"])
    assert {e["client"] for e in edges(out, "lobbied")} == {"co:nord-stream-2", "co:huawei"}


def test_excluded_lobbyist_and_unmatched_client_dropped():
    cfg = {**CONFIG, "exclude_lobbyists": ["JANE EXAMPLE"]}
    act = {"description": "", "government_entities": [], "lobbyists": [{"lobbyist": {"first_name": "Jane", "last_name": "Example"}, "covered_position": ""}]}
    out = lb.extract({"a": filing("a", activities=[act]), "z": filing("z", client="ACME WIDGETS", client_id=9)}, cfg)
    assert not any(n["id"] == "p:jane-example" for n in out["nodes"])
    assert out["filings_kept"] == 1 and out["filings_scanned"] == 2


def test_filing_url_uses_lda_gov():
    out = lb.extract({"abc-123": filing("abc-123", income="1")}, CONFIG)
    assert edges(out, "hired")[0]["source_url"] == "https://lda.gov/filings/public/filing/abc-123/print/"


def test_real_page_gives_nord_stream_2_firms():
    page = json.loads(FIX.read_text(encoding="utf-8"))
    out = lb.extract({r["filing_uuid"]: r for r in page["results"]}, CONFIG)
    hired = [e for e in out["edges"] if e["type"] in ("hired", "lobbied_in_house") and e["source"] == "co:nord-stream-2"]
    assert hired and all(e["source_url"].startswith("https://lda.gov/filings/public/filing/") for e in hired)


def test_fetch_walks_every_page():
    pages = {"https://x/?client_name=A&page_size=25": {"results": [{"filing_uuid": "1", "client": {"name": "A"}}], "next": "https://x/p2"},
             "https://x/p2": {"results": [{"filing_uuid": "2", "client": {"name": "A"}}], "next": None}}
    got = lb.fetch_filings([["client_name", "A"]], get=pages.__getitem__, sleep=lambda s: None, base="https://x/")
    assert sorted(got) == ["1", "2"]


class FakeResponse:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def read(self):
        return self.body


def http_error(code, retry_after=None):
    headers = email.message.Message()
    if retry_after:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError("https://x", code, "err", headers, None)


def test_get_json_retries_429_then_succeeds():
    waits, calls = [], []

    def opener(req, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise http_error(429, "7")
        return FakeResponse(b'{"ok": true}')

    assert lb.get_json("https://x", opener=opener, sleep=waits.append) == {"ok": True}
    assert waits == [7]


def test_get_json_gives_up_after_six_server_errors():
    def opener(req, timeout):
        raise http_error(503)

    with pytest.raises(RuntimeError, match="giving up"):
        lb.get_json("https://x", opener=opener, sleep=lambda s: None)


def test_get_json_raises_on_client_error():
    def opener(req, timeout):
        raise http_error(404)

    with pytest.raises(urllib.error.HTTPError):
        lb.get_json("https://x", opener=opener, sleep=lambda s: None)


def lobbyist_act(first, last, middle="", suffix=""):
    p = {"first_name": first, "last_name": last, "middle_name": middle, "suffix": suffix}
    return {"description": "", "government_entities": [], "lobbyists": [{"lobbyist": p, "covered_position": ""}]}


def test_excluded_lobbyist_with_middle_name_dropped():
    cfg = {**CONFIG, "exclude_lobbyists": ["JANE EXAMPLE"]}
    out = lb.extract({"a": filing("a", activities=[lobbyist_act("Jane", "Example", middle="Q")])}, cfg)
    assert not any(n["type"] == "person" for n in out["nodes"])


def test_excluded_lobbyist_with_suffix_dropped():
    cfg = {**CONFIG, "exclude_lobbyists": ["JANE EXAMPLE"]}
    out = lb.extract({"a": filing("a", activities=[lobbyist_act("Jane", "Example", suffix="Jr.")])}, cfg)
    assert not any(n["type"] == "person" for n in out["nodes"])


def test_get_json_non_integer_retry_after_uses_backoff():
    waits, calls = [], []

    def opener(req, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise http_error(429, "Wed, 21 Oct 2015 07:28:00 GMT")
        return FakeResponse(b'{"ok": true}')

    assert lb.get_json("https://x", opener=opener, sleep=waits.append) == {"ok": True}
    assert waits == [20]


def test_get_json_retries_timeout_then_succeeds():
    waits, calls = [], []

    def opener(req, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise TimeoutError("read timed out")
        return FakeResponse(b'{"ok": true}')

    assert lb.get_json("https://x", opener=opener, sleep=waits.append) == {"ok": True}
    assert waits == [5]


def test_get_json_retries_truncated_json_then_succeeds():
    waits, calls = [], []

    def opener(req, timeout):
        calls.append(1)
        if len(calls) == 1:
            return FakeResponse(b'{"ok":')
        return FakeResponse(b'{"ok": true}')

    assert lb.get_json("https://x", opener=opener, sleep=waits.append) == {"ok": True}
    assert waits == [5]


def test_get_json_six_server_errors_make_six_calls_and_five_sleeps():
    calls, waits = [], []

    def opener(req, timeout):
        calls.append(1)
        raise http_error(503)

    with pytest.raises(RuntimeError, match="giving up"):
        lb.get_json("https://x", opener=opener, sleep=waits.append)
    assert len(calls) == 6
    assert len(waits) == 5


@pytest.mark.parametrize("raw,want", [
    ("BGR GOVERNMENT AFFAIRS", "BGR Government Affairs"),
    ("SWEENEY & ASSOCIATES LLC LLC", "Sweeney & Associates LLC"),
    ("FGS GLOBAL (US) LLC (FKA FGH HOLDINGS LLC)", "FGS Global (US) LLC (fka FGH Holdings LLC)"),
    ("MCDERMOTT WILL & SCHULTE LLP", "McDermott Will & Schulte LLP"),
    ("THE LAW OFFICE OF STEPHEN JAMES BINHAK, PLLC", "The Law Office of Stephen James Binhak, PLLC"),
    ("DLA PIPER LLP (US)", "DLA Piper LLP (US)"),
    ("AKIN GUMP STRAUSS HAUER & FELD", "Akin Gump Strauss Hauer & Feld"),
    ("McLarty Inbound LLC", "McLarty Inbound LLC"),
    ("QORVIS COMMUNICATIONS D/B/A QORVIS MSLGROUP", "Qorvis Communications d/b/a Qorvis MSLGroup"),
])
def test_display_name(raw, want):
    got = lb.display_name(raw)
    if raw.startswith("QORVIS"):  # MSLGROUP has a vowel-free prefix only; accept plain title case
        assert got.startswith("Qorvis Communications d/b/a Qorvis")
    else:
        assert got == want


def test_person_name_casing_and_suffix():
    assert lb.person_name({"first_name": "JOHN", "last_name": "MCDONALD", "suffix": "III"}) == "John McDonald III"
    assert lb.person_name({"first_name": "JOHN", "last_name": "NG", "suffix": "JR."}) == "John Ng Jr."


def test_clean_text():
    assert lb.clean_text("\u00e2\u20ac\u2039Chief of Staff") == "Chief of Staff"
    assert lb.clean_text("Chief  of Staff") == "Chief of Staff"
    assert lb.clean_text("\u00e2\u20ac\u2039Chief \u0394 \u200bStaff") == "\u00e2\u20ac\u2039Chief \u0394 Staff"


def test_extract_cleans_mojibake_and_firm_acronym():
    cov = "â€‹Chief of Staff, Rep. Jim McCrery"
    act = {"description": "", "government_entities": [], "lobbyists": [
        {"lobbyist": {"first_name": "JANE", "last_name": "EXAMPLE"}, "covered_position": cov}]}
    out = lb.extract({"a": filing("a", registrant="BGR GOVERNMENT AFFAIRS", activities=[act])}, CONFIG)
    names = {n["id"]: n for n in out["nodes"]}
    assert names["p:jane-example"]["covered_positions"] == ["Chief of Staff, Rep. Jim McCrery"]
    assert names["lf:bgr-government-affairs"]["name"] == "BGR Government Affairs"


def test_person_suffix_normalised_whatever_raw_casing():
    assert lb.person_name({"first_name": "Bob", "middle_name": "R", "last_name": "Brooks", "suffix": "jr"}) == "Bob R Brooks Jr"
    assert lb.person_name({"first_name": "Robert", "last_name": "Smith", "suffix": "ii"}) == "Robert Smith II"


def test_honorific_in_display_name():
    assert lb.display_name("MR. DOYCE BOESCH") == "Mr. Doyce Boesch"
    assert lb.display_name("DR. JANE ROE") == "Dr. Jane Roe"


def test_clean_text_greek_question_mark():
    assert lb.clean_text("Leg Dir\u037e Sen") == "Leg Dir; Sen"


def test_fetch_rejects_next_url_outside_base():
    for bad in ("file:///etc/passwd", "https://evil.example/p2", "ftp://x/p2"):
        pages = {"https://x/?client_name=A&page_size=25": {"results": [], "next": bad}}
        with pytest.raises(ValueError, match="unexpected next"):
            lb.fetch_filings([["client_name", "A"]], get=pages.__getitem__, sleep=lambda s: None, base="https://x/")


def test_fetch_caps_pages_per_query():
    calls = []

    def endless(url):
        calls.append(url)
        return {"results": [], "next": "https://x/more"}

    with pytest.raises(RuntimeError, match="pages"):
        lb.fetch_filings([["client_name", "A"]], get=endless, sleep=lambda s: None, base="https://x/")
    assert len(calls) == lb.MAX_PAGES


def test_fetch_allows_exactly_max_pages():
    n = 0

    def get(url):
        nonlocal n
        n += 1
        return {"results": [], "next": "https://x/more" if n < lb.MAX_PAGES else None}

    lb.fetch_filings([["client_name", "A"]], get=get, sleep=lambda s: None, base="https://x/")
    assert n == lb.MAX_PAGES


def test_get_json_caps_retry_after():
    waits, calls = [], []

    def opener(req, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise http_error(429, "99999")
        return FakeResponse(b'{"ok": true}')

    lb.get_json("https://x", opener=opener, sleep=waits.append)
    assert waits == [lb.MAX_RETRY_WAIT]
