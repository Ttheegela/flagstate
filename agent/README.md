# Flagstate agent

A live investigator for the Flagstate sanctions data. You give it a ship, company or person (by name or IMO). It checks the repo's research index and the US/UK/EU/UN lists, pulls live facts, compares them with what it saw last time, runs a risk analysis in a sandbox, and writes a short spoken briefing in which every claim cites a source.

## Run

```bash
cp agent/.env.example agent/.env      # fill in whichever keys you have
agent/.venv/bin/uvicorn agent.server:app --port 8787    # from the repo root
agent/.venv/bin/python -m pytest -q agent/tests          # offline tests
```

Each sponsor integration is optional. If its key is missing, the step falls back (template briefing, local subprocess, no-op tracing) or is marked `skipped`, so the service still runs offline.

## Env vars

| Var | Used by | Missing → |
|---|---|---|
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_REGION` (default `us-west-2`) | `llm.py` (Bedrock) | template briefing from the context |
| `BEDROCK_MODEL_ID` (default `us.anthropic.claude-haiku-4-5-20251001-v1:0`) | `llm.py` | default; a bare `anthropic.` id is retried with the `us.` inference-profile prefix if Bedrock asks for one |
| `DAYTONA_API_KEY` | `sandbox.py` | `analysis.py` runs locally (`"ran_in": "local"`) |
| `ARIZE_SPACE_ID`, `ARIZE_API_KEY`, `ARIZE_PROJECT_NAME` (default `flagstate`) | `tracing.py` | no-op spans |
| `ANCHOR_API_KEY` | `browse.py` | no live facts |
| `SURREAL_MEMORY_URL`, `SURREAL_MEMORY_TOKEN` | `memory.py` | recall/remember fall back |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | `voice.py` | `/jobs/{id}/audio` returns 503 |
| `ALLOWED_ORIGINS` (comma-separated, default `*`) | `server.py` CORS | `*` |

## Architecture

```
 browser (site) ──┐                 ElevenLabs Conversational AI agent
                  │ /investigate      │ server tools: /tools/search, /tools/investigate, /tools/status
                  ▼ /jobs/{id}        ▼
            ┌───────────────── server.py (FastAPI, in-memory jobs, 1 thread per job) ─────────────────┐
            │ pipeline.investigate(query, on_step)        every step timed + traced (Arize AX)          │
            │                                                                                            │
            │ 1 lookup    lookup.py         data/research-index.json + data/lists/*.json (IMO or name)  │
            │ 2 recall    memory.py         SurrealDB Agent Memory: what we saw last time               │
            │ 3 browse    browse.py         Anchor Browser: live registry facts + live view URL         │
            │ 4 analyse   sandbox.py        Daytona sandbox runs analysis.py -> risk flags              │
            │ 5 remember  memory.py         SurrealDB: store new facts, superseding old (history kept)  │
            │ 6 brief     llm.py            AWS Bedrock (Claude, Converse API): <=120-word briefing     │
            │ 7 eval      pipeline.py       fraction of claims whose source URL is in the context       │
            └────────────────────────────────────────────────────────────────────────────────────────────┘
                  │ /jobs/{id}/audio
                  ▼
              voice.py   ElevenLabs TTS (mp3 of the briefing)

 tracing.py: arize.otel.register + OpenInference Bedrock instrumentor; CHAIN/TOOL/LLM/EVALUATOR spans,
             eval logged as eval.claims_grounded.{score,label,explanation} on the trace.
```

## Routes

- `GET /health` lists which sponsor keys are configured (true/false only).
- `POST /investigate {"query"}` returns `{"job_id"}`.
- `GET /jobs/{job_id}` returns `{"status", "steps": [{"name","status","detail","ms"}], "result", "error"}`.
- `GET /jobs/{job_id}/audio` returns an mp3 of the briefing.
- `POST /tools/search {"query"}` is a fast lookup. Its `say` line is ready to read aloud.
- `POST /tools/investigate {"query"}` starts a job and returns the quick lookup, `job_id` and `say`.
- `POST /tools/status {"job_id"?}` returns progress, or the briefing, risk and top flags once the job is done. If `job_id` is omitted, it reports on the latest job.

Analysis flags (`analysis.py`, stdlib only): `on_official_list`, `name_changed`, `flag_changed`, `owner_or_manager_changed`, `dark_fleet_indicator`, `live_disagrees_with_record`, `changed_since_last_check`. Each flag has a `severity`, `evidence` and `source` URL.
