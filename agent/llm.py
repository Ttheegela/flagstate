"""Investigative briefing via AWS Bedrock (Converse API). Without AWS credentials, or if
Bedrock fails, returns a deterministic template briefing built from the same context."""
from __future__ import annotations

import json
import logging
import re

from .config import env

log = logging.getLogger(__name__)
DEFAULT_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
SYSTEM = (
    "You are a sanctions investigator briefing a colleague out loud. Write a short spoken-style briefing "
    "(at most 120 words, plain sentences, no lists, no markdown) about the subject, grounded ONLY in the JSON "
    "context you are given. Lead with whether it is on an official sanctions list, then the strongest risk flags "
    "and any changes since the last check. Never invent facts or URLs. Every claim must cite a source URL copied "
    "exactly from the context. Reply with JSON only, no prose around it: "
    '{"text": "<briefing>", "claims": [{"text": "<one factual claim>", "source": "<url from context>"}]}'
)


def _creds_available() -> bool:
    try:
        import boto3

        return boto3.Session().get_credentials() is not None
    except Exception:
        return False


def _parse(raw: str) -> dict:
    data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
    claims = [{"text": str(c["text"]), "source": str(c["source"])}
              for c in data.get("claims", []) if isinstance(c, dict) and c.get("text") and c.get("source")]
    return {"text": str(data["text"]).strip(), "claims": claims}


def _bedrock(context: dict) -> dict:
    import boto3

    client = boto3.client("bedrock-runtime", region_name=env("AWS_REGION", "us-west-2"))
    model = env("BEDROCK_MODEL_ID", DEFAULT_MODEL)
    kwargs = dict(system=[{"text": SYSTEM}], inferenceConfig={"maxTokens": 1000},
                  messages=[{"role": "user", "content": [{"text": "Context:\n" + json.dumps(context, default=str)}]}])
    try:
        resp = client.converse(modelId=model, **kwargs)
    except client.exceptions.ValidationException as e:
        # Newer Claude models on Bedrock need a cross-region inference profile id ("us." prefix).
        if "inference profile" not in str(e) or re.match(r"^(us|eu|apac|global)\.", model):
            raise
        model = "us." + model
        resp = client.converse(modelId=model, **kwargs)
    raw = next(b["text"] for b in resp["output"]["message"]["content"] if "text" in b)
    return {**_parse(raw), "model": model, "available": True}


def _template(context: dict, reason: str) -> dict:
    """Deterministic briefing: same shape, every claim tied to a URL from the context."""
    subject = context.get("subject") or context.get("query") or "This subject"
    flags = (context.get("analysis") or {}).get("flags") or []
    claims = [{"text": f["evidence"], "source": f["source"]} for f in flags if f.get("source")][:4]
    if not claims:
        claims = [{"text": f"{h['name']} appears on the {h['authority']} list ({h['program']})", "source": h["url"]}
                  for h in (context.get("lists") or [])[:2]]
    risk = (context.get("analysis") or {}).get("risk", "unknown")
    if claims:
        text = f"{subject}: overall risk {risk}. " + " ".join(c["text"].rstrip(".") + "." for c in claims)
    else:
        text = f"I found nothing on {subject} in the sanctions research or the official lists."
    words = text.split()
    text = " ".join(words[:120]) + ("..." if len(words) > 120 else "")
    return {"text": text, "claims": claims, "model": "template", "available": False, "reason": reason}


def brief(context: dict) -> dict:
    if not _creds_available():
        return _template(context, "AWS credentials not set")
    try:
        return _bedrock(context)
    except Exception as e:
        log.warning("bedrock failed: %s", e)
        return _template(context, f"bedrock failed: {type(e).__name__}: {e}"[:200])
