# Sanctions Influence Network

**An interactive knowledge graph linking sanctioned shipping to the lobbying around it.**

The map joins two datasets that are usually studied apart: the shadow fleet of tankers carrying Russian and
Iranian oil, with the companies that own and run them, and the US lobbying bought by their parent companies, banks
and state owners. It shows the people involved (officially named individuals, and lobbyists with the government jobs
they disclose) and marks the ships seen live on our God's Eye globe. Every line on the map opens the record it came from.

| | |
|---|---|
| **Open** | [`index.html`](index.html), the map · [`methods.html`](methods.html), methods and sources in plain language |
| **Scale** | 3,183 nodes · 3,708 links · 1,547 sanctioned ships · 1,513 US lobbying reports · 421 lobbyists |
| **Data as of** | 25 September 2026 |
| **Built at** | Trace the Unseen: Climate Intelligence Build Day, Microsoft Garage NYC (sanctions and evasion track) |

## Key findings

1. **The front companies don't lobby; their owners do.** We found zero US lobbying reports for the 18 ship
   managers, front companies and oil traders we searched, including Sovcomflot, Zulu, Fleet Tanqo, Lukoil and
   Rosneft. The lobbying comes from parent companies, banks and state-linked firms.
2. **Nord Stream 2 paid Washington firms $13.87 million (2016 to 2022)**, much of it on Russia-sanctions
   legislation such as S.722. The total is counted once per firm, client and quarter, with amendments and
   subcontracts not double-counted, and was checked by hand.
3. **Sanctioned Russian banks lobbied on the scope of sanctions.** Sberbank's US arm, VTB and Gazprombank hired
   firms after 2014; one stated issue was "clarifying scope of sanctions imposed by Executive Order 13660". All three
   are now fully blocked.
4. **Only 14 records join the two sides.** Examples: the Russian state owns Sovcomflot (Treasury); Gazprom owns
   Gazprom Neft, whose subsidiary runs listed tankers (Treasury); Rosneft controls its tanker company Rosnefteflot
   (Treasury); the US list links seven shipping companies to Arctic LNG 2, which hired a Washington firm in 2023.
5. **The revolving door is on the record.** 176 lobbyists on these accounts disclose past government posts,
   including former senators and a former counselor to the Secretary of the Treasury.
6. **Some listed ships are sailing right now.** Of 27 listed ships broadcasting positions in our God's Eye snapshot,
   24 are on the map; six connect through state-owned Sovcomflot to the lobbying side.

## Using the map

| Action | How |
|---|---|
| Guided story (9 steps) | Arrow keys, or **Back / Next** in the caption bar |
| Explore freely | **Explore** hides the story; **Overview** (`0`) shows everything |
| Search | `/`, then a company, ship, person or 7-digit IMO number |
| Connection between two names | **Find a path** (never routes through bills or bodies being lobbied) |
| Records behind anything | Click it: every link lists its date, record number and source |
| Filter | Russia · Iran · China and semiconductors · Other · Leads · **Live on AIS** |

**Visual key.** Columns run left to right: Government, Bills and orders, Lobbyists, Lobbying firms, Clients, Parent
companies, then the fleet in Russia, Iran and other clusters. Colour shows the side (blue companies and ships, orange
lobbying, green government); shape shows the type. A solid red ring means blocked (asset freeze), a dashed ring means
restricted (trade, loan or investment limits). Hollow shapes run listed ships but are on no list themselves. White lines
join the lobbying side to the fleet. A pulsing green ring means the ship was seen live on AIS.

## Data sources

