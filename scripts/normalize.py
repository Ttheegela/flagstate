"""Name normalisation shared by every build script. Mirrors app/normalize.js;
both must pass scripts/normalize_cases.json."""
from __future__ import annotations

import re
import unicodedata

# Legal-form suffixes dropped during normalisation (whole tokens only).
LEGAL_SUFFIXES = frozenset({
    "LLC", "LTD", "LIMITED", "INC", "INCORPORATED", "CORP", "CORPORATION",
    "CO", "COMPANY", "PLC", "GMBH", "SA", "SAS", "SARL", "SRL", "SPA",
    "BV", "NV", "AG", "KG", "OY", "AB", "AS", "PTY", "PJSC", "JSC",
    "OJSC", "PAO", "ZAO", "OOO", "OAO", "PC", "LP", "LLP", "SDN", "BHD",
    "KFT", "DOO", "EOOD", "AD", "SP", "ZOO", "TOO",
})

_PUNCT_RE = re.compile(r"[^A-Z0-9_\s]")
_IMO_RE = re.compile(r"^\s*(?:IMO\s*)?(\d{7})\s*$", re.IGNORECASE)


def normalize_name(name: str) -> str:
    """Case-fold, strip accents and non-Latin characters, punctuation and legal suffixes."""
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.encode("ascii", "ignore").decode("ascii").upper()
    text = _PUNCT_RE.sub(" ", text)
    return " ".join(t for t in text.split() if t not in LEGAL_SUFFIXES)


def parse_imo(text: str) -> str | None:
    """'9408695', 'IMO 9408695', 'imo9408695' -> '9408695'; anything else -> None."""
    match = _IMO_RE.match(text or "")
    return match.group(1) if match else None
