"""Variante (b) als LangGraph-Graph nach BPMN `_v4`: das LLM formuliert und extrahiert, der Code entscheidet.

    START → load_context → offer_engine → narrate → mandate_guard ─ ok ───────────→ send_and_wait
                               ▲                                └ Verstoss → template_message ─┘     │
                               │                                                                     ▼
                               └──── weiter ◄──── assess_response ◄──────────────────────── parse_response
                                                   │  └─ Gegenangebot annehmen (AC_next) → send_and_wait
                                                   ├─ Einigung / kein Deal → record_outcome → notify_supplier → END
                                                   └─ Eskalation → escalate → ask_buyer (interrupt)
                                                        ├─ weiterverhandeln → offer_engine
                                                        └─ abbrechen → record_outcome → notify_supplier → END

LLM-Nodes: ``narrate`` (sieht nur die Pakete) und ``parse_response`` (sieht nur die Antwort und was gesendet wurde).
Alle Entscheide über Zahlen und Mandat fallen in Code-Nodes. Rundenlogik wie Variante (a): ``round`` zählt
Angebotsrunden, ein Gegenangebot ist auch nach der letzten Runde annehmbar, eine abgelehnte Annahme zählt als Runde.
Narrator, Parser, Simulator und ERP-Adapter kommen per Closure in den Graphen; die verdeckten Parameter sind nie im
State. ``load_context`` liest Stammdaten und heutige Konditionen aus dem ERP, ``record_outcome`` schreibt auf jedem
Ausgang das Protokoll und bucht einen Abschluss (ADR 0015).

Eskalation (ADR 0015): ``escalate`` (Code) bereitet die Vorlage für die Einkäuferin auf und schreibt das Protokoll mit
Status «escalated»; ``ask_buyer`` enthält nur ``interrupt()``, weil LangGraph den Node beim Fortsetzen von vorn startet.
Der Runner setzt mit ``Command(resume={"decision": ..., "note": ...})`` und derselben ``thread_id`` fort. Die Eval
setzt nicht fort und wertet den Halt als Eskalation.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from einkaufsagent.domain import Context, Mandate, Terms
from einkaufsagent.erp import ErpAdapter, Exchange
from einkaufsagent.extract import ParsedReply, Parser, ParseResult, Sent
from einkaufsagent.hybrid import (
    BUYER_OPTIONS,
    BUYER_REJECTION,
    ESCALATION_HOLD,
    UNCLEAR_RETRY,
    accept_text,
    assess_reply,
    check_message,
    escalation_brief,
    notify_text,
    template_offer,
)
from einkaufsagent.narrate import Narrator
from einkaufsagent.policies import RuleBasedPolicy
from einkaufsagent.supplier_sim import LABELS, Supplier

Outcome = Literal["deal", "no_deal", "escalated", "error"]


class HybridAgent:
    """Variante (b). Narrator und Parser sind austauschbar (ADR 0011); Pakete und AC_next aus der Regel-Referenz."""

    variant = "b"

    def __init__(self, narrator: Narrator, parser: Parser, name: str | None = None):
        self.narrator = narrator
        self.parser = parser
        self.name = name or narrator.name
        self.engine = RuleBasedPolicy()


class HybridState(TypedDict, total=False):
    scenario_id: str
    negotiation_id: str  # Schlüssel des Protokolls im ERP (= thread_id)
    supplier_id: str
    context: dict[str, Any]  # aus dem ERP (load_context)
    mandate: dict[str, Any]
    transcript: Annotated[list[dict[str, Any]], operator.add]  # «event» beim Lieferanten nur für die Eval
    round: int
    offers: Annotated[list[dict[str, Any]], operator.add]  # alle Zusagen des Agenten
    turns: Annotated[list[dict[str, Any]], operator.add]  # Tokens, Latenz, Formatfehler pro LLM-Aufruf
    pending: dict[str, Any] | None  # nächste Nachricht: {"kind": "offer" | "accept", "packages": [...]}
    draft: str | None  # Angebotstext von narrate bzw. Standardtext
    template_reason: str | None  # warum der Standardtext hinausgeht (Metrik template_rate)
    prefix: list[str]  # Zurückweisungen aus Vorlagen vor der nächsten Nachricht
    sent: dict[str, Any] | None  # zuletzt gesendet (Sent)
    parsed: dict[str, Any] | None  # ParsedReply; None = nicht auswertbar
    parse_confidence: float | None
    parse_error: str | None
    rejected_demands: Annotated[list[str], operator.add]  # Grössen mit abgelehnter Forderung (ADR 0008)
    notes: Annotated[list[str], operator.add]  # Hinweise für das Protokoll der Einkäuferin
    outcome: Outcome | None
    end_reason: str | None
    deal_terms: dict[str, Any] | None
    escalation: dict[str, Any] | None  # Vorlage für die Einkäuferin (Payload des Interrupts)
    escalation_quantity: str | None  # betroffene Grösse der eskalierten Forderung oder Bedingung
    buyer_rejected: Annotated[
        list[str], operator.add
    ]  # von der Einkäuferin abgelehnt: nicht erneut eskalieren
    buyer_decision: str | None  # weiterverhandeln | abbrechen
    buyer_note: str | None  # freie Notiz der Einkäuferin, nur fürs Protokoll (geht an niemanden)


def _terms(ps: list[dict[str, Any]]) -> list[Terms]:
    return [Terms.model_validate(p) for p in ps]


def exchanges(state: HybridState) -> list[Exchange]:
    """Gesendete Nachrichten mit der extrahierten Reaktion, in Reihenfolge (eine Antwort pro Nachricht)."""
    parses = [t for t in state.get("turns", []) if t.get("node") == "parse_response"]
    return [
        Exchange(
            round=o["round"],
            sent_kind=o["action"],
            packages=o["packages"],
            reply_type=lg.get("reply_type"),
            chosen_package=lg.get("chosen_package"),
            counter_terms=lg.get("counter_terms"),
        )
        for o, lg in zip(state.get("offers", []), parses, strict=False)
    ]


def history(state: HybridState) -> list[str]:
    """Verlauf für die Einkäuferin, eine Zeile pro Nachricht (aus dem State, ohne LLM)."""
    lines = []
    for e in exchanges(state):
        packs = [Terms.model_validate(p).short() for p in e.packages]
        sent = (
            f"Annahme: {packs[0]}"
            if e.sent_kind == "accept"
            else "; ".join(f"{LABELS[i]}: {t}" for i, t in enumerate(packs))
        )
        reply = e.reply_type or "nicht auswertbar"
        if e.chosen_package:
            reply += f" Paket {e.chosen_package}"
        if e.counter_terms:
            reply += f" ({Terms.model_validate(e.counter_terms).short()})"
        lines.append(f"R{e.round} {sent} → {reply}")
    return lines


def normalize_decision(answer: Any) -> tuple[str, str]:
    """Antwort der Einkäuferin aus ``Command(resume=...)``: Dict mit ``decision`` und ``note`` oder nur der Text.
    Alles ausser «weiterverhandeln» gilt als «abbrechen» (sicherer Ausgang: es wird nichts zugesagt)."""
    if isinstance(answer, dict):
        decision, note = str(answer.get("decision", "")), str(answer.get("note") or "")
    else:
        decision, note = str(answer or ""), ""
    decision = decision.strip().lower()
    return ("weiterverhandeln" if decision == BUYER_OPTIONS[0] else "abbrechen"), note.strip()


def build_graph(agent: HybridAgent, supplier: Supplier, erp: ErpAdapter):
    engine = agent.engine

    def _cm(state: HybridState) -> tuple[Context, Mandate]:
        return Context.model_validate(state["context"]), Mandate.model_validate(state["mandate"])

    def load_context(state: HybridState) -> dict:
        ctx = erp.load_context(state["supplier_id"])
        Mandate.model_validate(state["mandate"])
        return {
            "context": ctx.model_dump(),
            "round": 0,
            "pending": None,
            "draft": None,
            "template_reason": None,
            "prefix": [],
            "sent": None,
            "parsed": None,
            "outcome": None,
            "end_reason": None,
            "deal_terms": None,
        }

    def offer_engine(state: HybridState) -> dict:
        ctx, m = _cm(state)
        t = state["round"] + 1
        if t > m.max_rounds:  # nur nach «weiterverhandeln» in der letzten Runde möglich
            return {"outcome": "no_deal", "end_reason": "round_limit"}
        packages = engine.packages(engine.value_at(t, ctx, m), ctx, m)
        if not packages:
            return {"outcome": "no_deal", "end_reason": "no_packages"}
        return {
            "round": t,
            "pending": {"kind": "offer", "packages": [p.model_dump() for p in packages]},
            "draft": None,
            "template_reason": None,
        }

    def narrate(state: HybridState) -> dict:
        res = agent.narrator.narrate(_terms(state["pending"]["packages"]), state["round"])
        log = {
            "node": "narrate",
            "round": state["round"],
            "input_tokens": res.input_tokens,
            "output_tokens": res.output_tokens,
            "latency_s": round(res.latency_s, 3),
        }
        reason = None if res.text else f"narrate_error: {res.error}"
        return {"draft": res.text, "template_reason": reason, "turns": [log]}

    def mandate_guard(state: HybridState) -> dict:
        if state.get("template_reason"):
            return {}
        _, m = _cm(state)
        problems = check_message(state["draft"], _terms(state["pending"]["packages"]), m, state["round"] == 1)
        return {"template_reason": "; ".join(problems)} if problems else {}

    def template_message(state: HybridState) -> dict:
        return {"draft": template_offer(_terms(state["pending"]["packages"]), first=state["round"] == 1)}

    def send_and_wait(state: HybridState) -> dict:
        pending, t = state["pending"], state["round"]
        packages = _terms(pending["packages"])
        prefix = state.get("prefix") or []
        if pending["kind"] == "offer":
            reason = state.get("template_reason")
            msg = {
                "role": "agent",
                "round": t,
                "action": "offer",
                "text": " ".join([*prefix, state["draft"]]),
                "template": bool(reason),
                "template_reason": reason,
            }
            reply = supplier.respond_to_offer(t, packages, msg["text"])
        else:
            msg = {
                "role": "agent",
                "round": t,
                "action": "accept",
                "text": " ".join([*prefix, accept_text(packages[0])]),
            }
            reply = supplier.respond_to_acceptance(t, packages[0], msg["text"])
        # Weiter geht nur der Text. «event» (Wahrheit des Simulators) liest kein Node, nur die Eval.
        return {
            "transcript": [msg, {"role": "supplier", "round": t, "event": reply.event, "text": reply.text}],
            "offers": [{"round": t, "action": pending["kind"], "packages": pending["packages"]}],
            "sent": pending,
            "pending": None,
            "prefix": [],
        }

    def parse_response(state: HybridState) -> dict:
        sent = Sent(state["sent"]["kind"], _terms(state["sent"]["packages"]))
        res = agent.parser.parse(state["transcript"][-1]["text"], sent)
        log = {
            "node": "parse_response",
            "round": state["round"],
            "input_tokens": res.input_tokens,
            "output_tokens": res.output_tokens,
            "latency_s": round(res.latency_s, 3),
            "format_errors": res.format_errors,
            # nur für die Metrik extraktion_korrekt (ADR 0010); kein Node liest diese Felder
            "reply_type": res.parsed.reply_type if res.parsed else None,
            "chosen_package": res.parsed.chosen_package if res.parsed else None,
            "counter_terms": res.parsed.counter_terms.model_dump()
            if res.parsed and res.parsed.counter_terms
            else None,
        }
        return {
            "parsed": res.parsed.model_dump() if res.parsed else None,
            "parse_confidence": res.confidence,
            "parse_error": res.error,
            "turns": [log],
        }

    def assess_response(state: HybridState) -> dict:
        ctx, m = _cm(state)
        parsed = state.get("parsed")
        parse = ParseResult(
            parsed=ParsedReply.model_validate(parsed) if parsed else None,
            confidence=state.get("parse_confidence"),
            error=state.get("parse_error"),
        )
        sent = Sent(state["sent"]["kind"], _terms(state["sent"]["packages"]))
        a = assess_reply(
            parse,
            sent,
            state["round"],
            state.get("rejected_demands", []),
            ctx,
            m,
            engine,
            state.get("buyer_rejected"),
        )
        update: dict = {
            "round": a.round,
            "notes": a.notes,
            "rejected_demands": a.rejected,
            "prefix": a.rejections,
        }
        if a.decision == "deal":
            update |= {"outcome": "deal", "deal_terms": a.terms.model_dump(), "end_reason": a.reason}
        elif a.decision == "no_deal":
            update |= {"outcome": "no_deal", "end_reason": a.reason}
        elif a.decision == "escalate":
            update |= {
                "outcome": "escalated",
                "end_reason": f"escalate:{a.reason}",
                "escalation_quantity": a.quantity,
            }
        elif a.decision == "accept_counter":
            update["pending"] = {"kind": "accept", "packages": [a.terms.model_dump()]}
        return update

    def _record(state: HybridState) -> None:
        deal = Terms.model_validate(state["deal_terms"]) if state.get("deal_terms") else None
        erp.record_outcome(
            negotiation_id=state["negotiation_id"],
            supplier_id=state["supplier_id"],
            status=state["outcome"],
            end_reason=state.get("end_reason") or "",
            rounds=state["round"],
            exchanges=exchanges(state),
            deal_terms=deal,
            notes=state.get("notes", []),
            buyer_decision=state.get("buyer_decision"),
            buyer_note=state.get("buyer_note"),
        )

    def escalate(state: HybridState) -> dict:
        ctx, m = _cm(state)
        brief = escalation_brief(
            supplier_name=ctx.supplier_name,
            round_=state["round"],
            max_rounds=m.max_rounds,
            reason=(state.get("end_reason") or "").removeprefix("escalate:"),
            notes=state.get("notes", []),
            last_reply=state["transcript"][-1]["text"],
            history=history(state),
        )
        _record(state)  # Status «escalated»; ein späteres record_outcome ersetzt das Protokoll
        hold = {"role": "agent", "round": state["round"], "action": "escalate", "text": ESCALATION_HOLD}
        return {"escalation": brief, "transcript": [hold]}

    def ask_buyer(state: HybridState) -> dict:
        # Nur der Interrupt: beim Fortsetzen startet dieser Node von vorn (LangGraph-Doku, ADR 0015).
        decision, note = normalize_decision(interrupt(state["escalation"]))
        update: dict = {"buyer_decision": decision, "buyer_note": note or None}
        update["notes"] = [f"Einkäuferin: {decision}" + (f" ({note})" if note else "")]
        if decision == "weiterverhandeln":
            q = state.get("escalation_quantity")
            update |= {
                "outcome": None,
                "end_reason": None,
                "escalation": None,
                "prefix": [BUYER_REJECTION if q else UNCLEAR_RETRY],
                "buyer_rejected": [q] if q else [],
            }
        return update

    def record_outcome(state: HybridState) -> dict:
        _record(state)
        return {}

    def notify_supplier(state: HybridState) -> dict:
        outcome = state["outcome"]
        deal = Terms.model_validate(state["deal_terms"]) if state.get("deal_terms") else None
        action = "walk_away" if state.get("end_reason") in ("round_limit", "no_packages") else "notify"
        text = notify_text(outcome, deal)
        return {"transcript": [{"role": "agent", "round": state["round"], "action": action, "text": text}]}

    def after_offer_engine(state: HybridState) -> Literal["narrate", "record_outcome"]:
        return "record_outcome" if state.get("outcome") else "narrate"

    def after_guard(state: HybridState) -> Literal["template_message", "send_and_wait"]:
        return "template_message" if state.get("template_reason") else "send_and_wait"

    def after_assess(
        state: HybridState,
    ) -> Literal["escalate", "record_outcome", "send_and_wait", "offer_engine"]:
        if state.get("outcome") == "escalated":
            return "escalate"
        if state.get("outcome"):
            return "record_outcome"
        return "send_and_wait" if state.get("pending") else "offer_engine"

    def after_buyer(state: HybridState) -> Literal["offer_engine", "record_outcome"]:
        return "offer_engine" if state.get("buyer_decision") == "weiterverhandeln" else "record_outcome"

    g = StateGraph(HybridState)
    for name, fn in [
        ("load_context", load_context),
        ("offer_engine", offer_engine),
        ("narrate", narrate),
        ("mandate_guard", mandate_guard),
        ("template_message", template_message),
        ("send_and_wait", send_and_wait),
        ("parse_response", parse_response),
        ("assess_response", assess_response),
        ("escalate", escalate),
        ("ask_buyer", ask_buyer),
        ("record_outcome", record_outcome),
        ("notify_supplier", notify_supplier),
    ]:
        g.add_node(name, fn)
    g.add_edge(START, "load_context")
    g.add_edge("load_context", "offer_engine")
    g.add_conditional_edges("offer_engine", after_offer_engine)
    g.add_edge("narrate", "mandate_guard")
    g.add_conditional_edges("mandate_guard", after_guard)
    g.add_edge("template_message", "send_and_wait")
    g.add_edge("send_and_wait", "parse_response")
    g.add_edge("parse_response", "assess_response")
    g.add_conditional_edges("assess_response", after_assess)
    g.add_edge("escalate", "ask_buyer")
    g.add_conditional_edges("ask_buyer", after_buyer)
    g.add_edge("record_outcome", "notify_supplier")
    g.add_edge("notify_supplier", END)
    return g.compile(checkpointer=InMemorySaver())
