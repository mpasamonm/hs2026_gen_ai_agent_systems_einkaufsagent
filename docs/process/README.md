# Soll-Prozess (BPMN 2.0)

Gültig ist seit dem 12.11.2026 `einkaufsagent-prozess_v5.bpmn` im Root (ADR 0002, 0007–0009, 0014, 0015 mit Nachtrag
12.11.). Gegenüber `_v4`: dritter Entscheid der Einkäuferin «freigeben» (Bedingung des Lieferanten annehmen). Der Code bucht
die Konditionen, denen der Lieferant unter der Bedingung zugestimmt hat (gewähltes Paket, unsere angenommene Annahme oder
ein Gegenangebot im Mandat), nur bei einer Bedingung auf einer Grösse, die das Mandat nicht regelt, ohne weitere Forderung
oder Bedingung; das Mandat ändert sich nicht. «abbrechen» und «freigeben» laufen über ein Join-Gateway zu «Ergebnis und
Protokoll erfassen». Lieferant in der Demo: Web-UI (ADR 0016). `einkaufsagent-prozess.bpmn` und `.png` in diesem Ordner sind
byte-gleiche Kopien davon.

`_v4` (09.11.2026) brachte gegenüber `_v3`: Gegenangebot annehmen als eigener Pfad (Annahme aus der Vorlage,
Bestätigung abwarten, extrahieren, bewerten); Fehlerpfade als Fehler-Grenzereignisse («Angebot formulieren» scheitert →
Standardtext, «Antwort extrahieren» scheitert → Eskalation); Zurückweisungen als Vorlagensatz aus «Antwort bewerten» (Annotation); «Eskalation aufbereiten» als Code
statt LLM (ADR 0014); «Eskalation entscheiden» mit `interrupt()` und den zwei Entscheiden der Einkäuferin; «Ergebnis und
Protokoll erfassen» auf jedem Ausgang; Konfidenz < 0,7 nur als Annotation (Spike gestrichen).

Abgelöste Fassungen im Root: `_v4` (zwei Entscheide der Einkäuferin, ADR 0015), `_v3` (ohne MCP und RAG, ADR 0009),
`_v2` (schlanke Fassung, ADR 0007, 0008) und `_v1` (inhaltlich «Prozess v2» aus ADR 0002, Namensfalle siehe CLAUDE.md §8).
Jede weitere Änderung kommt als neue Datei `_v6` in den Root.

