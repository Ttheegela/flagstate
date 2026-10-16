#!/usr/bin/env python3
"""Risk-flag analysis. Pure stdlib so it runs as-is inside a Daytona sandbox.

stdin:  {"lookup": lookup() result, "live": browse.fetch_live() result,
         "memory": memory.recall() rows, "changes": optional memory.remember() changes}
stdout: {"flags": [{"flag", "severity", "evidence", "source"}], "risk": "high|medium|low|none", "flag_count": n}
"""
import json
import re
import sys

RANK = {"high": 3, "medium": 2, "low": 1}
DARK = re.compile(r"shadow[- ]fleet|dark[- ]fleet|\bAIS\b|ship-to-ship|spoof|false flag|fraudulent(ly)? flag", re.I)
CHANGE_SEVERITY = {"flag": "high", "name": "high", "owner": "high", "manager": "high", "operator": "medium"}
COMPARE_FIELDS = ("flag", "name", "manager", "owner")


def _tokens(value):
    return set(re.sub(r"[^A-Z0-9]+", " ", str(value or "").upper()).split())


def _same(a, b):
    """Loose equality: half of the shorter value's words appear in the other."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return True  # nothing to compare
    return len(ta & tb) / min(len(ta), len(tb)) >= 0.5


def _fact_source(entry, needle):
    """URL of the source cited by the first fact containing `needle`, else the last (non-list) source."""
    urls = {s["n"]: s["url"] for s in entry.get("sources", [])}
    for fact in entry.get("facts", []):
        if needle.lower() in fact.get("text", "").lower() and fact.get("refs"):
            return urls.get(fact["refs"][0])
    return entry["sources"][-1]["url"] if entry.get("sources") else None


def analyse(payload):
    lk = payload.get("lookup") or {}
    live = payload.get("live") or {}
    live_facts = live.get("facts") or {}
    live_src = (live.get("sources") or [None])[0]
    research = lk.get("research") or []
    top = research[0] if research and research[0].get("match", 0) >= 2 else None
    flags = []

    def add(flag, severity, evidence, source):
        flags.append({"flag": flag, "severity": severity, "evidence": evidence, "source": source})

    # 1. On an official list (exact name or IMO hit), then research listings not already covered.
    listed_by = set()
    for hit in lk.get("lists") or []:
        if hit.get("match") == 3 and hit["authority"] not in listed_by:
            listed_by.add(hit["authority"])
            ref = f", ref {hit['ref']}" if hit.get("ref") else ""
            add("on_official_list", "high", f"{hit['authority']} sanctions list: {hit['name']} ({hit['program']}{ref})", hit["url"])
    if top:
        urls = {s["n"]: s["url"] for s in top.get("sources", [])}
        for l in top.get("listings", []):
            if l["by"] not in listed_by:
                listed_by.add(l["by"])
                add("on_official_list", "high", f"Listed by {l['by']} on {l['date']} ({l['program']})", urls.get(l.get("ref")))

        # 2. Identity history from research.
        former = [n["name"] for n in top.get("names", []) if not n.get("current")]
        if former:
            add("name_changed", "medium", f"Has also sailed as {', '.join(former)}", _fact_source(top, "also sailed as"))
        if len(top.get("flags") or []) > 1:
            add("flag_changed", "medium", f"Has sailed under {len(top['flags'])} flags: {', '.join(top['flags'])}",
                _fact_source(top, "flag"))
        for ev in top.get("events", []):
            if ev.get("kind") in ("ownership", "management"):
                add("owner_or_manager_changed", "medium", f"{ev['date']}: {ev['text']}", _fact_source(top, ev["text"]))

        # 3. Dark-fleet indicators in sources or research text.
        dark = next((s for s in top.get("sources", []) if DARK.search(s.get("url", "") + " " + s.get("label", ""))), None)
        if dark:
            add("dark_fleet_indicator", "medium", f"Named in a shadow-fleet register: {dark['label']}", dark["url"])
        else:
            texts = [f.get("text", "") for f in top.get("facts", [])] + [top.get("role") or ""]
            hit = next((t for t in texts if DARK.search(t)), None)
            if hit:
                add("dark_fleet_indicator", "medium", hit, _fact_source(top, hit[:40]))

        # 4. Live facts disagree with the research record.
        for field in COMPARE_FIELDS:
            live_val, rec_val = live_facts.get(field), top.get(field)
            if live_val and rec_val and not _same(live_val, rec_val):
                add("live_disagrees_with_record", "medium", f"Live {field} is {live_val}; research record says {rec_val}", live_src)

    # 5. Changed since the last time we looked (agent memory).
    changed = set()
    for row in payload.get("memory") or []:
        field = row.get("field")
        if row.get("superseded_at") or field in changed or field not in live_facts:
            continue
        if not _same(row.get("value"), live_facts[field]):
            changed.add(field)
            add("changed_since_last_check", CHANGE_SEVERITY.get(field, "low"),
                f"{field} was {row.get('value')} (seen {row.get('observed_at')}), now {live_facts[field]}", live_src)
    for c in payload.get("changes") or []:
        if c.get("field") not in changed and c.get("old") is not None:
            changed.add(c["field"])
            add("changed_since_last_check", CHANGE_SEVERITY.get(c["field"], "low"),
                f"{c['field']} was {c['old']} (seen {c.get('old_observed_at')}), now {c.get('new')}", live_src)

    flags.sort(key=lambda f: -RANK[f["severity"]])
    risk = flags[0]["severity"] if flags else "none"
    return {"flags": flags, "risk": risk, "flag_count": len(flags)}


if __name__ == "__main__":
    json.dump(analyse(json.load(sys.stdin)), sys.stdout)
