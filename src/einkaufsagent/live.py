"""Verhandlung im Terminal (ADR 0012, 0015): Die Einkäuferin entscheidet Eskalationen, optional ist ein Mensch der
Lieferant. Nur Variante (b).

    uv run ea-run --scenario S11 --variant b --policy rule --live                 # Simulator, Einkäuferin im Terminal
    uv run ea-run --scenario S04 --variant b --model gpt-5.6-luna --human --erp results/erp-demo.sqlite

Farben wie in der BPMN: orange = LLM, blau = Code, grün = Mensch. Der Runner streamt die Updates der Nodes, hält am
Interrupt von ``ask_buyer`` an und setzt mit ``Command(resume=...)`` und derselben ``thread_id`` fort (SW8 Folie 20).
Die verdeckten Werte des Szenarios (Spielkarte) nutzt nur die Auswertung am Schluss, nie der Graph.
"""

from __future__ import annotations

import os
import sys
import uuid
from collections.abc import Callable
from typing import Any

from langgraph.types import Command

from einkaufsagent.domain import Terms, buyer_value_chf, check_deal, check_terms
from einkaufsagent.erp import ErpAdapter
from einkaufsagent.eval import RecordingSupplier
from einkaufsagent.graph_b import HybridAgent, build_graph
from einkaufsagent.scenarios import Scenario
from einkaufsagent.supplier_sim import LABELS, SupplierReply, SupplierSimulator, analyse_zopa, same_terms

Ask = Callable[[str], str]
Out = Callable[[str], None]

_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
LLM, CODE, HUMAN, MSG, DIM = "38;5;208", "38;5;33", "38;5;34", "1", "2"


