"""Time-aware facts per subject: a new value supersedes the old one, history is kept.

Store: SurrealDB Agent Memory REST (POST /api/v1/{ctx}/facts, POST /api/v1/{ctx}/query) when
SURREAL_MEMORY_URL + SURREAL_MEMORY_TOKEN are set; otherwise (or if it errors) a local JSON file
agent/.memory.json with identical semantics. Each fact row: field, value, source, observed_at.
"""
from __future__ import annotations

import json
import logging
import re
import threading

import httpx

from agent.config import AGENT_DIR, env

LOCAL = AGENT_DIR / ".memory.json"
_lock = threading.Lock()
log = logging.getLogger(__name__)


def _key(subject: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")


def _norm(value) -> str:
    return str(value).strip().casefold()


def _client() -> httpx.Client | None:
    url, token = env("SURREAL_MEMORY_URL"), env("SURREAL_MEMORY_TOKEN")
    if not (url and token):
        return None
    base = url.rstrip("/")
    if "/api/v1/" not in base:
        base += "/api/v1/" + env("SURREAL_MEMORY_CONTEXT", "flagstate")
    return httpx.Client(base_url=base, headers={"Authorization": f"Bearer {token}"}, timeout=20)


def _remote_load(c: httpx.Client, key: str, subject: str) -> list[dict]:
    r = c.post("/query", json={"query": subject, "k": 50, "labels": [f"subject={key}"]})
    r.raise_for_status()
    rows = []
    for hit in r.json().get("hits", []):
        try:
            row = json.loads(hit.get("text", ""))
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("subject_key") == key:
            rows.append(row)
    return rows


def _remote_append(c: httpx.Client, key: str, subject: str, rows: list[dict]) -> None:
    for row in rows:
        c.post("/facts", json={
            "text": json.dumps({"subject_key": key, "subject": subject, **row}),
            "infer": "none",  # literal store: keeps the row exact and traceable to its source
            "memory_category": "knowledge",
            "labels": [f"subject={key}", f"field={row['field']}"],
        }).raise_for_status()  # observed_at is not allowed on literal writes; it lives inside the row
        # Same fact as a sentence for Agent Memory's knowledge graph (entities, relations, known-time).
        # Best effort: the literal row above is what recall depends on.
        try:
            c.post("/facts", json={
                "text": f"{subject} {row['field']} is {row['value']} (source: {row.get('source') or 'unknown'})",
                "infer": "full",
                "labels": [f"subject={key}", f"field={row['field']}"],
                "observed_at": row["observed_at"],
            }).raise_for_status()
        except httpx.HTTPError as e:
            log.warning("agent memory graph write failed: %s", type(e).__name__)


def _local_read() -> dict:
    return json.loads(LOCAL.read_text()) if LOCAL.exists() else {}


def _load(subject: str) -> list[dict]:
    key, c = _key(subject), _client()
    if c:
        try:
            with c:
                return _remote_load(c, key, subject)
        except httpx.HTTPError as e:
            log.warning("agent memory recall failed, using local file: %s", type(e).__name__)
    with _lock:
        return _local_read().get(key, [])


def _append(subject: str, rows: list[dict]) -> None:
    key, c = _key(subject), _client()
    if c:
        try:
            with c:
                return _remote_append(c, key, subject, rows)
        except httpx.HTTPError as e:
            log.warning("agent memory remember failed, using local file: %s", type(e).__name__)
    with _lock:
        data = _local_read()
        data.setdefault(key, []).extend(rows)
        LOCAL.write_text(json.dumps(data, indent=1))


def recall(subject: str) -> list[dict]:
    """Full history, oldest first. superseded_at is when the next value for that field was observed."""
    rows = sorted(_load(subject), key=lambda r: r["observed_at"])
    out, later = [], {}
    for r in reversed(rows):
        out.append({"field": r["field"], "value": r["value"], "source": r["source"],
                    "observed_at": r["observed_at"], "superseded_at": later.get(r["field"])})
        later[r["field"]] = r["observed_at"]
    return out[::-1]


def remember(subject: str, facts: dict, source: str, observed_at: str) -> list[dict]:
    """Store facts; a changed value supersedes the current one. Returns the changes vs previous values."""
    current = {r["field"]: r for r in recall(subject) if r["superseded_at"] is None}
    changes, rows = [], []
    for field, value in facts.items():
        if value is None or value == "":
            continue
        old = current.get(field)
        if old and _norm(old["value"]) == _norm(value):
            continue
        rows.append({"field": field, "value": value, "source": source, "observed_at": observed_at})
        if old:
            changes.append({"field": field, "old": old["value"], "new": value, "old_observed_at": old["observed_at"]})
    if rows:
        _append(subject, rows)
    return changes
