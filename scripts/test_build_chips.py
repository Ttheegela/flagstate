import io
import json
import urllib.error

import pytest

import build_chips as b

NOW1 = "2026-10-14T04:00:00Z"
NOW2 = "2026-10-15T04:00:00Z"
YEARS = [2021, 2022, 2023]
# reporter code -> (ISO3, name); 842 is Comtrade's code for the USA, 490 is "Other Asia, nes"
REPORTERS = {398: ("KAZ", "Kazakhstan"), 344: ("HKG", "China, Hong Kong SAR"), 842: ("USA", "USA"),
             643: ("RUS", "Russian Federation"), 490: ("S19", "Other Asia, nes"), 4: ("AFG", "Afghanistan")}
EXPORTS = {  # year -> {code: USD}
    2021: {398: 250_000, 344: 283_000_000, 842: 54_600_000},
    2022: {398: 18_259_000, 344: 208_000_000, 842: 10_000_000, 490: 5_000},
    2023: {398: 15_610_000, 344: 307_900_000},
}

NS = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML"


def party(pid, name, est, listed, country_id, program="RUSSIA-EO14024", subtype="3"):
    est_xml = ""
    if est:
        y, m, d = est.split("-")
        est_xml = (f'<Feature FeatureTypeID="646"><FeatureVersion><DatePeriod><Start><From><Year>{y}</Year>'
                   f'<Month>{int(m)}</Month><Day>{int(d)}</Day></From></Start></DatePeriod></FeatureVersion></Feature>')
    loc = (f'<Feature FeatureTypeID="25"><FeatureVersion><VersionLocation LocationID="L{pid}"/></FeatureVersion></Feature>')
    y, m, d = listed.split("-")
    return (f'<DistinctParty FixedRef="{pid}"><Profile ID="{pid}" PartySubTypeID="{subtype}"><Identity>'
            f'<Alias Primary="true"><DocumentedName><DocumentedNamePart>'
            f'<NamePartValue ScriptID="215">{name}</NamePartValue><NamePartValue ScriptID="215">{name} Sirketi</NamePartValue>'
            f'<NamePartValue ScriptID="10">名</NamePartValue>'
            f'</DocumentedNamePart></DocumentedName></Alias></Identity>{est_xml}{loc}</Profile></DistinctParty>',
            f'<Location ID="L{pid}"><LocationCountry CountryID="{country_id}"/></Location>',
            f'<SanctionsEntry ID="{pid}" ProfileID="{pid}"><EntryEvent><Date><Year>{y}</Year><Month>{int(m)}</Month>'
            f'<Day>{int(d)}</Day></Date></EntryEvent><SanctionsMeasure><Comment>{program}</Comment></SanctionsMeasure></SanctionsEntry>')


def sdn_xml(skip=()):
    rows = [party("44000", "LLC RM Design and Development", "2022-03-17", "2023-07-20", "1"),
            party("50775", "Innovio Ventures", None, "2024-10-30", "2"),
            party("50001", "Some Trading FZE", "2022-06-01", "2023-06-01", "3"),
            party("50002", "Moscow Chips OOO", "2022-05-01", "2023-01-01", "4")]
    rows = [r for r in rows if not any(f'ProfileID="{pid}"' in r[2] for pid in skip)]
    return (f'<?xml version="1.0" encoding="utf-8"?><Sanctions xmlns="{NS}">'
            '<DateOfIssue><Year>2026</Year><Month>10</Month><Day>14</Day></DateOfIssue>'
            '<ReferenceValueSets><CountryValues><Country ID="1" ISO2="KG">Kyrgyzstan</Country>'
            '<Country ID="2" ISO2="IN">India</Country><Country ID="3" ISO2="AE">UAE</Country>'
            '<Country ID="4" ISO2="RU">Russia</Country></CountryValues></ReferenceValueSets>'
            f'<DistinctParties>{"".join(r[0] for r in rows)}</DistinctParties>'
            f'<Locations>{"".join(r[1] for r in rows)}</Locations>'
            f'<SanctionsEntries>{"".join(r[2] for r in rows)}</SanctionsEntries></Sanctions>').encode()


