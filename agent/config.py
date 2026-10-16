"""Env config: loads agent/.env once. Empty values count as unset."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

AGENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = AGENT_DIR.parent
load_dotenv(AGENT_DIR / ".env")


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value else default
