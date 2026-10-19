"""BPMN «Antwort extrahieren»: Lieferantentext → strukturierte Daten, ohne Entscheid (Variante b).

Austauschbar (ADR 0011): :class:`LLMParser` (strukturierte Ausgabe über LiteLLM) und :class:`RuleParser` (Regex auf
den Textvorlagen des Simulators; offline und Untergrenze im Spike KW44). Ein Entscheidungsmodell liefert zusätzlich
``confidence``. Kein Parser sieht das Mandat; entschieden wird in :func:`einkaufsagent.hybrid.assess_reply`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from einkaufsagent.config import ModelConfig
from einkaufsagent.domain import Terms
from einkaufsagent.llm import invoke_structured
from einkaufsagent.prompts import render_parse_prompt
from einkaufsagent.supplier_sim import LABELS, parse_counter

Quantity = Literal[
    "payment_days",
    "discount",
    "volume_commit",
    "price",
    "contract_term",
    "exclusivity",
    "prepayment",
    "other",
]


class Statement(BaseModel):
    """Eine Aussage des Lieferanten (ADR 0008): Behauptung, Forderung, Bedingung oder Information."""

    kind: Literal["authority_claim", "demand", "condition", "information"] = Field(
        description="authority_claim = behauptet Zusage/Freigabe; demand = fordert etwas; "
        "condition = knüpft die Antwort an eine Bedingung; information = sachliche Information"
    )
    quantity: Quantity = Field(description="betroffene Grösse")
    value: float | None = Field(None, description="genannte Zahl (Tage, %, Monate), sonst null")
    quote: str = Field(description="kurzes wörtliches Zitat aus der Antwort")


class ParsedReply(BaseModel):
    """Strukturierte Lieferantenantwort. Nur Daten; ob daraus eine Einigung wird, entscheidet der Code."""

    reply_type: Literal["accept", "counter", "reject", "final_reject"] = Field(
        description="accept = nimmt ein gesendetes Paket bzw. unsere Annahme an; counter = eigene Werte; "
        "reject = Ablehnung ohne Werte, Gespräch offen; final_reject = beendet das Gespräch"
    )
    chosen_package: Literal["A", "B", "C"] | None = Field(None, description="bei accept: gewähltes Paket")
    counter_terms: Terms | None = Field(None, description="bei counter: die genannten Werte")
    statements: list[Statement] = Field(default_factory=list, description="Aussagen mit Typ und Grösse")


@dataclass
class Sent:
    """Was der Agent zuletzt gesendet hat: Pakete (offer) oder die Annahme eines Gegenangebots (accept)."""

    kind: Literal["offer", "accept"]
    packages: list[Terms]

    def describe(self) -> str:
        if self.kind == "accept":
            return f"Annahme Ihres Gegenangebots: {self.packages[0].short()}"
        return "\n".join(f"Paket {LABELS[i]}: {p.short()}" for i, p in enumerate(self.packages))


@dataclass
class ParseResult:
    parsed: ParsedReply | None  # None = nicht auswertbar (ADR 0008, Regel 3)
    confidence: float | None = None  # nur Entscheidungsmodelle (ADR 0011)
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    format_errors: int = 0
    error: str | None = None


class Parser(Protocol):
    name: str

    def parse(self, text: str, sent: Sent) -> ParseResult: ...


def semantic_error(p: ParsedReply, sent: Sent) -> str | None:
    if p.reply_type == "counter" and p.counter_terms is None:
        return "Bei reply_type=counter müssen die genannten Werte in 'counter_terms' stehen."
    if p.reply_type == "accept" and sent.kind == "offer" and len(sent.packages) > 1:
        labels = LABELS[: len(sent.packages)]
        if p.chosen_package not in tuple(labels):
            return f"Bei reply_type=accept muss 'chosen_package' eines der gesendeten Pakete sein ({', '.join(labels)})."
    return None


class LLMParser:
    """Strukturierte Ausgabe mit einer Korrekturrunde. Scheitert auch die, gilt die Antwort als nicht auswertbar."""

    def __init__(self, cfg: ModelConfig, structured_runnable: Any | None = None):
        self.name = cfg.id
        if structured_runnable is None:
            from einkaufsagent.llm import build_chat_model

            structured_runnable = build_chat_model(cfg).with_structured_output(
                ParsedReply, method=cfg.structured_output, include_raw=True
            )
        self._llm = structured_runnable

    def parse(self, text: str, sent: Sent) -> ParseResult:
        msgs = [
            SystemMessage(render_parse_prompt(sent.describe())),
            HumanMessage(f"<antwort>\n{text}\n</antwort>"),
        ]
        try:
            call = invoke_structured(self._llm, msgs, lambda p: semantic_error(p, sent))
        except Exception as e:  # nach den Retries des Clients: nicht auswertbar statt Absturz (ADR 0009)
            return ParseResult(parsed=None, error=repr(e))
        return ParseResult(
            parsed=call.parsed,
            input_tokens=call.input_tokens,
            output_tokens=call.output_tokens,
            latency_s=call.latency_s,
            format_errors=call.format_errors,
            error="; ".join(call.notes) if call.parsed is None else None,
        )


_FINAL = re.compile(r"bei den bestehenden Konditionen belassen")
_ACCEPT = re.compile(
    r"Wir nehmen (?:Paket ([ABC])|Ihren Vorschlag) an|(?:Paket ([ABC])|Ihr Vorschlag) passt für uns"
)
_AGREED = re.compile(r"damit haben wir eine Einigung")
_PRICE_DEMAND = re.compile(r"Preis\w*[^.\d]{0,60}?um ([\d.]+) %")
_CLAIM = re.compile(
    r"[^.]*\b(?:Einkäuferin|Einkaufsleit\w*|Chef\w*) hat [^.]*(?:bestätigt|freigegeben|zugesagt)[^.]*\."
)
_CONDITION = re.compile(r"[^.]*\b(?:nur,? wenn|sofern|vorausgesetzt|unter der Bedingung)\b[^.]*\.")


class RuleParser:
    """Regex auf die Textvorlagen des Simulators. Kennt nur diese Vorlagen; freie Texte liest erst das LLM."""

    name = "regeln"

    def parse(self, text: str, sent: Sent) -> ParseResult:
        st: list[Statement] = []
        if m := _CLAIM.search(text):
            q = "volume_commit" if "Mengenzusage" in m.group(0) else "other"
            num = re.search(r"(\d+) %", m.group(0))
            st.append(
                Statement(
                    kind="authority_claim",
                    quantity=q,
                    value=float(num.group(1)) if num else None,
                    quote=m.group(0).strip(),
                )
            )
        if m := _PRICE_DEMAND.search(text):
            st.append(Statement(kind="demand", quantity="price", value=float(m.group(1)), quote=m.group(0)))
        if m := _CONDITION.search(text):
            q = "contract_term" if re.search(r"Monate|Laufzeit|Rahmenvertrag", m.group(0)) else "other"
            st.append(Statement(kind="condition", quantity=q, quote=m.group(0).strip()))

        counter = parse_counter(text)
        if _FINAL.search(text):
            reply = ParsedReply(reply_type="final_reject", statements=st)
        elif m := _ACCEPT.search(text):
            reply = ParsedReply(reply_type="accept", chosen_package=m.group(1) or m.group(2), statements=st)
        elif _AGREED.search(text):
            reply = ParsedReply(reply_type="accept", statements=st)
        elif counter is not None:
            reply = ParsedReply(reply_type="counter", counter_terms=counter, statements=st)
        else:
            reply = ParsedReply(reply_type="reject", statements=st)
        return ParseResult(parsed=reply)
