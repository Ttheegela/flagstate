# Flagstate

Ask about any ship, company or person and get a sourced answer, by text or by voice. Flagstate checks the US, UK, EU and UN sanctions lists and a research snapshot on the shadow fleet, then sends a live investigator to the open web to see what has changed since the lists were written.

Built at the Daytona HackSprint NYC, October 2026.

## What it does

1. **Search**: type a ship name, a seven-digit IMO number, a company or a person. You get the research dossier, the official list entries, a wider OpenSanctions check and connections (owners, managers, US lobbying), each with its source.
2. **Investigate live**: one click starts an agent that
   - opens the ship's public registry page in a real cloud browser (**Anchor Browser**), stealth and proxy on, and reads its current name, flag and particulars,
   - recalls what it saw last time and records what changed, with the old fact superseded and its history kept (**SurrealDB Agent Memory**),
   - runs the risk analysis (flag hopping, renames, owner changes, list hits, live facts that contradict the lists) in an isolated sandbox (**Daytona**),
   - writes a short spoken briefing grounded only in the gathered sources (**AWS Bedrock**, Claude),
   - checks that every claim in the briefing cites a source it actually gathered, and traces every step (**Arize AX**),
   - reads the briefing aloud (**ElevenLabs**).
3. **Ask by voice**: an ElevenLabs voice agent answers questions like "Is TASSOS sanctioned, and has it changed flag?" using the same tools: quick search, start an investigation, check its progress.

## Architecture

```
browser (static site, Vercel)            ElevenLabs voice agent
   |  search: data/ + /api/*                 |  server tools
   |  investigate: POST /investigate         |  /tools/search, /tools/investigate, /tools/status
   v                                         v
           agent service (FastAPI, runs in a Daytona sandbox, public preview URL)
             lookup ─ recall ─ browse ─ analyse ─ remember ─ brief ─ eval
                       │        │         │          │         │       │
                 SurrealDB   Anchor    Daytona    SurrealDB  Bedrock  Arize
                 Agent Mem   Browser   sandbox    Agent Mem  (Claude) (traces + eval)
```

Every sponsor call degrades on its own: a missing key or a failed call marks that step `skipped` or `error` and the investigation carries on.

## Run it

```bash
# site
npx serve .

# agent (Python 3.12)
cd agent && uv venv --python 3.12 .venv && VIRTUAL_ENV=.venv uv pip install -r requirements.txt && cd ..
cp agent/.env.example agent/.env   # fill in keys; never commit agent/.env
agent/.venv/bin/python -m uvicorn agent.server:app --port 8787
```

Open the site and add `?agent=http://localhost:8787` (or the Daytona preview URL). See `agent/README.md` for routes and env vars.

## Tests

```bash
python3 -m pytest -q scripts && agent/.venv/bin/python -m pytest -q agent/tests && npm test && npm run smoke
```

## Data and credit

- Official lists: US Consolidated Screening List, UK Sanctions List, EU financial sanctions list, UN Security Council list (`data/lists/`).
- Wider check and connections: OpenSanctions bulk data (CC BY-NC 4.0), hosted on this repo's `data-latest` release.
- Lobbying: lda.gov filings.
- Research snapshot: the VeilTrace team, Trace the Unseen build day, 25 September 2026.

People are named only as official lists, government documents or their own lobbying filings name them. Corrections go through GitHub issues.

Code is MIT licensed. Data keeps its sources' terms; see `stories/about-the-data.html`.
