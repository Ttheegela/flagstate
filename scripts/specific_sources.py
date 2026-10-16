"""Point shadow-fleet source links at the exact record instead of a list's home page.

The fleet snapshot (stories/shadow-fleet/network, built 25 Sep 2026 in the research repo) cites
whole lists ("the UK sanctions list", "the OFAC SDN list") even where each line carries the list's
record id. This rewrites those links, in place, to the official per-entry page:

  US (OFAC SDN / Consolidated Screening List rows from OFAC)  -> OFAC Sanctions List Search entry
  UK sanctions list / OFSI consolidated list                   -> UK Sanctions List entry
  LDA filing cited by id                                       -> that filing
  FARA document cited by registration and exhibit              -> that document (else FARA's filings browser)
  EU act cited only by number                                  -> that act on EUR-Lex
  Ukraine war-sanctions database home (data came from the OpenSanctions export) -> that dataset page

A line without its own record id uses the record of the entity whose list entry holds the quoted
fact: the ship when one end is a ship, otherwise the line's source. A listed node with no record id on
any line gets one from the official list files in data/lists when exactly one entry there has its exact
normalised name (OFAC ids are the numeric refs in us.json). Links that still point at a
home page are left as they are; the pages label them as list homes.

Idempotent. Run: python3 scripts/specific_sources.py, then python3 scripts/build_research_index.py.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from normalize import normalize_name

ROOT = Path(__file__).resolve().parent.parent
FLEET = ROOT / "stories" / "shadow-fleet" / "network"
MAP_HTML = FLEET / "shadow_fleet_map.html"
KG_JS = ROOT / "stories" / "who-lobbies" / "influence-network" / "kg_data.js"
LISTS = ROOT / "data" / "lists"

OFAC_ENTRY = "https://sanctionssearch.ofac.treas.gov/Details.aspx?id={}"
UK_ENTRY = "https://search-uk-sanctions-list.service.gov.uk/designations/{}/{}"
LDA_FILING = "https://lda.gov/filings/public/filing/{}/print/"
FARA_EXHIBIT = "https://efile.fara.gov/docs/{}-Exhibit-AB-{}.pdf"
FARA_BROWSE = "https://efile.fara.gov/ords/fara/f?p=1381:1"  # the bare host serves a blank server page
EU_ACT = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_{}{:05d}"
UA_HOME = "https://war-sanctions.gur.gov.ua/en"
UA_DATASET = "https://www.opensanctions.org/datasets/ua_war_sanctions/"

US_HOMES = {
    "https://sanctionslist.ofac.treas.gov/Home/SdnList",
    "https://www.trade.gov/consolidated-screening-list",
    "https://sanctionssearch.ofac.treas.gov/",
}
UK_HOMES = {
    "https://www.gov.uk/government/publications/the-uk-sanctions-list",
    "https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets",
    "https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets/consolidated-list-of-targets",
    "https://search-uk-sanctions-list.service.gov.uk",
}
UK_TYPES = {"ship": "Ship", "person": "Individual"}  # anything else is an Entity

_OFAC_ID = re.compile(r"(?:OFAC ent_num |OpenSanctions ofac-)(\d+)")
_UK_ID = re.compile(r"\b([A-Z]{3}\d{4})\b")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_FARA = re.compile(r"reg (\d+), Exhibit AB (\d{8}-\d+)")
_FARA_DOC = re.compile(r"efile\.fara\.gov/docs/[\w.-]+\.pdf")
_EU_ACT = re.compile(r"(?:Reg \(EU\) |listing )(\d{4})/(\d+)")


class Records:
    """Each node's own OFAC and UK record ids, from its designation lines."""

    def __init__(self, nodes: list, edges: list, us_names: dict | None = None, uk_names: dict | None = None) -> None:
        self.kind = {n["id"]: n["type"] for n in nodes}
        self.us: dict[str, str] = {}
        self.uk: dict[str, str] = {}
        for e in edges:
            if e["type"] != "designated_by":
                continue
            for s in e.get("sources") or [e]:
                record = s.get("record") or ""
                if m := _OFAC_ID.search(record):
                    self.us.setdefault(e["source"], m.group(1))
                elif m := _UK_ID.fullmatch(record):
                    self.uk.setdefault(e["source"], m.group(1))
        for n in nodes:
            names = {normalize_name(x) for x in [n.get("name") or "", *(n.get("aliases") or [])]} - {""}
            for gov, ids, index in (("us", self.us, us_names or {}), ("uk", self.uk, uk_names or {})):
                if n["id"] in ids or gov not in (n.get("listed_by") or []):
                    continue
                found = set().union(*(index.get(k, set()) for k in names)) if names else set()
                if len(found) == 1:
                    ids[n["id"]] = found.pop()
        self.uk_owner = {rec: node for node, rec in self.uk.items()}

    def holder(self, source: str, target: str) -> list[str]:
        """Whose list entry holds a line's fact: the ship if one end is a ship, else the source."""
        return [target, source] if target.startswith("IMO") and not source.startswith("IMO") else [source, target]

    def uk_url(self, rec: str, node: str | None = None) -> str:
        node = node or self.uk_owner.get(rec, "")
        return UK_ENTRY.format(rec, UK_TYPES.get(self.kind.get(node, ""), "Entity"))


