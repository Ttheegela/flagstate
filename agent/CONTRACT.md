# Flagstate agent: module contract

Python 3.12 service in `agent/`. Every sponsor module must work with its key missing:
it returns a clearly marked fallback (`{"available": False, "reason": ...}` or a stub) instead of raising,
so the pipeline and tests run offline. Config comes from env (`agent/.env`, loaded once in `config.py`).

| File | Owner | Function(s) |
|---|---|---|
| `config.py` | backend | `env(name, default=None)` reads os.environ after `load_dotenv(agent/.env)` |
| `lookup.py` | backend | `lookup(query) -> {"query", "imo", "research": [...], "lists": [...]}` over repo `data/` (research-index + official lists) |
| `llm.py` (AWS Bedrock) | backend | `brief(context: dict) -> {"text": str, "claims": [{"text", "source"}]}` |
| `sandbox.py` (Daytona) | backend | `run_analysis(payload: dict) -> dict` runs `analysis.py` inside a Daytona sandbox, returns its JSON output |
| `analysis.py` | backend | pure script: reads JSON on stdin, writes JSON risk flags (flag/name/owner changes, list hits) |
| `tracing.py` (Arize) | backend | `setup()`; `span(name, **attrs)` context manager; `log_eval(name, score, label, explanation)` |
| `pipeline.py` | backend | `investigate(query, on_step) -> result`; steps: lookup, recall, browse, analyse, remember, brief, eval |
| `server.py` | backend | FastAPI app (see routes) |
| `browse.py` (Anchor) | tools | `fetch_live(query, imo=None) -> {"facts": {...}, "sources": [url], "live_view_url": str\|None, "available": bool}` |
| `memory.py` (SurrealDB Agent Memory) | tools | `recall(subject) -> [{"field","value","source","observed_at","superseded_at"}]`; `remember(subject, facts: dict, source: str, observed_at: str) -> [changes]` where a change is `{"field","old","new","old_observed_at"}` (new fact supersedes old, history kept) |
| `voice.py` (ElevenLabs TTS) | tools | `tts(text) -> bytes` (mp3) |
| `scribe.py` (ElevenLabs Scribe) | tools | `check_audio(bytes, filename, content_type, hints) -> {segments, entities, ...}` (raises `ScribeUnavailable` with no key); `check_text(text)` same shape, works offline |

## Routes (server.py)
- `GET /health`
- `POST /investigate {"query"}` -> `{"job_id"}` (runs in background, Anchor is slow)
- `GET /jobs/{job_id}` -> `{"status": "running|done|error", "steps": [{"name","status","detail","ms"}], "result": {...}}`
- `GET /jobs/{job_id}/audio` -> mp3 of the briefing
- ElevenLabs server tools (JSON in, JSON out, fast): `POST /tools/search {"query"}`, `POST /tools/investigate {"query"}` (starts job, returns job_id + quick lookup), `POST /tools/status {"job_id"}` (returns steps so far + briefing when done)
- `POST /scribe` (multipart `file`, optional `hints` comma-separated) -> speaker-labelled transcript plus every entity on record mentioned in it; 503 without an ElevenLabs key
- `POST /scribe/text {"text"}` -> the same for a pasted transcript (no key needed)
- CORS open to the site origin(s) in env `ALLOWED_ORIGINS` (default `*` for the hackathon)
