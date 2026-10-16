"""Compact index of OpenSanctions' consolidated sanctions data (CC BY-NC 4.0).

parse(data) takes the bytes of targets.simple.csv and returns entities
    [id, schema, imo, listed_by, names]
listed_by is plain words such as "Canada, EU, UK"; names holds up to MAX_NAMES
distinct names, primary first. Raises ValueError when the file has the wrong shape.
"""
from __future__ import annotations

import csv
import io

from normalize import normalize_name

csv.field_size_limit(2**31 - 1)

SOURCE_URL = "https://data.opensanctions.org/datasets/latest/sanctions/targets.simple.csv"
PAGE_URL = "https://www.opensanctions.org/datasets/sanctions/"
KEEP_SCHEMAS = {"Person", "Organization", "LegalEntity", "Company", "Vessel", "Airplane"}
MAX_NAMES = 6
REQUIRED = ["id", "schema", "name", "aliases", "identifiers", "program_ids", "dataset"]
AUTHORITIES = {
    "US": "US", "EU": "EU", "GB": "UK", "UN": "UN", "UA": "Ukraine", "SECO": "Switzerland",
    "CH": "Switzerland", "CA": "Canada", "AU": "Australia", "NZ": "New Zealand", "JP": "Japan",
    "PK": "Pakistan", "RU": "Russia", "IR": "Iran", "CN": "China", "SA": "Saudi Arabia",
    "AE": "UAE", "IN": "India", "NL": "Netherlands", "FR": "France", "CZ": "Czechia",
    "SG": "Singapore", "PH": "Philippines",
}


def listed_by(program_ids: str, datasets: str) -> str:
    """'CA-SEMA;EU-MARE;GB-RUS' -> 'Canada, EU, UK'; no programs -> first dataset name."""
    labels: list[str] = []
    for pid in (p.strip() for p in (program_ids or "").split(";")):
        if "-" not in pid:
            continue
        prefix = pid.split("-")[0]
        label = AUTHORITIES.get(prefix, prefix)
        if label not in labels:
            labels.append(label)
    if labels:
        return ", ".join(labels)
    return (datasets or "").split(";")[0].strip()


def _imo(identifiers: str) -> str:
    for ident in (i.strip() for i in (identifiers or "").split(";")):
        digits = ident[3:]
        if ident.upper().startswith("IMO") and len(digits) == 7 and digits.isdigit():
            return digits
    return ""


def parse(data: bytes) -> list[list]:
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"opensanctions: missing columns {missing}")
    out = []
    for row in reader:
        if row["schema"] not in KEEP_SCHEMAS:
            continue
        names: list[str] = []
        seen: set[str] = set()
        for name in [row["name"], *(row["aliases"] or "").split(";")]:
            name = name.strip()
            key = normalize_name(name)
            if key and key not in seen:
                seen.add(key)
                names.append(name)
        if names:
            out.append([row["id"], row["schema"], _imo(row["identifiers"]),
                        listed_by(row["program_ids"], row["dataset"]), names[:MAX_NAMES]])
    return out
