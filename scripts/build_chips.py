"""Build the chips-into-Russia data from free official sources.

Writes small JSON files to stories/chips-into-russia/data/:
  routes.json       HS 8542 exports to Russia by reporter (UN Comtrade) + EU27 exports (Eurostat)
  coverage.json     per reporter per year: chip row to Russia / reported, no chip row / not reported
  listing_lag.json  curated chip firms (data/chips-firms.json): founded -> OFAC listing, in months
  chips-meta.json   status per output, source URLs, retrieval time

Each output is built from its own sources. An output that fails (download error, failed sample
check, or more than 20% fewer rows than the committed copy) keeps its previous file and is marked
"kept-previous". Exits 1 when any output failed so the nightly workflow can open an issue.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

from normalize import normalize_name

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "stories" / "chips-into-russia" / "data"
US_LIST = ROOT / "data" / "lists" / "us.json"
USER_AGENT = "Flagstate/1.0 (+https://github.com/Ttheegela/flagstate)"
SHRINK_LIMIT = 0.8
FIRST_YEAR = 2019
INVASION = date(2022, 2, 24)

COMTRADE = "https://comtradeapi.un.org/public/v1"
COMTRADE_EXPORTS = COMTRADE + "/preview/C/A/HS?partnerCode=643&cmdCode=8542&flowCode=X&period={year}"
COMTRADE_RU_IMPORTS = COMTRADE + "/preview/C/A/HS?reporterCode=643&partnerCode=0&cmdCode=8542&flowCode=M&period={year}"
COMTRADE_DA = COMTRADE + "/getDA/C/A/HS"
COMTRADE_PAGE = "https://comtradeplus.un.org/"
COMTRADE_TERMS = "https://uncomtrade.org/docs/policy-on-comtrade-data-use/"
EUROSTAT_PARTNERS = ["RU", "TR", "KZ", "KG", "AM", "AE"]
EUROSTAT = ("https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409?format=JSON"
            "&freq=A&reporter=EU27_2020&" + "&".join(f"partner={p}" for p in EUROSTAT_PARTNERS)
            + f"&product=8542&flow=2&indicators=VALUE_IN_EUROS&sinceTimePeriod={FIRST_YEAR}")
EUROSTAT_PAGE = "https://ec.europa.eu/eurostat/databrowser/view/ds-045409/default/table?lang=en"
OFAC_XML = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML"
OFAC_PAGE = "https://ofac.treasury.gov/sanctions-list-service"
CSL_PAGE = "https://www.trade.gov/consolidated-screening-list"

# Comtrade codes that differ from ISO 3166 or carry no ISO3 in getDA.
COMTRADE_ISO3 = {490: "TWN"}  # "Other Asia, nes": Taiwan's trade, as Comtrade publishes it
# Senders always kept in routes.json: the transit countries and the pre-2022 large senders.
TRANSIT = ["KAZ", "KGZ", "ARM", "TUR", "ARE"]
ALWAYS_KEEP = TRANSIT + ["CHN", "HKG", "USA", "DEU", "NLD"]
TOP_N = 12  # plus the largest senders by peak year, to stay within Comtrade's "limited amounts"
OFAC_ESTABLISHED = "646"  # feature type "Organization Established Date"
OFAC_ENTITY_SUBTYPE = "3"
OFAC_LATIN_SCRIPT = "215"


def fetch(url: str, timeout: int = 300):
    """Open a URL and return the response (file-like). Caller closes it."""
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=timeout)


def fetch_bytes(url: str, opener=fetch, tries: int = 4, wait: float = 15.0, sleep=time.sleep) -> bytes:
    """Read a URL, retrying 429 and 5xx with growing waits."""
    for attempt in range(tries):
        try:
            with opener(url) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and exc.code < 500 or attempt == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == tries - 1:
                raise
        sleep(wait * (attempt + 1))
    raise AssertionError("unreachable")


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ---------- UN Comtrade + Eurostat ----------

def comtrade_reporters(da: dict, this_year: int) -> tuple[dict, dict]:
    """getDA -> ({year: set of ISO3 that reported}, {ISO3: name}). Years before this_year only."""
    by_year: dict[int, set] = {}
    names: dict[str, str] = {}
    for row in da["data"]:
        year = int(row["period"])
        if not FIRST_YEAR <= year < this_year:
            continue
        iso = COMTRADE_ISO3.get(row["reporterCode"]) or row.get("reporterISO")
        if not iso or len(iso) != 3 or not iso.isalpha():
            continue
        by_year.setdefault(year, set()).add(iso)
        names.setdefault(iso, "Taiwan" if iso == "TWN" else row.get("reporterDesc") or iso)
    return by_year, names


def build_trade(get, this_year: int, sleep=time.sleep, spacing: float = 6.0) -> tuple[dict, dict]:
    """Return (routes, coverage) documents. `get(url) -> bytes`."""
    da = json.loads(get(COMTRADE_DA))
    reported, names = comtrade_reporters(da, this_year)
    if not reported:
        raise ValueError("Comtrade availability list is empty")
    # code -> ISO3, from the same availability list
    code_iso = {r["reporterCode"]: COMTRADE_ISO3.get(r["reporterCode"]) or r.get("reporterISO") for r in da["data"]}
    years = sorted(reported)
    exports: dict[str, dict[int, float]] = {}
    for i, year in enumerate(years):
        if i:
            sleep(spacing)
        doc = json.loads(get(COMTRADE_EXPORTS.format(year=year)))
        if doc.get("error"):
            raise ValueError(f"Comtrade {year}: {doc['error']}")
        for row in doc["data"]:
            iso = code_iso.get(row["reporterCode"])
            if not iso or row.get("partnerCode") != 643 or row.get("flowCode") != "X":
                continue
            exports.setdefault(iso, {})[year] = exports.get(iso, {}).get(year, 0) + row["primaryValue"]
    ru_imports = {}
    for year in years:
        if "RUS" not in reported[year]:
            continue
        sleep(spacing)
        doc = json.loads(get(COMTRADE_RU_IMPORTS.format(year=year)))
        for row in doc.get("data") or []:
            ru_imports[year] = row["primaryValue"]

    totals = {y: sum(v.get(y, 0) for v in exports.values()) for y in years}
    peak = sorted(exports, key=lambda iso: -max(exports[iso].values()))
    keep = list(dict.fromkeys([*peak[:TOP_N], *(c for c in ALWAYS_KEEP if c in exports)]))
    senders = [{
        "iso3": iso,
        "name": names.get(iso, iso),
        "group": "transit" if iso in TRANSIT else "hk-china" if iso in ("HKG", "CHN") else "other",
        "usd": [None if iso not in reported[y] else round(exports[iso].get(y, 0)) for y in years],
    } for iso in sorted(keep, key=lambda iso: -sum(exports[iso].values()))]

    sleep(1)
    eu = json.loads(get(EUROSTAT))
    eu_years = eu["dimension"]["time"]["category"]["index"]
    eu_partners = eu["dimension"]["partner"]["category"]["index"]
    n_time = len(eu_years)
    eurostat = {}
    for partner, p in eu_partners.items():
        eurostat[partner] = [eu["value"].get(str(p * n_time + eu_years[str(y)])) if str(y) in eu_years else None
                             for y in years]

    retrieved = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    routes = {
        "hs": "8542",
        "unit": "USD, each reporter's own declared exports to Russia",
        "years": years,
        "retrieved": retrieved,
        "senders": senders,
        "all_reporters_usd": [round(totals[y]) for y in years],
        "reporters_with_row": [sum(1 for v in exports.values() if y in v) for y in years],
        "russia_imports_usd": [round(ru_imports[y]) if y in ru_imports else None for y in years],
        "eu27_exports_eur": eurostat,
        "sources": {
            "comtrade": {"label": "UN Comtrade", "url": COMTRADE_PAGE, "api": COMTRADE_EXPORTS.format(year="YYYY"), "terms": COMTRADE_TERMS},
            "russia_imports": {"label": "UN Comtrade (reporter Russia, imports from world)", "api": COMTRADE_RU_IMPORTS.format(year="YYYY")},
            "eurostat": {"label": "Eurostat Comext DS-045409 (CC BY 4.0)", "url": EUROSTAT_PAGE, "api": EUROSTAT},
        },
    }
    coverage = {
        "years": years,
        "retrieved": retrieved,
        "states": {"row": "Reported a chip export row to Russia", "none": "Reported trade, no chip row to Russia", "absent": "Did not report"},
        "names": {iso: names[iso] for iso in sorted(names)},
        # per year: ISO3 lists; anyone not listed did not report that year
        "by_year": {str(y): {"row": sorted(i for i in exports if y in exports[i]),
                             "none": sorted(reported[y] - {i for i in exports if y in exports[i]} - {"RUS"})} for y in years},
        "sources": {"availability": COMTRADE_DA, "exports": COMTRADE_EXPORTS.format(year="YYYY"), "page": COMTRADE_PAGE},
    }
    return routes, coverage


def check_trade(routes: dict, coverage: dict) -> None:
    years = routes["years"]
    kaz = next((s for s in routes["senders"] if s["iso3"] == "KAZ"), None)
    if 2022 not in years or not kaz or (kaz["usd"][years.index(2022)] or 0) <= 10_000_000:
        raise ValueError("sample check failed: Kazakhstan 2022 chip exports to Russia missing or under $10M")
    if not coverage["by_year"].get("2023", {}).get("row"):
        raise ValueError("sample check failed: no chip rows in 2023")


# ---------- OFAC SDN advanced XML ----------

def parse_sdn(stream) -> tuple[dict, str | None]:
    """Stream-parse SDN_ADVANCED.XML -> ({profile id: party}, date of issue)."""
    def local(tag):
        return tag.rsplit("}", 1)[-1]

    def ymd(el):
        if el is None:
            return None
        vals = {local(c.tag): c.text for c in el}
        try:
            return date(int(vals["Year"]), int(vals["Month"]), int(vals["Day"])).isoformat()
        except (KeyError, TypeError, ValueError):
            return None

    parties: dict[str, dict] = {}
    loc_country: dict[str, str] = {}
    country_iso2: dict[str, str] = {}
    issued = None
    for _, el in ET.iterparse(stream, events=("end",)):
        tag = local(el.tag)
        if tag == "DateOfIssue":
            issued = ymd(el)
        elif tag == "Country" and el.get("ID"):
            country_iso2[el.get("ID")] = el.get("ISO2") or ""
        elif tag == "Location":
            for c in el.iter():
                if local(c.tag) == "LocationCountry":
                    loc_country[el.get("ID")] = c.get("CountryID")
            el.clear()
        elif tag == "DistinctParty":
            profile = next(c for c in el if local(c.tag) == "Profile")
            name, aliases, est, locs = None, [], None, []
            for alias in profile.iter():
                if local(alias.tag) != "Alias":
                    continue
                parts = [v for v in alias.iter() if local(v.tag) == "NamePartValue"]
                latin = [v for v in parts if v.get("ScriptID") == OFAC_LATIN_SCRIPT] or parts
                if profile.get("PartySubTypeID") == OFAC_ENTITY_SUBTYPE:
                    latin = latin[:1]  # an entity's name parts are the same name in other spellings
                text = " ".join(v.text or "" for v in latin).strip()
                if alias.get("Primary") == "true" and name is None:
                    name = text
                aliases.append(text)
            for feature in profile.iter():
                if local(feature.tag) != "Feature":
                    continue
                for c in feature.iter():
                    if local(c.tag) == "VersionLocation":
                        locs.append(c.get("LocationID"))
                if feature.get("FeatureTypeID") == OFAC_ESTABLISHED and est is None:
                    est = ymd(next((c for c in feature.iter() if local(c.tag) == "From"), None))
            parties.setdefault(profile.get("ID"), {}).update(
                name=name or (aliases[0] if aliases else ""), aliases=aliases, est=est, locs=locs,
                entity=profile.get("PartySubTypeID") == OFAC_ENTITY_SUBTYPE)
            el.clear()
        elif tag == "SanctionsEntry":
            p = parties.setdefault(el.get("ProfileID"), {})
            dates = [ymd(c) for e in el if local(e.tag) == "EntryEvent" for c in e if local(c.tag) == "Date"]
            dates = [d for d in dates if d]
            if dates:
                p["listed"] = min([*dates, *([p["listed"]] if p.get("listed") else [])])
            p.setdefault("programs", set()).update(c.text for c in el.iter() if local(c.tag) == "Comment" and c.text)
            el.clear()
    for p in parties.values():
        p["countries"] = sorted({country_iso2.get(loc_country.get(l), "") for l in p.pop("locs", [])} - {""})
        p["programs"] = sorted(p.get("programs", ()))
    return parties, issued


def months_between(a: str, b: str) -> float:
    return round((date.fromisoformat(b) - date.fromisoformat(a)).days / 30.44, 1)


def entity_list_dates(us_records: list) -> dict:
    """normalised name -> earliest BIS Entity List date, from data/lists/us.json (CSL)."""
    out = {}
    for name, norm, program, when, *_ in us_records:
        if program.startswith("Entity List") and when:
            out[norm] = min(out.get(norm, when), when)
    return out


def build_lag(parties: dict, curated: dict, entity_list: dict, previous: dict | None) -> dict:
    releases = curated["releases"]
    prev_firms = {f["ofac_id"]: f for f in (previous or {}).get("firms", [])}
    firms = []
    for item in curated["firms"]:
        oid = str(item["ofac_id"])
        p = parties.get(oid)
        if item["release"] not in releases:
            raise ValueError(f"chips-firms.json: unknown release {item['release']}")
        if not p or not p.get("listed"):
            if oid in prev_firms:  # removed from the current list: keep the last copy we had, flagged
                firms.append({**prev_firms[oid], "on_current_list": False})
            continue
        bis = None
        if item.get("bis_name"):
            when = entity_list.get(normalize_name(item["bis_name"]))
            if when:
                bis = {"date": when, "name": item["bis_name"], "federal_register": item.get("bis_federal_register")}
        firms.append({
            "ofac_id": oid,
            "name": p["name"],
            "countries": p["countries"],
            "founded": p.get("est"),
            "listed": p["listed"],
            "months": months_between(p["est"], p["listed"]) if p.get("est") else None,
            "bis": bis,
            "reason": item["reason"],
            "release": item["release"],
            "on_current_list": True,
        })
    firms.sort(key=lambda f: (f["founded"] is None, f["founded"] or "", f["name"]))

    def stats(lags):
        lags = sorted(lags)
        if not lags:
            return {"n": 0, "median_months": None}
        q = statistics.quantiles(lags, n=4) if len(lags) > 1 else [lags[0]] * 3
        return {"n": len(lags), "median_months": round(statistics.median(lags), 1),
                "p25_months": round(q[0], 1), "p75_months": round(q[2], 1)}

    new = [f["months"] for f in firms if f["founded"] and f["founded"] >= INVASION.isoformat()]
    base = [months_between(p["est"], p["listed"]) for p in parties.values()
            if p.get("entity") and p.get("est") and p.get("listed") and p["est"] >= INVASION.isoformat()
            and "RUSSIA-EO14024" in p.get("programs", ())
            and p["countries"] and not set(p["countries"]) <= {"RU", "BY"}]
    return {
        "firms": firms,
        "releases": releases,
        "summary": {
            "curated_new": stats(new),
            "curated_total": len(firms),
            "curated_without_founding_date": sum(1 for f in firms if not f["founded"]),
            "curated_founded_before_invasion": sum(1 for f in firms if f["founded"] and f["founded"] < INVASION.isoformat()),
            "wider_base": {**stats(base), "definition": "OFAC entities under RUSSIA-EO14024 with an 'Organization Established Date' on or after 2022-02-24 and an address outside Russia and Belarus"},
        },
        "definition": "months = (OFAC listing date - OFAC 'Organization Established Date') / 30.44 days",
    }


def check_lag(lag: dict) -> None:
    rm = next((f for f in lag["firms"] if f["ofac_id"] == "44000"), None)
    if not rm or rm["months"] is None:
        raise ValueError("sample check failed: RM Design and Development (OFAC 44000) lag did not compute")


# ---------- orchestration ----------

def _rows(doc: dict, kind: str) -> int:
    if kind == "routes":
        return sum(1 for s in doc["senders"] for v in s["usd"] if v)
    if kind == "coverage":
        return sum(len(v["row"]) + len(v["none"]) for v in doc["by_year"].values())
    return len(doc["firms"])


def _publish(out_dir: Path, outputs: dict, now: str, previous_meta: dict, sources: dict, error: Exception | None) -> dict:
    """Write each output unless the build failed or it shrank too much. Returns meta per output."""
    meta = {}
    for kind, doc in outputs.items():
        path = out_dir / f"{kind}.json"
        prev = _read_json(path)
        err = error
        if err is None and prev and _rows(doc, kind) < SHRINK_LIMIT * _rows(prev, kind):
            err = ValueError(f"shrank from {_rows(prev, kind)} to {_rows(doc, kind)} rows")
        base = {"sources": sources, "checked_at": now}
        if err is not None:
            old = previous_meta.get(kind, {})
            meta[kind] = {**base, "status": "kept-previous", "error": f"{type(err).__name__}: {err}",
                          "updated_at": old.get("updated_at"), "row_count": _rows(prev, kind) if prev else 0}
            continue
        text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            _write_atomic(path, text)
        meta[kind] = {**base, "status": "fresh", "updated_at": now, "row_count": _rows(doc, kind)}
    return meta


def main(get=None, open_xml=None, out_dir: Path = OUT_DIR, us_list: Path = US_LIST,
         now: str | None = None, this_year: int | None = None, sleep=time.sleep) -> int:
    get = get or (lambda url: fetch_bytes(url, sleep=sleep))
    open_xml = open_xml or (lambda: fetch(OFAC_XML, timeout=600))
    now = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    this_year = this_year or datetime.now(timezone.utc).year
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = out_dir / "chips-meta.json"
    previous_meta = (_read_json(meta_path) or {}).get("outputs", {})
    meta = {}

    trade_sources = [COMTRADE_DA, COMTRADE_EXPORTS.format(year="YYYY"), EUROSTAT]
    try:
        routes, coverage = build_trade(get, this_year, sleep=sleep)
        check_trade(routes, coverage)
        err = None
    except Exception as exc:  # keep yesterday's routes and coverage
        routes = _read_json(out_dir / "routes.json") or {"senders": []}
        coverage = _read_json(out_dir / "coverage.json") or {"by_year": {}}
        err = exc
    meta.update(_publish(out_dir, {"routes": routes, "coverage": coverage}, now, previous_meta, trade_sources, err))

    lag_sources = [OFAC_XML, CSL_PAGE + " (via data/lists/us.json)"]
    try:
        curated = json.loads((out_dir / "chips-firms.json").read_text(encoding="utf-8"))
        with open_xml() as stream:
            parties, issued = parse_sdn(stream)
        us = (_read_json(Path(us_list)) or {}).get("records", [])
        lag = build_lag(parties, curated, entity_list_dates(us), _read_json(out_dir / "listing_lag.json"))
        lag["ofac_date_of_issue"] = issued
        lag["retrieved"] = now[:10]
        lag["sources"] = {"ofac": OFAC_XML, "ofac_page": OFAC_PAGE, "csl": CSL_PAGE}
        check_lag(lag)
        err = None
    except Exception as exc:
        lag = _read_json(out_dir / "listing_lag.json") or {"firms": []}
        err = exc
    meta.update(_publish(out_dir, {"listing_lag": lag}, now, previous_meta, lag_sources, err))

    s = (lag.get("summary") or {}).get("curated_new")
    if s:  # tiny file for the home card, so it needn't fetch the whole lag file
        _write_atomic(out_dir / "summary.json", json.dumps({"median_months": s["median_months"], "n": s["n"]}) + "\n")
    _write_atomic(meta_path, json.dumps({"outputs": meta}, indent=2) + "\n")
    for kind, m in meta.items():
        print(f"{kind}: {m['status']} ({m['row_count']} rows)" + (f" - {m['error']}" if m.get("error") else ""))
    return 1 if any(m["status"] != "fresh" for m in meta.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
