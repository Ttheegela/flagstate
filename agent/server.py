"""FastAPI service. Run from repo root: agent/.venv/bin/uvicorn agent.server:app --port 8787"""
from __future__ import annotations

import threading
from functools import lru_cache
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from . import lookup, pipeline, tracing
from .config import env

app = FastAPI(title="Flagstate agent")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in env("ALLOWED_ORIGINS", "*").split(",")],
                   allow_methods=["*"], allow_headers=["*"])
tracing.setup()
threading.Thread(target=lookup._data, daemon=True).start()  # warm the data cache so tool calls stay fast

JOBS: dict[str, dict] = {}  # ponytail: in-memory, lost on restart; fine for a demo


class Query(BaseModel):
    query: str


class JobRef(BaseModel):
    job_id: str | None = None  # voice agent may forget it; default to the latest job


def _start(query: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    job = {"id": job_id, "query": query, "status": "running", "steps": [], "result": None, "error": None, "audio": None}
    JOBS[job_id] = job

    def on_step(step):
        for i, s in enumerate(job["steps"]):
            if s["name"] == step["name"]:
                job["steps"][i] = step
                return
        job["steps"].append(step)

    def work():
        try:
            job["result"] = pipeline.investigate(query, on_step)
            job["status"] = "done"
        except Exception as e:
            job["status"], job["error"] = "error", f"{type(e).__name__}: {e}"

    threading.Thread(target=work, daemon=True).start()
    return job_id


def _job(job_id: str | None) -> dict:
    job = JOBS.get(job_id) if job_id else (list(JOBS.values())[-1] if JOBS else None)
    if not job:
        raise HTTPException(404, "job not found")
    return job


def _say_lookup(lk: dict) -> str:
    research, hits = lk["research"], [h for h in lk["lists"] if h["match"] == 3]
    if not research and not hits:
        return f"I found no match for {lk['query']} in the research or the official sanctions lists."
    parts = []
    if research:
        r = research[0]
        desc = ", ".join(x for x in (r.get("kind"), f"IMO {r['imo']}" if r.get("imo") else None,
                                     f"flagged {r['flag']}" if r.get("flag") else None) if x)
        parts.append(f"{r['name']}{', ' + desc if desc else ''}.")
        if r.get("listings"):
            parts.append("Listed by " + ", ".join(f"{l['by']} ({l['program']})" for l in r["listings"]) + ".")
    elif hits:
        authorities = sorted({h["authority"] for h in hits})
        parts.append(f"{hits[0]['name']} is on the {', '.join(authorities)} sanctions list.")
    return " ".join(parts)


def _compact_lookup(lk: dict) -> dict:
    return {"imo": lk["imo"],
            "research": [{k: r.get(k) for k in ("name", "kind", "imo", "flag", "manager")} for r in lk["research"][:3]],
            "lists": [{k: h[k] for k in ("authority", "name", "program", "url")} for h in lk["lists"][:5]]}


@app.get("/health")
def health():
    keys = {"daytona": "DAYTONA_API_KEY", "anchor": "ANCHOR_API_KEY", "arize": "ARIZE_API_KEY",
            "elevenlabs": "ELEVENLABS_API_KEY", "surreal": "SURREAL_MEMORY_URL"}
    configured = {name: bool(env(var)) for name, var in keys.items()}
    configured["bedrock"] = _aws_credentials()  # env keys locally, the instance role on EC2
    return {"ok": True, "configured": configured}


@lru_cache(maxsize=1)
def _aws_credentials() -> bool:
    import boto3
    return boto3.Session().get_credentials() is not None


@app.post("/investigate")
def investigate(body: Query):
    return {"job_id": _start(body.query)}


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = _job(job_id)
    return {"status": job["status"], "steps": job["steps"], "result": job["result"], "error": job["error"]}


@app.get("/jobs/{job_id}/audio")
def job_audio(job_id: str):
    job = _job(job_id)
    if job["status"] != "done":
        raise HTTPException(409, "job not finished")
    if job["audio"] is None:
        voice = pipeline._mod("voice")
        text = (job["result"].get("briefing") or {}).get("text")
        try:
            audio = voice.tts(text) if voice and text else None
        except Exception:  # voice.VoiceUnavailable or any API error
            audio = None
        if not audio:
            raise HTTPException(503, "text-to-speech unavailable")
        job["audio"] = audio
    return Response(content=job["audio"], media_type="audio/mpeg")


# ElevenLabs Conversational AI server tools: fast, compact JSON with a "say" line.
@app.post("/tools/search")
def tool_search(body: Query):
    lk = lookup.lookup(body.query)
    return {"say": _say_lookup(lk), **_compact_lookup(lk)}


@app.post("/tools/investigate")
def tool_investigate(body: Query):
    lk = lookup.lookup(body.query)
    job_id = _start(body.query)
    say = _say_lookup(lk) + " I've started a full investigation with live sources; ask me for the status in a few seconds."
    return {"say": say, "job_id": job_id, **_compact_lookup(lk)}


@app.post("/tools/status")
def tool_status(body: JobRef):
    job = _job(body.job_id)
    steps = [{"name": s["name"], "status": s["status"]} for s in job["steps"]]
    if job["status"] == "error":
        return {"say": "The investigation failed. " + (job["error"] or ""), "status": "error", "job_id": job["id"], "steps": steps}
    if job["status"] != "done":
        running = next((s["name"] for s in job["steps"] if s["status"] == "running"), "starting")
        done = [s["name"] for s in job["steps"] if s["status"] != "running"]
        say = f"Still working. Current step: {running}." + (f" Finished: {', '.join(done)}." if done else "")
        return {"say": say, "status": "running", "job_id": job["id"], "steps": steps}
    res = job["result"]
    flags = [{k: f[k] for k in ("flag", "severity", "evidence")} for f in (res.get("analysis") or {}).get("flags", [])[:3]]
    briefing = (res.get("briefing") or {}).get("text") or "The investigation finished but produced no briefing."
    return {"say": briefing, "status": "done", "job_id": job["id"], "steps": steps,
            "risk": (res.get("analysis") or {}).get("risk"), "top_flags": flags}
