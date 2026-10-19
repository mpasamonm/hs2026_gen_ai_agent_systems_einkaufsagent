# Soll-Prozess (BPMN 2.0)

Gültig ist seit dem 19.10.2026 `einkaufsagent-prozess_v3.bpmn` im Root (ADR 0002, 0007, 0008, 0009):
ERP-Adapter ohne MCP, Einkaufsrichtlinie ganz im Prompt statt RAG, keine Tool-Wahl durch das LLM, Protokoll mit
Paketwahl als Gedächtnis, Mensch statt LLM-Lieferant. `einkaufsagent-prozess.bpmn` und `.png` in diesem Ordner sind
byte-gleiche Kopien davon.

Abgelöste Fassungen im Root: `_v2` (schlanke Fassung, ADR 0007, 0008) und `_v1` (inhaltlich «Prozess v2» aus
ADR 0002, Namensfalle siehe CLAUDE.md §8). Jede weitere Änderung kommt als neue Datei `_v4` in den Root; geplant ist
`_v4` in KW44 mit Fehlerpfaden und dem Ergebnis des Klassifikations-Spikes (ADR 0009, 0011).

Die Dateien öffnen in [bpmn.io](https://demo.bpmn.io). Farben: orange = LLM, blau = Code, grün = Mensch.

## Prüfen und neu rendern

```bash
cd docs/process
npm install                                              # bpmn-moddle 10.3.1, bpmnlint 11.14.0, bpmn-js 18.31.0
python3 gen_bpmn_v3.py ../../einkaufsagent-prozess_v3.bpmn   # Layout und Inhalt sind im Generator definiert
node validate.mjs ../../einkaufsagent-prozess_v3.bpmn        # bpmn-moddle-Warnungen + bpmnlint «recommended»
uv run --no-project --with playwright==1.63.0 python -m playwright install chromium
uv run --no-project --with playwright==1.63.0 python render.py \
  ../../einkaufsagent-prozess_v3.bpmn ../../einkaufsagent-prozess_v3.png
cp ../../einkaufsagent-prozess_v3.bpmn einkaufsagent-prozess.bpmn
cp ../../einkaufsagent-prozess_v3.png einkaufsagent-prozess.png
```

Chromium braucht unter WSL/Ubuntu 24.04 `libasound2t64` (`sudo apt install libasound2t64`). Ohne sudo:
`apt-get download libasound2t64`, mit `dpkg -x` entpacken und den Ordner per `LD_LIBRARY_PATH` setzen.
`gen_bpmn.py` und `gen_bpmn_v2.py` erzeugen die abgelösten Fassungen `_v1` und `_v2`.

Stand 19.10.2026: bpmn-moddle 0 Warnungen, bpmnlint 0 Befunde, bpmn-js-Import 0 Warnungen; der Generator erzeugt
`_v3` byte-gleich.

## Mapping BPMN → LangGraph

| BPMN-Element | LangGraph | Typ | Ab |
| --- | --- | --- | --- |
| Start, «Mandat festlegen» | Graph-Input `mandate` (Pydantic-validiert) | Mensch | KW42 |
| «Kontext laden» | Node `load_context`: Stammdaten, heutige Konditionen, frühere Protokolle über den ERP-Adapter (Python-Schnittstelle über SQLite, ADR 0009) | Code | KW42 JSON-Stub, KW44 ERP-Adapter |
| Join vor «Pakete berechnen» | implizit: mehrere Edges auf `offer_engine` | – | KW43 |
| «Pakete berechnen (Code)» | Node `offer_engine` (Pakete und Konzessionskurve aus `RuleBasedPolicy`); Variante (c): Startpunkt aus der Paketwahl in früheren Protokollen | Code | gebaut 19.10. |
| «Angebot formulieren (LLM)» | Node `narrate` (`narrate.py`); sieht nur die Pakete und die Runde, nie das Mandat und nie den Lieferantentext | LLM | gebaut 19.10. |
| «Nachricht prüfen (Code)», «Mandat eingehalten?» | Node `mandate_guard` + Conditional Edge (`hybrid.check_message`) | Code | gebaut 19.10. |
| «Standardtext verwenden (Code)» | Node `template_message`; auch, wenn `narrate` nach den Retries scheitert | Code | gebaut 19.10. |
| «Angebot senden, Antwort abwarten» | Node `send_and_wait`: Eval mit dem Simulator, Demo und Live-Runden mit einem Menschen im Terminal (ADR 0012) | Code | KW42, Mensch KW46 |
| «Antwort extrahieren (LLM)» | Node `parse_response` (`extract.py`): Antworttyp, Paket, Gegenangebot, Aussagen mit Typ und Grösse; Einkaufsrichtlinie (Auszug) ganz im Prompt. Austauschbar (`LLMParser`, `RuleParser`, später Entscheidungsmodell mit `confidence`, ADR 0011) | LLM | gebaut 19.10. |
| «Antwort bewerten (Code)», «Bewertung?» | Node `assess_response` + Conditional Edge (`hybrid.assess_reply`): Einigung (inkl. AC_next), Eskalation nur nach ADR 0008 und 0013 (scheitert `parse_response`, gilt die Antwort als nicht auswertbar), sonst weiter | Code | gebaut 19.10. |
| «Weiterverhandeln?» | Conditional Edge nach `assess_response` (Runde < max. Runden, keine endgültige Absage); «kein Paket offen» in `offer_engine` | Code | gebaut 19.10. |
| «Eskalation aufbereiten (LLM)», «Eskalation entscheiden» | Node `escalate`: der Code gibt Richtlinie, Verlauf und frühere Protokolle mit, das LLM fasst zusammen (ohne Tool-Wahl); dann `interrupt()` | LLM + Mensch | KW46 |
| «Freigabe zum Weiterverhandeln?» | Conditional Edge nach `Command(resume=...)` | Mensch | KW46 |
| «Ergebnis und Protokoll erfassen» | Node `record_outcome` über den ERP-Adapter, auf allen Ausgängen; Protokoll vom Code (Startpakete, Reaktion und Paketwahl, Verlauf, Ergebnis, Hinweise); die Protokolle sind das Gedächtnis (c) | Code | KW44 |
| «Ergebnis mitteilen» | Node `notify_supplier` (Vorlage) | Code | gebaut 19.10. |
| «Ergebnis?», Endereignisse | `END`; Ergebnis steht in `state.outcome` | – | KW42 |

Variante (b) steht in `src/einkaufsagent/graph_b.py`. Variante (a) (`src/einkaufsagent/graph_a.py`) bündelt «Pakete», «Formulieren», «Extrahieren» und «Bewerten» in
einem LLM-Node `negotiate`; das ist die Baseline der Ablation.

## Fehlerbehandlung (gebaut 19.10., Zeichnung in `_v4`)

Retries mit Backoff übernimmt der Client (`max_retries=2`, Timeout 90 s). Scheitert ein LLM-Schritt danach, greifen die
bestehenden Fail-safes: Ohne Text von `narrate` geht der Standardtext hinaus; ohne auswertbare Antwort von
`parse_response` wird eskaliert (ADR 0008, Regel 3). Fällt das LLM aus, verhandelt der Agent also mit Vorlagen weiter
und übergibt der Einkäuferin, was er nicht lesen kann. Kein Fehler beendet den Graphen stillschweigend (SW6 Folie 27).
