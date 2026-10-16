"""Anchor Browser: live public facts for a ship (VesselFinder) or a company (OpenCorporates search).

Fast route: Anchor Web Unlocker (POST /v1/tools/fetch/webpage) + regex parse.
Fallback: one proxied Anchor session + AI task (POST /v1/tools/perform-web-task) returning JSON,
session deleted afterwards. The session's cdp_url embeds the API key: never log it.
"""
from __future__ import annotations

import html
import json
import re
from urllib.parse import quote_plus

import httpx

from agent.config import env

API = "https://api.anchorbrowser.io/v1"
VESSEL_URL = "https://www.vesselfinder.com/vessels/details/{imo}"
COMPANY_URL = "https://opencorporates.com/companies?q={q}"
OPENCORPORATES = "https://opencorporates.com"

# VesselFinder row label -> fact key. "AIS Flag" comes before "Flag" in the page, first non-empty wins.
VESSEL_FIELDS = {
    "Vessel Name": "name", "IMO number": "imo", "Callsign": "callsign", "Ship Type": "ship_type",
    "AIS Flag": "flag", "Flag": "flag", "Year of Build": "year_built", "Gross Tonnage": "gross_tonnage",
    "Deadweight": "deadweight", "Registered Owner": "registered_owner", "Manager": "manager",
    "ISM Manager": "ism_manager", "Navigation Status": "nav_status",
}
ROW = re.compile(r'<td class="(?:n3|tpc1)">((?:(?!<td).)*?)</td>\s*<td class="(?:v3|tpc2)[^"]*"[^>]*>(.*?)</td>', re.S)
EMPTY = {"", "-", "unknown", "n/a", "none", "null", "destination not available"}

VESSEL_TASK = ("Read this vessel details page. Return the vessel's current particulars as JSON: name, flag, "
               "ship_type, registered_owner, manager, destination, last_position_at. Use null for anything not shown.")
COMPANY_TASK = ("This is an OpenCorporates search for '{query}'. Return the best matching company as JSON: "
                "name, jurisdiction, company_number, status, registry_url. Use null for anything not shown.")


def _text(s: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def _put(facts: dict, key: str, value: str) -> None:
    if value.casefold() not in EMPTY:
        facts.setdefault(key, value)


def parse_vessel(page: str) -> dict:
    facts: dict = {}
    for label_html, value_html in ROW.findall(page):
        label = re.sub(r"\(.*?\)", "", _text(label_html)).strip()
        if label == "IMO / MMSI":
            _put(facts, "mmsi", _text(value_html).split("/")[-1].strip())
        elif label == "Position Received":
            when = re.search(r'data-title="([^"]+)"', value_html)
            _put(facts, "last_position_at", when.group(1) if when else "")
        elif label in VESSEL_FIELDS:
            _put(facts, VESSEL_FIELDS[label], _text(value_html))
    dest = re.search(r'class="_3-Yih">(.*?)</div>', page, re.S)
    if dest:
        _put(facts, "destination", _text(dest.group(1)))
    return facts


def parse_company(page: str) -> dict:
    # ponytail: OpenCorporates markup is from memory, not a saved sample; empty result falls back to the AI task.
    hits = []
    for attrs, name in re.findall(r'<a\b([^>]*\bcompany_search_result\b[^>]*)>(.*?)</a>', page, re.S):
        href = re.search(r'href="(/companies/([^/"]+)/([^"]+))"', attrs)
        if href:
            hits.append({"name": _text(name), "jurisdiction": href.group(2), "company_number": href.group(3),
                         "registry_url": OPENCORPORATES + href.group(1)})
    if not hits:
        return {}
    return {**hits[0], "match_count": str(len(hits))}


def _schema(*keys: str) -> dict:
    return {"type": "object", "properties": {k: {"type": ["string", "null"]} for k in keys}}


def _client(key: str) -> httpx.Client:
    return httpx.Client(base_url=API, headers={"anchor-api-key": key}, timeout=30)


def _ai_task(c: httpx.Client, url: str, prompt: str, schema: dict, on_live_view) -> tuple[dict, str | None]:
    r = c.post("/sessions", json={"session": {"proxy": {"active": True}}})
    r.raise_for_status()
    data = r.json()["data"]  # contains cdp_url (has the API key): never print/log this dict
    sid, live = data["id"], data.get("live_view_url")
    if on_live_view and live:
        on_live_view(live)
    try:
        r = c.post("/tools/perform-web-task", params={"sessionId": sid}, timeout=90,
                   json={"url": url, "prompt": prompt, "output_schema": schema})
        r.raise_for_status()
        result = r.json()["data"]["result"]
    finally:
        c.delete(f"/sessions/{sid}")
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except ValueError:
            result = {"summary": result}
    facts: dict = {}
    for k, v in (result or {}).items():
        if v is not None:
            _put(facts, k, str(v).strip())
    return facts, live


def fetch_live(query: str, imo: str | None = None, on_live_view=None) -> dict:
    """Current public facts. `on_live_view(url)` (optional) fires when a browser session starts,
    so the UI can embed the live view while the task runs (the session is deleted before we return)."""
    key = env("ANCHOR_API_KEY")
    if not key:
        return {"available": False, "reason": "no ANCHOR_API_KEY", "facts": {}, "sources": [], "live_view_url": None}
    if imo:
        url, parse, prompt = VESSEL_URL.format(imo=imo), parse_vessel, VESSEL_TASK
        schema = _schema("name", "flag", "ship_type", "registered_owner", "manager", "destination", "last_position_at")
    else:
        url, parse, prompt = COMPANY_URL.format(q=quote_plus(query)), parse_company, COMPANY_TASK.format(query=query)
        schema = _schema("name", "jurisdiction", "company_number", "status", "registry_url")
    out = {"available": True, "facts": {}, "sources": [url], "live_view_url": None, "method": "web_unlocker"}
    with _client(key) as c:
        try:
            r = c.post("/tools/fetch/webpage", json={"url": url})
            r.raise_for_status()
            out["facts"] = parse(r.text)
        except httpx.HTTPError:
            pass
        if out["facts"]:
            return out
        out["method"] = "ai_task"
        try:
            out["facts"], out["live_view_url"] = _ai_task(c, url, prompt, schema, on_live_view)
        except Exception as e:  # noqa: BLE001 - contract: never raise, report why
            out.update(available=False, reason=f"anchor {type(e).__name__}: {str(e)[:200]}")
    return out
