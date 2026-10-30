"""Umformulierungen der Simulator-Vorlagen (ADR 0010): Code-Prüfung, gleiche Wahrheit, andere Wörter."""

import re

from einkaufsagent import paraphrases
from einkaufsagent.domain import Terms
from einkaufsagent.eval import run_one, summarize
from einkaufsagent.extract import RuleParser
from einkaufsagent.graph_b import HybridAgent
from einkaufsagent.narrate import TemplateNarrator
from einkaufsagent.policies import RuleBasedPolicy
from einkaufsagent.supplier_sim import SupplierSimulator

NUM = re.compile(r"\d+(?:\.\d+)?")
OFFERS = [
    [Terms(payment_days=90, discount_pct=5.0)],
    [
        Terms(payment_days=60, discount_pct=2.5, volume_commit_pct=80),
        Terms(payment_days=45, discount_pct=1.0),
    ],
    [Terms(payment_days=35, discount_pct=0.0)],
]


def test_frozen_data_passes_code_check():
    assert paraphrases.validate() == []


def test_check_catches_new_or_missing_numbers():
    data = paraphrases.load()
    bad = {**data, "templates": {**data["templates"], "confirm": [*data["templates"]["confirm"]]}}
    bad["templates"]["confirm"][3] = "Einigung über 30 Tage: {terms}."
    bad["templates"]["confirm"][4] = "Gut, abgemacht."
    found = paraphrases.validate(bad)
    assert any("confirm[3]: eigene Zahl" in p for p in found)
    assert any("confirm[4]: Platzhalter" in p for p in found)


def _replies(sc, paraphrase):
    sim = SupplierSimulator(sc.hidden, sc.public.context, paraphrase=paraphrase)
    out = []
    for t, packages in enumerate(OFFERS * 2, start=1):
        r = sim.respond_to_offer(t, packages)
        out.append(r)
        if r.event == "counter":
            out.append(sim.respond_to_acceptance(t, r.terms))
    return out


def test_same_events_and_numbers_different_words(scenarios):
    changed = 0
    for sc in scenarios.values():
        orig, para = _replies(sc, False), _replies(sc, True)
        assert [(r.event, r.terms) for r in orig] == [(r.event, r.terms) for r in para], sc.id
        for o, p in zip(orig, para, strict=True):
            assert sorted(NUM.findall(o.text)) == sorted(NUM.findall(p.text)), (sc.id, o.text, p.text)
            changed += o.text != p.text
        assert _replies(sc, True)[0].text == para[0].text, "nicht reproduzierbar"
    assert changed > 0


def test_rule_parser_extracts_originals_but_not_paraphrases(scenarios):
    """Die Regex kennt nur den Originaltext; genau dort soll sich der Nutzen des LLM-Parsers zeigen."""
    agent = HybridAgent(TemplateNarrator(), RuleParser(), name="regelbasiert")
    orig = summarize([run_one(sc, agent, 1, None) for sc in scenarios.values()], 1)
    para = summarize([run_one(sc, agent, 1, None, paraphrase=True) for sc in scenarios.values()], 1)
    assert orig["extraktion_korrekt"] == 1.0 and orig["erfolgsquote"] == 1.0
    assert para["extraktion_korrekt"] < 1.0


def test_missed_acceptance_uses_simulator_terms_not_text(scenarios):
    """Variante (a) mit Umformulierungen: verpasste Annahmen hängen nicht mehr am Wortlaut."""
    rule = RuleBasedPolicy()
    a = [run_one(sc, rule, 1, None).missed_acceptance for sc in scenarios.values()]
    b = [run_one(sc, rule, 1, None, paraphrase=True).missed_acceptance for sc in scenarios.values()]
    assert a == b
