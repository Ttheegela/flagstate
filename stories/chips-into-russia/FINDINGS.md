# Semiconductors into Russia: what the official records show

Every figure here comes from free official sources and is rebuilt nightly by `scripts/build_chips.py`
into `data/routes.json`, `data/coverage.json` and `data/listing_lag.json`. Figures below are from the
build of 15 October 2026. Companies are named only where a US Treasury press release names them.
Nothing here is a legal finding; trade figures are declarations, not traced shipments.

Sources:

- UN Comtrade (database home https://comtradeplus.un.org/; figures from its public preview API), HS 8542 ("electronic integrated
  circuits"), annual exports with partner Russia, each country's own declaration, in US dollars; and
  the data-availability list (`/public/v1/getDA/C/A/HS`). Used under the Comtrade data-use policy
  (https://uncomtrade.org/docs/policy-on-comtrade-data-use/); the site publishes a small selection only.
- Eurostat Comext, dataset DS-045409, EU27 exports of HS 8542, in euros (CC BY 4.0).
- US Treasury (OFAC) SDN advanced XML (https://ofac.treasury.gov/sanctions-list-service), for listing dates,
  "Organization Established Date" and addresses.
- Consolidated Screening List (https://www.trade.gov/consolidated-screening-list), for BIS Entity List dates.
- US Treasury press releases jy1102, jy1402, jy1636, jy2546 and jy2700
  (https://home.treasury.gov/news/press-releases/<id>), for which firms were named for chips or electronics.

## 1. Who reported sending chips to Russia

Sum of every country's declared chip exports to Russia: $1,025M (2019), $1,110M (2020), $1,384M (2021),
$616M (2022), $562M (2023), $300M (2024), $260M (2025). Fewer countries report each recent year, so the
latest years are incomplete (section 3).

- **Europe and the US fell to almost nothing.** Netherlands $373M (2021) to $41M (2022) to a reported zero
  row from 2023; Germany $108M to $18M to under $0.1M; USA $55M to $10M to under $1M. Eurostat's EU27
  total to Russia: EUR 622M (2021), EUR 120M (2022), EUR 0.13M (2023).
- **Hong Kong and mainland China became almost all of it.** Hong Kong $283M (2021), $208M, $308M (2023),
  $172M, $190M (2025); China $72M (2021), $180M, $178M, $100M, $62M. Together 26% of the reported total
  in 2021, 87% in 2023 and 97% in 2025. Hong Kong's figures include re-exports.
- **Small countries appeared after the invasion.** Kazakhstan $0.25M (2021), $18.3M (2022), $15.6M (2023),
  $0.4M (2024); Kyrgyzstan $0.01M, $0.7M, $13.5M, $1.3M, $2.0M (2025); Armenia about $0, $13.1M, $15.7M,
  then a reported zero row in 2024 and 2025. Turkey $0.06M (2021) rising to $4.8M (2024); UAE $1.7M (2021),
  $4.8M (2022), $2.1M (2023), no report since.
- **EU exports to the same countries.** EU27 to Kazakhstan EUR 6.1M (2021) to EUR 17.9M (2022); to
  Turkey EUR 203M (2021) to EUR 371M (2023).
- **Russia's own figures stop.** Russia reported chip imports of $1,166M (2019), $1,254M (2020) and
  $1,555M (2021) and has published none since. Partner declarations are not the same as Russia's imports:
  in 2021 they add up to less than Russia's own figure.

## 2. How long the US took to list new chip suppliers

A hand-checked set of 64 firms outside Russia and Belarus that one of five US Treasury press releases
(November 2022 to October 2024) names for sending chips, microelectronics or electronic components to
Russia (`data/chips-firms.json`, joined to the OFAC list by OFAC id). Months = (OFAC listing date minus
the "Organization Established Date" in OFAC's own entry) / 30.44 days.

- **25 of the 64 were founded after 24 February 2022.** Median 20.3 months from founding to OFAC listing
  (middle half 16.1 to 25.8). Shortest: Milur Electronics (Armenia) 6.1 months; RM Design and Development
  (Kyrgyzstan), founded 17 March 2022 and listed 20 July 2023, 16.1 months. Longest: Pointer Electronics
  (India) 31.6 months.
- **35 were founded before the invasion** and 4 have no founding date in their OFAC entry (Abhar
  Technologies, Innovio Ventures, Shenzhen One World International Logistics, Sunshine Logistics
  Shenzhen); both groups are left out of the median.
- **The Entity List sometimes came first.** Allparts Trading, Avtex Semiconductor and Maxtronic were on the
  BIS Entity List on 12 April 2023 (88 FR 23332), about 18 months before OFAC listed them on 30 October 2024.
- **Wider base.** All 129 entities on OFAC's Russia programme (RUSSIA-EO14024) founded after the invasion
  and based outside Russia and Belarus: median 18.2 months (middle half 12.3 to 23.6).
- **Limits.** No official list says what goods a firm was listed for, so the set rests on the press
  releases; it is not every chip supplier. One firm from the releases (RRG Engineering Technologies, India)
  was not found on the current OFAC list and is not in the set.

## 3. What the records cannot see

In UN Comtrade's availability list, a country either reported a chip export row to Russia, reported its
trade with no such row, or did not report that year. Countries with a chip row: 56 (2019), 64 (2021),
55 (2022), 37 (2023), 18 (2024), 11 (2025 so far). Part of the fall is real (EU and US exports stopped)
and part is late reporting. A missing row is not proof of zero trade. Taiwan's trade appears as "Other
Asia, nes".
