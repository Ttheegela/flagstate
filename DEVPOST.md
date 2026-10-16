# Flagstate: Devpost submission

Submit at https://daytona-hacksprint-nyc.devpost.com/ by **3:30 PM**. Each section below maps to a Devpost field; paste as is.

## Name
Flagstate

## Tagline
The sanctions lists say who was listed. Flagstate shows what changed since, by search, by voice or from a recording.

## Summary (2-3 sentences)
Sanctions lists record a ship as it was on the day it was listed, but sanctioned tankers change flag, name and manager faster than the lists update. Flagstate checks the US, UK, EU and UN lists and a shadow-fleet research snapshot, then sends a live investigator to the ship's public registry page, remembers what it saw and flags what changed: tanker MERU (IMO 9187227) was flagged Comoros in our 25 September research and is flagged Equatorial Guinea today. Every claim links to its source, every briefing is scored by two evals, and you can ask by voice or drop in a recording to find every sanctioned name in it.

## Problem and impact
Journalists, researchers and compliance analysts tracking the shadow fleet face three gaps. The lists are a snapshot: an entry does not tell you the ship's flag or name today. The current facts are scattered across registry sites built for people, not software. And nobody keeps the last check, so a change goes unnoticed and an unsourced answer can't be published. Flag-hopping is how sanctioned tankers keep trading. Flagstate does the check in under a minute, keeps the history so a change is never missed, and cites a source for every claim.

## What it does
1. **Search** a ship name, a seven-digit IMO number, a company or a person: research dossier, official list entries, a wider OpenSanctions check and connections (owners, managers, US lobbying), each with its source. A 3D port scene on the home page shows four tankers from our data; click one to search it.
2. **Investigate live**: one click runs lookup, memory recall, live browse, sandboxed risk analysis, remember, sourced briefing and two evals, each step shown as it runs, ending in a "What changed" card (old value struck through, new value, when Flagstate first saw it), severity-tagged risk flags and a briefing you can play aloud.
3. **Ask by voice**: an ElevenLabs voice agent searches the lists, starts a live investigation, reports progress while it runs and reads the finished briefing.
4. **Check a recording**: drop in a radio call, press conference or hearing (or paste a transcript). ElevenLabs Scribe transcribes it with speakers and timestamps, primed with the ship and company names in our data, and every ship, company or person on record is marked and checked against the sanctions lists, including ships mentioned by a former name.

## How we used each sponsor
- **Daytona**: the risk analysis (list hits, flag hopping, renames, owner and manager changes, live facts that contradict the record) runs as code inside a Daytona sandbox, reused across runs; the sandbox id is shown in the UI. `agent/deploy_daytona.py` deploys the whole agent service into a public Daytona sandbox, ready for a tier with open outbound network.
- **Anchor Browser**: reads each ship's public registry page (VesselFinder) through Anchor's Web Unlocker, falling back to an Anchor browser session running an AI web task with a JSON schema, proxy and stealth on.
- **SurrealDB Agent Memory**: every fact is stored per ship with its source and the time it was observed. A new value supersedes the old one and the history is kept, so Flagstate can say "Flagstate first saw the flag change from Liberia to Cameroon on 16 October 2026". Each fact is also written as a sentence with `observed_at`, so Agent Memory's knowledge graph tracks it over time.
- **AWS**: Claude Haiku 4.5 on Amazon Bedrock writes the briefing from the gathered context only, returning each claim with its source URL, and also runs the faithfulness judge. The agent service runs on EC2 with an automatic HTTPS certificate and calls Bedrock through an IAM instance role, deployed in one command by `agent/deploy_ec2.py`.
- **Arize AX**: every investigation is one trace with agent, chain, tool, LLM and evaluator spans; Bedrock calls are auto-instrumented. Two evals are logged on every run: `claims_grounded` (the share of claims whose source the agent actually gathered) and `claims_faithful` (an LLM-as-judge check that each claim says only what its source supports). The faithfulness judge caught a real bug: the briefing said the flag "changed on" the date we first observed it, which the grounding check had scored as fine. We fixed the wording, and the voice tests now check for it.
- **ElevenLabs**: four uses. A Conversational AI voice agent on Claude Haiku 5.5 with three webhook tools (search, start investigation, check progress) pointed at the agent service; text-to-speech plays the briefing; Scribe speech-to-text checks recordings, with keyterms from our research index so obscure tanker names are spelled the way the sanctions data spells them; and ElevenLabs simulation tests drive the voice agent end to end against the live tools.

