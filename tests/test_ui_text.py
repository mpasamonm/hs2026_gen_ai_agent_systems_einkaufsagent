"""Texte der Web-UI (ADR 0016, Nachtrag 10.11.): nur Darstellung, nur öffentliche Daten des Szenarios."""

from einkaufsagent.erp import ErpAdapter
from einkaufsagent.extract import RuleParser
from einkaufsagent.graph_b import HybridAgent, build_graph
from einkaufsagent.narrate import TemplateNarrator
from einkaufsagent.ui_text import (
    NODE_DE,
    REPORT_HELP,
    explain_step,
    history_lines,
    invitation_text,
    mandate_lines,
    node_label,
    report_help,
    violations_de,
)


def test_every_graph_node_has_a_bpmn_name():
    agent = HybridAgent(TemplateNarrator(), RuleParser(), name="regelbasiert")
    graph = build_graph(agent, supplier=None, erp=ErpAdapter(":memory:"))
    nodes = set(graph.get_graph().nodes) - {"__start__", "__end__"}
    assert nodes <= set(NODE_DE), nodes - set(NODE_DE)
    assert node_label("ERP-Gedächtnis") == "ERP-Gedächtnis"  # unbekannte Namen bleiben


def test_parse_fields_in_german_with_codes():
    text = "accept · Paket B · condition/contract_term «nur mit 24 Monaten Laufzeit»"
    assert explain_step("parse_response", text) == (
        "nimmt an (accept) · Paket B · Bedingung zu Vertragslaufzeit (condition/contract_term) "
        "«nur mit 24 Monaten Laufzeit»"
    )
    assert explain_step("parse_response", "(ohne LLM) reject").startswith("(ohne LLM) lehnt ab (reject)")
    assert explain_step("parse_response", "nicht auswertbar (Timeout)") == "nicht auswertbar (Timeout)"
    assert explain_step("assess_response", "weiterverhandeln") == "weiterverhandeln"


def test_mandate_in_words_only_from_public_part(scenarios):
    sc = scenarios["S04"]
    canary = "CANARY-ui-text"
    sc = sc.model_copy(update={"hidden": sc.hidden.model_copy(update={"canary": canary})})
    lines = dict(mandate_lines(sc.public))
    assert "CHF 2'000" in lines["Mindestnutzen"]
    assert "Mengenzusage höchstens 80 %" in lines["Grenzen"] and "nicht unter heute" in lines["Grenzen"]
    assert "keine Preiserhöhung" in lines["Grenzen"] and "höchstens 6 Runden" in lines["Grenzen"]
    assert "90 Tage" not in lines["Grenzen"]  # Obergrenzen prüft check_terms nicht (Red-Teaming R6)
    assert "höchstens 90 Tage" in lines["Richtlinie"] and "nur für unsere Pakete" in lines["Richtlinie"]
    assert "1 % Rabatt CHF 2'500" in lines["Bewertung"]
    assert canary not in str(lines)


def test_report_help_and_violations():
    for start in REPORT_HELP:
        assert report_help(f"{start}: …")
    assert report_help("anderes") is None
    assert violations_de(["R2:volume_commit", "deal:not_agreed"]) == [
        "R2: Mengenzusage über dem Maximum (volume_commit)",
        "deal: gebucht ohne Zustimmung des Lieferanten (not_agreed)",
    ]


def test_invitation_names_subject_but_nothing_from_mandate_or_hidden(scenarios):
    sc = scenarios["S04"]
    canary = "CANARY-invitation"
    sc = sc.model_copy(update={"hidden": sc.hidden.model_copy(update={"canary": canary})})
    text = invitation_text(sc.public)
    assert sc.public.context.supplier_name in text and "nächsten 12 Monate" in text
    assert "30 Tage Zahlungsziel, 0 % Rabatt, keine Mengenzusage" in text and "CHF 250'000" in text
    assert "eigenen Vorschlag" in text and "verbindlich abnehmen" in text
    m = sc.public.mandate  # Ziel, Grenzen und Mindestnutzen bleiben verdeckt
    for secret in (f"{m.target_payment_days} Tage", f"{m.payment_days_max} Tage", "CHF 2'000", canary):
        assert secret not in text


def test_history_in_words_without_date_or_terms():
    items = [
        {"recorded_at": "2026-11-12T10:00:00", "status": "deal", "rounds": 1, "choice": "–"},
        {"recorded_at": "2026-11-12T11:00:00", "status": "escalated", "rounds": 3, "choice": "B"},
    ]
    assert history_lines(2, items) == [
        "2 frühere Verhandlungen mit diesem Lieferanten:",
        "· Abschluss nach 1 Runde",
        "· an die Einkäuferin eskaliert nach 3 Runden, Paket B gewählt",
    ]
    assert history_lines(0, []) == ["keine früheren Verhandlungen mit diesem Lieferanten"]
