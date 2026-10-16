import json
from pathlib import Path

import pytest

from normalize import normalize_name, parse_imo

CASES = json.loads((Path(__file__).parent / "normalize_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["names"], ids=lambda c: c["in"] or "<empty>")
def test_normalize_name(case):
    assert normalize_name(case["in"]) == case["out"]


@pytest.mark.parametrize("case", CASES["imos"], ids=lambda c: c["in"])
def test_parse_imo(case):
    assert parse_imo(case["in"]) == case["out"]
