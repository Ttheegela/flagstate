# Our research: sources, data and where to dig next

*Trace the Unseen build day, Fri 25 Sept 2026, Sanctions & evasion track. Written for teammates. Updated 15:08; trimmed for this site in Oct 2026.*

*Documented conduct is stated plainly with its source; our own inferences are called **leads**. People are named only when an official list or government release names them.*

## 1. The idea in one paragraph

A sanctions list only works when someone recognises the name. After Russia's full invasion of Ukraine (24 Feb 2022), Western chips kept reaching Russia through **new countries** (Kyrgyzstan, Kazakhstan, the UAE, Armenia, Turkey) and **short-lived companies**. Governments did list those companies, but months after they appeared: RM Design and Development, which the US Treasury's own entry says was established on 17 Mar 2022, was listed on 20 Jul 2023. What stays the same for years is **the product, the buyer and the route**. So our demo, for a chip distributor's compliance officer, says: *names change in weeks; the need doesn't.*

## 2. What's on the shelf (Materials)

| Item | What it is |
|---|---|
| `demo/index.html` | The live 3-minute demo (arrow keys; **E** = sources drawer for every number; **V** = presenter view) |
| `demo-slides/index.html` | Still images of the 7 screens (projector fallback) |
| `demo/SCRIPT.md` | The spoken script, with a number-by-number check table |
| `demo/DESIGN_SPEC.md` | Why each screen looks the way it does |
| `sanctions-explained/` | Plain-language explainer: how sanctions work, how evasion works |
| `shape-of-the-problem/` | Six diagrams of the system |
| `methods/methods-log.md` | **How** we found things: 21 discovery methods, 10 checks, the traps we fell into |
| `data-guide/` | What data we have, in plain words |

## 3. Data sources we used

