# Flagstate

**The sanctions lists say who was listed. Flagstate shows what changed since.**

Ask about any ship, company or person, by text or by voice. Flagstate checks the US, UK, EU and UN sanctions lists and a research snapshot on the shadow fleet, then sends a live investigator to the ship's public registry page, remembers what it saw, and flags what has changed. Every claim in its answer links to its source.

Live site: https://flagstate.vercel.app · Built at the Daytona HackSprint NYC, October 2026.

## The problem

Sanctioned tankers keep trading by changing their identity faster than the lists update. A ship listed under one name and flag re-registers under another flag, takes a new name, or moves to a new manager, often within weeks. Flag-hopping is the most common move: the hull stays the same, the paperwork changes.

The people who track this (journalists, researchers, compliance analysts) face three gaps:

1. **The lists are a snapshot.** A sanctions entry records the ship as it was on the day it was listed. It does not tell you the ship's flag or name today.
2. **The current facts are scattered.** A ship's present flag, call sign and particulars sit on public registry and tracking sites, many of them built for people, not software. Checking one ship means opening several sites by hand.
3. **Nobody remembers the last check.** Knowing a ship *changed* requires knowing what it was before. That history usually lives in someone's notes, if anywhere, and an answer without a source can't be published.

So a ship can sit on three sanctions lists and still sail under a flag none of them mention, and the person checking it has no quick way to notice.

## What Flagstate does

1. **Search** a ship name, a seven-digit IMO number, a company or a person. You get the research dossier, the official list entries, a wider OpenSanctions check and connections (owners, managers, US lobbying), each with its source.
2. **Investigate live.** One click starts an agent that checks the open web against what is on record:
   - **Recall**: what Flagstate saw for this ship before, from its memory.
   - **Browse**: the ship's current public registry page, read in a cloud browser.
   - **Analyse**: risk flags such as list hits, flag hopping, renames, owner or manager changes, and live facts that contradict the lists.
   - **Remember**: the new facts. A new value supersedes the old one and the history is kept.
   - **Brief**: a short spoken-style briefing grounded only in what was gathered, with a source for every claim.
   - **Evaluate**: a check that every claim in the briefing cites a source the agent actually gathered.
3. **Check a recording.** Drop in a radio call, press conference, hearing or podcast (or paste a transcript). ElevenLabs Scribe transcribes it with speakers and timestamps, biased towards the ship and company names in the data, and every ship, company or person on record is marked, checked against the lists and one click from a live investigation. IMO numbers count only when their check digit is valid, and an old name is resolved to the ship's current one ("heard as Front Balder, on record as TASSOS").
4. **Ask by voice.** A voice agent answers questions like "Is TASSOS sanctioned, and has it changed flag?" using the same tools: quick search, start an investigation, check its progress, read the briefing.

### What it found

- **MERU (IMO 9187227)**: flagged Comoros in the 25 September 2026 research snapshot; its public registry page now shows Equatorial Guinea. Flagstate caught this on the first live check.
- **TASSOS (IMO 9408695)**: listed by the US (Iran), the EU and the UK (Russia), recorded as Liberian-flagged; the live registry page shows Cameroon. Flagstate stores the change and shows it on every later check.

## How it works

```
browser (static site, Vercel)            ElevenLabs voice agent
   |  search: data/ + /api/*                 |  webhook tools
   |  investigate: POST /investigate         |  /tools/search, /tools/investigate, /tools/status
   v                                         v
        agent service (FastAPI, Python 3.12)
          lookup ─ recall ─ browse ─ analyse ─ remember ─ brief ─ eval
                    │        │        │          │         │       │
              SurrealDB   Anchor   Daytona   SurrealDB  Bedrock  Arize
```

| Step | Tool | What it does |
|---|---|---|
| Lookup | local data | Matches the query against the research snapshot and the four official lists |
| Recall / Remember | **SurrealDB Agent Memory** | Stores each fact per ship with its source and when it was observed; a new value supersedes the old one, history kept. Facts are also written as sentences with `observed_at` so Agent Memory's knowledge graph tracks them over time |
| Browse | **Anchor Browser** | Reads the ship's public registry page (VesselFinder) through Anchor's Web Unlocker, falling back to an Anchor browser session running an AI web task; proxy and stealth on |
| Analyse | **Daytona** | Runs the risk analysis as code inside a Daytona sandbox, reused across runs; the sandbox id is shown in the UI |
| Brief | **AWS Bedrock** (Claude Haiku 4.5) | Writes the briefing from the gathered context only, returning each claim with its source URL |
| Eval | **Arize AX** | Traces every investigation (agent, tool, LLM and evaluator spans) and logs a grounding score: the share of claims whose source was actually gathered |
| Voice | **ElevenLabs** | Reads the briefing aloud, powers the conversational voice agent, and transcribes recordings with Scribe (diarization, word timestamps, keyterms from the sanctions data) |

Each step fails on its own. A missing key or a failed call marks that step `skipped` or `error`, and the investigation carries on with what it has.

## Run it

```bash
# site
npx serve .

# agent (Python 3.12)
cd agent && uv venv --python 3.12 .venv && VIRTUAL_ENV=.venv uv pip install -r requirements.txt && cd ..
cp agent/.env.example agent/.env   # fill in keys; never commit agent/.env
agent/.venv/bin/python -m uvicorn agent.server:app --port 8787
```

Open the site and add `?agent=http://localhost:8787`. `agent/deploy_daytona.py` deploys the agent service into a public Daytona sandbox; see `agent/README.md` for routes and env vars.

## Tests

```bash
python3 -m pytest -q scripts && agent/.venv/bin/python -m pytest -q agent/tests && npm test && npm run smoke
```

## Limits

- **Registry coverage**: live facts come from one public registry page. It shows flag, name and particulars, but not owner or manager, which sit behind a paywall.
- **Agent hosting**: on Daytona's free tier, sandboxes can't reach Anchor or SurrealDB, so during the hackathon the agent service ran outside Daytona and only the analysis ran in a sandbox. The deploy script is ready for a tier with open egress.
- **Matching**: a name match is a possible match, not proof. Check the numbered source before you publish. Flagstate describes documented conduct and makes no legal findings.

## Data and credit

- Official lists: US Consolidated Screening List, UK Sanctions List, EU financial sanctions list, UN Security Council list (`data/lists/`).
- Wider check and connections: OpenSanctions bulk data (CC BY-NC 4.0), hosted on this repo's `data-latest` release.
- Lobbying: lda.gov filings.
- Research snapshot: the VeilTrace team, Trace the Unseen build day, 25 September 2026.

People are named only as official lists, government documents or their own lobbying filings name them. Corrections go through GitHub issues.

Code is MIT licensed. Data keeps its sources' terms; see `stories/about-the-data.html`.
