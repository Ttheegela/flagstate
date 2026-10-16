"""Parsers for the four official sanctions lists.

Each parser takes the raw downloaded bytes and returns records
    [name, normalised name, program, date (YYYY-MM-DD or ""), ref, imo or "", url or ""]
and raises ValueError when the file does not have the expected shape.
"""
from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime

from normalize import normalize_name

csv.field_size_limit(2**31 - 1)

LISTS = {
    "us": {
        "label": "United States",
        "download": "https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.csv",
        "page": "https://www.trade.gov/consolidated-screening-list",
    },
    "uk": {
        "label": "United Kingdom",
        "download": "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv",
        "page": "https://www.gov.uk/government/publications/the-uk-sanctions-list",
    },
    "eu": {
        "label": "European Union",
        "download": "https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw",
        "page": "https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions",
    },
    "un": {
        "label": "United Nations",
        "download": "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
        "page": "https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list",
    },
}

_US_PREFIXES = [
    ("RUSSIA", "Russia"), ("UKRAINE", "Russia/Ukraine"), ("BELARUS", "Belarus"),
    ("IRAN", "Iran"), ("IRGC", "Iran"), ("IFSR", "Iran"),
    ("DPRK", "North Korea"), ("NKOREA", "North Korea"),
    ("SYRIA", "Syria"), ("PAARSSR", "Syria"), ("VENEZUELA", "Venezuela"),
    ("CUBA", "Cuba"), ("BURMA", "Myanmar"), ("SDGT", "Terrorism"), ("FTO", "Terrorism"),
    ("SDNTK", "Narcotics"), ("ILLICIT-DRUGS", "Narcotics"), ("TCO", "Organised crime"),
    ("NPWMD", "Weapons proliferation"), ("GLOMAG", "Human rights and corruption"),
    ("CYBER", "Cyber"), ("BALKANS", "Western Balkans"),
    ("CMIC", "Chinese military companies"), ("SDNT", "Narcotics"), ("IRAQ", "Iraq"),
    ("LEBANON", "Lebanon"), ("LIBYA", "Libya"), ("SOMALIA", "Somalia"), ("SUDAN", "Sudan"),
    ("SOUTH SUDAN", "South Sudan"), ("YEMEN", "Yemen"), ("ZIMBABWE", "Zimbabwe"),
    ("CAR", "Central African Republic"), ("DRCONGO", "DR Congo"), ("NICARAGUA", "Nicaragua"),
    ("MALI", "Mali"), ("HK-EO13936", "Hong Kong"), ("HRIT", "Human rights"),
    ("ELECTION", "Election interference"), ("HOSTAGES", "Hostage-taking"),
    ("ICC", "International Criminal Court"),
]
_EU_CODES = {
    "UKR": "Russia/Ukraine", "RUS": "Russia", "RUSDA": "Russia", "BLR": "Belarus",
    "IRN": "Iran", "IRQ": "Iraq", "SYR": "Syria", "PRK": "North Korea",
    "AFG": "Afghanistan", "TAQA": "Terrorism", "EUAQ": "Terrorism", "TERR": "Terrorism",
    "HAM": "Terrorism", "HR": "Human rights", "COD": "DR Congo", "MMR": "Myanmar",
    "SOM": "Somalia", "CYB": "Cyber", "LBY": "Libya", "CAF": "Central African Republic",
    "VEN": "Venezuela", "CHEM": "Chemical weapons", "MDA": "Moldova", "NIC": "Nicaragua",
    "TUN": "Tunisia", "YEM": "Yemen", "SDN": "Sudan", "SDNZ": "Sudan", "SSD": "South Sudan",
    "HTI": "Haiti", "GTM": "Guatemala", "MLI": "Mali", "GIN": "Guinea",
}
_UN_TYPES = {
    "DRC": "DR Congo", "CAR": "Central African Republic", "DPRK": "North Korea",
    "GB": "Guinea-Bissau", "SouthSudan": "South Sudan",
}
_IMO_RE = re.compile(r"IMO\s*(\d{7})", re.IGNORECASE)
_UK_REGIME_RE = re.compile(r"^The (.+?)(?: \(Sanctions\)| Sanctions)")


def plain_program(raw: str, list_id: str) -> str:
    """Turn a list's program code into plain words; unknown codes pass through."""
    raw = (raw or "").strip()
    if list_id == "eu":
        return _EU_CODES.get(raw, raw)
    if list_id == "un":
        return _UN_TYPES.get(raw, raw)
    if list_id == "us":
        labels: list[str] = []
        for code in (c.strip().upper() for c in raw.split(";")):
            if not code:
                continue
            label = next((name for prefix, name in _US_PREFIXES if code.startswith(prefix)), code)
            if label not in labels:
                labels.append(label)
        return ", ".join(labels)
    return raw


