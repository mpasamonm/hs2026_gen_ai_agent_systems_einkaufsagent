"""BPMN «Angebot formulieren»: Pakete → Nachrichtentext (Variante b).

Der Narrator sieht nur die Pakete und die Runde, nie das Mandat und nie den Lieferantentext (Dual-LLM-Muster nach
Willison 2023): Eine Prompt Injection des Lieferanten erreicht das schreibende LLM nicht, und es kann keine Grenze
verraten, die es nicht kennt. Was es schreibt, prüft danach der Code (``hybrid.check_message``).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from einkaufsagent.config import ModelConfig
from einkaufsagent.domain import Terms
from einkaufsagent.hybrid import template_offer
from einkaufsagent.prompts import NARRATE_PROMPT, render_narrate_input
from einkaufsagent.supplier_sim import LABELS


@dataclass
class Narration:
    text: str | None  # None = gescheitert, der Code nimmt den Standardtext
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    error: str | None = None


class Narrator(Protocol):
    name: str

    def narrate(self, packages: list[Terms], round_: int) -> Narration: ...


class TemplateNarrator:
    """Ohne LLM: immer der Standardtext (offline und Regel-Referenz von Variante b)."""

    name = "vorlage"

    def narrate(self, packages: list[Terms], round_: int) -> Narration:
        return Narration(template_offer(packages, first=round_ == 1))


class LLMNarrator:
    def __init__(self, cfg: ModelConfig, chat_model: Any | None = None):
        self.name = cfg.id
        if chat_model is None:
            from einkaufsagent.llm import build_chat_model

            chat_model = build_chat_model(cfg)
        self._llm = chat_model

    def narrate(self, packages: list[Terms], round_: int) -> Narration:
        lines = [f"Paket {LABELS[i]}: {p.short()}" for i, p in enumerate(packages)]
        msgs = [SystemMessage(NARRATE_PROMPT), HumanMessage(render_narrate_input(lines, round_))]
        t0 = time.perf_counter()
        try:
            out = self._llm.invoke(msgs)
        except Exception as e:  # nach den Retries des Clients: Standardtext statt Absturz (ADR 0009)
            return Narration(None, latency_s=time.perf_counter() - t0, error=repr(e))
        usage = out.usage_metadata or {}
        content = out.content
        if not isinstance(content, str):  # manche Anbieter liefern Inhaltsblöcke
            content = "".join(b.get("text", "") for b in content if isinstance(b, dict))
        return Narration(
            content.strip() or None,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            latency_s=time.perf_counter() - t0,
            error=None if content.strip() else "leerer Text",
        )
