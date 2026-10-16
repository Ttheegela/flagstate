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

1. **Search** a ship name, a seven-digit IMO number, a company or a person. You get the research dossier, the official list entries, a wider OpenSanctions check and connections (owners, managers, US lobbying), each with its source. A 3D port scene on the home page shows four tankers from our data; click one to search it.
2. **Investigate live.** One click starts an agent that checks the open web against what is on record:
   - **Recall**: what Flagstate saw for this ship before, from its memory.
   - **Browse**: the ship's current public registry page, read in a cloud browser.
   - **Analyse**: risk flags such as list hits, flag hopping, renames, owner or manager changes, and live facts that contradict the lists.
   - **Remember**: the new facts. A new value supersedes the old one and the history is kept. The "What changed" card shows the old value struck through, the new value and when Flagstate first saw it.
   - **Brief**: a short spoken-style briefing grounded only in what was gathered, with a source for every claim.
   - **Evaluate**: two evals on every run. `claims_grounded` checks that every claim cites a source the agent actually gathered. `claims_faithful` is an LLM-as-judge check (on Bedrock) that each claim says only what its source supports.
3. **Ask by voice.** A voice agent answers questions like "Is TASSOS sanctioned, and has it changed flag?" using the same tools: quick search, start an investigation, check its progress, read the briefing.
4. **Check a recording.** Drop in a radio call, press conference, hearing or podcast, or paste a transcript. ElevenLabs Scribe speech-to-text transcribes it with speakers and timestamps, primed with keyterms from the research index, and every ship, company or person on record is marked, checked against the lists and one click from a live investigation. Ships mentioned by a former name are resolved to the current one ("heard as Front Balder, on record as TASSOS"). Matching is strict: an IMO number counts only when its check digit is valid, names of two or more words must match exactly, and a one-word name is marked "possible" and only when it sits next to a maritime word.

### What it found

- **MERU (IMO 9187227)**: flagged Comoros in the 25 September 2026 research snapshot; its public registry page now shows Equatorial Guinea. Flagstate caught this on the first live check.
- **TASSOS (IMO 9408695)**: listed by the US (Iran), the EU and the UK (Russia), recorded as Liberian-flagged; the live registry page shows Cameroon. Flagstate first saw the flag as Cameroon, stores that value and shows when it first saw it on every later check.

## Agent system design

Flagstate connects a static frontend to a FastAPI investigator that gathers evidence, compares historical observations, and returns a sourced briefing. The diagram shows the seven-stage pipeline, sponsor integrations, and separate search, recording, and voice paths.

![Flagstate agent system design: evidence intake, live investigation, briefing, evaluation, and delivery](docs/Software%20Architecture.png)

[View full-resolution diagram](docs/Software%20Architecture.png) · [Editable SVG](docs/Software%20Architecture.svg)

## How it works

```
browser (static site, Vercel)            ElevenLabs voice agent (Claude Haiku 5.5)
   |  search: data/ + /api/*                 |  webhook tools
   |  investigate: POST /investigate         |  /tools/search, /tools/investigate, /tools/status
   |  check a recording: POST /scribe,       |
   |    POST /scribe/text                    |
   v                                         v
        agent service (FastAPI, Python 3.12, on AWS EC2)
          lookup ─ recall ─ browse ─ analyse ─ remember ─ brief ─ eval
                    │        │        │          │         │       │
              SurrealDB   Anchor   Daytona   SurrealDB  Bedrock  Arize
          scribe ─ ElevenLabs Scribe ─ lookup
```

