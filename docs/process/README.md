# Soll-Prozess v2 (BPMN 2.0)

`einkaufsagent-prozess.bpmn` öffnet in [bpmn.io](https://demo.bpmn.io). `einkaufsagent-prozess.png` ist der
Render mit bpmn-js. Farben: orange = LLM, blau = Code, grün = Mensch. Entscheide in ADR 0002.

## Prüfen und neu rendern

```bash
cd docs/process
npm install bpmn-moddle@10.3.1 bpmnlint@11.14.0 bpmn-js@18.31.0
python3 gen_bpmn.py einkaufsagent-prozess.bpmn     # Layout und Inhalt sind im Generator definiert
node validate.mjs einkaufsagent-prozess.bpmn       # bpmn-moddle-Warnungen + bpmnlint «recommended»
python3 render.py einkaufsagent-prozess.bpmn einkaufsagent-prozess.png   # braucht playwright + Chromium
```

Stand 05.10.2026: bpmn-moddle 0 Warnungen, bpmnlint 0 Befunde, bpmn-js-Import 0 Warnungen.
Änderungen in bpmn.io direkt sind möglich; dann den Generator nicht mehr verwenden.

## Mapping BPMN → LangGraph

| BPMN-Element | LangGraph | Typ | Ab |
| --- | --- | --- | --- |
| Start, «Mandat festlegen» | Graph-Input `mandate` (Pydantic-validiert) | Mensch | KW42 |
| «Kontext laden (ERP via MCP)» | Node `load_context` | Code | KW42 Stub, KW43 MCP |
| «Strategie wählen (LLM)» | Node `plan` | LLM | KW43 |
| Join vor «Pakete berechnen» | implizit: mehrere Edges auf `offer_engine` | – | KW43 |
| «Pakete berechnen (Code)» | Node `offer_engine` | Code | KW43 |
| «Angebot formulieren (LLM)» | Node `narrate` | LLM | KW43 |
| «Nachricht prüfen (Code)», «Mandat eingehalten?» | Node `mandate_guard` + Conditional Edge | Code | KW43 |
| «Standardtext verwenden (Code)» | Node `template_message` | Code | KW43 |
| «Angebot senden», «Antwort empfangen» | Node `send_and_wait` (Simulator; real: Kanal + `interrupt()`) | Code | KW42 |
| Timer «48 h ohne Antwort» | Scheduler ausserhalb des Graphen, Resume per `Command` | – | nicht im MVP |
| «Antwort extrahieren (LLM)» | Node `parse_response` (strukturierte Ausgabe) | LLM | KW43 |
| «Antwort bewerten (Code)», «Bewertung?» | Node `assess_response` + Conditional Edge, 3 Ziele | Code | KW43 |
| «Weiterverhandeln?» | Conditional Edge (Runde < max. Runden, Paket offen, Lieferant verhandelt weiter) | Code | KW42 ohne «Paket offen» |
| «Eskalation aufbereiten (LLM)», «Eskalation entscheiden» | Node `escalate`: LLM-Zusammenfassung, dann `interrupt()` | LLM + Mensch | KW46 |
| «Freigabe zum Weiterverhandeln?» | Conditional Edge nach `Command(resume=...)` | Mensch | KW46 |
| «Konditionen im ERP erfassen (MCP)» | Node `book_deal` | Code | KW43 |
| «Ergebnis mitteilen» | Node `notify_supplier` | Code | KW43 |
| «Protokoll und Gedächtnis aktualisieren» | Node `update_memory` (LangGraph Store) | Code (+ LLM-Zusammenfassung) | KW46 |
| «Ergebnis?», Endereignisse | `END`; Ergebnis steht in `state.outcome` | – | KW42 |

Variante (a) (`src/einkaufsagent/graph_a.py`) bündelt «Strategie», «Pakete», «Formulieren», «Extrahieren» und
«Bewerten» in einem LLM-Node `negotiate`; das ist die Baseline der Ablation.