## How we tested it
- 48 agent tests, 139 data-pipeline tests, 84 frontend unit tests and 17 browser smoke tests, all passing.
- Live runs of every sponsor on real keys: TASSOS and MERU investigations end to end on the deployed site, with both evals.
- ElevenLabs simulation tests: a simulated journalist asks "Is TASSOS sanctioned?" then "Can you run a live check on whether it has changed flag?". The voice agent calls all three tools against the live EC2 agent, narrates progress and reads the briefing. Passed every success condition on three runs, including no invented facts. ElevenLabs' test harness runs the agent's turns on its own test model (Gemini 2.5 Flash); the live agent runs on Claude Haiku 5.5. The tests also showed the voice agent rephrasing "first seen" as "changed today", so its prompt now spells out that change dates are when Flagstate first saw a value.
- Scribe: five scripted recordings (news segment, VHF radio call, press briefing, court hearing, false-positive traps) with expected results, checked offline in tests and live against ElevenLabs.

## Architecture
```
browser (static site, Vercel)            ElevenLabs voice agent (Claude Haiku 5.5)
   |  search: data/ + /api/*                 |  webhook tools
   |  investigate: POST /investigate         |  /tools/search, /tools/investigate, /tools/status
   |  check a recording: POST /scribe        |
   v                                         v
        agent service (FastAPI, Python 3.12, on AWS EC2)
          lookup ─ recall ─ browse ─ analyse ─ remember ─ brief ─ eval
                    │        │        │          │         │       │
              SurrealDB   Anchor   Daytona   SurrealDB  Bedrock  Arize
          scribe ─ ElevenLabs Scribe ─ lookup
```
Each sponsor step fails on its own: a missing key or a failed call marks that step, and the investigation carries on with what it has.

## Challenges
- Daytona's free tier blocks outbound traffic from sandboxes to most domains, and it can't be lifted per sandbox, so the agent service couldn't reach Anchor or SurrealDB from inside Daytona. We kept the analysis in a Daytona sandbox and moved the service to AWS EC2.
- SurrealDB Agent Memory rejects `observed_at` on literal writes, so we store an exact literal row for recall plus a known-time sentence for the knowledge graph, written in the background so investigations don't wait on extraction.
- Anchor browsing takes seconds to a minute, too long for one voice turn, so the voice tools start a job and poll it while the agent narrates.
- Many ship names are ordinary words (SUN, TRUST, HENRY). Scribe matching keeps an IMO number only when its check digit is valid, requires exact matches for names of two or more words, and marks one-word names as possible matches only next to a maritime word.

## What's next
Watchlists that re-check saved ships nightly and alert on a change; owner and manager history from more registries; Arize datasets and experiments to compare briefing prompts; a public changes feed for newsrooms.

## Built with
python, fastapi, javascript, three.js, daytona, anchor-browser, surrealdb, amazon-bedrock, aws-ec2, claude, arize, elevenlabs, elevenlabs-scribe, vercel

## Links
- Live site: https://flagstate.vercel.app
- Repo: https://github.com/Ttheegela/flagstate
- Demo video: <!-- add link -->

## Team
- Tarun Theegela: agent pipeline, sponsor integrations, AWS and Vercel deploys <!-- email, socials -->
- Rajanee Shenkar: Arize evals, LLM-as-judge faithfulness check <!-- email, socials -->
- Adish Padalia: ElevenLabs Scribe "Check a recording" <!-- email, socials -->
- Bo: 3D port hero and front end <!-- email, socials -->

---

## 2-minute demo script
1. (0:00) "Sanctioned tankers change flag faster than the lists update. Flagstate catches it." Open flagstate.vercel.app; the 3D port shows four tankers from our data.
2. (0:10) Search **TASSOS**: dossier, US/EU/UK listings, connections. "That's what the lists know."
3. (0:20) Click **Investigate live**. Narrate the steps as they tick: SurrealDB recall, Anchor reads the live registry page, Daytona sandbox runs the risk analysis, Bedrock writes the briefing, Arize scores it.
4. (0:45) Point at **What changed**: Liberia struck through, Cameroon, first seen by Flagstate. Then the briefing: every claim links to its source, with the grounding and faithfulness scores.
5. (1:05) Press **Play briefing** (ElevenLabs).
6. (1:15) **Check a recording**: paste the coast-guard line about MERU and TASSOS (or drop `agent/tests/fixtures/scribe/2_vhf_radio_call.mp3`): ENISEY is found even when spoken by its former name, Federal Baffin.
7. (1:35) Open the voice widget: "Is TASSOS sanctioned? Has it changed flag?" Let it answer.
8. (1:55) "Six sponsors, one investigator. Flagstate."

## 3-minute pitch outline
- Problem (30 s): shadow fleet, flag hopping, lists lag reality.
- Live demo (90 s): steps 2-7 above.
- How (40 s): architecture in one picture; one line per sponsor; the faithfulness judge catching a real bug.
- Next (20 s): watchlists, alerts, newsroom feed.
