from agent.lookup import lookup


def test_name_matches_tassos():
    r = lookup("TASSOS")
    assert r["research"][0]["name"] == "TASSOS"
    assert r["imo"] == "9408695"
    assert {h["list"] for h in r["lists"] if h["match"] == 3} >= {"us", "uk"}
    assert all(h["url"].startswith("http") for h in r["lists"])


def test_imo_matches_in_any_form():
    for q in ("9408695", "IMO 9408695", "check imo 9408695 please"):
        r = lookup(q)
        assert r["imo"] == "9408695"
        assert r["research"][0]["name"] == "TASSOS"
        assert all(s["url"].startswith("http") for s in r["research"][0]["sources"])


def test_no_match():
    assert lookup("zzqx nothing here") == {"query": "zzqx nothing here", "imo": None, "research": [], "lists": []}
    assert lookup("")["research"] == []
