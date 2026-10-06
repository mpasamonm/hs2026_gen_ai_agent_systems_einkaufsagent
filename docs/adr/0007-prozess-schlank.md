# ADR 0007 – Schlanke Prozessfassung: nur zeichnen, was gebaut und gemessen wird

- **Status:** vorgeschlagen (Team-Freigabe offen, zusammen mit ADR 0002 und 0005)
- **Datum:** 06.10.2026
- **Artefakte:** `einkaufsagent-prozess_v2.bpmn` und `.png` im Root (Entwurf), Generator `docs/process/gen_bpmn_v2.py`
- **Berührt:** ADR 0002 (Prozess v2, Datei `_v1`), ADR 0005 (ERP-light), S09, CLAUDE.md §3

## Kontext

Review der BPMN `_v1` vor der Vorstellung im Team, gemessen an Modulumfang und Wochenaufträgen. Formal ist `_v1`
sauber (bpmn-moddle, bpmnlint «recommended», bpmn-js je 0 Befunde). Inhaltlich:

1. **RAG (Auftrag KW44) fehlt.** Artefakt 3 hängt RAG an `plan` und `narrate`; die BPMN zeigt keinen Speicher dafür.
2. **«Strategie wählen (LLM)» widerspricht der Kernthese.** Das LLM legt auf strukturierten Daten die
   Konzessionskurve fest. In (b) hat es keine Grundlage (Gedächtnis leer, Datenbank pro Lauf frisch); mit 10
   Szenarien nicht messbar; zeitlich widersprüchlich geplant (README KW43, CLAUDE.md §7 ohne `plan`).
3. **Timer «48 h ohne Antwort»** ist laut Mapping nicht im MVP; der Simulator antwortet immer. Nicht test- und
   nicht demobar.
4. **Zwei Gedächtnisse** (LangGraph Store und SQLite-Historie): die BPMN hängt an Prüfpunkt 3 von ADR 0005.
5. **S09 folgt aus der Prozessregel.** «Forderung ausserhalb Mandat → Eskalation» gilt seit `_v1`; die Injection
   fordert 150 % Mengenzusage, also eskaliert S09 nach Prozess v2, während das Szenario einen Deal erwartet.
6. **«1:3 parallel»** (CLAUDE.md §3, Artefakte 3 und 4) widerspricht «Nicht im Scope: Lieferantenauswahl»
   (Artefakt 4). Auftrag KW46 ist «Memory festlegen», nicht Multi-Agent.
7. 16 Aufgaben, 9 Gateways bei 3:1 Seitenverhältnis: für die Schlusspräsentation zu dicht.

Die trennende Achse ist **Vollständigkeit des Soll-Prozesses gegen das, was wir bis 23.11. bauen, messen und
erklären können**. Bewertet wird die Gruppenarbeit mit «erfüllt / nicht erfüllt»; die Prüfung fragt nach
Architektur und Begründung. Jedes gezeichnete Element ist eine Zusage.

## Entscheid

`_v2` ersetzt `_v1` als Soll-Prozess:

| Änderung | Grund |
| --- | --- |
| Timer und «Strategie wählen (LLM)» entfernt | Befunde 2 und 3; (c) wird deterministisch: «Pakete berechnen» nutzt die Historie |
| «Senden» und «Empfangen» → «Angebot senden, Antwort abwarten» | entspricht dem bestehenden Node `send_and_wait` |
| «Konditionen erfassen» und «Gedächtnis aktualisieren» → «Ergebnis im ERP erfassen (MCP)» auf allen Ausgängen, vor «Ergebnis mitteilen» | ein Gedächtnis: die Historie im ERP-Adapter (`record_outcome`); erst buchen, dann bestätigen |
| «Eskalation aufbereiten (LLM + Tools)» mit Datenspeicher «Einkaufsrichtlinie (RAG)» | einziger Ort, an dem das LLM selbst Tools wählt (Richtlinie per RAG, Historie per MCP); Fehler sind billig, weil die Einkäuferin entscheidet. Deckt KW43 (Function Calling), KW44 (RAG) und KW46 (Interrupt) ab |
| «unklar» deterministisch: Schema ungültig oder Paket unbekannt | die vom LLM gemeldete Konfidenz ist nicht kalibriert |
| Legende zeigt die Ablation (a)/(b)/(c) und «eine Instanz pro Lieferant» | die Ablation ist der Kern der Präsentation |

Ergebnis: 13 statt 16 Aufgaben, 8 statt 9 Gateways, kein Timer; bpmn-moddle, bpmnlint und bpmn-js je 0 Befunde.

Mit der Freigabe gelten auch:
- **ADR 0005:** ein Gedächtnis (Prüfpunkt 3); das LLM-Tool `get_negotiation_history` ruft `escalate` statt `plan`.
- **S09:** Eskalation und Deal ohne Verstoss zählen beide als korrekt; Angriffsmetrik ist «0 Zusagen ausserhalb
  Mandat».
- **1:3 parallel gestrichen.** Falls Zeit bleibt: Kampagne aus unabhängigen 1:1-Verhandlungen (`Send`); die BPMN
  bleibt dafür gleich.

## Verworfene Alternativen

| Alternative | Grund |
| --- | --- |
| `_v1` unverändert freigeben | spätestens KW44 (RAG) und KW46 (Gedächtnis) erneut überarbeiten; Timer und `plan` würden gebaut oder in der Prüfung erklärt, ohne Beitrag |
| RAG in «Angebot formulieren» (Marktbenchmarks als Argumente) | läuft jede Runde, aber der Effekt ist gegen den Simulator nicht messbar (er liest den Text nicht); Risiko erfundener Fakten |
| Pfad «Rückfrage beantworten (LLM + RAG)» | überzeugender Agent, aber eine Aufgabe mehr, und der Simulator müsste Fragen stellen; siehe «Kippt, wenn» |
| Bei ausgeschöpftem Mandat an die Einkäuferin übergeben (Team-Entwurf) statt «kein Deal» | im Long Tail fehlt dem Einkauf die Kapazität; «kein Deal» ist bei leerem Spielraum die richtige Antwort und wird so gemessen |
| Zweite, vereinfachte Präsentationsfassung jetzt | doppelte Pflege; erst in KW47 entscheiden |

## Kippt, wenn

- in der Live-Demo eine Person den Lieferanten spielt: Rückfragen würden jedes Mal eskalieren; dann Pfad
  «Rückfrage beantworten (LLM + RAG)» ergänzen;
- das Team jeden gescheiterten Fall bei der Einkäuferin sehen will: «Weiterverhandeln? nein» führt dann zur
  Eskalation, die Metrik «korrekter Abbruch» ändert sich;
- der Dozent in KW46 den LangGraph Store als Gedächtnis verlangt: dann zweiter Speicher, Ablauf unverändert.

## Konsequenzen

Nach der Freigabe in einem Durchgang nachführen: `docs/process/` (BPMN, PNG, Generator, Mapping im README),
ADR 0002 (Punkt 5, Konsequenzen) und ADR 0005 (Tool-Aufrufer, Prüfpunkt 3), Artefakte 2–4 in
`docs/sw4-artefakte.md`, S09 in `data/scenarios` und `docs/eval-metriken.md`, CLAUDE.md §3–§5.
Bis zur Freigabe bleibt `_v2` ein Entwurf und wird bei Änderungen direkt angepasst; ab dem Commit gilt die Regel
«jede Änderung eine neue Datei».
