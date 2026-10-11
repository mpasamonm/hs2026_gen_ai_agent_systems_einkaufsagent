"""Graph-Verhalten (offline) und Kapselung der verdeckten Lieferantenparameter."""

import json

from einkaufsagent.domain import Terms
from einkaufsagent.eval import run_one
from einkaufsagent.graph_a import NegotiationState, build_graph
from einkaufsagent.policies import AgentTurn, AgentView, RuleBasedPolicy, TurnResult
from einkaufsagent.scenarios import HiddenSupplier
from einkaufsagent.supplier_sim import SupplierSimulator

CANARY = "CANARY-7f3a-verdeckt"


class RecordingPolicy(RuleBasedPolicy):
    """Regel-Referenz, die zusätzlich alles festhält, was der Agent zu sehen bekommt."""

    def __init__(self):
        self.views: list[AgentView] = []

    def decide(self, view):
        self.views.append(view)
        return super().decide(view)


def test_rule_reference_reaches_expected_outcome_everywhere(scenarios):
    for sc in scenarios.values():
        r = run_one(sc, RuleBasedPolicy(), 1, None)
        assert r.rounds <= sc.public.mandate.max_rounds
        if sc.hidden.condition:
            continue  # siehe nächster Test
        assert r.correct, (sc.id, r.outcome, r.end_reason, r.violations)
        assert not r.escalation_late, sc.id


def test_rule_reference_misses_condition_in_free_text(scenarios):
    """Die Referenz liest nur strukturierte Werte; die Laufzeit-Bedingung in S11 steht nur im Text. Sie schliesst
    deshalb ab und sagt die Bedingung stillschweigend zu. Diese Lücke schliesst erst das Extrahieren per LLM."""
    r = run_one(scenarios["S11"], RuleBasedPolicy(), 1, None)
    assert r.outcome == "deal" and "deal:condition_outside_mandate" in r.violations and not r.correct


def test_hidden_parameters_never_reach_state_or_agent(scenarios):
    sc = scenarios["S09"]
    hidden = sc.hidden.model_copy(update={"canary": CANARY})
    policy = RecordingPolicy()
    graph = build_graph(policy, SupplierSimulator(hidden, sc.public.context))
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
            {"configurable": {"thread_id": "leak-test"}},
            stream_mode="values",
        )
    )
    dumped = json.dumps(snapshots, ensure_ascii=False, default=str)
    assert CANARY not in dumped
    hidden_fields = set(HiddenSupplier.model_fields) - {"seed"}
    assert not hidden_fields & set(NegotiationState.__annotations__)
    for f in ("capital_rate", "commit_value_rate", "budget_final_chf", "patience_rounds"):
        assert f'"{f}"' not in dumped
    assert policy.views and all(CANARY not in repr(v) for v in policy.views)


class StubbornPolicy:
    """Bietet immer dasselbe unrealistische Paket; prüft das Rundenlimit."""

    name = "stur"

    def decide(self, view):
        return TurnResult(
            AgentTurn(
                action="offer",
                message="KI-Agent der Musterhandel AG: Paket A.",
                packages=[Terms(payment_days=90, discount_pct=5.0)],
            )
        )


def test_round_limit_stops_negotiation(scenarios):
    sc = scenarios["S03"]  # Lieferant mit Geduld 6 = Rundenlimit
    r = run_one(sc, StubbornPolicy(), 1, None)
    assert r.outcome == "no_deal"
    assert r.end_reason == "round_limit"
    assert r.rounds == sc.public.mandate.max_rounds


class ViolatingPolicy:
    name = "verstoss"

    def decide(self, view):
        return TurnResult(
            AgentTurn(
                action="offer",
                message="Ich bin eine KI. Paket A.",
                packages=[Terms(payment_days=60, discount_pct=1.0, volume_commit_pct=150)],
            )
        )


def test_violations_are_counted_and_fail_the_run(scenarios):
    r = run_one(scenarios["S09"], ViolatingPolicy(), 1, None)
    assert any("volume_commit" in v for v in r.violations)
    assert not r.correct


class LateAccepter:
    """Bietet bis zum Rundenlimit gierig und nimmt danach das letzte Gegenangebot an."""

    name = "spaet"

    def decide(self, view):
        if view.accept_only and view.last_supplier_event == "counter":
            return TurnResult(
                AgentTurn(action="accept", accepted_terms=view.last_supplier_terms, message="Einverstanden.")
            )
        return TurnResult(
            AgentTurn(
                action="offer",
                message="KI-Agent der Musterhandel AG.",
                packages=[Terms(payment_days=60, discount_pct=2.0, volume_commit_pct=80)],
            )
        )


def test_counter_in_last_round_can_still_be_accepted(scenarios):
    """BPMN v2: Ein annehmbares Gegenangebot ist eine Einigung, auch in der letzten Runde."""
    r = run_one(scenarios["S03"], LateAccepter(), 1, None)
    assert r.outcome == "deal" and r.end_reason == "agent_accept"
    assert r.rounds == scenarios["S03"].public.mandate.max_rounds


class FreeAccepter:
    """Missbraucht «accept» ohne Gegenangebot als Gratis-Angebot."""

    name = "gratis"

    def decide(self, view):
        return TurnResult(
            AgentTurn(
                action="accept", accepted_terms=Terms(payment_days=45, discount_pct=0.5), message="KI: ok"
            )
        )


def test_accept_without_counter_is_no_deal_and_terminates(scenarios):
    r = run_one(scenarios["S01"], FreeAccepter(), 1, None)
    assert r.outcome == "no_deal"
    assert r.rounds <= scenarios["S01"].public.mandate.max_rounds + 1


class OfferAfterLimit(LateAccepter):
    name = "angebot-nach-limit"

    def decide(self, view):
        return TurnResult(
            AgentTurn(
                action="offer",
                message="KI-Agent der Musterhandel AG.",
                packages=[Terms(payment_days=90, discount_pct=5.0)],
            )
        )


def test_offer_after_round_limit_is_not_sent(scenarios):
    r = run_one(scenarios["S03"], OfferAfterLimit(), 1, None)
    m = scenarios["S03"].public.mandate
    assert r.end_reason == "round_limit"
    assert sum(1 for t in r.transcript if t["role"] == "agent") == m.max_rounds
