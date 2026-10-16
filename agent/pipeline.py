"""investigate(query): lookup -> recall -> browse -> analyse -> remember -> brief -> eval.
Each step is timed, traced and reported via on_step; a failing step is recorded and the job continues."""
from __future__ import annotations

import importlib
import json
import time
from datetime import datetime, timezone

from . import llm, lookup, sandbox, tracing

STEPS = ("lookup", "recall", "browse", "analyse", "remember", "brief", "eval")


class Skipped(Exception):
    pass


def _mod(name: str):
    """Sibling modules owned by the tools agent (browse, memory, voice); None if missing or broken."""
    try:
        return importlib.import_module(f"{__package__}.{name}")
    except Exception:
        return None


def _require(name: str):
    mod = _mod(name)
    if mod is None:
        raise Skipped(f"{name} module unavailable")
    return mod


def grounding_eval(briefing: dict, context: dict) -> dict:
    """Fraction of claims whose source URL appears in the gathered context."""
    claims = briefing.get("claims") or []
    haystack = json.dumps(context, default=str)
    grounded = [c for c in claims if c.get("source") and c["source"] in haystack]
    score = len(grounded) / len(claims) if claims else 0.0
    label = "no_claims" if not claims else "grounded" if score == 1 else "partially_grounded" if grounded else "ungrounded"
    return {"name": "claims_grounded", "score": round(score, 3), "label": label,
            "explanation": f"{len(grounded)}/{len(claims)} claims cite a source found in the gathered context"}


def _detail(name: str, out) -> str:
    if out is None:
        return ""
    if name == "lookup":
        return f"{len(out['research'])} research matches, {len(out['lists'])} list hits"
    if name == "recall":
        return f"{len(out)} remembered facts"
    if name == "browse":
        return f"{len(out.get('facts') or {})} live facts from {len(out.get('sources') or [])} sources"
    if name == "analyse":
        return f"{out['flag_count']} flags, risk {out['risk']} (ran in {out.get('ran_in')})"
    if name == "remember":
        return f"{len(out)} changes recorded"
    if name == "brief":
        return f"{len(out['claims'])} claims via {out.get('model')}"
    if name == "eval":
        return out["explanation"]
    return ""


def investigate(query: str, on_step=None) -> dict:
    on_step = on_step or (lambda step: None)
    steps: list[dict] = []
    result: dict = {"query": query, "steps": steps}

    def run(name, fn, kind="CHAIN", input=None):
        rec = {"name": name, "status": "running", "detail": "", "ms": 0}
        steps.append(rec)
        on_step(dict(rec))
        t0 = time.perf_counter()
        out = None
        with tracing.span(name, kind=kind, input=input) as s:
            try:
                out = fn()
                rec.update(status="done", detail=_detail(name, out))
                tracing.set_output(s, out)
            except Skipped as e:
                rec.update(status="skipped", detail=str(e))
            except Exception as e:
                rec.update(status="error", detail=f"{type(e).__name__}: {e}"[:300])
        rec["ms"] = int((time.perf_counter() - t0) * 1000)
        on_step(dict(rec))
        return out

    with tracing.span("investigate", kind="AGENT", input=query) as root:
        lk = run("lookup", lambda: lookup.lookup(query), "TOOL", query) or {"research": [], "lists": [], "imo": None}
        top = lk["research"][0] if lk["research"] else None
        imo = lk.get("imo") or (top or {}).get("imo")
        subject = (top["name"] if top and top["match"] >= 2 else None) or query
        key = f"IMO{imo}" if imo else lookup.normalize_name(subject) or subject
        result.update(subject=subject, imo=imo, lookup=lk)

        memory = run("recall", lambda: _require("memory").recall(key), "TOOL", key) or []
        def on_live_view(url):  # surface the Anchor live view while the session is still open
            on_step({"name": "browse", "status": "running", "detail": "browser session live", "ms": 0, "live_view_url": url})

        live = run("browse", lambda: _require("browse").fetch_live(subject, imo=imo, on_live_view=on_live_view), "TOOL", {"query": subject, "imo": imo}) or {}
        analysis = run("analyse", lambda: sandbox.run_analysis({"lookup": lk, "live": live, "memory": memory}), "TOOL") or {}

        def remember():
            facts, source = live.get("facts") or {}, (live.get("sources") or [None])[0]
            if not facts and top:  # no live data: seed memory with the research record as a baseline
                facts = {k: top.get(k) for k in ("name", "flag", "manager") if top.get(k)}
                source = top["sources"][-1]["url"] if top.get("sources") else None
            if not facts:
                raise Skipped("no facts to remember")
            return _require("memory").remember(key, facts, source or "", datetime.now(timezone.utc).isoformat())

        changes = run("remember", remember, "TOOL") or []
        context = {"query": query, "subject": subject, "imo": imo, "research": lk["research"][:2],
                   "lists": lk["lists"][:5], "live": live, "analysis": analysis, "changes": changes}
        briefing = run("brief", lambda: llm.brief(context), "LLM", context) or {"text": "", "claims": []}

        def evaluate():
            ev = grounding_eval(briefing, context)
            tracing.log_eval(ev["name"], ev["score"], ev["label"], ev["explanation"])
            return ev

        ev = run("eval", evaluate, "EVALUATOR")
        if ev:
            tracing.log_eval(ev["name"], ev["score"], ev["label"], ev["explanation"])  # also on the root span
        result.update(live=live, memory=memory, analysis=analysis, changes=changes, briefing=briefing, eval=ev,
                      flags=analysis.get("flags") or [],
                      sandbox={"ran_in": analysis.get("ran_in"), "sandbox_id": analysis.get("sandbox_id")})
        tracing.set_output(root, {"briefing": briefing.get("text"), "risk": analysis.get("risk")})
    return result