def specific_url(url: str, record: str, file: str, quote: str, source: str, target: str, recs: Records) -> str:
    record, file, quote = record or "", file or "", quote or ""
    if url in US_HOMES:
        if m := _OFAC_ID.search(record):
            return OFAC_ENTRY.format(m.group(1))
        for node in recs.holder(source, target):
            if node in recs.us:
                return OFAC_ENTRY.format(recs.us[node])
        return url
    if url in UK_HOMES:
        if m := (_UK_ID.fullmatch(record) or _UK_ID.search(file) or _UK_ID.search(quote)):
            return recs.uk_url(m.group(1))
        for node in recs.holder(source, target):
            if node in recs.uk:
                return recs.uk_url(recs.uk[node], node)
        return url
    if url in ("https://lda.senate.gov", "https://efile.fara.gov"):
        if m := _FARA.search(file):
            return FARA_EXHIBIT.format(*m.groups())
        if m := _FARA_DOC.search(file):
            return "https://" + m.group(0)
        if m := _UUID.search(file):
            return LDA_FILING.format(m.group(0))
        return FARA_BROWSE if "fara" in url else url
    if url == "https://eur-lex.europa.eu/" and (m := _EU_ACT.search(quote)):
        return EU_ACT.format(m.group(1), int(m.group(2)))
    if url == UA_HOME:
        return UA_DATASET
    return url


def fix_edges(edges: list, recs: Records) -> dict:
    """Rewrite edges.json in place; return {(old url, quote): new url} for files without record ids."""
    seen: dict = {}
    for e in edges:
        for s in e.get("sources") or []:
            new = specific_url(s["url"], s.get("record") or e.get("record"), s.get("file"), s.get("quote"), e["source"], e["target"], recs)
            seen.setdefault((s["url"], s.get("quote") or ""), set()).add(new)
            s["url"] = new
        if e.get("sources"):
            e["source_url"] = e["sources"][0]["url"]
        elif e.get("source_url"):
            e["source_url"] = specific_url(e["source_url"], e.get("record"), e.get("source_file"), e.get("quote"), e["source"], e["target"], recs)
    return {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}


def fix_node_sources(nodes: list) -> None:
    for n in nodes:
        for s in n.get("sources") or []:
            if s.get("url") == UA_HOME:
                s["url"] = UA_DATASET
                s["label"] = "Ukraine War and Sanctions database (GUR; not a sanctions list), OpenSanctions export: names and flag countries"


def fix_profiles(obj, by_quote: dict) -> None:
    if isinstance(obj, dict):
        if isinstance(obj.get("url"), str):
            obj["url"] = by_quote.get((obj["url"], obj.get("quote") or ""), obj["url"])
        for v in obj.values():
            fix_profiles(v, by_quote)
    elif isinstance(obj, list):
        for v in obj:
            fix_profiles(v, by_quote)


def fix_map(data: dict, recs: Records) -> None:
    """FLEET_DATA keeps sources as a table of [url, file]; lines point into it as [src, quote, record, angle, conf]."""
    table = data["sources"]
    index = {tuple(s): i for i, s in enumerate(table)}
    for e in data["edges"]:
        for r in e.get("src") or []:
            url, file = table[r[0]]
            quote = data["quotes"][r[1]] if r[1] is not None else ""
            new = specific_url(url, r[2], file, quote, e["s"], e["t"], recs)
            if new != url:
                key = (new, file)
                if key not in index:
                    index[key] = len(table)
                    table.append([new, file])
                r[0] = index[key]
    fix_node_sources(data["nodes"])


def fix_kg(data: dict, recs: Records) -> None:
    for e in data["edges"]:
        if e.get("u"):
            e["u"] = specific_url(e["u"], e.get("r"), e.get("f"), e.get("q"), e["s"], e["t"], recs)


def name_index(list_id: str, pattern: str) -> dict[str, set[str]]:
    """Normalised name -> record ids, for the ids that have an official per-entry page."""
    out: dict[str, set[str]] = {}
    for rec in json.loads((LISTS / f"{list_id}.json").read_text(encoding="utf-8"))["records"]:
        if re.fullmatch(pattern, rec[4]):
            out.setdefault(rec[1], set()).add(rec[4])
    return out


def main() -> None:
    nodes = json.loads((FLEET / "nodes.json").read_text(encoding="utf-8"))
    edges = json.loads((FLEET / "edges.json").read_text(encoding="utf-8"))
    recs = Records(nodes, edges, name_index("us", r"\d+"), name_index("uk", r"[A-Z]{3}\d{4}"))
    by_quote = fix_edges(edges, recs)
    fix_node_sources(nodes)
    (FLEET / "edges.json").write_text(json.dumps(edges, indent=1, ensure_ascii=False), encoding="utf-8")
    (FLEET / "nodes.json").write_text(json.dumps(nodes, indent=1, ensure_ascii=False), encoding="utf-8")

    profiles = json.loads((FLEET / "ship_profiles.json").read_text(encoding="utf-8"))
    fix_profiles(profiles, by_quote)
    (FLEET / "ship_profiles.json").write_text(json.dumps(profiles, ensure_ascii=False), encoding="utf-8")

    html = MAP_HTML.read_text(encoding="utf-8")
    head = "window.FLEET_DATA="
    start = html.index(head) + len(head)
    end = html.index(";</script>", start)
    data = json.loads(html[start:end])
    fix_map(data, recs)
    MAP_HTML.write_text(html[:start] + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + html[end:], encoding="utf-8")

    js = KG_JS.read_text(encoding="utf-8")
    kg = json.loads(js[len("window.KG="):-2])
    fix_kg(kg, recs)
    KG_JS.write_text("window.KG=" + json.dumps(kg, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")


if __name__ == "__main__":
    main()
