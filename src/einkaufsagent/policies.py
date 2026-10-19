"""Entscheidungslogik des Agenten pro Runde.

* :class:`LLMPolicy`: Variante (a), das LLM entscheidet alles (Aktion, Pakete, Text).
* :class:`RuleBasedPolicy`: deterministische Referenz ohne LLM (Konzessionskurve + AC_next).
  Dient als Baseline im Benchmark und für Offline-Tests ohne API-Key.

Beide sehen nur :class:`AgentView`, also öffentliche Daten und den Gesprächsverlauf.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from einkaufsagent.config import ModelConfig
from einkaufsagent.domain import Context, Mandate, Terms, buyer_value_chf, check_terms
from einkaufsagent.llm import invoke_structured
from einkaufsagent.prompts import chf, render_system_prompt_a, render_turn_instruction


class AgentTurn(BaseModel):
    """Entscheid des Einkaufsagenten für die nächste Nachricht."""

    action: Literal["offer", "accept", "walk_away", "escalate"] = Field(
        description="offer = neue Pakete; accept = letztes Gegenangebot annehmen; "
        "walk_away = ohne Deal beenden; escalate = an die Einkäuferin übergeben"
    )
    message: str = Field(description="Nachricht an den Lieferanten, Deutsch")
    packages: list[Terms] = Field(default_factory=list, description="Bei offer: 2 bis 3 Pakete, sonst leer")
    accepted_terms: Terms | None = Field(
        None, description="Bei accept: die Werte des Gegenangebots, sonst null"
    )
    rationale: str = Field("", description="Ein Satz Begründung, intern")


@dataclass
class AgentView:
    context: Context
    mandate: Mandate
    transcript: list[dict[str, Any]]  # {"role": "agent"|"supplier", "text": str, ...}
    round_next: int
    last_supplier_event: str | None = None
    last_supplier_terms: Terms | None = None  # nur für die Regel-Referenz (entspricht perfektem Parser)
    accept_only: bool = False  # Rundenlimit erreicht: nur noch accept, walk_away oder escalate


@dataclass
class TurnResult:
    turn: AgentTurn
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    format_errors: int = 0
    notes: list[str] = field(default_factory=list)


class FormatError(RuntimeError):
    """Das Modell lieferte auch nach einer Korrekturaufforderung keine gültige Ausgabe.
    ``result`` trägt die bis dahin verbrauchten Tokens, damit Kosten vollständig gezählt werden."""

    def __init__(self, message: str, result: TurnResult):
        super().__init__(message)
        self.result = result


class Policy(Protocol):
    name: str

    def decide(self, view: AgentView) -> TurnResult: ...


def _semantic_error(t: AgentTurn) -> str | None:
    if t.action == "offer" and not (1 <= len(t.packages) <= 3):
        return "Bei action=offer müssen 1 bis 3 Pakete in 'packages' stehen."
    if t.action == "accept" and t.accepted_terms is None:
        return "Bei action=accept müssen die Werte des Gegenangebots in 'accepted_terms' stehen."
    if not t.message.strip():
        return "Das Feld 'message' darf nicht leer sein."
    return None


class LLMPolicy:
    """Variante (a): reines LLM, Mandat nur im Prompt."""

    def __init__(self, cfg: ModelConfig, structured_runnable: Any | None = None):
        self.cfg = cfg
        self.name = cfg.id
        if structured_runnable is None:
            from einkaufsagent.llm import build_chat_model

            structured_runnable = build_chat_model(cfg).with_structured_output(
                AgentTurn, method=cfg.structured_output, include_raw=True
            )
        self._llm = structured_runnable

    def _messages(self, view: AgentView) -> list[BaseMessage]:
        msgs: list[BaseMessage] = [SystemMessage(render_system_prompt_a(view.context, view.mandate))]
        for m in view.transcript:
            if m["role"] == "agent":
                msgs.append(AIMessage(m["text"]))
            else:
                msgs.append(HumanMessage(f"Lieferant: {m['text']}"))
        msgs.append(
            HumanMessage(render_turn_instruction(view.round_next, view.mandate.max_rounds, view.accept_only))
        )
        return msgs

    def decide(self, view: AgentView) -> TurnResult:
        call = invoke_structured(self._llm, self._messages(view), _semantic_error)
        res = TurnResult(
            turn=call.parsed or AgentTurn(action="walk_away", message="-"),
            input_tokens=call.input_tokens,
            output_tokens=call.output_tokens,
            latency_s=call.latency_s,
            format_errors=call.format_errors,
            notes=call.notes,
        )
        if call.parsed is None:
            raise FormatError("; ".join(call.notes), res)
        return res


class RuleBasedPolicy:
    """Deterministische Referenz: lineare Konzession vom Anspruchsniveau zum Mindestnutzen, 3 MESO-Pakete,
    Annahme nach AC_next (Gegenangebot ≥ Wert des eigenen nächsten Angebots), Eskalation bei Forderungen."""

    name = "regelbasiert"

    def _aspiration(self, ctx: Context, m: Mandate) -> float:
        target = Terms(payment_days=m.target_payment_days, discount_pct=m.target_discount_pct)
        return max(buyer_value_chf(target, ctx, m), 1.5 * m.min_value_chf)

    def value_at(self, t: int, ctx: Context, m: Mandate) -> float:
        asp = self._aspiration(ctx, m)
        frac = (t - 1) / max(1, m.max_rounds - 1)
        return asp - (asp - m.min_value_chf) * frac

    def packages(self, value: float, ctx: Context, m: Mandate) -> list[Terms]:
        a, cur = ctx.annual_volume_chf, ctx.current_terms
        # Drei Profile: Zahlungsziel mit Mengenzusage, Rabatt mit Mengenzusage, Zahlungsziel ohne Zusage
        shapes = [
            (m.target_payment_days, m.max_volume_commit_pct),
            (cur.payment_days, m.max_volume_commit_pct),
            (m.payment_days_max, 0.0),
        ]
        out: list[Terms] = []
        for days, vol in shapes:
            d = 100 * (
                value / a
                - (days - cur.payment_days) / 365 * m.buyer_capital_rate
                + vol / 100 * m.buyer_commit_cost_rate
            )
            d = min(m.discount_max_pct, max(cur.discount_pct, math.ceil(d / 0.25) * 0.25))
            t = Terms(payment_days=days, discount_pct=d, volume_commit_pct=vol)
            if not check_terms(t, ctx, m) and buyer_value_chf(t, ctx, m) >= m.min_value_chf - 1e-6:
                out.append(t)
        return out

    def acceptable(self, c: Terms, t: int, ctx: Context, m: Mandate) -> bool:
        """AC_next: Gegenangebot im Mandat, ≥ Mindestnutzen und mindestens so viel wert wie das eigene Angebot
        in Runde t; ab der letzten Runde genügt der Mindestnutzen. Auch Variante (b) entscheidet damit."""
        if check_terms(c, ctx, m):
            return False
        vc = buyer_value_chf(c, ctx, m)
        return vc >= m.min_value_chf and (vc >= self.value_at(t, ctx, m) or t >= m.max_rounds)

    def decide(self, view: AgentView) -> TurnResult:
        ctx, m, t = view.context, view.mandate, view.round_next
        # ADR 0008: Eine Forderung ausserhalb des Mandats zuerst ablehnen; erst die wiederholte Forderung eskalieren.
        # Bedingungen im Freitext (S11) sieht die Referenz nicht, weil sie nur strukturierte Werte liest.
        demands = sum(1 for x in view.transcript if x["role"] == "supplier" and x.get("event") == "demand")
        if view.last_supplier_event == "demand" and demands >= 2:
            return TurnResult(
                AgentTurn(
                    action="escalate",
                    message="Danke für die Information. Eine Preiserhöhung kann ich nicht zusagen; "
                    "ich gebe Ihr Anliegen an unsere Einkäuferin weiter, sie meldet sich bei Ihnen.",
                    rationale="Forderung ausserhalb des Mandats wiederholt",
                )
            )
        decline = (
            "Eine Preiserhöhung kann ich im Rahmen meines Auftrags nicht zusagen. "
            if view.last_supplier_event == "demand"
            else ""
        )
        c = view.last_supplier_terms
        if (
            view.last_supplier_event in ("counter", "decline")
            and c is not None
            and self.acceptable(c, t, ctx, m)
        ):
            return TurnResult(
                AgentTurn(
                    action="accept",
                    accepted_terms=c,
                    message=f"Einverstanden, wir nehmen Ihren Vorschlag an: {c.short()}.",
                    rationale=f"AC_next: {chf(buyer_value_chf(c, ctx, m))} CHF ≥ eigenes nächstes Angebot",
                )
            )
        pk = [] if view.accept_only else self.packages(self.value_at(t, ctx, m), ctx, m)
        if not pk:
            return TurnResult(
                AgentTurn(
                    action="walk_away",
                    message="Danke für das Gespräch. Wir belassen es bei den heutigen Konditionen.",
                    rationale="keine Pakete",
                )
            )
        intro = (
            "Guten Tag, ich bin der KI-Einkaufsagent der Musterhandel AG und verhandle im Auftrag "
            "unseres Einkaufs. "
            if t == 1
            else ""
        )
        body = " ".join(f"Paket {'ABC'[i]}: {p.short()}." for i, p in enumerate(pk))
        return TurnResult(
            AgentTurn(
                action="offer",
                packages=pk,
                message=f"{intro}{decline}Wir schlagen Ihnen folgende Pakete vor: {body}",
                rationale=f"Zielwert Runde {t}: {chf(self.value_at(t, ctx, m))} CHF",
            )
        )
