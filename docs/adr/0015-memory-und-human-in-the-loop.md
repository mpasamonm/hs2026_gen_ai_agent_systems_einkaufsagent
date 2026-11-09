# ADR 0015 – Memory und Human-in-the-loop

- **Status:** angenommen am 09.11.2026; gebaut am 09.11.2026 (Bau 1, ADR 0014; Nachtrag unten)
- **Datum:** 09.11.2026
- **Berührt:** ADR 0008 (Eskalationsregel), ADR 0009 (ERP-Adapter, Protokoll, Mensch als Lieferant), ADR 0012 (Demo),
  ADR 0014 (Umfang)
- **Quellen:** SW8 Folien 6, 7, 9–11, 15, 17, 19–21, 24, 26, 30; langgraph 1.2.12

## Kontext

Wochenauftrag KW46: «Memory festlegen». SW8 unterscheidet Kurzzeitgedächtnis (State eines Threads, gesichert vom
Checkpointer) und Langzeitgedächtnis über Threads hinweg (Store, Folien 7 und 15) und zeigt Human-in-the-loop mit
`interrupt()` und `Command(resume=…)` (Folien 19–21). Der Auftrag auf SW8 Folie 17 («Fügt eurer Lösung
Checkpointer/InMemorySaver hinzu») ist erfüllt: Beide Graphen kompilieren mit `InMemorySaver`.

Offen sind drei Fragen: Wo liegt das Langzeitgedächtnis, wie wartet der Graph auf die Einkäuferin, und wie kommt ein
Mensch als Lieferant in den Graphen? Die trennende Achse ist **Persistenz und Nähe zum Vokabular der Folien gegen Aufwand
und einen einzigen Speicher**.

**Widerspruch Folie ↔ Doku:** SW8 Folie 19 sagt, der Graph «läuft an derselben Stelle weiter». Laut LangGraph-Doku
startet beim Fortsetzen der ganze Node neu; Code vor `interrupt()` läuft zweimal. Gebaut wird nach der Doku.

## Entscheid

| Punkt | Entscheid | Grund |
| --- | --- | --- |
| Kurzzeitgedächtnis | Graph-State mit `InMemorySaver`, ein Thread (`thread_id`) pro Verhandlung | schon gebaut; eine Verhandlung dauert in Demo und Eval Minuten |
| Langzeitgedächtnis | Protokoll als eigene Tabelle im ERP-Adapter über SQLite (ADR 0009): Lieferant, Startpakete, Reaktion und Paketwahl pro Runde, Ergebnis, Konditionen, Hinweise. Geschrieben vom Code auf jedem Ausgang | ein einziger Speicher für Buchung und Gedächtnis; nur typisierte Felder aus dem Code (OWASP LLM05, Agentic ASI06); abfragbar pro Lieferant mit SQL |
| Eskalation | Node `escalate` (Code: Vorlage mit Verlauf, Grund und Forderung) → Node `ask_buyer`, der nur `interrupt(payload)` enthält → Runner im Terminal setzt mit `Command(resume=…)` und derselben `thread_id` fort | Der Node startet beim Fortsetzen neu; deshalb steht nichts mit Nebenwirkung vor `interrupt()` |
| Entscheid der Einkäuferin | «weiterverhandeln» (Mandat bleibt, die Forderung wird zurückgewiesen) oder «abbrechen»; dazu eine freie Notiz fürs Protokoll | Behauptungen ändern das Mandat nie (ADR 0008); ein neues Mandat ist eine neue Verhandlung, kein Pfad im Agenten |
| Eval | `ask_buyer` unterbricht den Lauf; die Eval wertet einen Halt dort als `escalated` und setzt nicht fort | Metriken und Szenarien bleiben gleich; Eskalation korrekt / unnötig / verspätet wie bisher |
| Mensch als Lieferant | `HumanSupplier` mit `input()` hinter derselben Schnittstelle wie der Simulator, per Closure in den Graphen (ADR 0009) | Der Graph bleibt gleich, der Eval-Pfad unverändert; der Mensch sieht nur den Text wie der Simulator |
| Variante für Live-Runden | nur (b) | (a) beendet den Lauf über das Ereignis des Simulators, das ein Mensch nicht liefert; (b) liest die Einigung aus dem Text (ADR 0013) |

