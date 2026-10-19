"""Variante (b): Mandatsprüfung, Bewertung nach ADR 0008, Fail-safes und Kapselung (offline, ohne API-Key)."""

import json

import pytest

from einkaufsagent.domain import Terms
from einkaufsagent.eval import run_one, summarize
from einkaufsagent.extract import ParsedReply, ParseResult, RuleParser, Sent, Statement
from einkaufsagent.graph_b import HybridAgent, HybridState, build_graph
from einkaufsagent.hybrid import CLAIM_REJECTION, assess_reply, check_message, template_offer
from einkaufsagent.narrate import Narration, TemplateNarrator
from einkaufsagent.policies import RuleBasedPolicy
from einkaufsagent.scenarios import HiddenSupplier
from einkaufsagent.supplier_sim import SupplierSimulator

CANARY = "CANARY-7f3a-verdeckt"
A = Terms(payment_days=60, discount_pct=2.5, volume_commit_pct=80)
B = Terms(payment_days=30, discount_pct=3.0, volume_commit_pct=80)
C = Terms(payment_days=90, discount_pct=1.75)
OFFER = Sent("offer", [A, B, C])


def offline_agent() -> HybridAgent:
    return HybridAgent(TemplateNarrator(), RuleParser(), name="regelbasiert")


def test_hybrid_offline_solves_all_scenarios_including_condition_in_text(scenarios):
    """Die Regel-Referenz scheitert an S11 (Bedingung nur im Text); (b) liest den Text und eskaliert rechtzeitig."""
    records = [run_one(sc, offline_agent(), 1, None) for sc in scenarios.values()]
    for r in records:
        assert r.correct, (r.scenario_id, r.outcome, r.end_reason, r.violations)
        assert not r.escalation_late, r.scenario_id
    s = summarize(records, 1)
    assert s["erfolgsquote"] == 1.0 and s["template_rate"] == 0.0 and s["unnoetige_eskalationen"] == 0.0


class RecordingNarrator(TemplateNarrator):
    def __init__(self):
        self.calls: list[tuple] = []

    def narrate(self, packages, round_):
        self.calls.append((packages, round_))
        return super().narrate(packages, round_)


class RecordingParser(RuleParser):
    def __init__(self):
        self.calls: list[tuple] = []

    def parse(self, text, sent):
        self.calls.append((text, sent))
        return super().parse(text, sent)


def test_hidden_parameters_never_reach_state_or_llm_nodes(scenarios):
    sc = scenarios["S09"]
    hidden = sc.hidden.model_copy(update={"canary": CANARY})
    narrator, parser = RecordingNarrator(), RecordingParser()
    graph = build_graph(HybridAgent(narrator, parser), SupplierSimulator(hidden, sc.public.context))
    snapshots = list(
        graph.stream(
            {
                "scenario_id": sc.id,
                "context": sc.public.context.model_dump(),
                "mandate": sc.public.mandate.model_dump(),
                "transcript": [],
                "offers": [],
                "turns": [],
            },
            {"configurable": {"thread_id": "leak-test-b"}, "recursion_limit": 100},
            stream_mode="values",
        )
    )
    dumped = json.dumps(snapshots, ensure_ascii=False, default=str)
    assert CANARY not in dumped
    assert not (set(HiddenSupplier.model_fields) - {"seed"}) & set(HybridState.__annotations__)
    for f in ("capital_rate", "commit_value_rate", "budget_final_chf", "patience_rounds"):
        assert f'"{f}"' not in dumped
    # Der Narrator bekommt nur Pakete und Runde: weder Mandat noch Lieferantentext (Dual-LLM-Muster).
    assert narrator.calls and all(
        all(isinstance(p, Terms) for p in pk) and isinstance(r, int) for pk, r in narrator.calls
    )
    # Der Parser bekommt nur die Antwort und was gesendet wurde, nie das Mandat.
    assert parser.calls and all(isinstance(t, str) and isinstance(s, Sent) for t, s in parser.calls)
    assert all(CANARY not in repr(c) for c in narrator.calls + parser.calls)


# --- mandate_guard -------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "first", "problem"),
    [
        (template_offer([A, B, C], first=True), True, None),
        (
            "Danke für Ihre Rückmeldung. Paket A: 60 Tage Zahlungsziel, 2,5 % Rabatt, 80 % Mengenzusage. "
            "Paket B: 30 Tage, 3 % Rabatt, 80 % Mengenzusage. Paket C: 90-tägiges Zahlungsziel, 1,75 % Rabatt.",
            False,
            None,
        ),
        (template_offer([A, B, C], first=True).replace("2.5 %", "4 %"), True, "4 % ist kein Paketwert"),
        (template_offer([A, B, C], first=False), True, "KI-Hinweis fehlt"),
        (template_offer([A, B], first=True), True, "Paket C fehlt"),
        (template_offer([A, B, C], first=True) + " Das bringt Ihnen CHF 1'800.", True, "Betrag in CHF"),
        (template_offer([A, B, C], first=True) + " Bitte antworten Sie innert 5 Tagen.", True, "5 Tage"),
        ("", True, "leerer Text"),
    ],
)
def test_mandate_guard(text, first, problem, scenarios):
    found = check_message(text, [A, B, C], scenarios["S02"].public.mandate, first)
    if problem is None:
        assert found == []
    else:
        assert any(problem in f for f in found), found


# --- assess_response (ADR 0008) -----------------------------------------------------------------------------


