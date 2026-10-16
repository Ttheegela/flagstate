# Flagstate: Devpost submission draft

Submit at https://daytona-hacksprint-nyc.devpost.com/ by **3:30 PM**.

## Name
Flagstate

## Tagline
Ask about any ship, company or person: sanctions lists plus a live investigator that catches what changed, by text or by voice.

## Summary (2-3 sentences)
Sanctions lists say who was listed, not what the ship looks like today. Flagstate checks the US, UK, EU and UN lists and a shadow-fleet research snapshot, then sends a live investigator to the ship's public registry page, remembers what it saw, and flags what changed: for example, tanker MERU (IMO 9187227) was flagged Comoros in our 25 September research and is flagged Equatorial Guinea today. Every claim in the briefing links to its source, and you can ask it all by voice.

## Problem and impact
Journalists, researchers and compliance teams tracking the shadow fleet face ships that change name, flag and manager faster than the lists update. Flag-hopping is the main way sanctioned tankers keep trading. Checking each ship means opening registry sites by hand, remembering what you saw last time, and writing it up with sources. Flagstate does that in under a minute and keeps the history, so a change never gets missed.

## How it works
1. Search: instant match across the research snapshot, the four official lists, OpenSanctions and US lobbying filings.
2. Investigate live: lookup, recall, live browse, sandboxed analysis, remember, sourced briefing, grounding eval, all shown step by step in the page.
3. Ask by voice: an ElevenLabs voice agent with three tools (search, start investigation, check progress) answers "Is TASSOS sanctioned, and has it changed flag?"

## How we used each sponsor
- **Daytona**: the risk analysis (flag hopping, renames, owner changes, list hits, live facts contradicting the lists) runs as code inside a Daytona sandbox, reused across runs, with the sandbox id shown in the UI. `agent/deploy_daytona.py` deploys the whole agent service into a public Daytona sandbox with a preview URL.
- **Anchor Browser**: reads each ship's public registry page (VesselFinder) through Anchor's Web Unlocker, falling back to an Anchor browser session running an AI web task with a JSON schema, with proxy and stealth on. Companies and people go through the AI task.
- **SurrealDB Agent Memory**: every fact is stored per ship with its source and the time it was observed. A new value supersedes the old one and history is kept, so the agent can say "flag changed from Liberia to Cameroon, first seen at ...". Each fact is also written as a sentence with `observed_at` so Agent Memory's knowledge graph tracks it over time.
- **AWS**: Claude Haiku 4.5 on Bedrock writes a short spoken-style briefing grounded only in the gathered context, returning each claim with its source URL. The agent service itself runs on EC2 (Caddy HTTPS, Bedrock through an instance role), deployed by `agent/deploy_ec2.py`.
- **Arize AX**: every investigation is one trace with AGENT, CHAIN, TOOL, LLM and EVALUATOR spans; Bedrock calls are auto-instrumented. A grounding eval (`claims_grounded`: share of claims whose source was actually gathered) is logged on every run. <!-- Rajanee: add the faithfulness eval + dashboard sentence here -->
- **ElevenLabs**: text-to-speech reads the briefing aloud (Play button), and a Conversational AI agent with webhook tools answers by voice. <!-- Adish: add voice/prompt details here -->

## Architecture
```
browser (static site, Vercel)            ElevenLabs voice agent
   |  search: data/ + /api/*                 |  webhook tools
   |  investigate: POST /investigate         |  /tools/search, /tools/investigate, /tools/status
   v                                         v
        agent service (FastAPI, Python 3.12, on AWS EC2)
          lookup ─ recall ─ browse ─ analyse ─ remember ─ brief ─ eval
                    │        │        │          │         │       │
              SurrealDB   Anchor   Daytona   SurrealDB  Bedrock  Arize
```
Each sponsor step fails on its own: a missing key or failed call marks that step and the investigation carries on.

## Challenges
- Daytona's free tier blocks outbound traffic from sandboxes to most domains, and it can't be lifted per sandbox, so the agent service itself couldn't reach Anchor or SurrealDB from inside Daytona. We kept the analysis in Daytona and moved the agent service to AWS EC2; the Daytona deploy script is ready for a higher tier.
- SurrealDB Agent Memory rejects `observed_at` on literal writes, so we store an exact literal row for recall plus a known-time sentence for the knowledge graph.
- Anchor browse takes seconds to a minute, too long for a voice turn, so the voice tools start a job and poll it.

## What's next
Watchlists that re-check saved ships nightly and alert on a change; owner and manager history from more registries; a public changes feed for newsrooms.

## Built with
python, fastapi, javascript, daytona, anchor-browser, surrealdb, aws-bedrock, claude, arize, elevenlabs, vercel

## Links
- Live site: https://flagstate.vercel.app
- Repo: https://github.com/Ttheegela/flagstate
- Demo video: <!-- add link -->

## Team
Tarun Theegela, Rajanee Shenkar, Adish Padalia, Bo <!-- add emails and socials -->

---

## 2-minute demo script
1. (0:00) "Sanctioned tankers change flag faster than the lists update. Flagstate catches it." Open flagstate.vercel.app.
2. (0:10) Search **TASSOS**: research dossier, US/UK/EU listings, connections. "That's what the lists know."
3. (0:25) Click **Investigate live**. Narrate the steps as they tick: SurrealDB recall, Anchor reads the live registry page, Daytona sandbox runs the risk analysis.
4. (0:50) Point at **What changed**: flag Liberia → Cameroon. Then the briefing: every claim links to its source; "8/8 claims sourced", the Arize eval.
5. (1:10) Press **Play briefing** (ElevenLabs).
6. (1:20) Search **9187227** (MERU), Investigate live: first-ever check catches Comoros → Equatorial Guinea since our 25 September snapshot.
7. (1:40) Open the voice widget: "Has TASSOS changed flag?" Let it answer.
8. (1:55) "Six sponsors, one investigator. Flagstate."

## 3-minute pitch outline
- Problem (30 s): shadow fleet, flag hopping, lists lag reality.
- Live demo (90 s): steps 2-7 above.
- How (40 s): one slide of the architecture; one line per sponsor.
- Next (20 s): watchlists, alerts, newsroom feed.
