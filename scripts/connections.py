"""Compact sanctions-relationship graph from OpenSanctions' entities.ftm.json (CC BY-NC 4.0).

parse(lines) reads FollowTheMoney JSON lines and returns
    {"entities": [[id, schema, names, imo, authorities]],
     "links":    [[subject, object, kind, role, authorities]]}
A link reads as the sentence "subject role object", e.g. TASSOS / Property in the
interest of / Zulu Ships Management. Only entities that appear in a link are kept.
"""
from __future__ import annotations

import json

SOURCE_URL = "https://data.opensanctions.org/datasets/latest/sanctions/entities.ftm.json"
PAGE_URL = "https://www.opensanctions.org/datasets/sanctions/"
ENTITY_SCHEMAS = {"Person", "Organization", "Company", "LegalEntity", "Vessel", "Airplane"}
MAX_NAMES = 6
# kind -> (first property, second property, default wording reading first -> second)
RELATIONS = {
    "Directorship": ("director", "organization", "Director of"),
    "UnknownLink": ("subject", "object", "Linked to"),
    "Representation": ("agent", "client", "Acting for"),
    "Membership": ("member", "organization", "Member of"),
    "Family": ("person", "relative", "Family member of"),
}
ROLE_TRANSLATIONS = {
    "Līdzekļi": "Linked to (assets)",
    "Līdzekļi; kapitāldaļas": "Linked to (assets, shares)",
    "related-to": "Related to",
}
DATASET_AUTHORITIES = {
    "us": "US", "gb": "UK", "eu": "EU", "un": "UN", "ch": "Switzerland", "ca": "Canada", "au": "Australia",
    "nz": "New Zealand", "jp": "Japan", "ua": "Ukraine", "fr": "France", "de": "Germany", "lv": "Latvia",
    "lt": "Lithuania", "sa": "Saudi Arabia", "il": "Israel", "vn": "Vietnam", "in": "India", "pl": "Poland",
}


def authorities(datasets) -> list[str]:
    out: list[str] = []
    for ds in datasets or []:
        prefix = ds.split("_")[0].lower()
        label = DATASET_AUTHORITIES.get(prefix, prefix.upper())
        if label not in out:
            out.append(label)
    return out


def _first(values) -> str:
    return (values or [""])[0].strip()


def _sentence(kind: str, props: dict):
    """Return (subjects, objects, role) so that "subject role object" reads correctly."""
    if kind == "Ownership":
        role = _first(props.get("role"))
        if role.lower().startswith("owns"):
            return props.get("owner") or [], props.get("asset") or [], role
        return props.get("asset") or [], props.get("owner") or [], role or "Owned by"
    first, second, default = RELATIONS[kind]
    role = _first(props.get("relationship" if kind == "Family" else "role")) or default
    return props.get(first) or [], props.get(second) or [], role


def _imo(props: dict) -> str:
    for value in props.get("imoNumber") or []:
        digits = value.upper().removeprefix("IMO").strip()
        if len(digits) == 7 and digits.isdigit():
            return digits
    return ""


def parse(lines) -> dict:
    entities: dict[str, list] = {}
    merged: dict[tuple, list] = {}
    seen = 0
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except ValueError as exc:
            raise ValueError(f"connections: bad JSON line ({exc})") from exc
        seen += 1
        schema = record.get("schema")
        props = record.get("properties") or {}
        if schema == "Ownership" or schema in RELATIONS:
            subjects, objects, role = _sentence(schema, props)
            role = ROLE_TRANSLATIONS.get(role, role)
            auth = authorities(record.get("datasets"))
            for s in subjects:
                for o in objects:
                    if s == o:
                        continue
                    key = (s, o, schema, role)
                    if key in merged:
                        merged[key][4] += [a for a in auth if a not in merged[key][4]]
                    else:
                        merged[key] = [s, o, schema, role, list(auth)]
        elif schema in ENTITY_SCHEMAS:
            names: list[str] = []
            for name in [record.get("caption") or "", *(props.get("name") or []), *(props.get("alias") or [])]:
                name = name.strip()
                if name and name not in names:
                    names.append(name)
            if names:
                entities[record["id"]] = [record["id"], schema, names[:MAX_NAMES], _imo(props), authorities(record.get("datasets"))]
    if not seen:
        raise ValueError("connections: no FollowTheMoney records")
    links = [l for l in merged.values() if l[0] in entities and l[1] in entities]
    used = {x for l in links for x in l[:2]}
    return {"entities": [entities[i] for i in sorted(used)], "links": links}
