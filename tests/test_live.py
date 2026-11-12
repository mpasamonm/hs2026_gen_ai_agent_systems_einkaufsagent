"""Runner im Terminal (ADR 0015): Einkäuferin und Mensch als Lieferant mit Skript-Eingaben, ohne API-Key."""

from einkaufsagent.erp import ErpAdapter
from einkaufsagent.extract import ParsedReply, ParseResult, RuleParser
from einkaufsagent.graph_b import HybridAgent
from einkaufsagent.live import HumanSupplier, run_live
from einkaufsagent.narrate import TemplateNarrator


def scripted(*answers):
    it = iter(answers)
    prompts: list[str] = []

    def ask(prompt: str) -> str:
        prompts.append(prompt)
        return next(it)

    return ask, prompts


def offline_agent(parser=None) -> HybridAgent:
    return HybridAgent(TemplateNarrator(), parser or RuleParser(), name="regelbasiert")


def test_live_buyer_aborts_escalation(scenarios):
    sc = scenarios["S11"]
    ask, prompts = scripted("a", "Laufzeit nicht gewünscht")
    lines: list[str] = []
    erp = ErpAdapter()
    final = run_live(sc, offline_agent(), erp, ask=ask, out=lines.append)
    assert final["outcome"] == "escalated" and final["buyer_decision"] == "abbrechen"
    assert any("Eskalation an die Einkäuferin" in x for x in lines)
    assert any("Entscheid der Einkäuferin: abbrechen (Laufzeit nicht gewünscht)" in x for x in lines)
    assert len(prompts) == 2


def test_live_buyer_approves_condition(scenarios):
    """ADR 0015, Nachtrag 12.11.: «f» erscheint nur mit freigebbaren Konditionen und bucht den Abschluss."""
    sc = scenarios["S11"]
    ask, prompts = scripted("f", "24 Monate ok")
    lines: list[str] = []
    erp = ErpAdapter()
    final = run_live(sc, offline_agent(), erp, ask=ask, out=lines.append)
    assert final["outcome"] == "deal" and final["buyer_decision"] == "freigeben"
    assert "f = freigeben" in prompts[0] and any("Freigeben heisst: Abschluss zu" in x for x in lines)
    assert any("Ergebnis: deal (buyer_approved)" in x for x in lines)
    assert any("Verstösse: keine" in x for x in lines)  # die Zusage unter Bedingung gilt als Zustimmung
    assert erp.current_terms(sc.public.context.supplier_id).short() in " ".join(lines)


def test_live_keeps_protocols_across_runs_in_the_same_erp(scenarios):
    sc = scenarios["S02"]
    erp = ErpAdapter()
    for _ in range(2):
        lines: list[str] = []
        run_live(sc, offline_agent(), erp, ask=scripted()[0], out=lines.append)
    assert any("1 frühere Verhandlung" in x for x in lines)
    assert len(erp.protocols(sc.public.context.supplier_id)) == 2


class AcceptsPackageB:
    """Steht für das LLM: liest die Antwort des Menschen als Annahme von Paket B."""

    name = "fake-llm"

    def parse(self, text, sent):
        return ParseResult(parsed=ParsedReply(reply_type="accept", chosen_package="B"))


def test_human_supplier_sees_only_text_and_confirms_deal(scenarios):
    sc = scenarios["S02"]
    ask, prompts = scripted("Paket B nehmen wir gerne.", "j")
    lines: list[str] = []
    erp = ErpAdapter()
    final = run_live(sc, offline_agent(AcceptsPackageB()), erp, human=True, ask=ask, out=lines.append)
    assert final["outcome"] == "deal" and final["transcript"][1] == {
        "role": "supplier",
        "round": 1,
        "event": "human",
        "text": "Paket B nehmen wir gerne.",
    }
    assert erp.current_terms(sc.public.context.supplier_id).model_dump() == final["deal_terms"]
    assert any("Verstösse: keine" in x for x in lines) and any("Stimmen Sie" in p for p in prompts)


def test_human_supplier_shows_text_not_packages():
    lines: list[str] = []
    h = HumanSupplier(ask=scripted("", "Nein danke.")[0], out=lines.append)  # leere Eingabe wird wiederholt
    r = h.respond_to_offer(1, [], "Paket A: Zahlungsziel 60 Tage.")
    assert r.event == "human" and r.text == "Nein danke."
    assert lines == ["\n  Agent → Lieferant (Runde 1): Paket A: Zahlungsziel 60 Tage."]
