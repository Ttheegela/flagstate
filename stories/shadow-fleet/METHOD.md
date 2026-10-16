# Method: following hulls, not names

These are the steps behind [FINDINGS.md](FINDINGS.md). The scripts in
[../../tools/fleet/](../../tools/fleet/) run steps 1 to 4 on public files.

## 1. Get the public list files

| File | Where it comes from | What we use |
|---|---|---|
| UK Sanctions List (CSV) | UK government, Office of Financial Sanctions Implementation / FCDO | ship rows: IMO number, regime, "Date Designated", "Current owner/operator (s)", "Previous owner/operator (s)" |
| US OFAC SDN list | OpenSanctions export ("targets.simple" CSV) | vessel rows: IMO in the identifiers field, programme text, "first seen" date |
| US Consolidated Screening List (optional) | US government trade.gov download | a second view of the US programme codes |
| EU financial sanctions (optional) | OpenSanctions export of the EU list | company names, for the manager check |
| EU ship annex (optional) | The EU act on EUR-Lex (for July 2026: Regulation 2026/1848, entries 652 to 692) | you type or paste the IMO numbers into a small `imo,date` CSV |

## 2. Join by IMO number, nothing else

- Keep only seven-digit IMO numbers. Strip spaces and the letters "IMO".
- One hull can have several rows on one list (for example one per regime, or one per past
  name). Collapse them per IMO and keep the **earliest** designation date.
- Join the UK Russia-regime hulls (625 in the file we used, report dated 21 September 2026)
  to the US vessel entries on that number.

## 3. State the programme filter, every time

This is the trap. The word "Iran" appears in two different ways in the US data:

1. as a **programme code** on the entry (upper case, such as `IRAN-EO13902` or `IFSR`), and
2. as a **cited order** inside a Russia action (text such as "Executive Order 13846 (Iran)").

Counting the first only gives one number; counting both gives another. Adding a second US
file, or the US terrorism programme, moves it again. With our files:

| Filter | Tankers on the UK Russia list and a US list |
|---|---|
| US entry carries an Iran programme code (**strict**) | **42** |
| plus Russia actions that also cite the Iran order E.O. 13846 (IVY, OLIA, PANDA) | 45 |
| plus a ship whose Iran code (IFSR) appears only in the Consolidated Screening List (FRUNZE) | 46 |
| plus ships the US listed only under its terrorism programme (SDGT) | 54 |

None of the US Russia-programme ships fall inside the strict 42. Any number quoted from this
work should carry its filter in the same sentence. Two teammates got 42 and 45 from the
same files before we found this.

## 4. Compare dates and names on the joined hulls

- **Who listed first:** UK date minus US date, in days. Positive means the US was first.
- **Name mismatch:** compare the UK name with the US primary name after removing spaces and
  punctuation. The UK list sometimes writes a ship as `IMO 9417464 ('TANI')`; use the quoted
  name. Say whether US aliases count: 16 of 42 differ on the primary name, 13 if aliases count.

## Why names fail

- A hull can carry a different name on each list, and the same name can belong to
  different hulls over time. Across all sources, the 42 hulls had a median of 4 names each
  (range 2 to 7).
- Search by name also returns the wrong ship. One search for a listed tanker returned a
  different ship with a different IMO number, which we dropped. Always confirm the IMO number
  on each page you use.
- Managers change too. Companies named after the ship they own, or after one of its former
  names, are common. Screening a new company name finds nothing; screening the hull finds it.

## Checking managers

- Read the UK list's "Current owner/operator" column for each joined hull and match those
  names against the US, EU and UK company entries after normalising (upper case, drop
  punctuation and suffixes such as LTD, LLC, FZE).
- Exact normalised matching misses spelling variants and transliterations, so "no hit"
  means "not found by this matcher", not "proven unlisted".
- **Registered-agent addresses are noise.** One Majuro address had about 145 rows in the US
  file; a Seychelles address had 16 rows across unrelated programmes. Treat an address
  shared by more than about 15 listed firms as an agent's address, not a cluster.
- **Publishing rule:** `tools/fleet/mgrs.py` replaces the name of any manager with no list
  hit by `UNLISTED-nn`. Keep it that way for anything public.

## Dates and sources we could not fully trust

- **US dates** are OpenSanctions "first seen" dates. Entries dated 20 or 21 April 2023 are
  the start of that dataset, not listing dates.
- **Manager changes:** for "when did the manager change" questions, we used the dated ship
  pages of Ukraine's war-sanctions database, which is not a sanctions list, and treated those
  as single-source leads.
- **EU act numbers:** the July 2026 ship act is Regulation 2026/1848. The act that froze the
  shipping firms is cited as Implementing Regulation 2026/1843 on the EUR-Lex page we read
  and as 2026/1845 in the OpenSanctions EU export. We have not resolved which is right.

## What would make this stronger

Dated ship histories (the free Equasis registry, AIS tracking, or commercial ship
databases) would let us test whether manager and flag changes follow listings. We did not
have those on the day.
