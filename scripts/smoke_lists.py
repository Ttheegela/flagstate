"""Post-build check: every data file loads and finds a known name. Exit 1 on any problem.

Samples are names that have been on each list for years. If one is ever delisted,
the nightly issue will say so; replace it with another long-standing name.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from normalize import normalize_name

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = {"us": "TASSOS", "uk": "TASSOS", "eu": "Saddam Hussein Al-Tikriti", "un": "ERIC BADEGE"}


def check(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    lists_dir = Path(root) / "data" / "lists"
    for list_id, sample in SAMPLES.items():
        path = lists_dir / f"{list_id}.json"
        try:
            records = json.loads(path.read_text(encoding="utf-8"))["records"]
        except Exception as exc:
            problems.append(f"{list_id}: cannot load {path.name}: {exc}")
            continue
        if any(not isinstance(r, list) or len(r) != 7 for r in records):
            problems.append(f"{list_id}: malformed record")
        if normalize_name(sample) not in {r[1] for r in records}:
            problems.append(f"{list_id}: sample {sample!r} not found")
    try:
        meta = json.loads((lists_dir / "meta.json").read_text(encoding="utf-8"))["lists"]
        missing = sorted(set(SAMPLES) - set(meta))
        if missing:
            problems.append(f"meta.json: missing {missing}")
    except Exception as exc:
        problems.append(f"meta.json: {exc}")
    try:
        index = json.loads((Path(root) / "data" / "research-index.json").read_text(encoding="utf-8"))
        if not any(e.get("name") == "TASSOS" for e in index["entries"]):
            problems.append("research-index.json: TASSOS not found")
    except Exception as exc:
        problems.append(f"research-index.json: {exc}")
    return problems


def main() -> int:
    problems = check()
    print("\n".join(problems) if problems else "smoke check passed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