CURATED = {
    "releases": {"jy1636": {"date": "2023-07-20", "title": "t", "url": "https://home.treasury.gov/news/press-releases/jy1636",
                            "ofac_action_url": "https://ofac.treasury.gov/recent-actions/20230720", "federal_register": None},
                 "jy2700": {"date": "2024-10-30", "title": "t", "url": "https://home.treasury.gov/news/press-releases/jy2700",
                            "ofac_action_url": "https://ofac.treasury.gov/recent-actions/20241030", "federal_register": None}},
    "firms": [{"ofac_id": "44000", "release": "jy1636", "reason": "integrated circuits"},
              {"ofac_id": "50775", "release": "jy2700", "reason": "integrated circuits",
               "bis_name": "Innovio Ventures", "bis_federal_register": "88 FR 70352"}],
}
US_LIST = {"records": [["Innovio Ventures", "INNOVIO VENTURES", "Entity List (EL)", "2023-10-06", "x", "", ""],
                       ["INNOVIO VENTURES", "INNOVIO VENTURES", "Russia", "", "50775", "", ""]]}


def make_get(exports=EXPORTS, fail=None):
    def get(url):
        if fail and fail in url:
            raise OSError("timed out")
        if url == b.COMTRADE_DA:
            return json.dumps({"data": [{"period": y, "reporterCode": c, "reporterISO": iso, "reporterDesc": name}
                                        for y in YEARS for c, (iso, name) in REPORTERS.items()
                                        if not (c == 643 and y > 2021)]}).encode()
        if "reporterCode=643" in url:
            return json.dumps({"data": [{"primaryValue": 1_555_400_000}]}).encode()
        if url.startswith(b.COMTRADE + "/preview"):
            year = int(url.rsplit("period=", 1)[1])
            return json.dumps({"error": "", "data": [{"reporterCode": c, "partnerCode": 643, "flowCode": "X", "primaryValue": v}
                                                     for c, v in exports[year].items()]}).encode()
        if url == b.EUROSTAT:
            return json.dumps({"dimension": {"time": {"category": {"index": {"2021": 0, "2022": 1, "2023": 2}}},
                                             "partner": {"category": {"index": {"RU": 0}}}},
                               "value": {"0": 622191502, "1": 119972350, "2": 127481}}).encode()
        raise AssertionError(f"unexpected url {url}")
    return get


def run(tmp_path, get=None, xml=None, now=NOW1):
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    (out / "chips-firms.json").write_text(json.dumps(CURATED))
    us = tmp_path / "us.json"
    us.write_text(json.dumps(US_LIST))
    xml = xml if xml is not None else sdn_xml()
    code = b.main(get=get or make_get(), open_xml=lambda: io.BytesIO(xml), out_dir=out, us_list=us,
                  now=now, this_year=2024, sleep=lambda s: None)
    read = lambda name: json.loads((out / f"{name}.json").read_text())
    return code, read


