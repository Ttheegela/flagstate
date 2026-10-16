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


def _converse(system: str, user_text: str, max_tokens: int = 1000) -> tuple[str, str]:
    """One Bedrock Converse call. Returns (raw_text, model_used); raises on failure."""
    import boto3

    client = boto3.client("bedrock-runtime", region_name=env("AWS_REGION", "us-west-2"))
    model = env("BEDROCK_MODEL_ID", DEFAULT_MODEL)
    kwargs = dict(system=[{"text": system}], inferenceConfig={"maxTokens": max_tokens},
                  messages=[{"role": "user", "content": [{"text": user_text}]}])
    try:
        resp = client.converse(modelId=model, **kwargs)
    except client.exceptions.ValidationException as e:
        # Newer Claude models on Bedrock need a cross-region inference profile id ("us." prefix).
        if "inference profile" not in str(e) or re.match(r"^(us|eu|apac|global)\.", model):
            raise
        model = "us." + model
        resp = client.converse(modelId=model, **kwargs)
    raw = next(b["text"] for b in resp["output"]["message"]["content"] if "text" in b)
    return raw, model


def _bedrock(context: dict) -> dict:
    raw, model = _converse(SYSTEM, "Context:\n" + json.dumps(context, default=str))
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


JUDGE_SYSTEM = (
    "You are a strict fact-checker reviewing a sanctions investigator's briefing. You are given the JSON context "
    "the investigator gathered and the claims it made from that context, each citing a source URL. For each claim, "
    "judge whether its text is actually supported by the context the source points to (not just that the URL "
    "appears somewhere, but that the claim does not overstate, invent, or contradict what that context says). "
    "Use only the given context, no outside knowledge. Reply with JSON only, no prose around it: "
    '{"score": <fraction 0-1 of claims that are faithful>, '
    '"label": "faithful"|"partially_faithful"|"unfaithful", '
    '"explanation": "<one sentence, e.g. 2/3 claims faithful; claim 2 overstates the flag change>"}'
)


def judge_faithfulness(briefing: dict, context: dict) -> dict:
    """LLM-as-judge: do the briefing's claims say only what the gathered context supports?
    Complements `claims_grounded` (which only checks the source URL is present) with a content check."""
    claims = briefing.get("claims") or []
    if not claims:
        return {"name": "claims_faithful", "score": 0.0, "label": "no_claims",
                "explanation": "no claims to judge", "model": None, "available": False}
    if not _creds_available():
        return {"name": "claims_faithful", "score": None, "label": "unavailable",
                "explanation": "AWS credentials not set", "model": None, "available": False}
    try:
        payload = json.dumps({"claims": claims, "context": context}, default=str)
        raw, model = _converse(JUDGE_SYSTEM, payload, max_tokens=400)
        data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
        score = round(float(data["score"]), 3)
        label = str(data.get("label") or ("faithful" if score == 1 else "unfaithful" if score == 0 else "partially_faithful"))
        explanation = str(data.get("explanation") or "")
        return {"name": "claims_faithful", "score": score, "label": label,
                "explanation": explanation, "model": model, "available": True}
    except Exception as e:
        log.warning("faithfulness judge failed: %s", e)
        return {"name": "claims_faithful", "score": None, "label": "unavailable",
                "explanation": f"judge failed: {type(e).__name__}: {e}"[:200], "model": None, "available": False}