| Source | Used for |
|---|---|
| UK sanctions list (21 Sep 2026) | Listed ships, hull numbers, owners and operators, flags |
| US Treasury SDN list and US Consolidated Screening List | Blocked and restricted entities; ships' "Linked To" companies |
| EU asset-freeze list | EU listings and dates |
| Ukraine war-sanctions database | Former names and flags only (not a sanctions list) |
| US Lobbying Disclosure Act database ([lda.gov API](https://lda.gov/api/redoc/v1/)) | Clients, firms, fees, issues, bills, lobbyists and their past posts |
| Foreign Agents Registration Act filings ([En+ Group exhibit](https://efile.fara.gov/docs/6170-Exhibit-AB-20200316-80.pdf), [Hikvision statement](https://efile.fara.gov/docs/3731-Supplemental-Statement-20250430-53.pdf)) | Two foreign-agent contracts (En+ Group, Hikvision) |
| US Treasury press releases | Ownership statements (e.g. jl2629, jy2777) |
| Team research | The shadow-fleet map (`research/shadow-fleet/`) and a lobbying study including EU register entries |
| God's Eye View sanctions layer | Snapshot of listed ships seen on live AIS (20:11 UTC, 25 Sep 2026) |

## Method in brief

1. Ships are joined across lists by their permanent IMO hull number; the lists supply owners and operators.
2. Lobbying reports were pulled in full (every page) for the clients in our story: 3,232 scanned, 1,513 kept after
   exact client matching.
3. Fees count each firm, client and quarter once (latest version stating an amount); subcontracted fees are shown
   but not added to client totals.
4. Sanctions status is looked up by record number on the US and UK lists: **blocked** vs **restricted**.
5. Links between the two sides are hand-checked against official sources in `scripts/curated.json`.
6. The team's lobbying layer is merged by name, each match checked by hand; where both sources link the same pair,
   the link carrying the filing number and amount is kept.

Full detail, in plain language: [`methods.html`](methods.html).

## Confidence and naming

- **Documented** (3,676 links): an official record states it directly. **Reported** (1): an official filing seen in
  summary only. **Lead** (31): our inference, drawn dotted, hideable with the Leads filter.
- We describe documented conduct with its source and make no legal findings; "charged" is never "convicted".
- People are named only where an official list or release names them, or in their own lobbying disclosure, in that
  role. Unlisted firms known only from non-official sources appear as a description (12).

## Limitations

- "No path found" and "no lobbying found" are not proof of no relationship or no influence.
- US lobbying only, plus a few EU register entries from team research; fees are self-reported and rounded to $10,000.
- En+ Group cannot be searched by name on the lobbying API (the "+" is ignored); it comes from earlier targeted pulls.
- Bills are limited to key bills and those named in three or more reports (125).
- Live AIS is a moment in time: sanctioned tankers often switch off or spoof their transponders.
- Six people from the shadow-fleet research await re-checking and are marked "(?)".

## Rebuilding

The scripts in `scripts/` document the method and run from the event workspace, which holds the raw pulls:

```
python scripts/fetch_lda.py       # every page of lobbying reports for the chosen clients -> pulls/lda/
python scripts/extract_lobby.py   # lobbying layer: clients, firms, lobbyists, bills, fees
python scripts/build_kg.py        # merge with the shadow-fleet map and curated links -> kg_data.js
```

To view locally, serve the folder (`python -m http.server 8792`) and open `http://localhost:8792`. The page loads
force-graph from cdn.jsdelivr.net, so it needs an internet connection.

## Files

| Path | Contents |
|---|---|
| `index.html` | The interactive map |
| `methods.html` | Methods and sources in plain language |
| `kg_data.js` | Built graph data (nodes, links, sources) |
| `data/godseye_live.json` | The God's Eye live-AIS snapshot used for the green markers |
| `scripts/curated.json` | Hand-checked links and sanctions statuses, each with its source |
| `scripts/*.py` | Fetch, extract and build scripts |

## Credits

Built by our team with AI agents (Claude Code) doing research, cross-checking and building under human direction.
Graph rendering by [force-graph](https://github.com/vasturiano/force-graph) (MIT). Fonts: Inter and JetBrains Mono
(SIL Open Font Licence). Sanctions lists and lobbying records are public government data.