def test_fresh_build(tmp_path):
    code, read = run(tmp_path)
    assert code == 0
    routes = read("routes")
    assert routes["years"] == YEARS
    kaz = next(s for s in routes["senders"] if s["iso3"] == "KAZ")
    assert kaz["usd"] == [250_000, 18_259_000, 15_610_000] and kaz["group"] == "transit"
    usa = next(s for s in routes["senders"] if s["iso3"] == "USA")
    assert usa["usd"][2] == 0  # reported in 2023, no chip row
    assert routes["russia_imports_usd"] == [1_555_400_000, None, None]
    assert routes["eu27_exports_eur"]["RU"] == [622191502, 119972350, 127481]
    cov = read("coverage")
    assert cov["by_year"]["2022"]["row"] == ["HKG", "KAZ", "TWN", "USA"]
    assert cov["by_year"]["2023"]["none"] == ["AFG", "TWN", "USA"]
    assert "RUS" not in cov["by_year"]["2021"]["none"]
    lag = read("listing_lag")
    rm = next(f for f in lag["firms"] if f["ofac_id"] == "44000")
    assert rm["name"] == "LLC RM Design and Development"  # Latin script only
    assert (rm["founded"], rm["listed"], rm["months"], rm["countries"]) == ("2022-03-17", "2023-07-20", 16.1, ["KG"])
    innovio = next(f for f in lag["firms"] if f["ofac_id"] == "50775")
    assert innovio["months"] is None and innovio["bis"]["date"] == "2023-10-06"
    assert read("summary") == {"median_months": 16.1, "n": 1}
    s = lag["summary"]
    assert s["curated_new"] == {"n": 1, "median_months": 16.1, "p25_months": 16.1, "p75_months": 16.1}
    assert s["curated_without_founding_date"] == 1
    # wider base: post-invasion entities outside RU/BY (RM Design, Some Trading), not the Moscow firm
    assert s["wider_base"]["n"] == 2
    meta = json.loads((tmp_path / "out" / "chips-meta.json").read_text())["outputs"]
    assert {m["status"] for m in meta.values()} == {"fresh"}


def test_comtrade_failure_keeps_previous_and_lag_still_updates(tmp_path):
    run(tmp_path)
    before = (tmp_path / "out" / "routes.json").read_text()
    code, _ = run(tmp_path, get=make_get(fail="preview"), now=NOW2)
    assert code == 1
    assert (tmp_path / "out" / "routes.json").read_text() == before
    meta = json.loads((tmp_path / "out" / "chips-meta.json").read_text())["outputs"]
    assert meta["routes"]["status"] == meta["coverage"]["status"] == "kept-previous"
    assert "timed out" in meta["routes"]["error"] and meta["routes"]["updated_at"] == NOW1
    assert meta["listing_lag"]["status"] == "fresh" and meta["listing_lag"]["updated_at"] == NOW2


def test_sample_check_rejects_missing_kazakhstan(tmp_path):
    low = {**EXPORTS, 2022: {**EXPORTS[2022], 398: 5_000_000}}
    code, _ = run(tmp_path, get=make_get(low))
    assert code == 1
    assert not (tmp_path / "out" / "routes.json").exists()


def test_shrink_guard(tmp_path):
    run(tmp_path)
    fewer = {y: {398: v[398]} for y, v in EXPORTS.items()}
    code, read = run(tmp_path, get=make_get(fewer), now=NOW2)
    assert code == 1
    assert len(read("routes")["senders"]) == 4  # yesterday's file
    meta = json.loads((tmp_path / "out" / "chips-meta.json").read_text())["outputs"]
    assert "shrank" in meta["routes"]["error"]


def test_ofac_failure_and_delisted_firm(tmp_path):
    run(tmp_path)
    code, _ = run(tmp_path, xml=b"<broken", now=NOW2)
    assert code == 1
    # a firm that disappears from the list keeps its last known row, flagged
    code, read = run(tmp_path, xml=sdn_xml(skip=["50775"]), now=NOW2)
    innovio = next(f for f in read("listing_lag")["firms"] if f["ofac_id"] == "50775")
    assert innovio["on_current_list"] is False and innovio["bis"]["date"] == "2023-10-06"


def test_fetch_retries_429():
    calls, waits = [], []

    def opener(url):
        calls.append(url)
        if len(calls) < 3:
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)
        return io.BytesIO(b"ok")

    assert b.fetch_bytes("u", opener=opener, sleep=waits.append) == b"ok"
    assert waits == [15.0, 30.0]
    with pytest.raises(urllib.error.HTTPError):
        b.fetch_bytes("u", opener=lambda url: (_ for _ in ()).throw(urllib.error.HTTPError(url, 404, "nf", {}, None)), sleep=waits.append)