Variante (c) würde vor dem ersten Angebot das letzte Protokoll desselben Lieferanten lesen (zum Beispiel die frühere
Paketwahl). Sie ist gestrichen (ADR 0014); die Tabelle ist so angelegt, dass (c) ohne Umbau möglich bleibt.

## Verworfene Alternativen

| Alternative | Grund |
| --- | --- |
| LangGraph Store (`InMemoryStore`, SW8 Folie 15) als Langzeitgedächtnis | zweiter Speicher neben dem ERP-Adapter; ohne `index` liefert `search` alle Einträge des Namespace und ignoriert die Anfrage; `InMemoryStore` ist nach einem Neustart ebenfalls leer |
| `SqliteSaver` als Checkpointer schon jetzt | Paket `langgraph-checkpoint-sqlite` nicht installiert; 3.1.3 verlangt `langgraph-checkpoint` ≥ 4.3.1 (installiert 4.2.0), 3.1.1 passt. Nötig erst, wenn die Einkäuferin nach einem Neustart entscheidet |
| `interrupt()` direkt in `escalate` | die Aufbereitung liefe beim Fortsetzen ein zweites Mal |
| `interrupt()` in `send_and_wait` für den Menschen als Lieferanten | einheitlich mit der Eskalation, ändert aber den Graphen für die Eval; erst nötig für eine Web-UI oder LangGraph Studio |
| Supervisor oder Multi-Agent (SW8 Folie 24) | ein Agent pro Lieferant mit festem Ablauf genügt; SW8 Folie 26: «All steps predetermined … Autonomy is in text generation» |

## Kippt, wenn

- die Einkäuferin nach einem Neustart des Prozesses entscheiden soll (realistisch: Eskalationen warten Tage): dann
  `SqliteSaver` mit `langgraph-checkpoint-sqlite` 3.1.1, gepinnt;
- in Protokollen nach Freitext gesucht werden soll: dann Store mit `index` oder Volltextsuche in SQLite;
- die Demo über LangGraph Studio oder eine Web-UI läuft: dann `interrupt()` auch für den Lieferanten.

## Konsequenzen

- Bau 1: `erp.py` mit Protokolltabelle, `record_outcome` vor `notify_supplier`, Metrik `korrekt_gebucht`; `escalate`
  und `ask_buyer` in `graph_b.py`; Runner und `HumanSupplier` im Terminal. Der Canary-Test muss grün bleiben: keine
  `hidden`-Felder im Protokoll.
- `_v4` zeichnet `ask_buyer` und die beiden Entscheide der Einkäuferin.
- Prüfungsbegründung: «Kurzzeitgedächtnis ist der State eines Threads im Checkpointer, Langzeitgedächtnis sind die
  Protokolle im ERP-Adapter. Der Code schreibt sie, nicht das LLM; ein Store wäre ein zweiter Speicher ohne Mehrwert.»

## Nachtrag 09.11.2026: gebaut und gemessen

**So ist es gebaut** (Commits 6f90a8d, 078fa0b, 2b435b9; BPMN `_v4` in 6fd90bb):

- `erp.py`: `ErpAdapter` über SQLite mit den Tabellen `supplier`, `conditions`, `protocol` und `protocol_round`
  (Reaktion und Paketwahl pro Nachricht). Eine Verbindung pro Lauf; die Eval nutzt `:memory:`, die Demo mit
  `--erp PFAD` eine Datei, damit die Protokolle über Läufe bleiben. `load_context` liest Stammdaten und heutige
  Konditionen aus dem ERP; `record_outcome` schreibt auf jedem Ausgang, idempotent pro Verhandlung, und bucht bei
  einem Deal die Konditionen. `protocols(supplier_id)` liest frühere Protokolle; der Runner zeigt sie an, der Graph
  nutzt sie nicht.
- Eskalation: `assess_response` → `escalate` (Code: Vorlage `escalation_brief` mit Grund, Zitat, Verlauf und letzter
  Antwort; Protokoll mit Status «escalated»; Zwischenbescheid an den Lieferanten) → `ask_buyer` (nur `interrupt()`) →
  `after_buyer`. Resume-Wert `{"decision": "weiterverhandeln" | "abbrechen", "note": …}`; alles ausser
  «weiterverhandeln» gilt als «abbrechen». Nach «weiterverhandeln» weist der Code dieselbe Grösse künftig per Vorlage
  zurück und eskaliert sie nicht erneut (Schutz der Einkäuferin, ADR 0008); eine Annahme unter dieser Bedingung ist
  kein Abschluss. Die Notiz der Einkäuferin geht nur ins Protokoll.
