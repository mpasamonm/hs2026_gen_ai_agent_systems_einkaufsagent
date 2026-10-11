# Soll-Prozess (BPMN 2.0)

Gültig ist seit dem 11.10.2026 die schlanke Fassung `einkaufsagent-prozess_v2.bpmn` im Root (ADR 0002, 0007,
0008). `einkaufsagent-prozess.bpmn` und `.png` in diesem Ordner sind byte-gleiche Kopien davon.
`einkaufsagent-prozess_v1.bpmn` im Root ist die abgelöste Fassung «Prozess v2» (Namensfalle, siehe CLAUDE.md §8).
Jede weitere Änderung kommt als neue Datei `_v3` in den Root.

Die Dateien öffnen in [bpmn.io](https://demo.bpmn.io). Farben: orange = LLM, blau = Code, grün = Mensch.

## Prüfen und neu rendern

```bash
cd docs/process
npm install                                              # bpmn-moddle 10.3.1, bpmnlint 11.14.0, bpmn-js 18.31.0
python3 gen_bpmn_v2.py ../../einkaufsagent-prozess_v2.bpmn   # Layout und Inhalt sind im Generator definiert
node validate.mjs ../../einkaufsagent-prozess_v2.bpmn        # bpmn-moddle-Warnungen + bpmnlint «recommended»
uv run --no-project --with playwright==1.63.0 python -m playwright install chromium
uv run --no-project --with playwright==1.63.0 python render.py \
  ../../einkaufsagent-prozess_v2.bpmn ../../einkaufsagent-prozess_v2.png
cp ../../einkaufsagent-prozess_v2.bpmn einkaufsagent-prozess.bpmn
cp ../../einkaufsagent-prozess_v2.png einkaufsagent-prozess.png
```

Chromium braucht unter WSL/Ubuntu 24.04 `libasound2t64` (`sudo apt install libasound2t64`). Ohne sudo:
`apt-get download libasound2t64`, mit `dpkg -x` entpacken und den Ordner per `LD_LIBRARY_PATH` setzen.
`gen_bpmn.py` erzeugt die abgelöste Fassung `_v1`.

Stand 11.10.2026: bpmn-moddle 0 Warnungen, bpmnlint 0 Befunde, bpmn-js-Import 0 Warnungen.

## Mapping BPMN → LangGraph

| BPMN-Element | LangGraph | Typ | Ab |
| --- | --- | --- | --- |
| Start, «Mandat festlegen» | Graph-Input `mandate` (Pydantic-validiert) | Mensch | KW42 |
| «Kontext laden (MCP)» | Node `load_context`, MCP-Tool `get_supplier_context` (ADR 0005) | Code | KW42 Stub, KW43 MCP |
| Join vor «Pakete berechnen» | implizit: mehrere Edges auf `offer_engine` | – | KW43 |
| «Pakete berechnen (Code)» | Node `offer_engine`; Variante (c): Startpunkt aus der Historie | Code | KW43 |
| «Angebot formulieren (LLM)» | Node `narrate`, ohne RAG (ADR 0007) | LLM | KW43 |
| «Nachricht prüfen (Code)», «Mandat eingehalten?» | Node `mandate_guard` + Conditional Edge | Code | KW43 |
| «Standardtext verwenden (Code)» | Node `template_message` | Code | KW43 |
| «Angebot senden, Antwort abwarten» | Node `send_and_wait` (Simulator; real: Kanal + `interrupt()`) | Code | KW42 |
| «Antwort extrahieren (LLM)» | Node `parse_response`: Paket, Gegenangebot, Aussagen mit Typ; ab KW44 mit Regel aus der Einkaufsrichtlinie (Retrieval fest im Node) | LLM | KW43, RAG KW44 |
| «Antwort bewerten (Code)», «Bewertung?» | Node `assess_response` + Conditional Edge: Einigung (inkl. AC_next), Eskalation nur nach ADR 0008, sonst weiter | Code | KW43 |
| «Weiterverhandeln?» | Conditional Edge (Runde < max. Runden, Paket offen, keine endgültige Absage) | Code | KW42 ohne «Paket offen» |
| «Eskalation aufbereiten (LLM + Tools)», «Eskalation entscheiden» | Node `escalate`: LLM mit den Tools Richtlinien-Suche (RAG) und `get_negotiation_history` (MCP), dann `interrupt()` | LLM + Mensch | KW46 (RAG ab KW44) |
| «Freigabe zum Weiterverhandeln?» | Conditional Edge nach `Command(resume=...)` | Mensch | KW46 |
| «Ergebnis im ERP erfassen (MCP)» | Node `record_outcome` (MCP-Tool) auf allen Ausgängen; die Historie ist das Gedächtnis (c) | Code | KW43 |
| «Ergebnis mitteilen» | Node `notify_supplier` | Code | KW43 |
| «Ergebnis?», Endereignisse | `END`; Ergebnis steht in `state.outcome` | – | KW42 |

Variante (a) (`src/einkaufsagent/graph_a.py`) bündelt «Pakete», «Formulieren», «Extrahieren» und «Bewerten» in
einem LLM-Node `negotiate`; das ist die Baseline der Ablation.
