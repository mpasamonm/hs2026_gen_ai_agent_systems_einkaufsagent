"""ERP-Adapter (ADR 0015): Kontext laden, Protokoll auf jedem Ausgang, Buchung und Metrik korrekt_gebucht."""

from einkaufsagent.domain import Terms
from einkaufsagent.erp import ErpAdapter, Exchange
from einkaufsagent.eval import run_one, summarize
from einkaufsagent.extract import RuleParser
from einkaufsagent.graph_b import HybridAgent, build_graph
from einkaufsagent.narrate import TemplateNarrator
from einkaufsagent.supplier_sim import SupplierSimulator


def offline_agent() -> HybridAgent:
    return HybridAgent(TemplateNarrator(), RuleParser(), name="regelbasiert")


def negotiate(sc, erp: ErpAdapter, nid: str) -> dict:
    graph = build_graph(offline_agent(), SupplierSimulator(sc.hidden, sc.public.context), erp)
    return graph.invoke(
        {
            "scenario_id": sc.id,
            "negotiation_id": nid,
            "supplier_id": sc.public.context.supplier_id,
            "mandate": sc.public.mandate.model_dump(),
            "transcript": [],
            "offers": [],
            "turns": [],
        },
        {"configurable": {"thread_id": nid}, "recursion_limit": 100},
    )


def test_context_comes_from_erp(scenarios):
    ctx = scenarios["S02"].public.context
    erp = ErpAdapter()
    erp.seed(ctx)
    assert erp.load_context(ctx.supplier_id) == ctx


def test_deal_is_booked_and_protocol_keeps_package_choice(scenarios):
    sc = scenarios["S02"]
    erp = ErpAdapter()
    erp.seed(sc.public.context)
    final = negotiate(sc, erp, "n1")
    assert final["outcome"] == "deal"
    [p] = erp.protocols(sc.public.context.supplier_id)
    assert p["status"] == "deal" and p["rounds"] == final["round"]
    assert p["start_packages"] == final["offers"][0]["packages"]
    assert Terms.model_validate(p["deal_terms"]) == erp.current_terms(sc.public.context.supplier_id)
    last = p["exchanges"][-1]
    assert last["reply_type"] == "accept"
    assert last["sent_kind"] == "accept" or last["chosen_package"] in ("A", "B", "C")


def test_no_deal_and_escalation_leave_conditions_unchanged(scenarios):
    for sid, status in (("S06", "no_deal"), ("S08", "escalated")):
        sc = scenarios[sid]
        erp = ErpAdapter()
        erp.seed(sc.public.context)
        negotiate(sc, erp, sid)
        [p] = erp.protocols(sc.public.context.supplier_id)
        assert p["status"] == status and p["deal_terms"] is None and p["notes"] is not None
        assert erp.current_terms(sc.public.context.supplier_id) == sc.public.context.current_terms


def test_protocols_survive_across_negotiations_in_a_file(scenarios, tmp_path):
    """Langzeitgedächtnis: zwei Verhandlungen (zwei Threads) mit demselben Lieferanten in derselben Datei."""
    sc = scenarios["S02"]
    path = tmp_path / "erp.sqlite"
    for nid in ("erste", "zweite"):
        erp = ErpAdapter(path)
        erp.seed(sc.public.context)
        negotiate(sc, erp, nid)
        erp.close()
    erp = ErpAdapter(path)
    assert [p["negotiation_id"] for p in erp.protocols(sc.public.context.supplier_id)] == ["erste", "zweite"]


def test_record_outcome_is_idempotent(scenarios):
    ctx = scenarios["S02"].public.context
    erp = ErpAdapter()
    erp.seed(ctx)
    ex = [Exchange(1, "offer", [Terms(payment_days=60, discount_pct=2).model_dump()], "reject", None, None)]
    for _ in range(2):
        erp.record_outcome("n", ctx.supplier_id, "escalated", "escalate:unclear", 1, ex, None, ["x"])
    [p] = erp.protocols(ctx.supplier_id)
    assert len(p["exchanges"]) == 1


def test_korrekt_gebucht_offline_and_on_misread_acceptance(scenarios):
    records = [run_one(sc, offline_agent(), 1, None) for sc in scenarios.values()]
    assert all(r.booked_ok for r in records)
    assert summarize(records, 1)["korrekt_gebucht"] == 1.0

    class AlwaysAccept:
        name = "liest-immer-annahme"

        def parse(self, text, sent):
            from einkaufsagent.extract import ParsedReply, ParseResult

            return ParseResult(parsed=ParsedReply(reply_type="accept", chosen_package="A"))

    r = run_one(scenarios["S03"], HybridAgent(TemplateNarrator(), AlwaysAccept()), 1, None)
    assert r.outcome == "deal" and r.booked_ok is False


def test_variant_a_has_no_booking_metric(scenarios):
    from einkaufsagent.policies import RuleBasedPolicy

    r = run_one(scenarios["S02"], RuleBasedPolicy(), 1, None)
    assert r.booked_ok is None and summarize([r], 1)["korrekt_gebucht"] is None
