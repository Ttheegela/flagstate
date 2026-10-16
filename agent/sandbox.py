"""Run analysis.py inside a Daytona sandbox (one reused sandbox, auto-stops when idle).
Without DAYTONA_API_KEY, or if Daytona fails, runs analysis.py locally in a subprocess."""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import threading
from pathlib import Path

from .config import env

log = logging.getLogger(__name__)
ANALYSIS = Path(__file__).with_name("analysis.py")
SANDBOX_NAME = "flagstate-analysis"
AUTO_STOP_MINUTES = 15
_sandbox = None
_lock = threading.Lock()


def _local(payload: dict, reason: str | None = None) -> dict:
    proc = subprocess.run([sys.executable, str(ANALYSIS)], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=30, check=True)
    out = {**json.loads(proc.stdout), "ran_in": "local"}
    if reason:
        out["reason"] = reason
    return out


def _get_sandbox():
    """Reuse the cached sandbox, else find ours by name, else create it."""
    global _sandbox
    if _sandbox is not None:
        return _sandbox
    from daytona import CreateSandboxFromSnapshotParams, Daytona, DaytonaConfig

    daytona = Daytona(DaytonaConfig(api_key=env("DAYTONA_API_KEY")))
    try:
        sb = daytona.get(SANDBOX_NAME)
        if getattr(sb.state, "value", sb.state) != "started":
            sb.start(timeout=60)
    except Exception:
        sb = daytona.create(CreateSandboxFromSnapshotParams(
            language="python", name=SANDBOX_NAME, auto_stop_interval=AUTO_STOP_MINUTES), timeout=90)
    _sandbox = sb
    return sb


def _run_remote(payload: dict) -> dict:
    sb = _get_sandbox()
    sb.fs.upload_file(ANALYSIS.read_bytes(), "analysis.py")
    sb.fs.upload_file(json.dumps(payload).encode(), "payload.json")
    resp = sb.process.exec("python3 analysis.py < payload.json", timeout=60)
    if resp.exit_code != 0:
        raise RuntimeError(f"analysis exited {resp.exit_code}: {resp.result[:300]}")
    return {**json.loads(resp.result), "ran_in": "daytona", "sandbox_id": sb.id}


def run_analysis(payload: dict) -> dict:
    global _sandbox
    if not env("DAYTONA_API_KEY"):
        return _local(payload, "DAYTONA_API_KEY not set")
    with _lock:  # ponytail: one sandbox, serialised; a pool if concurrent jobs matter
        for attempt in range(2):
            try:
                return _run_remote(payload)
            except Exception as e:  # stale cached sandbox (auto-stopped) gets one retry
                log.warning("daytona attempt %d failed: %s", attempt + 1, e)
                _sandbox = None
                err = f"{type(e).__name__}: {e}"[:200]
    return _local(payload, f"daytona failed, ran locally: {err}")
