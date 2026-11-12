# Einkaufsagent – LLM schlägt vor, Code entscheidet

Gruppenarbeit «Generative KI und Agentensysteme», FHNW Hochschule für Wirtschaft, HS 2026. Abgabe am 23.11.2026.

Ein LangGraph-Agent verhandelt für die fiktive Musterhandel AG mit kleineren Lieferanten (Long Tail, unter
CHF 250'000 Jahresvolumen) Zahlungsziel, Rabatt und Mengenzusage nach. Er bietet pro Runde 2–3 gleichwertige Pakete an
(MESO, Vorbild Pactum bei Walmart), bleibt strikt im Mandat der Einkäuferin und übergibt an sie, was das Mandat nicht
regelt. Die Kernthese «LLM schlägt vor, Code entscheidet» belegen wir mit einer Ablation gegen simulierte Lieferanten
mit verdeckten Parametern und bekannter Wahrheit: (a) reines LLM gegen (b) Hybrid, in dem das LLM nur liest und
formuliert und Code Pakete berechnet, jede Nachricht gegen das Mandat prüft und über Annahme entscheidet.

**Einstieg:** [`docs/gesamtsystem.md`](docs/gesamtsystem.md) erklärt Problem, Ansatz, Umsetzung, Evaluation und
Limitationen mit Quellen; die Entscheide mit Alternativen stehen in [`docs/adr/`](docs/adr/README.md).

## Start

Voraussetzung: Python ≥ 3.12 und [uv](https://docs.astral.sh/uv/). Ohne API-Key laufen die Tests, die Regel-Referenz
und Variante (b) mit Vorlage und Regex-Parser.

```bash
uv sync                                                # Abhängigkeiten aus uv.lock
uv run pytest                                          # 98 Tests, offline
uv run ea-eval --policy rule --repeats 3               # Regel-Referenz auf 11 Dev-Szenarien: Erfolg 0.91
uv run ea-eval --variant b --policy rule               # Variante (b) offline (Vorlage + Regex-Parser): 1.00
uv run ea-run --scenario S02 --policy rule             # eine Verhandlung im Klartext
uv run ea-run --scenario S11 --variant b --policy rule --live   # Eskalation, Einkäuferin entscheidet im Terminal
uv run ea-ui --model offline                           # Web-UI offline: http://127.0.0.1:8080, «Simulator», S11
```

Mit Zugang zum FHNW-LiteLLM (Modell `gpt-5.6-luna`) und optional LangSmith:

```bash
cp .env.example .env                                   # LITELLM_BASE_URL, LITELLM_API_KEY, LangSmith-Key eintragen
uv run ea-check-models                                 # Luna: function_calling ok
uv run ea-eval --variant b --model gpt-5.6-luna --repeats 3                                    # Dev-Set
uv run ea-eval --variant b --model gpt-5.6-luna --repeats 3 --scenarios data/scenarios/test.jsonl   # Testset
uv run ea-eval --model gpt-5.6-luna --repeats 3        # Variante (a), reines LLM
```

Schalter: `--variant a|b`, `--paraphrase` (Lieferantentexte umformuliert), `--scenarios` (Dev- oder Testset),
`--repeats`. Ergebnisse landen in `results/<zeitstempel>_…/` (`runs.jsonl` mit vollem Verlauf, `summary.md`,
`summary.json`).

## Demo: Mensch als Lieferant

```bash
export LANGSMITH_TRACING=false
uv run ea-ui                                           # Browser: http://127.0.0.1:8080 (S04, Mensch, Luna, ERP mit Vorgeschichte)
uv run ea-run --scenario S04 --variant b --model gpt-5.6-luna --human   # Terminal
```

Eine Person spielt den Lieferanten und versucht, den Agenten zu manipulieren. Die Web-UI (NiceGUI, ADR 0016) zeigt links
das Gespräch und rechts die Schritte farbig wie die BPMN: was das LLM vorschlägt (orange) und was der Code entscheidet
(blau). Bei einer Eskalation hält der Graph an (`interrupt()`), und die Einkäuferin entscheidet über eine grüne Karte:
weiterverhandeln, eine Bedingung freigeben (der Code bucht, was der Lieferant zugesagt hat) oder abbrechen. Am
Schluss folgt die Auswertung gegen die Spielkarte. Die UI ist nur Darstellung über demselben Runner wie das Terminal, das
als Fallback bleibt. Das ERP ist ein Ersatz in SQLite (ADR 0005); in der UI liegt es im Speicher, mit einer früheren
Verhandlung als Vorgeschichte, die die Einkäuferin am Start und bei einer Eskalation sieht (Langzeitgedächtnis; der Agent
nutzt sie nicht). Jede Verhandlung startet gleich, und nichts bleibt zurück (ADR 0016, Nachtrag 12.11.). Ablauf, Fallbacks und Spielkarten:
[`docs/demo.md`](docs/demo.md).

## Ergebnisse (finale Läufe vom 09.11.2026, `gpt-5.6-luna`, 3 Wiederholungen)

| Variante | Erfolg Dev (11) | Erfolg Testset (15) | Testset umformuliert | Spielraum Testset | Verstösse Testset | Angriffe erfolgreich | unnötige Eskalationen Testset | USD pro Erfolg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (a) reines LLM | 0.82 | 0.73 | 0.71 | 0.25 | 2 | 0 | 0.06 | 0.0031 |
| **(b) Hybrid** | **1.00** | **0.98** | **0.93** | **0.70** | **0** | **0** | 0.12 | 0.0017 |
| Regel-Referenz ohne LLM | 0.91 | 0.80 | – | 0.70 | 9 | 0 | 0 | 0 |
| (b) mit Regex-Parser statt LLM | 1.00 | 0.80 | 0.13 | 0.70 | 5 | 0 | 0 | 0 |

**Erfolg** heisst: erwartetes Ergebnis (Abschluss, kein Abschluss oder Eskalation) ohne Mandatsverstoss.
**Gesicherter Spielraum** ist der Anteil des möglichen Nutzens über dem Mindestnutzen, den ein Abschluss sichert.
Kurz gesagt: Zum Lesen braucht es das LLM (der Regex-Parser bricht bei umformulierten Texten ein), zum Entscheiden
den Code (das reine LLM verschenkt Spielraum, verpasst Eskalationen und schliesst zweimal unter dem Mindestnutzen ab).
Kein Angriff erreicht sein Ziel, auch nicht gegen (a). Auf dem Dev-Set liegt (b) bei der Erfolgsquote 18 Punkte vor (a),
knapp unter der selbst gesetzten Schwelle von 20 Punkten. Spielraum (+48) und Testset (+25) liegen klar darüber
(ADR 0013, Nachtrag).

Alle Läufe vom selben Code-Stand mit Befehlen, Kosten und Fehlläufen: [`docs/ergebnisse/2026-11-09/`](docs/ergebnisse/2026-11-09/README.md).
Sie liefen auf Commit `3ac6beb`. Danach kamen nur die Web-UI, die Vorgeschichte im ERP der UI und der Entscheid
«freigeben» nach einer Eskalation dazu; der Eval-Pfad blieb gleich. Die sechs Läufe ohne LLM ergeben auf dem Stand der
Vorabgabe (12.11.2026) dieselben `runs.jsonl`, bis auf die Laufzeit.
Metriken: [`docs/eval-metriken.md`](docs/eval-metriken.md).

## Wo was liegt

| Pfad | Inhalt |
| --- | --- |
| `docs/gesamtsystem.md` | Gesamtsystem und Begründungen: Grundlage für Präsentation und Prüfung |
| `docs/adr/` | 17 Architekturentscheide mit Alternativen und «kippt, wenn» (Index in `README.md`) |
| `einkaufsagent-prozess_v5.bpmn`, `.png` | gültiger Soll-Prozess (BPMN 2.0); Zuordnung BPMN → LangGraph in `docs/process/README.md`; `_v1`–`_v4` als Historie |
| `docs/eval-metriken.md` | Definition und Zielwert jeder Metrik |
| `docs/ergebnisse/` | versionierte Ergebnisse der finalen Läufe |
| `docs/demo.md` | Demo-Ablauf, Aufzeichnung, Live-Runden, Spielkarten |
| `src/einkaufsagent/graph_a.py` | Variante (a): `load_context → negotiate ⇄ send_and_wait → finalize`, ein LLM-Node entscheidet alles |
| `src/einkaufsagent/graph_b.py` | Variante (b): `offer_engine → narrate → mandate_guard → send_and_wait → parse_response → assess_response →` Runde, Annahme, `escalate → ask_buyer` oder `record_outcome` |
| `src/einkaufsagent/hybrid.py`, `domain.py` | Code-Schritte: Mandatsprüfung, Bewertung nach ADR 0008, Vorlagen, Nutzenfunktion |
| `src/einkaufsagent/extract.py`, `narrate.py`, `prompts.py` | LLM-Schritte von (b) (austauschbar) und alle Prompts |
| `src/einkaufsagent/erp.py`, `live.py` | ERP-Adapter (SQLite, Protokoll, Buchung) und Runner im Terminal |
| `src/einkaufsagent/ui.py`, `ui_session.py`, `ui_text.py` | Web-UI `ea-ui` über dem Runner (Lauf im Hintergrund-Thread; Sicht des Lieferanten links, intern mit Mandat, Schritten und Auswertung rechts; ADR 0016) |
| `src/einkaufsagent/supplier_sim.py` | regelbasierter Lieferanten-Simulator mit verdeckten Parametern, ZOPA-Analyse |
| `src/einkaufsagent/eval.py`, `benchmark.py` | Eval und Modellvergleich |
| `data/scenarios/` | 11 Dev-Szenarien, 15 Testszenarien mit Angriffen (Aufbau in `README.md`) |
| `data/paraphrases/` | eingefrorene Umformulierungen der Lieferantentexte mit Prompt und Stichprobe |
| `scripts/` | Szenarien und Testset erzeugen und prüfen, Fehlerbilder und Strategie auswerten (`analyse_strategie.py`, ADR 0017) |
| `tests/` | Offline-Tests, darunter Canary-Tests: verdeckte Werte erreichen nie State, Prompt oder ERP |
| `CLAUDE.md` | Arbeitsstand und Übergabe zwischen Sessions (Arbeitsprotokoll) |

## Limitationen in Kürze

- Gemessen gegen einen regelbasierten Simulator mit synthetischen Texten. Live-Runden mit unbeteiligten Personen stehen
  noch aus (Stand 12.11.2026); bisher gibt es eigene Proben und ein Red-Teaming durch Claude (`docs/demo.md` §3).
  Externe Validität ist die Hauptlimitation.
- 11 Dev- und 15 Testszenarien × 3 Wiederholungen: Ein Szenario entspricht 9 bzw. 6,7 Prozentpunkten; Unterschiede
  unter etwa 20 Punkten nicht interpretieren.
- Mit `gpt-5.6-luna` scheitert kein Angriff, auch nicht gegen (a); der Sicherheitsgewinn von (b) ist strukturell, mit
  diesem Modell aber nicht messbar. Der Preis der Abwehr sind unnötige Eskalationen (Denial of Service gegen die
  Einkäuferin), ADR 0013.
- Szenarien, Testset und Regel-Referenz stammen aus einer Hand; die Testtexte schrieb ein Modell einer anderen Familie
  (Claude Opus), der Code rechnet die Wahrheit (ADR 0010).
- Eine Eskalation wartet nur, solange der Prozess läuft (`InMemorySaver`).
- Die Verhandlungsstrategie schliesst effizient ab (Rabatt gegen Mengenzusage), maximiert aber nicht: Die Konzession ist
  zeitabhängig ohne Gegnermodell; wer bis zur letzten Runde ablehnt, drückt unseren Nutzen offline um 57 %, nie unter den
  Mindestnutzen (ADR 0017).

Ausführlich: `docs/gesamtsystem.md` §5.

## Grundsätze

- **Die Evaluation ist die Spezifikation.** Keine Prompt- oder Architekturänderung ohne Messung auf denselben
  Szenarien; das erwartete Ergebnis jedes Szenarios ist aus seinen Parametern hergeleitet.
- **Verdeckte Lieferantenparameter erreichen den Agenten nie.** Simulator, Mensch und ERP kommen per Closure in den
  Graphen; Canary-Tests prüfen State, Prompts und den Inhalt der Datenbank.
- **LLM schlägt vor, Code entscheidet** – ab Variante (b). Variante (a) ist bewusst die Baseline ohne diese Trennung.

Fiktive Firma, keine echten Lieferanten, keine echten Daten.
