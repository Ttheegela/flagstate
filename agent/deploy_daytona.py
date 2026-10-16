"""Deploy the Flagstate agent service into a public Daytona sandbox and print its preview URL.

    agent/.venv/bin/python -m agent.deploy_daytona

Re-running updates the code and restarts the server in the same sandbox. Needs DAYTONA_API_KEY in agent/.env;
the sandbox gets a copy of agent/.env so the service can reach the other sponsors.
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
from daytona import CreateSandboxFromSnapshotParams, Daytona, DaytonaConfig, SessionExecuteRequest

from .config import AGENT_DIR, REPO_ROOT, env

NAME = "flagstate-agent"
PORT = 8787
APP = "/home/daytona/flagstate"
DEPS = ("fastapi 'uvicorn[standard]' httpx python-dotenv boto3 daytona surrealdb elevenlabs "
        "arize-otel openinference-instrumentation-bedrock opentelemetry-sdk opentelemetry-exporter-otlp")


def files() -> list[tuple[Path, str]]:
    out = [(p, f"{APP}/agent/{p.name}") for p in AGENT_DIR.glob("*.py")]
    out.append((AGENT_DIR / ".env", f"{APP}/agent/.env"))
    out.append((REPO_ROOT / "scripts" / "normalize.py", f"{APP}/scripts/normalize.py"))
    out.append((REPO_ROOT / "data" / "research-index.json", f"{APP}/data/research-index.json"))
    out += [(p, f"{APP}/data/lists/{p.name}") for p in (REPO_ROOT / "data" / "lists").glob("*.json")]
    return out


def main() -> None:
    daytona = Daytona(DaytonaConfig(api_key=env("DAYTONA_API_KEY")))
    try:
        sb = daytona.get(NAME)
        if getattr(sb.state, "value", sb.state) != "started":
            sb.start(timeout=120)
        print("reusing sandbox", sb.id)
    except Exception:
        # ponytail: never auto-stops, so the demo URL stays up; stop it by hand after the event
        sb = daytona.create(CreateSandboxFromSnapshotParams(
            name=NAME, language="python", public=True, auto_stop_interval=0), timeout=180)
        print("created sandbox", sb.id)

    sb.process.exec(f"mkdir -p {APP}/agent {APP}/scripts {APP}/data/lists", timeout=30)
    for src, dst in files():
        sb.fs.upload_file(src.read_bytes(), dst)
    print("uploaded", len(files()), "files")

    r = sb.process.exec(f"pip install -q {DEPS}", timeout=600)
    if r.exit_code:
        raise SystemExit(f"pip failed: {r.result[-500:]}")

    sb.process.exec(f"pkill -f 'uvicorn agent.server' || true", timeout=30)
    session = "flagstate-server"
    try:
        sb.process.create_session(session)
    except Exception:
        pass  # exists from a previous deploy
    sb.process.execute_session_command(session, SessionExecuteRequest(
        command=f"cd {APP} && python -m uvicorn agent.server:app --host 0.0.0.0 --port {PORT}", run_async=True))

    url = sb.get_preview_link(PORT).url.rstrip("/")
    for _ in range(30):
        try:
            if httpx.get(f"{url}/health", timeout=5).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(2)
    else:
        raise SystemExit(f"server did not answer on {url}/health")
    print("AGENT_URL", url)


if __name__ == "__main__":
    main()
