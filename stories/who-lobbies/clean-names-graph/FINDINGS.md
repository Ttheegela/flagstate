# Clean names, listed interests

*How companies on US sanctions or export blacklists show up in lobbying records through names that are not listed. Trace the Unseen, 25 September 2026. Six research angles, each checked by an independent verifier; graph built from the verified links only.*

**Open `index.html`** (works from disk). Hover a dot or line for its source; filter by listed company, country, or documented links only.

## The pattern

A listed company rarely signs a lobbying form itself. A **clean name** signs instead, and the listed company appears only in the small print:
- **A US subsidiary as the client:** Hikvision USA, Huawei Technologies USA, Futurewei, Sberbank CIB USA.
- **A parent as the client:** En+ Group for Rusal.
- **A law firm "on behalf of":** "Akin Gump on behalf of SMIC".
- **A funded project company:** Nord Stream 2 AG for Gazprom.
- **A trade association or coalition:** drone coalitions funded by DJI; the US-China Business Council.
- **A government:** Bulgaria for Lukoil's Burgas refinery; Russian ministries for state banks.

US lobbying filings have a **"foreign entities"** box where the client must name foreign companies that own, control or fund it. That box is where many listed parents appear: Hangzhou Hikvision and its state-owned parent CETC behind Hikvision USA (2022), and Huawei behind Huawei Technologies USA and Futurewei (2022).

Lobbying is legal. Being listed is a legal status; nothing here says any lobbying was unlawful.

## By the numbers

- **61 organisations:** 17 listed companies, 12 clean intermediaries, 6 trade associations or coalitions, 20 lobbying or law firms, 6 governments or lawmakers.
- **60 links: 48 Documented** (an official record shows the link) and **12 Leads** (plausible, not yet proven, drawn dashed).
- **228 lobbying filings** with foreign entities from Russia, Belarus, Iran, China, Hong Kong, the UAE, Turkey or Kazakhstan were scanned, and 616 names checked against the lists. Most pre-2022 hits (Alfa-Bank, Gazprom, VEB) came **years before** those firms were listed, so they show the channel, not lobbying while listed.

## Strongest cases

1. **Hikvision** (on the US export blacklist since 9 Oct 2019). Its US arm, Hikvision USA, paid Sidley Austin up to **$500,000 a quarter** (2018 to 2021). A 2022 filing through The Elevation Association names Hangzhou Hikvision and state-owned CETC as foreign entities. *Documented.*
2. **Rusal via En+.** Rusal filed nothing under its own name. Its parent En+ paid Mercury Public Affairs **$108,500 a month** (later $54,250) from 2019 to 2022 under the foreign-agent law, and DCI Group $10,000 to $40,000 a quarter from 2021 to 2025. The hiring is *documented*; the ownership link as drawn is a *lead*.
3. **SMIC** (on the US export blacklist). "**Akin Gump on behalf of SMIC**" reported $50,000 to $140,000 a quarter (2020 to 2022) on export eligibility; Capitol Counsel also named SMIC as a foreign entity. *Documented.*
4. **Sberbank.** Its US arm, Sberbank CIB USA, paid the Madison Group ($50,000 to $105,000) and the Podesta Group ($20,000 to $110,000) a quarter in 2016 and 2017. *Documented.*
5. **Gazprom via Nord Stream 2.** Capitol Counsel and Roberti Global lobbied on pipeline permitting (Q3 2017). The filings themselves say Gazprom funds 50% of the pipeline company and the Russian state owns 38% of Gazprom. *Documented.*

Also on the graph: **Huawei** through Huawei Technologies USA (Squire Patton Boggs) and Futurewei; **DJI** as a funder of drone coalitions (its US arm's link to the listed parent is a lead); **Arctic LNG 2**, which is itself listed and filed **directly**, the reverse pattern; **Lukoil** through the government of Bulgaria; **Alrosa** and the Antwerp World Diamond Centre (a lead, from press reporting).

## What we could not see

- Lobbying outside US disclosure systems (Brussels, national capitals, think tanks) is mostly invisible; Russian-linked entities are barred from the EU Transparency Register.
- Only 8 links carry a dollar amount; many filings report none.
- Some foreign-agent exhibits black out the client's name. One figure ($573,618.62 in a Sidley Austin foreign-agent filing) is unverified, so it is kept in the data but not used for line thickness.
- Where verifiers disagreed about a corporate link, it was marked as a lead.

## Files

- `index.html`: the interactive graph (data embedded).
- `nodes.json`, `edges.json`: every organisation and link, with type, dates, amounts, evidence grade and source reference (filing ID or URL).
