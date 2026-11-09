"""Eskalation mit interrupt() und Command(resume=...) (ADR 0015), offline mit Vorlage und Regex-Parser."""

from langgraph.types import Command

from einkaufsagent.erp import ErpAdapter
from einkaufsagent.extract import ParsedReply, ParseResult, RuleParser, Sent, Statement
from einkaufsagent.graph_b import HybridAgent, build_graph, normalize_decision
from einkaufsagent.hybrid import BUYER_REJECTION, ESCALATION_HOLD, assess_reply
from einkaufsagent.narrate import TemplateNarrator
from einkaufsagent.policies import RuleBasedPolicy
from einkaufsagent.supplier_sim import SupplierSimulator


def start(sc, nid: str, **mandate_update):
    erp = ErpAdapter()
    erp.seed(sc.public.context)
    agent = HybridAgent(TemplateNarrator(), RuleParser(), name="regelbasiert")
    graph = build_graph(agent, SupplierSimulator(sc.hidden, sc.public.context), erp)
    cfg = {"configurable": {"thread_id": nid}, "recursion_limit": 100}
    first = graph.invoke(
        {
            "scenario_id": sc.id,
            "negotiation_id": nid,
            "supplier_id": sc.public.context.supplier_id,
            "mandate": sc.public.mandate.model_copy(update=mandate_update).model_dump(),
            "transcript": [],
            "offers": [],
            "turns": [],
        },
        cfg,
    )
    return graph, cfg, erp, first


def test_graph_halts_at_ask_buyer_with_brief_and_protocol(scenarios):
    sc = scenarios["S11"]
    graph, cfg, erp, first = start(sc, "s11")
    [irq] = first["__interrupt__"]
    assert graph.get_state(cfg).next == ("ask_buyer",)
    brief = irq.value
    assert brief["optionen"] == ["weiterverhandeln", "abbrechen"]
    assert "Bedingung" in brief["grund"] and brief["verlauf"] and brief["letzte_antwort"]
    assert first["outcome"] == "escalated" and first["transcript"][-1]["text"] == ESCALATION_HOLD
    [p] = erp.protocols(sc.public.context.supplier_id)
    assert p["status"] == "escalated" and p["buyer_decision"] is None


def test_abort_records_decision_and_notifies(scenarios):
    sc = scenarios["S11"]
    graph, cfg, erp, _ = start(sc, "s11-abbruch")
    final = graph.invoke(Command(resume={"decision": "abbrechen", "note": "Laufzeit nicht gewünscht"}), cfg)
    assert final["outcome"] == "escalated" and final["buyer_decision"] == "abbrechen"
    assert final["transcript"][-1]["action"] == "notify" and "Einkäuferin" in final["transcript"][-1]["text"]
    [p] = erp.protocols(sc.public.context.supplier_id)
    assert p["buyer_decision"] == "abbrechen" and p["buyer_note"] == "Laufzeit nicht gewünscht"
    assert erp.current_terms(sc.public.context.supplier_id) == sc.public.context.current_terms
    assert "Laufzeit nicht gewünscht" not in " ".join(
        t["text"] for t in final["transcript"]
    )  # Notiz bleibt intern


def test_continue_rejects_condition_and_does_not_escalate_again(scenarios):
    sc = scenarios["S11"]
    graph, cfg, erp, first = start(sc, "s11-weiter")
    final = graph.invoke(Command(resume={"decision": "weiterverhandeln"}), cfg)
    assert "__interrupt__" not in final  # dieselbe Bedingung geht nicht ein zweites Mal an die Einkäuferin
    agent_msgs = [t for t in final["transcript"] if t["role"] == "agent"]
    resumed = agent_msgs[agent_msgs.index(next(t for t in agent_msgs if t["action"] == "escalate")) + 1]
    assert resumed["action"] == "offer" and resumed["text"].startswith(BUYER_REJECTION)
    assert final["round"] > first["round"]
    assert final["outcome"] != "deal"  # eine Annahme nur unter der Bedingung ist kein Abschluss
    [p] = erp.protocols(sc.public.context.supplier_id)
    assert p["status"] == final["outcome"] and p["buyer_decision"] == "weiterverhandeln"


def test_continue_after_repeated_demand(scenarios):
    sc = scenarios["S08"]
    graph, cfg, _, first = start(sc, "s08-weiter")
    assert first["end_reason"] == "escalate:repeated_demand"
    final = graph.invoke(Command(resume="weiterverhandeln"), cfg)
    assert "__interrupt__" not in final and final["outcome"] == "no_deal"
    assert all(p["price_change_pct"] == 0 for o in final["offers"] for p in o["packages"])  # Mandat bleibt


def test_continue_in_last_round_ends_at_round_limit(scenarios):
    graph, cfg, _, first = start(scenarios["S11"], "s11-limit", max_rounds=1)
    assert first["round"] == 1 and "__interrupt__" in first
    final = graph.invoke(Command(resume="weiterverhandeln"), cfg)
    assert final["outcome"] == "no_deal" and final["end_reason"] == "round_limit" and final["round"] == 1


def test_anything_but_continue_means_abort():
    assert normalize_decision({"decision": " Weiterverhandeln ", "note": " ok "}) == (
        "weiterverhandeln",
        "ok",
    )
    assert normalize_decision("ja") == ("abbrechen", "")
    assert normalize_decision(None) == ("abbrechen", "")


def test_buyer_rejected_quantity_is_rejected_not_escalated(scenarios):
    sc = scenarios["S08"]
    ctx, m = sc.public.context, sc.public.mandate
    price = Statement(kind="demand", quantity="price", value=3.0, quote="um 3 % erhöhen")
    term = Statement(kind="condition", quantity="contract_term", value=24, quote="nur bei 24 Monaten")
    sent = Sent("offer", RuleBasedPolicy().packages(1500, ctx, m) or [ctx.current_terms])
    for st, reply in ((price, "reject"), (term, "accept")):
        parse = ParseResult(parsed=ParsedReply(reply_type=reply, chosen_package="A", statements=[st]))
        a = assess_reply(parse, sent, 2, ["price"], ctx, m, RuleBasedPolicy(), [st.quantity])
        assert a.decision == "offer" and a.rejections == [BUYER_REJECTION]