- Lieferant: Schnittstelle `Supplier` mit `respond_to_offer(t, packages, text)` und `respond_to_acceptance(t, terms,
  text)`. Der Simulator liest `text` nicht; `HumanSupplier` (`live.py`) zeigt nur `text`, liest per `input()` und
  liefert das Ereignis `human`. Runner: `ea-run --variant b --live` (Simulator, Einkäuferin im Terminal) und `--human`
  (Mensch als Lieferant); Ausgabe pro Node farbig nach LLM, Code und Mensch, am Schluss Protokoll und Auswertung gegen
  die verdeckten Werte des Szenarios (Spielkarte). Bei einem Abschluss fragt der Runner den Menschen, ob er zugestimmt
  hat.
- Metrik `korrekt_gebucht` (`eval.booking_ok`), nur (b). Canary-Test prüft zusätzlich den DB-Inhalt. 70 Tests grün
  (vorher 52).

**Messung** (alle am 09.11.2026, Ordner unter `results/`, nicht versioniert):

| Lauf | vorher | nach Bau 1 |
| --- | --- | --- |
| `ea-eval --variant b --policy rule` | 1.0 (`145801_b_regelbasiert`) | 1.0, alle 11 Läufe bis auf den Text identisch, `korrekt_gebucht` 1.0 (`151521_b_regelbasiert`) |
| dito `--paraphrase` | 0.273 (`145802`) | 0.273, identisch, `korrekt_gebucht` 1.0 (`151522`) |
| `ea-eval --policy rule --repeats 3` (a) | 0.909, 3 Verstösse | identisch (`151249_a_regelbasiert`) |
| (b) Luna × 3 | Erfolg 1.00, pass^3 1.00, Spielraum 0.715, Extraktion 0.952 (`143531`) | 1.00, 1.00, 0.715, 0.952, `korrekt_gebucht` 1.00, 0.045 USD (`151614_b_gpt-5.6-luna`) |
| (b) Luna × 3 `--paraphrase` | 1.00, unnötig eskaliert 0.074, Extraktion 0.988 (`143659`) | 1.00, 0.037 (S06 einmal, «ohne Gegenleistung»), 0.976, `korrekt_gebucht` 1.00 (`152717`) |

Die Metriken von (b) ändern sich nicht; die Unterschiede mit Luna liegen im bekannten Rauschen (ADR 0008).
Live geprüft: S04 mit Luna und Mensch als Lieferant (Bedingung «Vorauskasse» → Eskalation → abbrechen; zweiter Lauf mit
derselben ERP-Datei zeigt das frühere Protokoll, Paket B gebucht).

**Abweichungen vom Entscheid:** keine. Präzisiert: Der Zwischenbescheid an den Lieferanten steht in `escalate`, damit
das Transcript der Eval gleich bleibt; die Annahme eines Gegenangebots läuft in `_v4` als eigener Pfad, im Code über
denselben Node `send_and_wait`.


## Nachtrag 09.11.2026: Kippregel «Web-UI» geprüft

Die dritte Kippregel oben verlangt `interrupt()` auch für den Lieferanten, sobald die Demo über LangGraph Studio oder eine
Web-UI läuft. Für die beschlossene Web-UI (ADR 0012 und 0014, Nachträge) greift sie **nicht**, und das ist ein
ausdrücklicher Widerspruch zur Regel, kein stilles Übergehen: Die Regel nahm an, dass die Oberfläche den Graphen selbst
steuert und zwischen zwei Eingaben anhält, wie Studio. Die gewählte UI startet dagegen `run_live` in einem
Hintergrund-Thread; `ask` blockiert dort, bis die Person im Browser antwortet, genau wie `input()` im Terminal. Der Graph,
`HumanSupplier` und der Eval-Pfad bleiben gleich. Die Eskalation läuft weiter über `interrupt()` in `ask_buyer` und
`Command(resume=…)` im Runner.

Neu kippt die Regel, wenn die UI einen Neustart des Prozesses überdauern oder mehrere Verhandlungen gleichzeitig führen
soll: dann `interrupt()` für den Lieferanten und `SqliteSaver` (erste Kippregel).
