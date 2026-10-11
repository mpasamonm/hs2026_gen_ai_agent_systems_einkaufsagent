from einkaufsagent.domain import Terms
from einkaufsagent.supplier_sim import SupplierSimulator, analyse_zopa


def test_dev_scenarios_with_consistent_labels(scenarios):
    assert len(scenarios) == 11
    for sc in scenarios.values():
        z = analyse_zopa(sc.public.context, sc.public.mandate, sc.hidden)
        if sc.expected_outcome == "deal":
            assert z.exists, sc.id
        if sc.expected_outcome == "no_deal":
            assert not z.exists, sc.id
        if sc.expected_outcome == "escalate":
            assert sc.hidden.opening_demand or sc.hidden.condition, sc.id
            assert sc.escalation_deadline_round is not None, sc.id


def test_volume_commitment_is_required_somewhere(scenarios):
    """Mindestens ein Deal-Szenario ist ohne Mengenzusage nicht lösbar (prüft integratives Verhandeln)."""
    needs_commit = []
    for sc in scenarios.values():
        if sc.expected_outcome != "deal":
            continue
        m = sc.public.mandate.model_copy(update={"max_volume_commit_pct": 0})
        if not analyse_zopa(sc.public.context, m, sc.hidden).exists:
            needs_commit.append(sc.id)
    assert needs_commit, "kein Szenario erzwingt eine Mengenzusage"


def test_budget_grows_monotonically(scenarios):
    for sc in scenarios.values():
        sim = SupplierSimulator(sc.hidden, sc.public.context)
        budgets = [sim.budget(t) for t in range(1, sc.hidden.patience_rounds + 1)]
        assert budgets == sorted(budgets), sc.id
        assert abs(budgets[-1] - sc.hidden.budget_final_chf) < 1e-6


def test_counter_offer_fits_budget(scenarios):
    sc = scenarios["S02"]
    sim = SupplierSimulator(sc.hidden, sc.public.context)
    greedy = Terms(payment_days=90, discount_pct=5.0, volume_commit_pct=0)
    assert (
        sim.respond_to_offer(1, [greedy]).event == "reject"
    )  # Budget in Runde 1 zu klein für ein Gegenangebot
    r = sim.respond_to_offer(3, [greedy])
    assert r.event == "counter"
    assert sim.net_cost(r.terms) <= sim.budget(3) + 1e-6
    assert sim.respond_to_acceptance(4, r.terms).event == "confirm"


def test_final_reject_after_patience(scenarios):
    sc = scenarios["S07"]
    sim = SupplierSimulator(sc.hidden, sc.public.context)
    greedy = Terms(payment_days=90, discount_pct=5.0)
    assert sim.respond_to_offer(sc.hidden.patience_rounds + 1, [greedy]).event == "reject_final"


def test_demand_and_injection(scenarios):
    s8 = scenarios["S08"]
    sim = SupplierSimulator(s8.hidden, s8.public.context)
    assert sim.respond_to_offer(1, [Terms(payment_days=45, discount_pct=0.5)]).event == "demand"
    s9 = scenarios["S09"]
    sim = SupplierSimulator(s9.hidden, s9.public.context)
    greedy = [Terms(payment_days=90, discount_pct=5.0)]
    assert "150 %" not in sim.respond_to_offer(1, greedy).text
    assert "150 %" in sim.respond_to_offer(2, greedy).text


def test_condition_turns_acceptance_into_conditional_counter(scenarios):
    """S11: Auch ein annehmbares Paket bekommt nur ein Gegenangebot unter der Bedingung (ADR 0008)."""
    sc = scenarios["S11"]
    sim = SupplierSimulator(sc.hidden, sc.public.context)
    cheap = Terms(payment_days=35, discount_pct=0.0)
    r = sim.respond_to_offer(1, [cheap])
    assert r.event == "counter" and r.terms == cheap
    assert sc.hidden.condition.text in r.text
