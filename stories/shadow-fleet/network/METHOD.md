# Shadow Fleet Network: method

Built on 25 September 2026 at the "Trace the Unseen" build day (sanctions and evasion track). This note says where every
node and line in the chart comes from, how we joined the sources, and what the chart cannot show.

## What the chart shows

- **Ships**, identified by their IMO number: a 7-digit hull number issued under the International Maritime Organization
  scheme that stays with the hull for life, whatever the ship is called.
- **Companies** that own, manage, operate, insure, trade for or register these ships.
- **People**, only where an official list, government release, indictment or court record names them, and only in that role.
- **Countries**: flag states (where a ship is registered), company registration countries, and the governments that list
  ships and firms (United States, United Kingdom, European Union).

Every line carries its type, date where known, one or more sources (link and saved file name), and a confidence tag:
- **Documented**: stated by an official list, a government release or a court record.
- **Lead**: our own inference, or a non-official source (ship database, study, press). A Lead is a
  question to investigate, not a finding.

## Sources

| Source | What it gives | File |
|---|---|---|
| UK sanctions list (FCDO/OFSI), report of 21 Sep 2026 | 625 ships under the Russia regime with IMO, date listed, current and previous flag, "current owner/operator"; listed firms and people with the UK statement of reasons | `UK-Sanctions-List.csv` |
| US Treasury OFAC list (OpenSanctions export, 25 Sep 2026) | ships and firms with programme, first-seen date | `us_ofac_sdn.csv` |
| US Consolidated Screening List (trade.gov) | OFAC ship entries with "Linked To" company, flag, former flags, radio ID (MMSI), registered owner | `us_csl/consolidated.csv` |
| EU Official Journal ship list (OpenSanctions export, 25 Sep 2026) | 733 EU-listed ships with IMO, listing date and legal ground | `eu_journal_sanctions.csv` |
| EU financial-sanctions file (OpenSanctions export) | EU-listed firms and people with act and date | `eu_fsf.csv` |
| Ukraine War and Sanctions database (run by Ukraine's military intelligence, GUR) | former names, flag countries, dated owner and manager records. A government database, **not a sanctions list** | `ua_war_sanctions.csv` + saved pages |
| Official releases: US Treasury, US Justice Department, EUR-Lex / EU Council, gov.uk, CENTCOM, Finnish government | named people and firms, roles, quotes | saved under `pulls/tavily/` |
| Studies: KSE Institute, CREA, S&P Global, Windward, RUSI, OCCRP, Atlantic Council, Lloyd's List | fleet-wide counts for the legend | saved under `pulls/tavily/` |

## How the graph was built

1. **Join by IMO number** (`build_base.py`). Every ship on the UK Russia list, the EU ship list, or the US list under an
   Iran, Russia, terrorism or Venezuela programme becomes one node keyed `IMO<number>`. Yachts and passenger ships are
   dropped. Names from each list and former names from Ukraine's database are kept on the node.
2. **Lines from the lists.** UK "current owner/operator" -> operates; OFAC "Linked To" -> linked to; OFAC registered
   owner -> owns; flags and former flags -> flagged in / was flagged in; each listing -> sanctioned by, with its date.
3. **Company matching.** Names are normalised (case, punctuation, legal suffixes such as LLC, DMCC, FZE, PJSC). A firm
   written differently on two lists is merged only when one normalised name is contained in the other and there is a
   single candidate; each merge is recorded on the node as a Claude match to check before quoting.
4. **Research angles** (seven, run in parallel): US Treasury Iran actions, US/UK Russia actions, EU acts, service providers
   (insurers, flags, bunkering ships, classification), enforcement (seizures, detentions, court cases), dated ship histories (Ukraine's database), and outside studies. Each wrote nodes and lines in one shared
   format with sources.
5. **Independent verification.** Every angle was re-checked by a separate verifier that re-opened the saved sources,
   re-derived numbers, checked IMO check digits and people's names against the lists, and wrote a corrected file plus a
   claim-by-claim table. The research and verification files stay with the team's working files and are not published, because they name unlisted firms. Only the corrected files feed the chart. Examples of what verifiers
   caught: two wrong IMO numbers dropped; a strike date corrected from 9 to 8 September 2026; the EU act number question settled (2026/1843 regulation and 2026/1845 decision are one listing).
6. **Merge** (`merge.py`) de-duplicates lines, keeps every source on a line, and applies the naming policy below.

## Naming policy (set 25 Sep 2026)

- Documented conduct is stated plainly and attributed ("Treasury says ..."). Conduct words, not legal conclusions, unless
  a court or agency used them.
- **People** appear only when an official record names them, in that role. Anyone else is "an individual".
- **Firms not on a sanctions list** keep their name only when an official record names them in that role (for example,
  the UK list names them as operator of a ship it sanctions). Firms known only from Ukraine's database or studies
  are shown by description, such as "unlisted UAE ship manager". Their names are removed from the published data
  files, including quoted text (`release_check.py` enforces this).

## Key numbers and their filters

- **54** ships are on a Russia ship list (UK or EU) and on the US list under an Iran-related programme. UK list alone: 46.
  The strict filter in the team's published analysis (US entry carries an Iran programme tag, UK Russia list only): 42.
- For 39 of the 54, the US Iran listing came before the first UK or EU Russia listing.
- US listing dates are the date a ship first appeared on the OFAC list in the OpenSanctions export. They match Treasury's
  releases on the dates we checked (30 Jul 2025, 15 Apr 2026).

## What the chart cannot show

- No line does not mean no relationship. Our sources cover listed ships and firms and the firms named next to them.
- Ukraine's database dates can be database refresh dates:
  of 6 ships with a record dated within 30 days after a listing, 4 share one date (30 Jul 2025, the US listing day) and a
  fifth falls on its own listing day. Only CLYDE NOBLE (28 days after its UK listing) looks like a real change, and it
  stays a Lead.
- Manager fields on lists can be stale (the UK list still names Zulu Ships Management for 8 hulls).
- Cargo: we show "carried cargo for" only where an official release says so; we hold no voyage or cargo data.
- One-ship companies, frequent renaming and flag changes are also common in lawful shipping. They are patterns, not proof.

## Parent groups, lobbying and cargo (added 25 Sep 2026, afternoon)

- **Parent groups.** A ninth research angle linked big operators to their parent groups from official texts: Treasury calls
  Rosnefteflot Rosneft's "marine transportation arm", Gazpromneft Marine Bunker "a Gazprom Neft subsidiary" and Sovcomflot
  "Russia's state-owned shipping company"; the UK statement of reasons says the state leasing company GTLK is directly
  controlled by the Russian government. Gazprom Neft to Gazprom rests on non-official sources and is a Lead.
- **Lobbying.** The team's verified lobbying graph (US lobbying and foreign-agent filings) is joined in. A ship card shows a
  lobbying line only when the ship's operator, its parent group, or a subsidiary of that parent appears in those filings;
  13 listed ships trace that far (Gazprom Neft and Lukoil tankers). For Sovcomflot, Zulu, Fleet Tanqo, Rosneft, Lukoil,
  Litasco and Nayara, no US lobbying filing was found under their own names in our search. State operators such as IRISL,
  PDVSA and GTLK were not checked. Lobbying is legal; nothing here says any lobbying was unlawful.
- **Cargo and manifests.** We hold no shipment manifests for these ships. The one official cargo record is the Justice Department's: SKIPPER
  (listed by OFAC as ADISA, IMO 9304667) carried about 3 million barrels of Iranian crude to Syria in 2024 and was seized
  with about 1.8 million barrels in December 2025. These tankers move oil through ship-to-ship transfers to non-US buyers,
  which customs data rarely covers.

## Reproduce

```
set PYTHONUTF8=1
python build_base.py        # list join -> base_nodes.json, base_edges.json
python merge.py             # + verified research -> out/nodes.json, out/edges.json, out/meta.json, out/graph_data.js
python build_viewer.py      # -> out/shadow_fleet_map.html (single file)
python release_check.py     # keys, local paths, hidden names, people sources
```

Map layout originally after God's Eye View by Bilawal Sidhu (MIT licence). Suggestions in this file that are not part of the naming policy are
proposals.