def _imo(text: str) -> str:
    match = _IMO_RE.search(text or "")
    return match.group(1) if match else ""


def _record(name: str, program: str, date: str, ref: str, imo: str = "", url: str = "") -> list[str]:
    return [name, normalize_name(name), program, date, ref, imo, url]


def _require(fields, required: list[str], list_id: str) -> None:
    missing = [f for f in required if f not in (fields or [])]
    if missing:
        raise ValueError(f"{list_id}: missing columns {missing}")


def _dedupe(records: list[list[str]]) -> list[list[str]]:
    """Drop records whose name normalises to nothing, and repeats of (ref, name)."""
    seen: set[tuple[str, str]] = set()
    out = []
    for record in records:
        key = (record[4], record[1])
        if record[1] and key not in seen:
            seen.add(key)
            out.append(record)
    return out


def parse_us(data: bytes) -> list[list[str]]:
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    _require(reader.fieldnames, ["_id", "source", "name", "programs", "start_date", "alt_names", "ids"], "us")
    out = []
    for row in reader:
        name = (row["name"] or "").strip()
        if not name:
            continue
        program = plain_program(row["programs"], "us") or (row["source"] or "").split(" - ")[0].strip()
        date = (row["start_date"] or "").strip()[:10]
        imo = _imo(row["ids"])
        names = [name] + [alt.strip() for alt in (row["alt_names"] or "").split(";")]
        out += [_record(n, program, date, row["_id"], imo) for n in names if n]
    return _dedupe(out)


def _dmy(text: str) -> str:
    try:
        return datetime.strptime(text.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def parse_uk(data: bytes) -> list[list[str]]:
    text = data.decode("utf-8-sig")
    banner, _, body = text.partition("\n")
    if not banner.startswith("Report Date"):
        raise ValueError("uk: first line is not the 'Report Date' banner")
    reader = csv.DictReader(io.StringIO(body))
    _require(reader.fieldnames, ["Unique ID", "Name 6", "Regime Name", "Date Designated", "IMO number"], "uk")
    out = []
    for row in reader:
        name = (row["Name 6"] or "").strip()
        if not name:
            continue
        regime = (row["Regime Name"] or "").strip()
        match = _UK_REGIME_RE.match(regime)
        program = match.group(1) if match else regime
        out.append(_record(name, program, _dmy(row["Date Designated"] or ""), row["Unique ID"], _imo(row["IMO number"])))
    return _dedupe(out)


def parse_eu(data: bytes) -> list[list[str]]:
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")), delimiter=";")
    required = ["Entity_LogicalId", "Entity_DesignationDate", "Entity_Regulation_Programme",
                "Entity_Regulation_PublicationUrl", "NameAlias_WholeName"]
    _require(reader.fieldnames, required, "eu")
    out = []
    for row in reader:
        name = (row["NameAlias_WholeName"] or "").strip()
        if not name:
            continue
        url = (row["Entity_Regulation_PublicationUrl"] or "").strip()
        out.append(_record(
            name,
            plain_program(row["Entity_Regulation_Programme"], "eu"),
            (row["Entity_DesignationDate"] or "").strip()[:10],
            row["Entity_LogicalId"],
            url=url if url.startswith("http") else "",
        ))
    return _dedupe(out)


def parse_un(data: bytes) -> list[list[str]]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"un: not XML ({exc})") from exc
    if root.tag != "CONSOLIDATED_LIST" or (root.find("INDIVIDUALS") is None and root.find("ENTITIES") is None):
        raise ValueError("un: not a UN consolidated list")
    out = []
    groups = (
        ("ENTITIES", "ENTITY", "ENTITY_ALIAS", ("FIRST_NAME",)),
        ("INDIVIDUALS", "INDIVIDUAL", "INDIVIDUAL_ALIAS", ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME")),
    )
    for group_tag, item_tag, alias_tag, name_tags in groups:
        group = root.find(group_tag)
        if group is None:
            continue
        for item in group.findall(item_tag):
            name = " ".join((item.findtext(t) or "").strip() for t in name_tags if (item.findtext(t) or "").strip())
            if not name:
                continue
            program = plain_program(item.findtext("UN_LIST_TYPE") or "", "un")
            date = (item.findtext("LISTED_ON") or "").strip()[:10]
            ref = (item.findtext("REFERENCE_NUMBER") or "").strip()
            out.append(_record(name, program, date, ref))
            for alias in item.findall(alias_tag):
                alias_name = (alias.findtext("ALIAS_NAME") or "").strip()
                if alias_name:
                    out.append(_record(alias_name, program, date, ref))
    return _dedupe(out)


PARSERS = {"us": parse_us, "uk": parse_uk, "eu": parse_eu, "un": parse_un}
