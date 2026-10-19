"""Chat-Modelle über den LiteLLM-Proxy (OpenAI-kompatible Chat-Completions-API)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI

from einkaufsagent.config import ModelConfig, litellm_settings


def build_chat_model(cfg: ModelConfig) -> ChatOpenAI:
    base_url, api_key = litellm_settings()
    kwargs: dict = {}
    if cfg.reasoning_effort is not None:
        kwargs["reasoning_effort"] = cfg.reasoning_effort
    if cfg.temperature is not None:
        kwargs["temperature"] = cfg.temperature
    return ChatOpenAI(
        model=cfg.id,
        base_url=base_url,
        api_key=api_key,
        timeout=90,
        max_retries=2,
        use_responses_api=False,  # LiteLLM-Proxy: einheitlich Chat Completions für alle Anbieter
        tags=[cfg.id],
        **kwargs,
    )


@dataclass
class StructuredCall:
    """Ergebnis eines strukturierten Aufrufs mit höchstens einer Korrekturrunde; ``parsed`` ist None bei Formatfehler."""

    parsed: Any = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    format_errors: int = 0
    notes: list[str] = field(default_factory=list)


def invoke_structured(
    llm: Any, msgs: list[BaseMessage], check: Callable[[Any], str | None] = lambda _: None
) -> StructuredCall:
    """``llm`` ist ein ``with_structured_output(..., include_raw=True)``-Runnable. ``check`` prüft die Semantik
    und liefert eine Fehlermeldung; die geht als Korrekturaufforderung einmal ans Modell zurück."""
    res = StructuredCall()
    t0 = time.perf_counter()
    for attempt in range(2):
        out = llm.invoke(msgs)
        usage = getattr(out.get("raw"), "usage_metadata", None) or {}
        res.input_tokens += int(usage.get("input_tokens", 0))
        res.output_tokens += int(usage.get("output_tokens", 0))
        parsed = out.get("parsed")
        err = str(out.get("parsing_error")) if out.get("parsing_error") else None
        if parsed is not None and err is None:
            err = check(parsed)
        if err is None and parsed is not None:
            res.parsed = parsed
            break
        res.format_errors += 1
        res.notes.append(err or "leere Ausgabe")
        if attempt == 0:
            msgs = [*msgs, HumanMessage(f"Deine Ausgabe war ungültig: {err}. Antworte erneut im Schema.")]
    res.latency_s = time.perf_counter() - t0
    return res
