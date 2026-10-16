"""Arize AX tracing (OpenTelemetry + OpenInference). No-op without ARIZE_SPACE_ID/ARIZE_API_KEY:
the default OTel tracer then hands out non-recording spans."""
from __future__ import annotations

import json
import logging
from contextlib import contextmanager

from opentelemetry import trace

from .config import env

log = logging.getLogger(__name__)
_tracer = None
enabled = False


def setup():
    global _tracer, enabled
    if _tracer is not None:
        return
    space_id, api_key = env("ARIZE_SPACE_ID"), env("ARIZE_API_KEY")
    if space_id and api_key:
        try:
            from arize.otel import register
            from openinference.instrumentation.bedrock import BedrockInstrumentor

            provider = register(space_id=space_id, api_key=api_key,
                                project_name=env("ARIZE_PROJECT_NAME", "flagstate"), verbose=False)
            BedrockInstrumentor().instrument(tracer_provider=provider)
            _tracer = provider.get_tracer("flagstate")
            enabled = True
        except Exception as e:
            log.warning("Arize tracing disabled: %s", e)
    if _tracer is None:
        _tracer = trace.get_tracer("flagstate")


def _value(v):
    if isinstance(v, (str, bool, int, float)):
        return v
    return json.dumps(v, default=str)[:20000]


@contextmanager
def span(name: str, kind: str = "CHAIN", input=None, **attrs):
    """kind: OpenInference span kind (CHAIN, TOOL, LLM, AGENT, EVALUATOR)."""
    setup()
    with _tracer.start_as_current_span(name) as s:
        s.set_attribute("openinference.span.kind", kind)
        if input is not None:
            s.set_attribute("input.value", _value(input))
        for k, v in attrs.items():
            s.set_attribute(k, _value(v))
        yield s


def set_output(s, value):
    s.set_attribute("output.value", _value(value))


def log_eval(name: str, score: float, label: str, explanation: str):
    """Record an eval as attributes on the current span (shows up on the trace in Arize)."""
    s = trace.get_current_span()
    s.set_attribute(f"eval.{name}.score", float(score))
    s.set_attribute(f"eval.{name}.label", label)
    s.set_attribute(f"eval.{name}.explanation", explanation)
