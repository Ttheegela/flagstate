"""US lobbying-disclosure (LDA) layer: fetch filings for tracked clients and extract a graph.

Ported from the VeilTrace knowledge graph (veil-trace@88dcaa2 research/knowledge-graph/scripts/
fetch_lda.py and extract_lobby.py). Changes: clients, queries and aliases come from
data/lobbying-clients.json; lobbied/lobbied_on edges are kept per client; filing URLs use
lda.gov; lobbyists in exclude_lobbyists are dropped.

extract() output:
  nodes: lobby firms, clients, their foreign parents, lobbyists (named by the filing), government
         bodies lobbied, bills/orders named, former government posts (the revolving door)
  edges: hired, lobbied_in_house, lobbyist_at, lobbied_for, lobbied, lobbied_on,
         foreign_entity_of, formerly_served_in. Every edge carries its filing UUIDs and URL.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

from normalize import normalize_name

BASE = "https://lda.gov/api/v1/filings/"
FILING_URL = "https://lda.gov/filings/public/filing/%s/print/"
DELAY = 1.2
MAX_PAGES = 400  # per query
MAX_RETRY_WAIT = 120  # seconds
USER_AGENT = "Flagstate/1.0 (+https://github.com/Ttheegela/flagstate)"

SUBCONTRACT = re.compile(r"ON BEHALF OF|\bTHROUGH\b|\(FOR ", re.I)
BILL_RE = re.compile(r"\b(S\.\s?\d{2,5}|H\.\s?R\.\s?\d{2,5}|E\.?O\.?\s?\d{5}|Executive Order\s?\d{5})", re.I)
POSTS = [
    (r"treasury", "gov:us-treasury", "US Treasury"),
    (r"commerce|\bdoc\b", "gov:us-commerce", "US Commerce Department"),
    (r"state dep|dept\. of state|department of state|secretary of state|ambassador|\bstate\b.*secy|secy.*\bstate\b", "gov:us-state", "US State Department"),
    (r"white house|\bwh\b|to (the )?pres|ast to pres|potus|national economic council|natl econ|\bnsc\b|national security council|\beop\b|ustr|trade representative", "gov:white-house", "White House"),
    (r"senat|\bsen\b|\bsen\.|\bs\.? maj|senate", "gov:us-senate", "US Senate"),
    (r"house|congress|representative|\brep\b|\brep\.|speaker|\bspkr\b", "gov:us-house", "US House of Representatives"),
    (r"defense|pentagon|army|navy|air force", "gov:us-defense", "US Defense Department"),
    (r"justice|doj|attorney", "gov:us-justice", "US Justice Department"),
]
POST_RE = [(re.compile(p, re.I), gid, name) for p, gid, name in POSTS]
ROLE_WORDS = re.compile(r"chief|director|counsel|assist|asst|staff|member|senator|secretary|secy|advis|aide|"
                        r"correspondent|ambassador|representative|congress|legislative|\bla\b|\bld\b|\bcos\b", re.I)
KEY_BILLS = {
    "bill:s722": "S.722 Countering Iran's Destabilizing Activities Act (2017), the vehicle for new Russia sanctions",
    "bill:hr3364": "H.R.3364 Countering America's Adversaries Through Sanctions Act (CAATSA, 2017)",
    "bill:s1705": "S.1705 Chip Security Act",
    "bill:hr3447": "H.R.3447 Chip Security Act",
    "bill:s3455": "S.3455 ZTE Enforcement Review and Oversight Act",
    "bill:eo13660": "Executive Order 13660 (2014): first US sanctions over Ukraine",
    "bill:eo13873": "Executive Order 13873 (2019): securing telecom supply chains",
    "bill:eo14017": "Executive Order 14017 (2021): America's supply chains",
}
BILL_KEEP = re.compile(r"sanction|export control|export administration|entity list|russia|china|chinese|huawei|zte|"
                       r"countering|pipeline|nord stream|caatsa|adversar|outbound|cfius|iran|hikvision|drone|unmanned|"
                       r"chip security|ofac|magnitsky|ukraine", re.I)
GOV_BODIES = [
    (r"SENATE", "gov:us-senate", "US Senate"),
    (r"HOUSE OF REP", "gov:us-house", "US House of Representatives"),
    (r"TREASURY", "gov:us-treasury", "US Treasury"),
    (r"COMMERCE", "gov:us-commerce", "US Commerce Department"),
    (r"STATE - DEPT|STATE DEPT|DEPARTMENT OF STATE", "gov:us-state", "US State Department"),
    (r"WHITE HOUSE|EXECUTIVE OFFICE|NATIONAL SECURITY COUNCIL|TRADE REPRESENTATIVE|USTR", "gov:white-house", "White House"),
    (r"DEFENSE", "gov:us-defense", "US Defense Department"),
    (r"ENERGY - DEPT", "gov:us-energy", "US Energy Department"),
]
GOV_RE = [(re.compile(p, re.I), gid, name) for p, gid, name in GOV_BODIES]


def load_config(path) -> dict:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("queries", "clients", "associations", "foreign_entity_aliases", "exclude_lobbyists"):
        if key not in cfg:
            raise ValueError(f"lobbying config: missing {key}")
    return cfg


def get_json(url: str, opener=urllib.request.urlopen, sleep=time.sleep) -> dict:
    for attempt in range(6):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with opener(request, timeout=60) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise
            if attempt < 5:
                if exc.code == 429:
                    try:
                        wait = int(exc.headers.get("Retry-After"))
                    except (TypeError, ValueError):
                        wait = 20 * (attempt + 1)
                    sleep(min(wait, MAX_RETRY_WAIT))
                else:
                    sleep(5 * (attempt + 1))
        except (OSError, ValueError):
            # URLError, timeouts and truncated JSON are transient.
            if attempt < 5:
                sleep(5 * (attempt + 1))
    raise RuntimeError("giving up on " + url)


def fetch_filings(queries, get=get_json, sleep=time.sleep, base: str = BASE) -> dict[str, dict]:
    filings: dict[str, dict] = {}
    for param, value in queries:
        url = base + "?" + urllib.parse.urlencode({param: value, "page_size": 25})
        for _ in range(MAX_PAGES):
            data = get(url)
            for r in data.get("results") or []:
                if isinstance(r, dict) and r.get("filing_uuid") and isinstance(r.get("client"), dict):
                    filings[r["filing_uuid"]] = r
            url = data.get("next")
            if url and not url.startswith(base):
                raise ValueError(f"unexpected next URL: {url}")
            sleep(DELAY)
            if not url:
                break
        else:
            raise RuntimeError(f"more than {MAX_PAGES} pages for {param}={value}")
    return filings


ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\ufeff]")
WORD_MAP = {w.lower(): w for w in ("LLC", "LLP", "LP", "PLLC", "US", "USA", "DLA", "APCO", "ACG", "II", "III", "IV")}
WORD_MAP.update({"fka": "fka", "jr": "Jr", "sr": "Sr", "mr": "Mr", "mrs": "Mrs", "ms": "Ms", "dr": "Dr", "of": "of", "and": "and", "the": "the", "for": "for"})


def clean_text(s: str) -> str:
    """Undo UTF-8-read-as-cp1252 mojibake, drop zero-width characters, collapse whitespace."""
    s = s or ""
    if "\u00e2\u20ac" in s or "\u00c3" in s:
        try:
            s = s.encode("cp1252").decode("utf-8")
        except (UnicodeError, ValueError):
            pass
    return re.sub(r"\s+", " ", ZERO_WIDTH.sub("", s).replace("\u037e", ";")).strip()


def _word(w: str, first: bool, acronyms: bool) -> str:
    low = w.lower()
    if low in WORD_MAP and not (first and low in ("of", "and", "the", "for")):
        return WORD_MAP[low]
    if acronyms and 2 <= len(w) <= 4 and not re.search("[aeiouy]", low):
        return w.upper()
    out = w.capitalize()
    return "Mc" + out[2:].capitalize() if low.startswith("mc") and len(w) > 3 else out


def display_name(raw: str, acronyms: bool = True) -> str:
    """Title-case a (usually ALL-CAPS) LDA name; keep acronyms; trust tokens that already have lowercase."""
    out, prev = [], None
    for i, tok in enumerate(clean_text(raw).split()):
        key = re.sub(r"[^a-z0-9]", "", tok.lower())
        if key and key == prev:
            continue
        prev = key
        if tok.lower() == "d/b/a":
            out.append("d/b/a")
        elif re.search("[a-z]", tok):
            out.append(tok)
        else:
            out.append(re.sub("[A-Za-z]+", lambda m: _word(m.group(), i == 0, acronyms), tok))
    return " ".join(out)


def slug(s: str) -> str:
    s = re.sub(r"[.,'\"()&]", " ", s.lower())
    s = re.sub(r"\b(llc|l l c|inc|ltd|lp|llp|pllc|corp|corporation|co|company|the)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def person_name(p: dict) -> str:
    parts = [p.get("first_name") or "", p.get("middle_name") or "", p.get("last_name") or "", p.get("suffix") or ""]
    name = " ".join(display_name(x, acronyms=False) for x in parts if x and x.strip())
    return re.sub(r"\b(jr|sr|ii|iii|iv)\b", lambda m: WORD_MAP[m.group().lower()], name, flags=re.I)


def money(r: dict) -> float:
    for k in ("income", "expenses"):
        v = r.get(k)
        if v not in (None, ""):
            try:
                return float(v)
            except ValueError:
                pass
    return 0.0


def extract(filings, config: dict) -> dict:
    filings = filings if isinstance(filings, dict) else {r["filing_uuid"]: r for r in filings}
    client_re = [(re.compile(c["pattern"]), c["id"], c["name"], c["group"]) for c in config["clients"]]
    fe_re = [(re.compile(p, re.I), fid, t, n) for p, fid, t, n in config["foreign_entity_aliases"]]
    assoc = set(config["associations"])
    excluded = {normalize_name(n) for n in config["exclude_lobbyists"]}

    def match_client(name: str):
        for rx, cid, disp, grp in client_re:
            if rx.search(name.upper()):
                return cid, disp, grp
        return None

    nodes: dict[str, dict] = {}
    agg: dict[tuple, dict] = {}

    def node(nid, typ, name, **kw):
        n = nodes.setdefault(nid, {"id": nid, "type": typ, "name": name, "layer": "lobby"})
        for k, v in kw.items():
            if v not in (None, "", [], {}):
                n.setdefault(k, v)
        return n

    # One filing per (registrant, client, year, period): the version stating an amount, then the most recent.
    latest: dict[tuple, dict] = {}
    for r in filings.values():
        key = ((r.get("registrant") or {}).get("id"), r["client"].get("id"), r.get("filing_year"), r.get("filing_period"))
        rank = (money(r) > 0, r.get("dt_posted") or "")
        if key not in latest or rank > (money(latest[key]) > 0, latest[key].get("dt_posted") or ""):
            latest[key] = r
    canonical = {r["filing_uuid"] for r in latest.values()}

    def edge(s, t, typ, r, client=None, text=None):
        key = (s, t, typ, client)
        e = agg.setdefault(key, {"source": s, "target": t, "type": typ, "filings": [], "years": set(),
                                 "amount": 0.0, "texts": set(), "confidence": "Documented"})
        if client:
            e["client"] = client
        uuid = r["filing_uuid"]
        if uuid not in e["filings"]:
            e["filings"].append(uuid)
            if typ == "hired":
                # Count each firm-client-quarter once (latest version), never subcontracted money toward the client.
                if SUBCONTRACT.search(r["client"].get("name") or ""):
                    e["sub_amount"] = e.get("sub_amount", 0.0) + (money(r) if uuid in canonical else 0.0)
                    e["subcontract"] = True
                elif uuid in canonical:
                    e["amount"] += money(r)
        if r.get("filing_year"):
            e["years"].add(int(r["filing_year"]))
        if text:
            e["texts"].add(text[:220])
        return e

    kept = 0
    for r in filings.values():
        cname = (r["client"].get("name") or "").strip()
        m = match_client(cname)
        if not m:
            continue
        cid, cdisp, grp = m
        kept += 1
        ctype = "association" if cid in assoc else "person" if cid.startswith("p:") else "company"
        cn = node(cid, ctype, cdisp, group=grp)
        cn["type"], cn["name"] = ctype, cdisp
        cn.setdefault("lda_names", [])
        if cname not in cn["lda_names"]:
            cn["lda_names"].append(cname)
        rname = clean_text((r.get("registrant") or {}).get("name") or "")
        reg_match = match_client(rname)
        self_filed = reg_match is not None and reg_match[0] == cid
        if self_filed:
            fid = cid
        else:
            fid = "lf:" + slug(rname)
            node(fid, "lobbyfirm", display_name(rname))
        hired = edge(cid, fid, "lobbied_in_house" if self_filed else "hired", r)
        for fe in r.get("foreign_entities") or []:
            fname = clean_text(fe.get("name") or "")
            if not fname:
                continue
            note = "; ".join(re.findall(r"\(([^)]*)\)", fname))
            base = re.sub(r"\s*\([^)]*\)", "", fname).strip()
            if re.fullmatch(r"(joint stock company|llc|pjsc|oao|jsc)", base, re.I) and note:
                base, note = note, ""
            hit = next(((fid_, t_, n_) for rx, fid_, t_, n_ in fe_re if rx.search(base)), None)
            if hit and hit[0] is None:
                continue
            fm = match_client(base)
            if hit:
                feid, fetype, fename = hit
            elif fm:
                feid, fetype, fename = fm[0], "company", fm[1]
            else:
                feid, fetype, fename = "co:" + slug(base), "company", display_name(base)
            if feid == cid:
                continue
            node(feid, fetype, fename, country=fe.get("country") or "", group=grp,
                 role="named as a foreign entity on a US lobbying filing")
            fe_e = edge(feid, cid, "foreign_entity_of", r, text=note)
            if fe.get("ownership_percentage"):
                fe_e["ownership_pct"] = fe["ownership_percentage"]
        for act in r.get("lobbying_activities") or []:
            desc = clean_text(act.get("description") or "")
            for b in set(BILL_RE.findall(desc)):
                bid = "bill:" + re.sub(r"[^a-z0-9]", "", b.lower().replace("executive order", "eo"))
                if bid not in KEY_BILLS and not BILL_KEEP.search(desc):
                    continue
                label = re.sub(r"^(ExecutiveOrder|E\.?O\.?)", "EO ", re.sub(r"\s+", "", b))
                node(bid, "bill", label, title=KEY_BILLS.get(bid, ""))
                edge(fid, bid, "lobbied_on", r, client=cid, text=desc)
            for ge in act.get("government_entities") or []:
                gname = ge.get("name") if isinstance(ge, dict) else str(ge)
                for rx, gid, gdisp in GOV_RE:
                    if gname and rx.search(gname):
                        node(gid, "government", gdisp)
                        edge(fid, gid, "lobbied", r, client=cid, text=desc)
                        break
            if desc:
                hired["texts"].add(desc[:220])
            for entry in act.get("lobbyists") or []:
                p = entry.get("lobbyist") if isinstance(entry, dict) else None
                if not p:
                    continue
                pn = person_name(p)
                short = " ".join(x.strip() for x in (p.get("first_name"), p.get("last_name")) if x and x.strip())
                if not pn or {normalize_name(n) for n in (pn, short)} & excluded:
                    continue
                pid = "p:" + slug(pn)
                cov = clean_text(entry.get("covered_position") or "")
                pnode = node(pid, "person", pn, role="lobbyist (named in US lobbying disclosure)")
                if cov and not ROLE_WORDS.search(cov) and not re.search(r"white house|treasury|commerce|potus|nsc|ustr", cov, re.I):
                    cov = ""
                if cov and re.search(r"\bintern", cov, re.I) and not re.search(r"chief|director|counsel|assist|asst|staff|secretary|advis|aide|correspondent|member", cov, re.I):
                    cov = ""
                if cov and cov.lower() not in ("n/a", "na", "none"):
                    pnode.setdefault("covered_positions", [])
                    if cov not in pnode["covered_positions"]:
                        pnode["covered_positions"].append(cov)
                    for rx, gid, gdisp in POST_RE:
                        if rx.search(cov):
                            node(gid, "government", gdisp)
                            edge(pid, gid, "formerly_served_in", r, text=cov)
                            break
                edge(pid, fid, "lobbyist_at", r)
                edge(pid, cid, "lobbied_for", r)

    # Keep a bill only if it is a key bill or at least 3 filings name it.
    bill_filings: dict[str, set] = defaultdict(set)
    for (s, t, typ, _c), e in agg.items():
        if typ == "lobbied_on":
            bill_filings[t].update(e["filings"])
    drop = {n["id"] for n in nodes.values() if n["type"] == "bill" and n["id"] not in KEY_BILLS and len(bill_filings[n["id"]]) < 3}
    for b in drop:
        nodes.pop(b, None)

    edges = []
    for (s, t, typ, _c), e in agg.items():
        if t in drop:
            continue
        yrs = sorted(e.pop("years"))
        e["years"] = [yrs[0], yrs[-1]] if yrs else []
        e["texts"] = sorted(e["texts"])[:4]
        e["n_filings"] = len(e["filings"])
        e["source_url"] = FILING_URL % e["filings"][0]
        e["dataset"] = "US lobbying disclosures (LDA)"
        if not e["amount"]:
            e.pop("amount")
        edges.append(e)
    return {"nodes": list(nodes.values()), "edges": edges, "filings_kept": kept, "filings_scanned": len(filings)}