Die Dateien öffnen in [bpmn.io](https://demo.bpmn.io). Farben: orange = LLM, blau = Code, grün = Mensch.

## Prüfen und neu rendern

```bash
cd docs/process
npm install                                              # bpmn-moddle 10.3.1, bpmnlint 11.14.0, bpmn-js 18.31.0
python3 gen_bpmn_v5.py ../../einkaufsagent-prozess_v5.bpmn   # Layout und Inhalt sind im Generator definiert
node validate.mjs ../../einkaufsagent-prozess_v5.bpmn        # bpmn-moddle-Warnungen + bpmnlint «recommended»
uv run --no-project --with playwright==1.63.0 python -m playwright install chromium
uv run --no-project --with playwright==1.63.0 python render.py \
  ../../einkaufsagent-prozess_v5.bpmn ../../einkaufsagent-prozess_v5.png
cp ../../einkaufsagent-prozess_v5.bpmn einkaufsagent-prozess.bpmn
cp ../../einkaufsagent-prozess_v5.png einkaufsagent-prozess.png
```

Chromium braucht unter WSL/Ubuntu 24.04 `libasound2t64` (`sudo apt install libasound2t64`). Ohne sudo:
`apt-get download libasound2t64`, mit `dpkg -x` entpacken und den Ordner per `LD_LIBRARY_PATH` setzen.
`gen_bpmn.py` bis `gen_bpmn_v4.py` erzeugen die abgelösten Fassungen `_v1` bis `_v4`.

Stand 12.11.2026: bpmn-moddle 0 Warnungen, bpmnlint 0 Befunde, bpmn-js-Import 0 Warnungen; der Generator erzeugt
`_v5` byte-gleich.

## Mapping BPMN → LangGraph

| BPMN-Element | LangGraph | Typ | Stand |
| --- | --- | --- | --- |
| Start, «Mandat festlegen» | Graph-Input `mandate` (Pydantic-validiert) | Mensch | gebaut |
| «Kontext laden» | Node `load_context`: Stammdaten und heutige Konditionen aus dem ERP-Adapter (`erp.py`, SQLite, ADR 0009, 0015). Frühere Protokolle zeigt der Runner an, der Graph nutzt sie nicht | Code | gebaut 09.11. |
| Join vor «Pakete berechnen» | implizit: mehrere Edges auf `offer_engine` | – | gebaut |
| «Pakete berechnen (Code)» | Node `offer_engine` (Pakete und Konzessionskurve aus `RuleBasedPolicy`); nach «weiterverhandeln» in der letzten Runde: Rundenlimit | Code | gebaut 19.10. |
| «Angebot formulieren (LLM)», Grenzereignis «LLM-Fehler: kein Text» | Node `narrate` (`narrate.py`); sieht nur Pakete und Runde. Scheitert er nach den Retries, setzt er `template_reason`, und `mandate_guard` schickt zum Standardtext | LLM | gebaut 19.10. |
| «Nachricht prüfen (Code)», «Mandat eingehalten?» | Node `mandate_guard` + Conditional Edge (`hybrid.check_message`) | Code | gebaut 19.10. |
| «Standardtext verwenden (Code)» | Node `template_message` | Code | gebaut 19.10. |
| «Angebot senden, Antwort abwarten» | Node `send_and_wait` (`pending.kind = offer`); vor die Nachricht kommen Zurückweisungen aus Vorlagen (`prefix`). Eval: Simulator; Demo und Live-Runden: `HumanSupplier` (`live.py`), sieht nur den Text | Code | gebaut, Mensch 09.11. |
| «Annahme senden, Bestätigung abwarten» | derselbe Node `send_and_wait` mit `pending.kind = accept`, Text aus `hybrid.accept_text` | Code | gebaut 19.10. |
| «Antwort extrahieren (LLM)», Grenzereignis «LLM-Fehler: nicht auswertbar» | Node `parse_response` (`extract.py`): Antworttyp, Paket, Gegenangebot, Aussagen mit Typ und Grösse; Einkaufsrichtlinie (Auszug) im Prompt. Scheitert er, ist `parsed` leer und `assess_response` eskaliert (ADR 0008, Regel 3); die Zeichnung kürzt diesen Weg ab | LLM | gebaut 19.10. |
| «Antwort bewerten (Code)», «Bewertung?», «Nächster Schritt?» | Node `assess_response` + Conditional Edge `after_assess` (`hybrid.assess_reply`): Einigung, Eskalation nur nach ADR 0008, Gegenangebot annehmen (AC_next), neue Runde oder kein Deal; Zurückweisungen als Vorlagensätze; Grössen, die die Einkäuferin abgelehnt hat, werden nicht erneut eskaliert | Code | gebaut 19.10., ergänzt 09.11. |
| «Eskalation aufbereiten (Code)» | Node `escalate`: Vorlage `hybrid.escalation_brief` (Grund, Zitat, Verlauf, letzte Antwort), Protokoll mit Status «escalated», Zwischenbescheid an den Lieferanten; berechnet ohne LLM, welche Konditionen die Einkäuferin freigeben könnte (oder keine), und bietet «freigeben» nur dann an (ADR 0014, 0015) | Code | gebaut 09.11., Freigabe 12.11. |
| «Eskalation entscheiden», «Entscheid der Einkäuferin?», Join danach | Node `ask_buyer` mit nur `interrupt(payload)`; Runner (Web-UI oder Terminal): `Command(resume={"decision", "note"})` mit derselben `thread_id`; Conditional Edge `after_buyer`: weiterverhandeln → `offer_engine`; freigeben → `record_outcome` mit den freigebbaren Konditionen als Abschluss; abbrechen → `record_outcome`. Ein «freigeben» ohne freigebbare Konditionen gilt als «abbrechen». Die Eval hält am Interrupt an | Mensch | gebaut 09.11., Freigabe 12.11. |
| «Ergebnis und Protokoll erfassen» | Node `record_outcome` über `ErpAdapter.record_outcome`, auf allen Ausgängen, idempotent pro Verhandlung; bucht bei Deal die Konditionen; Metrik `korrekt_gebucht` | Code | gebaut 09.11. |
| «Ergebnis mitteilen» | Node `notify_supplier` (Vorlage) | Code | gebaut 19.10. |
| «Ergebnis?», Endereignisse | `END`; Ergebnis steht in `state.outcome` (`deal`, auch mit `buyer_decision = freigeben`; `no_deal`; `escalated` mit `buyer_decision = abbrechen`) | – | gebaut |

Variante (b) steht in `src/einkaufsagent/graph_b.py`. Variante (a) (`src/einkaufsagent/graph_a.py`) bündelt «Pakete»,
«Formulieren», «Extrahieren» und «Bewerten» in einem LLM-Node `negotiate`; das ist die Baseline der Ablation. ERP-Adapter,
Eskalation mit `interrupt()` und Mensch als Lieferant gibt es nur in (b) (ADR 0015).

## Fehlerbehandlung (gebaut 19.10., gezeichnet seit `_v4`)

Retries mit Backoff übernimmt der Client (`max_retries=2`, Timeout 90 s). Scheitert ein LLM-Schritt danach, greifen die
Fail-safes: Ohne Text von `narrate` geht der Standardtext hinaus; ohne auswertbare Antwort von `parse_response` wird
eskaliert (ADR 0008, Regel 3). Fällt das LLM aus, verhandelt der Agent also mit Vorlagen weiter und übergibt der
Einkäuferin, was er nicht lesen kann. Kein Fehler beendet den Graphen stillschweigend (SW6 Folie 27).