| Source | What it gives | Access today | Watch out for |
|---|---|---|---|
| **UN Comtrade** | What each country **says** it exported, by product and year (a second, independent source) | Free preview API, [comtradeplus.un.org (database home)](https://comtradeplus.un.org/) | Use only aggregate rows (isAggregate true, motCode 0, partner2Code 0) or totals double; 500-row cap; wait 3.5 s between calls |
| **OpenSanctions** | US, EU and Ukraine lists as CSV | Downloaded locally | `first_seen` 2023-04-20 is when the dataset started, **not** a listing date |
| **Official lists** | US (OFAC SDN, BIS Entity List), UK, EU, UN | Official pages below | The EU asset-freeze list does **not** include EU Annex IV export restrictions; check both |
| **Ukraine's War & Sanctions site** (GUR) | Foreign parts found in Russian weapons | [war-sanctions.gur.gov.ua](https://war-sanctions.gur.gov.ua/en/components/2090) | GUR is a party to the war; cite it as such |
| **Tavily** (web search) | Finds official pages and reporting to confirm a lead | API key (held privately) | Cite the page, never Tavily's AI summary (it invented a paragraph once) |

## 4. Official references (check listing dates here, nowhere else)

**Lists and rules**
- OFAC 50 percent rule and FAQs: [FAQ 399](https://ofac.treasury.gov/faqs/399), [FAQ 401](https://ofac.treasury.gov/faqs/401), [FAQ 1105](https://ofac.treasury.gov/faqs/1105), [Russia FAQs](https://ofac.treasury.gov/faqs/topic/6626)
- Common High Priority List (the battlefield-goods list, chips are Tier 1): [bis.gov CHPL](https://www.bis.gov/licensing/country-guidance/common-high-priority-items-list-chpl)
- BIS Entity List rules: [15 CFR 744.11](https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-744/section-744.11)
- UK Sanctions List: [gov.uk](https://www.gov.uk/government/publications/the-uk-sanctions-list); OFSI: [about](https://www.gov.uk/government/organisations/office-of-financial-sanctions-implementation/about)
- UN Security Council humanitarian exemption, Res. 2664 (2022): [un.org](https://main.un.org/securitycouncil/en/content/sres2664-2022)

**US designations behind our demo**
- 20 Jul 2023 (RM Design and Development, GTME, Basis Trade Prosoft, Region-Prof, Onelek and others): [OFAC recent action](https://ofac.treasury.gov/recent-actions/20230720); Federal Register [2023-16934](https://www.federalregister.gov/documents/2023/08/08/2023-16934/notice-of-ofac-sanctions-action); Treasury press release jy1636
- 23 Feb 2024 (ELEM GROUP and others): [OFAC recent action](https://ofac.treasury.gov/recent-actions/20240223)
- 1 May 2024: [OFAC recent action](https://ofac.treasury.gov/recent-actions/20240501)
- 12 Jun 2024 (ITIC and others): [OFAC recent action](https://ofac.treasury.gov/recent-actions/20240612); press release jy2404
- 30 Oct 2024 (Turkish and other suppliers; Testkomplekt's suppliers named): [OFAC recent action](https://ofac.treasury.gov/recent-actions/20241030); [press release jy2700](https://home.treasury.gov/news/press-releases/jy2700)
- Other Treasury releases cited: [jy1494](https://home.treasury.gov/news/press-releases/jy1494), jy1731, jy1871 (2 Nov 2023), jy1978 (12 Dec 2023), [sb0468](https://home.treasury.gov/news/press-releases/sb0468)
- Entity List additions, 19 Oct 2023: [Federal Register 2023-23048](https://www.federalregister.gov/documents/2023/10/19/2023-23048/entity-list-additions)

**EU**
- EU Annex IV export-restriction entries (Shisan Ltd entry 964, Rama Group entry 963, same Bishkek address): Decision (CFSP) 2026/1849 and Regulation OJ L 2026/1848, 24 Jul 2026 (on EUR-Lex)
- Council document on earlier listings: [ST-11618-2024](https://data.consilium.europa.eu/doc/document/ST-11618-2024-INIT/en/pdf)

**Context**
- CREA, false-flag tankers carrying Russian oil (2025): [energyandcleanair.org](https://energyandcleanair.org/publication/flags-of-inconvenience-113-vessels-flying-a-false-flag-transported-eur-4-7-bn-russian-oil-in-first-three-quarters-of-2025/)
- Oxfam on remittances to Somalia (how sanctions can hurt the wrong people): [oxfamamerica.org](https://www.oxfamamerica.org/explore/research-publications/hanging-by-a-thread-the-ongoing-threat-to-somalias-remittance-lifeline/)
- UN sanctions regimes overview: [un.org PDF](https://main.un.org/securitycouncil/sites/default/files/subsidiary_organs_series_7sep23_.pdf)

## 5. Findings beyond the demo (verified, good places to expand)

- **AI chips.** Bloomberg reported Shreya Life Sciences shipping H100 servers to Russia; OFAC listed it two days later (30 Oct 2024).
- **Medicine and humanitarian goods** (the other side of sanctions): see `sanctions-explained/` for exemptions and over-compliance.

## 6. Open leads for someone to pick up

1. **The teammate's leads** (being checked now): Georgia's Kulevi refinery (EU 21st package, July 2026); Lukoil International's sale and OFAC's March 2026 "control, not just 50%" guidance; shadow-fleet service providers (refuelling, ship-to-ship).
2. **Add EU Annex IV and other export-control lists to our checker.** It is blind to them today.
3. **Catch short and transliterated names** (GTME) without false alarms: screen tax and registration numbers, not only names.
4. **Who took over after a listing?** For a listed shipper, find who shipped to the same buyers in the next six months.
5. **Other products:** machine tools, bearings, and climate-linked goods (Russian timber, aluminium, fertiliser relabelled through third countries). A wave of agents is on these now.

## 7. Rules we keep

- State documented conduct plainly with its source: government findings, and what the records directly show (for example "kept shipping after being sanctioned"). Describe conduct; don't write "illegal" unless a court or agency said so.
- Use "lead" only for our own inferences about firms that aren't listed (timing, a shared address, a one-ship company).
- Listing dates from **official pages only**, and the **first** restriction counts (for ELEM Group that is the US Commerce Entity List, 7 Dec 2023).
- **Two independent signals** before calling a pattern, and **ID, address and country agreement** before saying two records are the same company.
- Every number traces to a saved raw answer; our verifier agent re-derives every figure.
- People are named only when an official list or government release names them, in that role.

---

## 8. Numbers that remain and where they come from

These are the items that stand on official or public sources. "Check" says how it was verified: *verified* = re-derived by
our skeptic from the saved raw answer; *official* = from a government page.

| Claim | Value | Source | Check |
|---|---|---|---|
| Russia's full-scale invasion of Ukraine. | 24 Feb 2022 | Public record | official |
| Kyrgyzstan's own reported chip exports to Russia, declared value, by year 2019 to 2024. No row was returned for 2019 and 2020 (not the same as a reported zero). 2024 may be incomplete. | 2023: $13.5 million (2019 to 2024: no row, no row, $0.006M, $0.66M, $13.5M, $1.3M) | Kyrgyzstan's own export report to the UN (UN Comtrade), aggregate rows (receipt: `8542_exports_to_russia_2019_2024_AGGREGATE.json, field "aggregate" (corrected totals, LOG 10:19)`) | official |
| Kazakhstan's own reported chip exports to Russia, declared value, 2019 to 2024. | 2022: $18.3 million (2019 to 2024: $0.33M, $0.18M, $0.25M, $18.3M, $15.6M, $0.41M) | UN Comtrade, aggregate rows (same receipt) | official |
| Armenia's own reported chip exports to Russia, declared value, 2019 to 2024 (no row returned for 2024). | 2022: $13.1 million (2019 to 2024: $0.12M, $0.005M, $0.002M, $13.1M, $15.7M, no row) | UN Comtrade, aggregate rows (same receipt) | official |
| The UN's trade database returns one total split across several rows plus a summary row; adding every row counted each total twice (Kyrgyzstan 2023: $27.1 million summed, $13.5 million on the summary row). We use summary rows only. Also corrected: Kazakhstan 2022 $18.3 million (not $36.5 million), Armenia 2022 $13.1 million (not $52.4 million). | $27.1M counted, $13.5M correct | UN Comtrade (receipt: `pulls/comtrade/8542_exports_to_russia_2019_2024_AGGREGATE.json (Kyrgyzstan 2023: all_rows_sum 27,062,780; aggregate 13,531,390); LOG 10:19`) | verified |
| RM Design and Development (Bishkek, Kyrgyzstan): the US Treasury sanctions entry reads "Established 17 Mar 2022", 21 days after the invasion. Listed by the US Treasury on 20 Jul 2023. | at least 16 months from founding to listing | Federal Register 2023-16934 (published 8 Aug 2023, action 20 Jul 2023) | official |
| ELEM GROUP (Almaty, Kazakhstan) was first restricted by the US Commerce Department (Entity List) on 7 Dec 2023; the US Treasury sanctions list followed on 23 Feb 2024. | 7 Dec 2023 | 88 FR 85097; ofac.treasury.gov/recent-actions/20240223 | official |
| STRELOI EKOMMERTS (St Petersburg) listed by the US Treasury; ITIC LLC FZ (Dubai) listed by the US Treasury and, on 25 Feb 2025, the EU. | 12 Dec 2023; 12 Jun 2024 | ofac.treasury.gov/recent-actions/20231212 and 20240612 | official |
| Testkomplekt (Russia) listed by the US Treasury and the UK. On 30 Oct 2024 the US Treasury listed Shenzhen One World, Shenzhen A Technology and Innovio Ventures; its press release names Testkomplekt as their customer. | 19 May 2023; 8 Aug 2023; 30 Oct 2024 | Treasury jy1494; UK Sanctions List RUS1949; Treasury jy2700 | official |
| Enkor Grupp (Kaliningrad) listed by the US Treasury. Titan-Micro listed by the US Treasury. Sinno Electronics (Hong Kong) on the US Commerce Entity List and the US Treasury list. | 14 Sep 2023; 19 May 2023; 28 Jun 2022 and 30 Sep 2022 | OFAC recent actions; Federal Register 2023-21224; Treasury jy1494 | official |
| Ukraine's defence intelligence (GUR, a party to the war) documents the STM32F765VIT6 microcontroller, a flight-control chip, in the Shahed-136 drone. | STM32F765VIT6 in Shahed-136 | GUR War and Sanctions portal, component 2090 (`https://war-sanctions.gur.gov.ua/en/components/2090`) | official |
| Bloomberg reported that Shreya Life Sciences (India) shipped servers with H100 AI chips to Russia. Shreya was added to the US Treasury sanctions list two days after that report. The reported shipments are Bloomberg's, not re-checked by us. | 30 Oct 2024 | US Treasury sanctions list via OpenSanctions (first-seen date); Bloomberg report | verified |
| Why Iran's oil hides: tankers transfer oil ship to ship off Johor, Malaysia, and it is relabelled as Malaysian or Omani blends (cited context, not re-checked by us). | context | US House committee report; United Against Nuclear Iran ship-to-ship tracking | approximate |
| A listing date for Sinno was really a dataset start date (shown 20 Apr 2023; real US listing 30 Sep 2022). Caught by our checker. | correction | Team log, 25 Sep 2026 | verified |
