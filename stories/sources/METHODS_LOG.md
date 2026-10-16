# Methods log: how we find and check sanctions-evasion leads (Fri 25 Sept 2026)

What we did, how, what it found, what worked, what didn't. Newest entries last in each section. Times EDT.
Rating: **works** · **works with care** · **weak** · **failed**. Findings themselves live in `LOG_2026-09-25.md`; questions in `QUESTIONS_2026-09-25.md`.


---

## A. Discovery methods (how we find leads)

| # | Method | How (tools / recipe) | What it found | Rating | Lessons |
|---|---|---|---|---|---|
| A2 | **Mirror statistics (countries' own reports)** | UN Comtrade free preview API, reporter -> Russia, by HS code and year | Kyrgyzstan ~$0 -> $13.5M (2023) chips; Kazakhstan -> $18.3M (2022); Armenia -> $13.1M (2022) | works with care | Filter to aggregate rows only (isAggregate, motCode 0, partner2Code 0), or totals double. Pre-2014 rows are flagged differently. Rate-limited: 3.5 s between calls. Declared values; latest year may be partial. |
| A13 | **Sibling finder** | Normalised address on the official lists; weight 1/log(tenants) | Back-test: 240 Russia-programme address pairs on the US list, listed ~167 days apart | works with care | Strict address key is sound; loose matcher false-merges (plot buildings, same street in different cities). Registered-agent addresses (Monrovia) are noise. |
| A14 | **Listing lag** | First suspicious date vs official listing date (OFAC recent-actions, Federal Register, UK list) | RM Design and Development: established 17 Mar 2022 per its own OFAC entry, listed 20 Jul 2023 | works | Official pages only; show lags as "at least". |
| A15 | **Web corroboration** | Tavily `corroborate`: official domains first (treasury, OFAC, BIS, gov.uk, EU), then investigative outlets | 10 of 12 leads confirmed; caught ITIC listed, Sinno's real date | works | Advanced depth; general topic (news topic missed official pages). Never cite the AI summary: it invented a paragraph once. |

## B. Verification methods (how we check)

| # | Method | What it caught | Rating |
|---|---|---|---|
| B1 | **Independent verifier per investigator** (re-derives every figure from saved raw files, never from the report) | Figures with no saved file behind them; double-counted totals | works |
| B2 | **Official page for every listing date** | Sinno's "2023-04-20" (OpenSanctions dataset start) vs real 2022-09-30; RM Design 2023-07-20 not Aug 8 | works |
| B4 | **Run the tool on known positives** | Checker missed "Hoshine Silicon", then "Katrade", then "GTME" (short/transliterated) | works (and still finding gaps) |
| B5 | **Two independent signals per lead** | Stops a shared office address becoming a "front company" claim | works |
| B7 | **Cross-source triangulation** (countries' own statistics vs official pages) | Middle-country chip exports jump after 2022 in countries' own reports | works |
| B8 | **Save every raw answer with its time; cite the file** | Made B1 possible; exposed the file-overwrite bug | works |

## C. What didn't work (traps and dead ends)

| Trap | Where | Fix / workaround |
|---|---|---|
| Summing all Comtrade rows | our 10:00 figures ($52M Armenia) | Aggregate rows only (corrected 10:19) |
| OpenSanctions `first_seen` as a listing date | Sinno | Official pages; 2023-04-20 = dataset start |
| Exact-string list search | missed ITIC | Normalised + fuzzy checker |
| Checker blind to short/transliterated names | Hoshine, Katrade, GTME | Contained multi-word and rare single-word rules added; GTME still open |
| Save files named to the second | two raw answers overwritten | Microseconds + process id in names |
| Parallel agents sharing scratch scripts | nearly posted as wrong agent | Per-agent folders |
| Screening only against asset-freeze lists | Shisan Ltd and Rama Group are on EU Annex IV (export restrictions, 2026-07-24), invisible to our checker | Add EU Annex IV and other export-control lists to the checker |
| Comtrade free preview row cap | Turkey 4-code pull cut off at 500 rows | One code and one year per call |

## D. How we organise the work (orchestration)

| # | Practice | Rating | Notes |
|---|---|---|---|
| D1 | Cards on the team board; agents with their own keys claim, work, comment, send to check | works | Board join glitch: one-word names until the fix is deployed |
| D2 | Parallel waves of 3-12 agents, each on one angle, with a verifier behind each | works | Verifiers caught errors in most rounds |
| D3 | Big-picture thinkers alongside investigators | works | Produced the "need, not the name" and "method is the product" framings |
| D4 | Lead reviews every build before commit (tests, secrets scan, known positives) | works | Caught checker misses |
| D5 | One running findings log + questions log + this methods log | works | Corrections written in place with CORRECTED |
| D6 | Unlisted companies agency-only | works | Findings name only listed entities |

## E. Open method questions

- How to catch short and transliterated names (GTME) without flooding false positives? (transliteration table; screen IDs, not names)
- Can the sibling finder rank candidates *before* they're listed (true prediction), not just re-find same-wave listings?
- How to separate a real 2024 drop (bank pressure after E.O. 14114) from gaps in the data?
- How to verify registration dates without official registries?

---

## Updates (newest last)

| Time | Entry |
|---|---|
| 12:08 | Log started; backfilled from the whole morning. |