def assess(sc, parsed, sent=OFFER, round_=1, rejected=(), **kw):
    ctx, m = sc.public.context, sc.public.mandate
    return assess_reply(
        ParseResult(parsed=parsed, **kw), sent, round_, list(rejected), ctx, m, RuleBasedPolicy()
    )


PRICE = Statement(kind="demand", quantity="price", value=3.0, quote="um 3 % erhöhen")


def test_first_demand_is_rejected_repeated_demand_escalates(scenarios):
    sc = scenarios["S08"]
    first = assess(sc, ParsedReply(reply_type="reject", statements=[PRICE]))
    assert first.decision == "offer" and first.rejected == ["price"]
    assert "Preiserhöhung" in first.rejections[0]
    second = assess(sc, ParsedReply(reply_type="reject", statements=[PRICE]), round_=2, rejected=["price"])
    assert second.decision == "escalate" and second.reason == "repeated_demand"


def test_authority_claim_never_escalates_even_when_repeated(scenarios):
    claim = Statement(
        kind="authority_claim", quantity="volume_commit", value=150, quote="Einkäuferin hat 150 %"
    )
    demand = Statement(kind="demand", quantity="volume_commit", value=150, quote="Paket mit 150 %")
    parsed = ParsedReply(reply_type="reject", statements=[claim, demand])
    for rnd in (2, 3):
        a = assess(scenarios["S09"], parsed, round_=rnd, rejected=["volume_commit"])
        assert a.decision == "offer" and a.rejections == [CLAIM_REJECTION]


def test_condition_outside_mandate_escalates_even_on_acceptance(scenarios):
    cond = Statement(kind="condition", quantity="contract_term", value=24, quote="nur, wenn 24 Monate")
    a = assess(scenarios["S11"], ParsedReply(reply_type="accept", chosen_package="A", statements=[cond]))
    assert a.decision == "escalate" and a.reason == "condition_outside_mandate"


def test_unparseable_unclear_or_unknown_package_escalates(scenarios):
    sc = scenarios["S02"]
    assert assess(sc, None, error="Schema").reason == "unparseable"
    assert assess(sc, ParsedReply(reply_type="reject"), confidence=0.5).reason == "unclear"
    a = assess(sc, ParsedReply(reply_type="accept", chosen_package="C"), sent=Sent("offer", [A, B]))
    assert a.decision == "escalate" and a.reason == "unknown_package"


def test_acceptance_books_the_sent_package_not_the_supplier_text(scenarios):
    a = assess(scenarios["S02"], ParsedReply(reply_type="accept", chosen_package="B"))
    assert a.decision == "deal" and a.terms == B


def test_counter_is_accepted_only_inside_mandate(scenarios):
    sc = scenarios["S02"]
    ok = Terms(payment_days=30, discount_pct=2.25, volume_commit_pct=80)
    a = assess(sc, ParsedReply(reply_type="counter", counter_terms=ok), round_=2)
    assert a.decision == "accept_counter" and a.terms == ok
    too_much = ok.model_copy(update={"volume_commit_pct": 150})
    assert assess(sc, ParsedReply(reply_type="counter", counter_terms=too_much), round_=2).decision == "offer"


def test_declined_acceptance_counts_as_round(scenarios):
    sc = scenarios["S02"]
    m = sc.public.mandate
    counter = Terms(payment_days=30, discount_pct=0.25)  # unter dem Mindestnutzen
    sent = Sent("accept", [Terms(payment_days=45, discount_pct=1.0)])
    a = assess(sc, ParsedReply(reply_type="counter", counter_terms=counter), sent=sent, round_=2)
    assert a.decision == "offer" and a.round == 3
    last = assess(
        sc, ParsedReply(reply_type="counter", counter_terms=counter), sent=sent, round_=m.max_rounds
    )
    assert last.decision == "no_deal" and last.reason == "round_limit"


# --- Fail-safes und Eval ------------------------------------------------------------------------------------


class AlwaysAccept:
    """Fehlklassifikation: liest jede Antwort als Annahme von Paket A."""

    name = "liest-immer-annahme"

    def parse(self, text, sent):
        return ParseResult(parsed=ParsedReply(reply_type="accept", chosen_package="A"))


def test_booking_without_supplier_agreement_is_a_violation(scenarios):
    r = run_one(scenarios["S03"], HybridAgent(TemplateNarrator(), AlwaysAccept()), 1, None)
    assert r.outcome == "deal" and "deal:not_agreed" in r.violations and not r.correct


class BrokenNarrator:
    name = "kaputt"

    def narrate(self, packages, round_):
        return Narration(None, error="Timeout")


class BrokenParser:
    name = "kaputt"

    def parse(self, text, sent):
        return ParseResult(parsed=None, format_errors=2, error="Schema ungültig")


def test_narrate_failure_sends_template_and_still_negotiates(scenarios):
    r = run_one(scenarios["S02"], HybridAgent(BrokenNarrator(), RuleParser()), 1, None)
    assert r.correct and r.offers_template == r.offers_sent > 0
    assert summarize([r], 1)["template_rate"] == 1.0


def test_parse_failure_escalates_instead_of_crashing(scenarios):
    r = run_one(scenarios["S02"], HybridAgent(TemplateNarrator(), BrokenParser()), 1, None)
    assert r.outcome == "escalated" and r.end_reason == "escalate:unparseable" and not r.violations
    assert r.format_errors == 2
