"""Eval-Metriken «Angebote ohne Konditionen» und «verpasste Annahmen» (ADR 0006)."""

from einkaufsagent.domain import Terms
from einkaufsagent.eval import parse_counter, run_one, summarize
from einkaufsagent.policies import AgentTurn, RuleBasedPolicy, TurnResult
from einkaufsagent.supplier_sim import SupplierSimulator


def test_counter_template_is_parsed(scenarios):
    """Bricht, wenn sich die Textvorlage des Simulators ändert; dann COUNTER_TEXT nachführen."""
    sc = scenarios["S02"]
    sim = SupplierSimulator(sc.hidden, sc.public.context)
    counter = sim.respond_to_offer(1, [Terms(payment_days=90, discount_pct=5.0, volume_commit_pct=80)])
    assert counter.event == "counter" and parse_counter(counter.text) == counter.terms
    decline = sim.respond_to_acceptance(1, Terms(payment_days=30, discount_pct=0.0))
    assert decline.event == "decline" and parse_counter(decline.text) == decline.terms


class WalkAfterCounter:
    """Bietet ein Paket ohne Zahlen im Text und geht beim ersten Gegenangebot."""

    name = "geht"

    def decide(self, view):
        if view.last_supplier_event == "counter":
            return TurnResult(AgentTurn(action="walk_away", message="Dann belassen wir es."))
        return TurnResult(
            AgentTurn(
                action="offer",
                message="KI-Agent der Musterhandel AG: folgendes Paket.",
                packages=[Terms(payment_days=60, discount_pct=2.0, volume_commit_pct=80)],
            )
        )


def test_walking_away_from_acceptable_counter_is_a_missed_acceptance(scenarios):
    r = run_one(scenarios["S02"], WalkAfterCounter(), 1, None)
    assert r.outcome == "no_deal" and r.missed_acceptance
    assert r.offers_sent == 1 and r.offers_without_terms == 1


def test_rejecting_counter_below_walk_away_is_not_missed(scenarios):
    r = run_one(scenarios["S03"], WalkAfterCounter(), 1, None)  # Gegenangebot unter dem Mindestnutzen
    assert r.outcome == "no_deal" and not r.missed_acceptance


def test_rule_reference_has_terms_in_every_offer_and_no_missed_acceptance(scenarios):
    records = [run_one(sc, RuleBasedPolicy(), 1, None) for sc in scenarios.values()]
    s = summarize(records, 1)
    assert s["angebote_ohne_konditionen"] == 0.0
    assert s["verpasste_annahmen"] == 0
    s = summarize([*records, run_one(scenarios["S02"], WalkAfterCounter(), 1, None)], 1)
    assert s["verpasste_annahmen"] == 1 and s["angebote_ohne_konditionen"] > 0