def paint(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def _terms_line(packages: list[dict]) -> str:
    ts = [Terms.model_validate(p).short() for p in packages]
    return ts[0] if len(ts) == 1 else " | ".join(f"{LABELS[i]}: {t}" for i, t in enumerate(ts))


class HumanSupplier:
    """Mensch als Lieferant (ADR 0015): sieht nur den Text der Nachricht, nie die Pakete aus dem State."""

    def __init__(self, ask: Ask = input, out: Out = print):
        self._ask, self._out = ask, out

    def respond_to_offer(self, t: int, packages: list[Terms], text: str = "") -> SupplierReply:
        return self._reply(t, text)

    def respond_to_acceptance(self, t: int, terms: Terms, text: str = "") -> SupplierReply:
        return self._reply(t, text)

    def _reply(self, t: int, text: str) -> SupplierReply:
        self._out(paint(MSG, f"\n  Agent → Lieferant (Runde {t}): {text}"))
        answer = ""
        while not answer.strip():
            answer = self._ask(paint(HUMAN, "  Ihre Antwort als Lieferant: "))
        return SupplierReply(event="human", text=answer.strip())


class Printer:
    """Zeigt pro Node, was das LLM vorschlägt und was der Code entscheidet."""

    def __init__(self, out: Out, human: bool, offline: set[str] | None = None):
        self.out, self.human = out, human
        self.offline = offline or set()  # Nodes ohne LLM (Vorlage bzw. Regex, --policy rule)
        self.draft: str | None = None
        self.narrate_failed = False

    def llm(self, node: str, text: str) -> None:
        if node in self.offline:
            self.out(paint(CODE, f"  [Code] {node} (ohne LLM): {text}"))
        else:
            self.out(paint(LLM, f"  [LLM]  {node}: {text}"))

    def code(self, node: str, text: str) -> None:
        self.out(paint(CODE, f"  [Code] {node}: {text}"))

    def message(self, who: str, text: str) -> None:
        self.out(paint(MSG, f"\n  {who}: {text}"))

    def show(self, node: str, u: dict[str, Any]) -> None:
        match node:
            case "load_context":
                c = u["context"]
                cur = Terms.model_validate(c["current_terms"]).short()
                self.code(node, f"{c['supplier_name']} ({c['category']}), heute: {cur}")
            case "offer_engine":
                if u.get("outcome"):
                    self.code(node, f"kein Paket mehr möglich ({u['end_reason']})")
                else:
                    self.out("")
                    self.code(node, f"Runde {u['round']}, Pakete {_terms_line(u['pending']['packages'])}")
            case "narrate":
                self.draft, self.narrate_failed = u.get("draft"), not u.get("draft")
                if self.narrate_failed:
                    self.llm(node, f"gescheitert ({u.get('template_reason')})")
                else:
                    self.llm(node, f"Text formuliert ({len(self.draft)} Zeichen)")
            case "mandate_guard":
                if self.narrate_failed:
                    self.code(node, "kein LLM-Text, Standardtext folgt")
                elif u.get("template_reason"):
                    self.code(node, f"LLM-Text verworfen: {u['template_reason']}")
                    self.out(paint(DIM, f"         verworfen: {self.draft}"))
                else:
                    self.code(node, "Zahlen und Pakete geprüft, Text darf hinaus")
            case "template_message":
                self.code(node, "Standardtext aus der Vorlage statt LLM-Text")
            case "send_and_wait":
                agent, supplier = u["transcript"]
                if not self.human:  # beim Menschen hat HumanSupplier beides schon gezeigt
                    self.message(f"Agent → Lieferant (Runde {agent['round']})", agent["text"])
                    self.message("Lieferant → Agent", supplier["text"])
            case "parse_response":
                self._parsed(u)
            case "assess_response":
                self._assessed(u)
            case "escalate":
                self.code(node, "Vorlage für die Einkäuferin aufbereitet, Protokoll mit Status «escalated»")
                self.message("Agent → Lieferant", u["transcript"][0]["text"])
            case "ask_buyer":
                self.out(paint(HUMAN, f"  [Mensch] Einkäuferin: {u['buyer_decision']}"))
            case "record_outcome":
                self.code(node, "Ergebnis und Protokoll im ERP erfasst")
            case "notify_supplier":
                self.message("Agent → Lieferant", u["transcript"][0]["text"])

    def _parsed(self, u: dict) -> None:
        p = u.get("parsed")
        if p is None:
            self.llm("parse_response", f"nicht auswertbar ({u.get('parse_error')})")
            return
        parts = [p["reply_type"]]
        if p.get("chosen_package"):
            parts.append(f"Paket {p['chosen_package']}")
        if p.get("counter_terms"):
            parts.append(f"Gegenangebot {Terms.model_validate(p['counter_terms']).short()}")
        for s in p.get("statements", []):
            parts.append(f"{s['kind']}/{s['quantity']} «{s['quote'][:70]}»")
        self.llm("parse_response", " · ".join(parts))

    def _assessed(self, u: dict) -> None:
        outcome = u.get("outcome")
        if outcome == "deal":
            text = f"Einigung: {Terms.model_validate(u['deal_terms']).short()}"
        elif outcome == "no_deal":
            text = f"kein Abschluss ({u['end_reason']})"
        elif outcome == "escalated":
            text = f"Eskalation nach ADR 0008 ({u['end_reason'].removeprefix('escalate:')})"
        elif (u.get("pending") or {}).get("kind") == "accept":
            text = "Gegenangebot im Mandat und annehmbar (AC_next): Annahme senden"
        else:
            text = "weiterverhandeln"
        self.code("assess_response", text)
        for sentence in u.get("prefix") or []:
            self.code("assess_response", f"Vorlage: «{sentence}»")


def ask_buyer_in_terminal(brief: dict, ask: Ask, out: Out) -> dict:
    out(paint(HUMAN, "\n  ── Eskalation an die Einkäuferin ──"))
    for key in ("lieferant", "runde", "grund", "mandat"):
        out(paint(HUMAN, f"  {key.capitalize()}: {brief[key]}"))
    out(paint(HUMAN, "  Verlauf:"))
    for line in brief["verlauf"]:
        out(paint(HUMAN, f"    {line}"))
    out(paint(HUMAN, f"  Letzte Antwort: {brief['letzte_antwort']}"))
    for note in brief["hinweise"]:
        out(paint(HUMAN, f"  Hinweis: {note}"))
    choice = ""
    while choice not in ("w", "a"):
        choice = ask(paint(HUMAN, "  Entscheid [w = weiterverhandeln, a = abbrechen]: ")).strip().lower()[:1]
    note = ask(paint(HUMAN, "  Notiz fürs Protokoll (optional, geht nicht an den Lieferanten): ")).strip()
    return {"decision": "weiterverhandeln" if choice == "w" else "abbrechen", "note": note}


def run_live(
    sc: Scenario,
    agent: HybridAgent,
    erp: ErpAdapter,
    human: bool = False,
    paraphrase: bool = False,
    ask: Ask = input,
    out: Out = print,
) -> dict[str, Any]:
    ctx, m = sc.public.context, sc.public.mandate
    sim = None if human else RecordingSupplier(SupplierSimulator(sc.hidden, ctx, paraphrase=paraphrase))
    supplier = HumanSupplier(ask, out) if human else sim
    erp.seed(ctx)
    nid = str(uuid.uuid4())
    graph = build_graph(agent, supplier, erp)
    cfg = {
        "configurable": {"thread_id": nid},
        "recursion_limit": 100,
        "run_name": f"live-{sc.id}",
        "tags": ["variante-b", "live", agent.name, sc.id, *(["mensch"] if human else [])],
        "metadata": {"scenario_id": sc.id, "variant": "b", "human": human},
    }
    out(paint(MSG, f"{sc.id} · {ctx.supplier_name} · Lieferant: {'Mensch' if human else 'Simulator'}"))
    earlier = erp.protocols(ctx.supplier_id)
    out(
        paint(CODE, f"  [Code] ERP-Gedächtnis: {len(earlier)} frühere Verhandlung(en) mit diesem Lieferanten")
    )
    for p in earlier[-3:]:
        choice = next((x["chosen_package"] for x in reversed(p["exchanges"]) if x["chosen_package"]), "–")
        out(
            paint(
                CODE,
                f"         {p['recorded_at']}: {p['status']} nach {p['rounds']} Runden, Paketwahl {choice}",
            )
        )

    offline = {"narrate"} if agent.narrator.name == "vorlage" else set()
    offline |= {"parse_response"} if agent.parser.name == "regeln" else set()
    printer = Printer(out, human, offline)
    command: Any = {
        "scenario_id": sc.id,
        "negotiation_id": nid,
        "supplier_id": ctx.supplier_id,
        "mandate": m.model_dump(),
        "transcript": [],
        "offers": [],
        "turns": [],
    }
    while True:
        for chunk in graph.stream(command, cfg, stream_mode="updates"):
            for node, update in chunk.items():
                if node != "__interrupt__" and update:
                    printer.show(node, update)
                elif node == "record_outcome":
                    printer.show(node, {})
        snapshot = graph.get_state(cfg)
        if not snapshot.interrupts:
            break
        command = Command(resume=ask_buyer_in_terminal(snapshot.interrupts[0].value, ask, out))
    final = snapshot.values
    report(sc, final, erp, sim, human, ask, out)
    return final


def report(sc: Scenario, final: dict, erp: ErpAdapter, sim, human: bool, ask: Ask, out: Out) -> None:
    """Ergebnis, Protokoll im ERP und Auswertung gegen die Spielkarte (verdeckte Werte des Szenarios, ADR 0012)."""
    ctx, m = sc.public.context, sc.public.mandate
    out(
        paint(
            MSG,
            f"\nErgebnis: {final.get('outcome')} ({final.get('end_reason')}) nach {final.get('round')} Runden",
        )
    )
    p = erp.protocols(ctx.supplier_id)[-1]
    choices = ", ".join(
        f"R{x['round']} {x['reply_type'] or '?'} {x['chosen_package'] or ''}".strip() for x in p["exchanges"]
    )
    out(paint(CODE, f"  Protokoll im ERP: Status {p['status']}, Reaktionen {choices}"))
    if p["buyer_decision"]:
        note = f" ({p['buyer_note']})" if p["buyer_note"] else ""
        out(paint(CODE, f"  Entscheid der Einkäuferin: {p['buyer_decision']}{note}"))
    out(paint(CODE, f"  Konditionen im ERP: {erp.current_terms(ctx.supplier_id).short()}"))

    violations = [
        f"R{o['round']}:{v.code}"
        for o in final.get("offers", [])
        for t in o["packages"]
        for v in check_terms(Terms.model_validate(t), ctx, m)
    ]
    line = "  Spielkarte: "
    if final.get("outcome") == "deal" and final.get("deal_terms"):
        dt = Terms.model_validate(final["deal_terms"])
        violations += [f"deal:{v.code}" for v in check_deal(dt, ctx, m) if v.code == "below_walk_away"]
        if human:
            agreed = (
                ask(paint(HUMAN, f"  Lieferant: Stimmen Sie {dt.short()} zu? [j/n]: ")).strip().lower()[:1]
                == "j"
            )
        else:
            last = sim.replies[-1] if sim and sim.replies else None
            agreed = last is not None and last.event in ("accept", "confirm") and same_terms(last.terms, dt)
        if not agreed:
            violations.append("deal:not_agreed")
        value = buyer_value_chf(dt, ctx, m)
        z = analyse_zopa(ctx, m, sc.hidden)
        share = (
            (value - m.min_value_chf) / (z.max_value_chf - m.min_value_chf)
            if z.max_value_chf > m.min_value_chf
            else None
        )
        line += f"Nutzen {value:.0f} CHF (Mindestnutzen {m.min_value_chf:.0f})"
        if share is None:
            line += ", ZOPA leer"
        else:
            line += f", Anteil am Spielraum {share:.2f}"
            line += " (mehr, als der simulierte Lieferant zugestanden hätte)" if share > 1 else ""
    else:
        line += f"kein Abschluss; erwartet war laut Szenario {sc.expected_outcome}"
    out(paint(MSG, line))
    out(paint(MSG, f"  Verstösse: {', '.join(violations) or 'keine'}"))
