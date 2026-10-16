import specific_sources as s

NODES = [
    {"id": "IMO9408695", "type": "ship", "name": "TASSOS", "listed_by": ["us", "uk"]},
    {"id": "co:zulu", "type": "company", "name": "Zulu Ships LLC", "listed_by": ["us"]},
    {"id": "p:x", "type": "person", "name": "X Person", "listed_by": ["uk"]},
]
EDGES = [
    {"source": "IMO9408695", "target": "gov:us", "type": "designated_by", "sources": [{"record": "OFAC ent_num 54815"}]},
    {"source": "IMO9408695", "target": "gov:uk", "type": "designated_by", "sources": [{"record": "RUS3483"}]},
]
RECS = s.Records(NODES, EDGES, us_names={"ZULU SHIPS": {"123"}}, uk_names={"X PERSON": {"RUS0001"}})
UK_HOME = "https://www.gov.uk/government/publications/the-uk-sanctions-list"
CSL = "https://www.trade.gov/consolidated-screening-list"


def url(u, record="", file="", quote="", source="IMO9408695", target="gov:us"):
    return s.specific_url(u, record, file, quote, source, target, RECS)


def test_list_homes_become_entries():
    assert url(CSL, "OFAC ent_num 54815") == "https://sanctionssearch.ofac.treas.gov/Details.aspx?id=54815"
    assert url(UK_HOME, "RUS3483") == "https://search-uk-sanctions-list.service.gov.uk/designations/RUS3483/Ship"
    # no record: the ship's entry holds "UK current owner/operator", the company's holds its own fields
    assert url(UK_HOME, source="co:zulu", target="IMO9408695").endswith("/RUS3483/Ship")
    assert url(CSL, source="co:zulu", target="cc:mh").endswith("id=123")  # exact-name join to the US list
    assert url(UK_HOME, source="p:x", target="gov:uk").endswith("/RUS0001/Individual")
    assert url(CSL, source="co:unknown", target="cc:mh") == CSL  # nothing to join: left for the page to label


def test_filings_acts_and_datasets():
    uuid = "94c50936-34e6-4f6f-b4fd-61fe518d8d08"
    assert url("https://lda.senate.gov", file=f"LDA filing {uuid}") == f"https://lda.gov/filings/public/filing/{uuid}/print/"
    assert url("https://efile.fara.gov", file="efile.fara.gov reg 6170, Exhibit AB 20200316-80") == \
        "https://efile.fara.gov/docs/6170-Exhibit-AB-20200316-80.pdf"
    assert url("https://efile.fara.gov", file="team note") == s.FARA_BROWSE
    assert url("https://eur-lex.europa.eu/", quote="Reg (EU) 2026/1848 point (h)") == \
        "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202601848"
    assert url(s.UA_HOME) == s.UA_DATASET
    assert url("https://home.treasury.gov/news/press-releases/sb0215") == "https://home.treasury.gov/news/press-releases/sb0215"
