# ADR 0015 – Memory und Human-in-the-loop

- **Status:** angenommen am 09.11.2026 (Entscheid; gebaut in Bau 1, ADR 0014)
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
