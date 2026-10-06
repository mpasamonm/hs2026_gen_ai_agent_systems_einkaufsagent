"""Variante (a) als LangGraph-Graph: reines LLM gegen simulierten Lieferanten, mit Rundenlimit.

    START → load_context → negotiate ─┬─ offer/accept → send_and_wait ─┬─ weiter → negotiate
                                      │                                └─ Ende → finalize → END
                                      └─ walk_away/escalate/Fehler ─────────────→ finalize → END

Rundenlogik (wie BPMN v2): ``round`` zählt Angebotsrunden. Ein Gegenangebot darf der Agent auch nach
der letzten Runde noch annehmen (eine zusätzliche Runde nur mit accept, walk_away oder escalate).
Eine Annahme, die der Lieferant ablehnt (Werte ≠ Gegenangebot), zählt als Runde; damit endet jeder Lauf
nach höchstens max_rounds + 1 Agentenentscheiden.

Variante (a) bündelt die BPMN-Schritte «Pakete berechnen», «Angebot formulieren», «Antwort extrahieren»
und «Antwort bewerten» in einem LLM-Node; ab Variante (b) werden sie zu eigenen Code-Nodes
(docs/process/README.md). Policy und Lieferanten-Simulator kommen per Closure in den Graphen;
die verdeckten Lieferantenparameter sind damit nie Teil des States.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from einkaufsagent.domain import Context, Mandate, Terms
from einkaufsagent.policies import AgentView, FormatError, Policy
from einkaufsagent.supplier_sim import SupplierSimulator

Outcome = Literal["deal", "no_deal", "escalated", "error"]


class NegotiationState(TypedDict, total=False):
    scenario_id: str
    context: dict[str, Any]  # öffentlicher ERP-Kontext (Context)
    mandate: dict[str, Any]  # Mandat (Mandate)
    transcript: Annotated[list[dict[str, Any]], operator.add]  # sichtbarer Nachrichtenverlauf
    round: int  # Angebotsrunden (abgelehnte Annahmen zählen mit)
    offers: Annotated[list[dict[str, Any]], operator.add]  # alle Zusagen des Agenten (für die Mandatsprüfung)
    turns: Annotated[list[dict[str, Any]], operator.add]  # Tokens, Latenz, Formatfehler pro LLM-Entscheid
    pending: dict[str, Any] | None  # letzter Entscheid des Agenten (AgentTurn)
    last_supplier_event: str | None
    last_supplier_terms: dict[str, Any] | None
    outcome: Outcome | None
    end_reason: str | None
    deal_terms: dict[str, Any] | None


def build_graph(policy: Policy, supplier: SupplierSimulator):
    def load_context(state: NegotiationState) -> dict:
        # KW42: Kontext kommt aus dem Szenario (JSON-Stub). KW43: ERP-Mock über MCP.
        Context.model_validate(state["context"])
        Mandate.model_validate(state["mandate"])
        return {
            "round": 0,
            "outcome": None,
            "end_reason": None,
            "pending": None,
            "last_supplier_event": None,
            "last_supplier_terms": None,
            "deal_terms": None,
        }

    def negotiate(state: NegotiationState) -> dict:
        terms = state.get("last_supplier_terms")
        accept_only = state["round"] >= state["mandate"]["max_rounds"]
        view = AgentView(
            context=Context.model_validate(state["context"]),
            mandate=Mandate.model_validate(state["mandate"]),
            transcript=state.get("transcript", []),
            round_next=state["round"] + 1,
            last_supplier_event=state.get("last_supplier_event"),
            last_supplier_terms=Terms.model_validate(terms) if terms else None,
            accept_only=accept_only,
        )
        try:
            res = policy.decide(view)
        except FormatError as e:
            r = e.result
            return {
                "outcome": "error",
                "end_reason": "format_error",
                "turns": [
                    {
                        "round": view.round_next,
                        "action": "error",
                        "input_tokens": r.input_tokens,
                        "output_tokens": r.output_tokens,
                        "format_errors": r.format_errors,
                        "error": str(e),
                    }
                ],
            }
        turn = res.turn
        log = {
            "round": view.round_next,
            "action": turn.action,
            "input_tokens": res.input_tokens,
            "output_tokens": res.output_tokens,
            "latency_s": round(res.latency_s, 3),
            "format_errors": res.format_errors,
            "rationale": turn.rationale,
        }
        if accept_only and turn.action == "offer":
            # Rundenlimit: neues Angebot wird nicht mehr gesendet und zählt nicht als Zusage.
            return {
                "pending": turn.model_dump(),
                "turns": [log],
                "outcome": "no_deal",
                "end_reason": "round_limit",
            }
        msg_round = view.round_next if turn.action == "offer" else state["round"]
        update: dict = {
            "pending": turn.model_dump(),
            "transcript": [
                {"role": "agent", "round": msg_round, "action": turn.action, "text": turn.message}
            ],
            "turns": [log],
        }
        if turn.action in ("offer", "accept"):
            committed = turn.packages if turn.action == "offer" else [turn.accepted_terms]
            update["offers"] = [
                {"round": msg_round, "action": turn.action, "packages": [p.model_dump() for p in committed]}
            ]
        if turn.action == "offer":
            update["round"] = view.round_next
        return update

    def send_and_wait(state: NegotiationState) -> dict:
        turn = state["pending"]
        t = state["round"]
        if turn["action"] == "offer":
            reply = supplier.respond_to_offer(t, [Terms.model_validate(p) for p in turn["packages"]])
        else:
            reply = supplier.respond_to_acceptance(t, Terms.model_validate(turn["accepted_terms"]))
        update: dict = {
            "transcript": [{"role": "supplier", "round": t, "event": reply.event, "text": reply.text}],
            "last_supplier_event": reply.event,
            "last_supplier_terms": reply.terms.model_dump() if reply.terms else None,
        }
        if reply.event in ("accept", "confirm"):
            update |= {
                "outcome": "deal",
                "deal_terms": reply.terms.model_dump(),
                "end_reason": "supplier_accept" if reply.event == "accept" else "agent_accept",
            }
        elif reply.event == "reject_final":
            update |= {"outcome": "no_deal", "end_reason": "supplier_final_reject"}
        elif turn["action"] == "accept":
            update["round"] = t + 1  # abgelehnte Annahme = neuer Vorschlag, zählt als Runde
        return update

    def finalize(state: NegotiationState) -> dict:
        if state.get("outcome"):
            return {}
        action = (state.get("pending") or {}).get("action")
        if action == "escalate":
            return {"outcome": "escalated", "end_reason": "escalate"}
        if action == "walk_away":
            return {"outcome": "no_deal", "end_reason": "walk_away"}
        return {"outcome": "no_deal", "end_reason": "round_limit"}

    def route_after_negotiate(state: NegotiationState) -> Literal["send_and_wait", "finalize"]:
        if state.get("outcome"):
            return "finalize"
        return "send_and_wait" if state["pending"]["action"] in ("offer", "accept") else "finalize"

    def route_after_reply(state: NegotiationState) -> Literal["negotiate", "finalize"]:
        if state.get("outcome"):
            return "finalize"
        max_rounds = state["mandate"]["max_rounds"]
        if state["round"] < max_rounds:
            return "negotiate"
        open_counter = state.get("last_supplier_event") in ("counter", "decline")
        return "negotiate" if state["round"] == max_rounds and open_counter else "finalize"

    g = StateGraph(NegotiationState)
    g.add_node("load_context", load_context)
    g.add_node("negotiate", negotiate)
    g.add_node("send_and_wait", send_and_wait)
    g.add_node("finalize", finalize)
    g.add_edge(START, "load_context")
    g.add_edge("load_context", "negotiate")
    g.add_conditional_edges("negotiate", route_after_negotiate)
    g.add_conditional_edges("send_and_wait", route_after_reply)
    g.add_edge("finalize", END)
    return g.compile(checkpointer=InMemorySaver())
