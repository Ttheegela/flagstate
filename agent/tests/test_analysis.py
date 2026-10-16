import json
import subprocess
import sys
from pathlib import Path

from agent.analysis import analyse
from agent.lookup import lookup

LIVE = {"facts": {"flag": "Cameroon", "name": "TASSOS"}, "sources": ["https://live.example/tassos"]}
MEMORY = [{"field": "flag", "value": "Liberia", "source": "x", "observed_at": "2026-10-01", "superseded_at": None}]


def test_flags_for_tassos():
    out = analyse({"lookup": lookup("TASSOS"), "live": LIVE, "memory": MEMORY})
    kinds = {f["flag"] for f in out["flags"]}
    assert {"on_official_list", "name_changed", "flag_changed", "owner_or_manager_changed",
            "dark_fleet_indicator", "live_disagrees_with_record", "changed_since_last_check"} <= kinds
    assert out["risk"] == "high"
    assert all(f["source"] and f["source"].startswith("http") for f in out["flags"])
    change = next(f for f in out["flags"] if f["flag"] == "changed_since_last_check")
    assert change["severity"] == "high" and "Liberia" in change["evidence"] and "Cameroon" in change["evidence"]


def test_clean_subject_has_no_flags():
    assert analyse({"lookup": lookup("zzqx nothing"), "live": {}, "memory": []}) == {"flags": [], "risk": "none", "flag_count": 0}


def test_runs_as_script():
    script = Path(__file__).parents[1] / "analysis.py"
    payload = json.dumps({"lookup": lookup("9408695"), "live": {}, "memory": []})
    out = json.loads(subprocess.run([sys.executable, str(script)], input=payload, capture_output=True, text=True, check=True).stdout)
    assert out["risk"] == "high"