| Step | Tool | What it does |
|---|---|---|
| Lookup | local data | Matches the query against the research snapshot and the four official lists |
| Recall / Remember | **SurrealDB Agent Memory** | Stores each fact per ship with its source and when it was observed; a new value supersedes the old one, history kept. Facts are also written as sentences with `observed_at` so Agent Memory's knowledge graph tracks them over time |
| Browse | **Anchor Browser** | Reads the ship's public registry page (VesselFinder) through Anchor's Web Unlocker, falling back to an Anchor browser session running an AI web task; proxy and stealth on |
| Analyse | **Daytona** | Runs the risk analysis as code inside a Daytona sandbox, reused across runs; the sandbox id is shown in the UI |
| Brief | **AWS Bedrock** (Claude Haiku 4.5) | Writes the briefing from the gathered context only, returning each claim with its source URL; also runs the faithfulness judge |
| Eval | **Arize AX** | Traces every investigation (agent, tool, LLM and evaluator spans; Bedrock calls auto-instrumented) and logs two evals: `claims_grounded` (the share of claims whose source was actually gathered) and `claims_faithful` (an LLM-as-judge check that each claim says only what its source supports). The faithfulness judge caught a real bug: the briefing said the flag "changed on" the date we first observed it, which the grounding check had scored as fine. We fixed the wording |
| Scribe | **ElevenLabs Scribe** | `POST /scribe` (audio) and `POST /scribe/text` (pasted transcript). Speech-to-text with speakers and word timestamps, keyterms from the research index so obscure tanker names are spelled the way the sanctions data spells them; every ship, company or person on record is then matched against the lists |
| Voice | **ElevenLabs** | Reads the briefing aloud (text-to-speech) and powers the conversational voice agent, which runs on Claude Haiku 5.5 with three webhook tools: search, start investigation, check progress |
| Hosting | **AWS EC2** | The agent service runs on one EC2 instance, deployed by `agent/deploy_ec2.py`: Caddy gives it HTTPS on `<ip>.sslip.io`, and it calls Bedrock through an IAM instance role |

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

Open the site and add `?agent=http://localhost:8787`. See `agent/README.md` for routes and env vars.

Deploy: `agent/.venv/bin/python -m agent.deploy_ec2` puts the agent on one EC2 instance (Amazon Linux, Caddy with an automatic HTTPS certificate on `<ip>.sslip.io`, Bedrock through an instance role so no AWS keys leave your machine) and prints its URL; set it in `<meta name="flagstate-agent">`. `agent/deploy_daytona.py` does the same in a public Daytona sandbox, for a Daytona tier with open outbound network.

## Tests

```bash
python3 -m pytest -q scripts && agent/.venv/bin/python -m pytest -q agent/tests && npm test && npm run smoke
```

48 agent tests, 139 data-pipeline tests, 84 frontend unit tests and 17 browser smoke tests, all passing.

ElevenLabs simulation tests drive the voice agent against the live tools: a simulated journalist asks "Is TASSOS sanctioned?" and then asks for a live check on whether it has changed flag. The agent passed every success condition on three runs. ElevenLabs runs the test turns on its own test model (Gemini 2.5 Flash); the live agent runs on Claude Haiku 5.5.

The five Scribe sample recordings (news segment, VHF radio call, press briefing, court hearing, false-positive traps) are in `agent/tests/fixtures/scribe`, each with expected results.

## Limits

- **Registry coverage**: live facts come from one public registry page. It shows flag, name and particulars, but not owner or manager, which sit behind a paywall.
- **Agent hosting**: the agent service runs on AWS EC2. Daytona's free tier blocks sandboxes from reaching Anchor and SurrealDB, so Daytona runs the analysis sandbox rather than the whole service; `agent/deploy_daytona.py` is ready for a tier with open outbound network.
- **Matching**: a name match is a possible match, not proof. Check the numbered source before you publish. Flagstate describes documented conduct and makes no legal findings.
- **Scribe rate limit**: `/scribe` has no rate limit. Every upload spends ElevenLabs credits. That is fine for a demo; cap it before wider use.

## Team

- Tarun Theegela: agent pipeline, sponsor integrations, AWS and Vercel deploys
- Rajanee Shenkar: Arize evals, LLM-as-judge faithfulness check
- Adish Padalia: ElevenLabs Scribe "Check a recording"
- Bo: 3D port hero and front end

## Data and credit

- Official lists: US Consolidated Screening List, UK Sanctions List, EU financial sanctions list, UN Security Council list (`data/lists/`).
- Wider check and connections: OpenSanctions bulk data (CC BY-NC 4.0), hosted on this repo's `data-latest` release.
- Lobbying: lda.gov filings.
- Research snapshot: the VeilTrace team, Trace the Unseen build day, 25 September 2026.

People are named only as official lists, government documents or their own lobbying filings name them. Corrections go through GitHub issues.

Code is MIT licensed. Data keeps its sources' terms; see `stories/about-the-data.html`.
