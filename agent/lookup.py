"""Search the repo's research index and official lists. Port of app/search.js;
name normalisation comes straight from scripts/normalize.py."""
from __future__ import annotations

import importlib.util
import json
import re
from functools import lru_cache

from .config import REPO_ROOT

DATA = REPO_ROOT / "data"
LIST_IDS = ("us", "uk", "eu", "un")
LIMIT = 10
RESEARCH_LIMIT = 5
_ANY_IMO = re.compile(r"(?<!\d)(\d{7})(?!\d)")

# Load scripts/normalize.py by path so scripts/ never lands on sys.path.
_spec = importlib.util.spec_from_file_location("flagstate_normalize", REPO_ROOT / "scripts" / "normalize.py")
_normalize = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_normalize)
normalize_name, parse_imo = _normalize.normalize_name, _normalize.parse_imo


@lru_cache(maxsize=1)
def _data():
    research = json.loads((DATA / "research-index.json").read_text())["entries"]
    meta = json.loads((DATA / "lists" / "meta.json").read_text())["lists"]
    lists = {l: json.loads((DATA / "lists" / f"{l}.json").read_text())["records"] for l in LIST_IDS}
    return research, lists, meta


def _score(q_norm: str, tokens: list[str], norm: str) -> int:
    """3 exact, 2 every query word present, 1 at least 60% of words; last word may be a prefix."""
    if not norm or not tokens:
        return 0
    if norm == q_norm:
        return 3
    words = norm.split()
    last = len(tokens) - 1
    hit = sum(
        1 for i, t in enumerate(tokens)
        if t in words or (i == last and len(t) >= 3 and any(w.startswith(t) for w in words))
    )
    if hit == len(tokens):
        return 2
    return 1 if hit / len(tokens) >= 0.6 else 0


def lookup(query: str) -> dict:
    text = (query or "").strip()
    imo = parse_imo(text)
    if not imo:
        m = _ANY_IMO.search(text)
        imo = m.group(1) if m else None
    q_norm = "" if imo else normalize_name(text)
    tokens = q_norm.split() if q_norm else []
    out = {"query": text, "imo": imo, "research": [], "lists": []}
    if not (imo or tokens):
        return out
    research, lists, meta = _data()

    scored = []
    for e in research:
        s = (3 if e.get("imo") == imo else 0) if imo else max((_score(q_norm, tokens, k) for k in e["keys"]), default=0)
        if s:
            scored.append((s, e))
    scored.sort(key=lambda x: (-x[0], len(x[1]["name"]), x[1]["name"]))
    out["research"] = [{**{k: v for k, v in e.items() if k != "keys"}, "match": s} for s, e in scored[:RESEARCH_LIMIT]]

    hits = []
    for list_id, records in lists.items():
        for r in records:
            s = (3 if r[5] == imo else 0) if imo else _score(q_norm, tokens, r[1])
            if s:
                hits.append((s, list_id, r))
    hits.sort(key=lambda x: (-x[0], len(x[2][0])))
    seen = set()
    for s, list_id, r in hits:
        key = f"{list_id}:{r[4]}" if r[4] else f"{list_id}:name:{r[1]}"
        if key in seen:
            continue
        seen.add(key)
        out["lists"].append({
            "list": list_id, "authority": meta[list_id]["label"], "name": r[0], "program": r[2],
            "date": r[3], "ref": r[4], "imo": r[5], "url": r[6] or meta[list_id]["source_url"], "match": s,
        })
        if len(out["lists"]) == LIMIT:
            break

    top = out["research"][0] if out["research"] else None
    if not imo and top and top["match"] == 3:
        out["imo"] = top.get("imo")
    return out
