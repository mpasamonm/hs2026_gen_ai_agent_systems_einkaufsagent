# CLAUDE.md – Einkaufsagent (Gruppenarbeit GenKI & Agentensysteme, FHNW HSW, HS 2026)

Diese Datei ist die Übergabe für jede neue Session. Stand: 06.10.2026. Das Repository ist ab jetzt die
führende Quelle; die claude.ai-Dokumente sind nur noch Referenz (`kontext/README.md`).

## 1. Projekt in fünf Sätzen

Ein LangGraph-Agent verhandelt für die fiktive Musterhandel AG mit kleineren Lieferanten (Long Tail, unter
CHF 250'000 Jahresvolumen) Zahlungsziel, Rabatt und Mengenzusage nach. Er bietet 2–3 gleichwertige Pakete an
(MESO, Vorbild Pactum bei Walmart) und bleibt strikt im Mandat der Einkäuferin. Kernthese: «LLM schlägt vor,
Code entscheidet», belegt durch eine Ablation: (a) reines LLM, (b) Hybrid mit Offer Engine und Mandatsprüfung
im Code, (c) Hybrid plus Lieferanten-Gedächtnis. Gemessen wird gegen simulierte Lieferanten mit verdeckten
Parametern und bekannter Wahrheit (ZOPA). Team-Entscheid vom 05.10.2026 (ADR 0001).

## 2. Quellen und Vorrang

1. Massgeblich sind die Originale in `kontext/originale/` (lokal, nicht im Git). `modul-originalquellen.md`
   enthält Anhang A–E byte-genau: **nie verändern oder kürzen.**
2. Anhang C stammt aus der älteren SW4-Fassung. Aktuell ist `2026_SW4_Agentensystem2.pdf`, Text in
   `kontext/sw4-folien-v2-extrakt.md`. Foliennummern ab Folie 3 um 1 höher als in Anhang C.
3. Arbeitshilfen: `kontext/briefing-export-2026-10-06.md`, `docs/sw4-artefakte.md`, `docs/adr/`.
   `docs/gesamtsystem.md` ist die Grundlage fürs Team (Präsentation, Prüfung); bei jedem Entscheid nachführen.
   Werte mit «Annahme» sind Startwerte.
4. Bei einem Widerspruch gilt das Original. Den Widerspruch ausdrücklich nennen, nicht still auflösen.

## 3. Modulrahmen (aus Anhang A und B)

- Bewertung «erfüllt/nicht erfüllt»; Voraussetzung für die mündliche Prüfung, die zu rund 50 % die
  Gruppenarbeit abfragt. Jede Person muss das Gesamtsystem erklären können.
- Abschlusspräsentation 23.11.2026, 13.00 Uhr, 10 Minuten inkl. Fragen: Problem, Ansatz, Umsetzung,
  Evaluation, Erkenntnisse und Limitationen, möglichst mit Demo.
- Abgabe: Link auf ausführbare Lösung, Projektartefakte, Präsentation als PDF. Abgabetermin in den
  Unterlagen nicht genannt (bei den Dozierenden klären).
- Pro-Code mit LangGraph; No- und Low-Code-Tools (n8n, Voiceflow) sind nicht erlaubt.
- Wochenaufträge laut Semesterprogramm:

| KW | Datum | Auftrag | Konkret bei uns |
| --- | --- | --- | --- |
| 42 | 12.10. | Erste lauffähige Version, Tracing funktioniert | Variante (a), Eval, Benchmark, LangSmith |
| 43 | 19.10. | MCP-Server anbinden | ERP-Mock als MCP-Server (SQLite), Variante (b) |
| 44 | 26.10. | RAG einbauen | Einkaufsrichtlinie und Marktbenchmarks, Hybrid Retrieval |
| 45 | – | Blockwoche | – |
| 46 | 09.11. | Memory festlegen | Lieferanten-Gedächtnis (c), Eskalation per Interrupt, 1:3 parallel |
| 47 | 16.11. | Safeguarding (minimal prompt-basiert), Evaluation | Angriffsszenarien, Guardrails, Chat-UI, voller Eval-Lauf |
| 48 | 23.11. | Abschlusspräsentation | Demo |

## 4. Entscheide (Details und «kippt, wenn» in `docs/adr/`)

| # | Entscheid | Status |
| --- | --- | --- |
| D1 / ADR 0001 | Use-Case Einkaufsagent; Fallback Invoice Guard, falls Variante (a) schon fast fehlerfrei ist | angenommen |
| D2 | Apertus nur als Referenzzeile | angenommen; Apertus-Chatmodell nicht im LiteLLM |
| D3 | Recherche just-in-time als Spike mit ADR | angenommen |
| D4 | Hermetische Evals: feste Szenarien und Seeds | angenommen |
| D5 | Modelle über FHNW-LiteLLM | angenommen |
| D6 | Konditionen-Nachverhandlung mit Paketen statt freiem Feilschen | angenommen |
| D7 | LLM-Lieferant aus anderer Modellfamilie als der Agent | gilt ab LLM-Simulator (KW46) |
| ADR 0002 | Prozess v2: LLM extrahiert und formuliert, Code bewertet und entscheidet | **vorgeschlagen, Team-Freigabe offen** |
| ADR 0003 | Regelbasierter Lieferanten-Simulator für KW42 | angenommen |
| ADR 0004 | Kandidaten: gpt-5.6-luna, azure_ai/gpt-oss-120b, azure_ai/mistral-large-3 + Regel-Referenz; **Arbeitsmodell gpt-5.6-luna** | angenommen (Benchmark 06.10.2026) |
| ADR 0005 | ERP-light: schmaler MCP-Server (FastMCP, SQLite) mit 3 Tools statt vollem ERP-Mock | **vorgeschlagen, Team-Freigabe offen** |
| ADR 0006 | D1-Spike: Variante (a) nicht fast fehlerfrei, Hybrid-Story trägt; kein Invoice Guard | angenommen |
| ADR 0007 | Schlanke Prozessfassung `einkaufsagent-prozess_v2.bpmn` (Entwurf): ohne Timer und LLM-Strategie, RAG in der Eskalation, ein Gedächtnis, ohne 1:3 | **vorgeschlagen, Team-Freigabe offen** |

## 5. Architektur heute (Variante a)

- Graph `src/einkaufsagent/graph_a.py`: `load_context → negotiate ⇄ send_and_wait → finalize`.
  `negotiate` ist ein LLM-Node (`LLMPolicy`, strukturierte Ausgabe `AgentTurn`); er bündelt die
  BPMN-Schritte Strategie, Pakete, Formulieren, Extrahieren und Bewerten.
- Lieferant: `supplier_sim.py`, regelbasiert. Konzessionsbudget nach Faratin et al. (1998), Geduld,
  Gegenangebot durch Kürzen des besten Pakets, optional Preisforderung und Prompt Injection.
- Referenz ohne LLM: `RuleBasedPolicy` (lineare Konzession, 3 MESO-Pakete, Annahme nach AC_next).
- Szenarien: `data/scenarios/dev.jsonl` (10 Stück), erzeugt und gegen die ZOPA geprüft mit
  `scripts/build_scenarios.py`. 7 × Deal (S09 mit Injection), 2 × ohne ZOPA, 1 × Eskalation.
- Eval: `eval.py`, Metriken in `docs/eval-metriken.md`. Benchmark: `benchmark.py`.
  Modellprüfung: `check_models.py`.
- Prozess: `docs/process/einkaufsagent-prozess.bpmn` (v2). Zuordnung BPMN → LangGraph in
  `docs/process/README.md`. Änderungen über `docs/process/gen_bpmn.py`, danach validieren und rendern.

**Invarianten – nie brechen**
- Verdeckte Lieferantenparameter (`hidden` im Szenario) gelangen nie in den Graph-State, einen Prompt oder
  LangSmith-Metadaten. Der Simulator kommt per Closure in den Graphen; der Canary-Test in
  `tests/test_graph_and_isolation.py` muss grün bleiben.
- Rundenlogik wie BPMN v2: `round` zählt Angebotsrunden. Ein Gegenangebot ist auch nach der letzten Runde
  annehmbar. «accept» gilt nur für das letzte Gegenangebot; eine abgelehnte Annahme zählt als Runde.
- Ab Variante (b) entscheidet nur Code über Zahlen und Mandat; das LLM extrahiert und formuliert.

## 6. Stand am 06.10.2026

Erledigt:
- BPMN-Review mit Befundtabelle; v2 geprüft mit bpmn-moddle, bpmnlint «recommended» und bpmn-js 18.31.0,
  jeweils ohne Befund. Artefakte 2 und 3 im SW4-Dokument angepasst.
- Repo-Gerüst: Python 3.12, uv-Lockfile, langgraph 1.2.12, langchain-openai 1.6.7, langsmith 0.14.4,
  pydantic 2.13.5.
- 10 Szenarien, Variante (a), Eval, Benchmark, Modellprüfung; 20 Offline-Tests grün; ruff sauber.
- Offline-Baseline der Regel-Referenz: 10/10 korrekt, 0 Mandatsverstösse, Ø 2,3 Runden, gesicherter
  Spielraum 0,715.
- KW42 abgeschlossen (Session 06.10.2026):
  - LiteLLM `https://litellm.engines.aisl.science`; LangSmith-Konto in der EU-Region (`LANGSMITH_ENDPOINT`
    nötig), Projekt `einkaufsagent`. Repo: github.com/mpasamonm/hs2026_gen_ai_agent_systems_einkaufsagent (privat).
  - `ea-check-models`: Luna `function_calling`, gpt-oss und Mistral nur `json_schema` (ADR 0004).
  - Preise in `config/models.toml` sind die FHNW-Preise aus `/model/info` des Proxys.
  - Tracing nachgewiesen (`verhandlung-S04`, 10 Graph-Knoten, 4 LLM-Aufrufe).
  - Benchmark: Luna 0,80 Erfolg, 0 Verstösse, 0.0028 USD pro Erfolg → Arbeitsmodell (ADR 0004).
  - D1-Spike und Fehlerbilder in ADR 0006; Zielwerte in `docs/eval-metriken.md` und Artefakt 4 justiert.
  - `scripts/analyse_fehlerbilder.py` wertet `runs.jsonl` aus (Leaks, Text ohne Konditionen, verpasste Annahmen, S09).
- 11.10.2026: `angebote_ohne_konditionen` und `verpasste_annahmen` fest in `eval.py` und Benchmark-Tabelle
  (`tests/test_eval_metrics.py`); das Skript nutzt dieselbe Logik, Zahlen aus ADR 0006 unverändert reproduziert.

## 7. Nächste Schritte in dieser Reihenfolge

1. **KW42** – erledigt am 06.10.2026 (§6). Für den Unterricht am 12.10.: Trace per Share-Link zeigen,
   Benchmark-Tabelle aus ADR 0004, Fehlerbilder aus ADR 0006.
2. **Team-Entscheide einholen** (blockiert Schritte 4–5):
   - ADR 0002 (Prozess v2) zusammen mit ADR 0007 (schlanke Fassung `einkaufsagent-prozess_v2.bpmn`) freigeben
     → Status «angenommen»; offen ist dabei der RAG-Ort (Eskalation oder «Angebot formulieren»).
   - ADR 0005 (ERP-light) mit den Prüfpunkten am Ende der ADR freigeben oder anpassen (sync statt async,
     History-Tool, ein Gedächtnis statt zwei).
   - S09: Zählt eine Eskalation bei Manipulation als korrekt? Heute erwartet S09 einen Deal (ADR 0006).
   - Rollen im Team; Abgabetermin bei den Dozierenden klären.
3. **Ohne Freigabe möglich**
   - ~~Metriken `angebote_ohne_konditionen` und `verpasste_annahmen` in `eval.py`~~ erledigt am 11.10.2026.
   - Briefing für das Testset (andere Person): abwechslungsreiche Mandate und heutige Konditionen, ein Szenario
     mit bindendem Rundenlimit, Angriffsszenarien.
4. **Nach der Freigabe**
   - Ändert sich der Prozess (z.B. durch ADR 0005), neue Datei `einkaufsagent-prozess_v2.bpmn` im Root; `_v1`
     bleibt. `docs/process/einkaufsagent-prozess.bpmn` und PNG im Gleichschritt nachführen, validieren, rendern.
   - Abschnitt «Vorbereitung KW42» in `docs/sw4-artefakte.md` (State-Code, Graph-Tabelle) auf v2 nachziehen.
   - **Gesamtplan erstellen** (Auftrag vom 05.10.2026; Folie 16 der aktuellen SW4-Fassung fragt ebenfalls «Was
     wollt ihr in den nächsten Wochen umsetzen?»): Architektur, Stack, Meilensteine pro KW bis zur Demo,
     Deliverables für Präsentation und Abgabe. Schwerpunkt Reflexion, Limitationen, Schwächen und
     Ausbaumöglichkeiten, wie es eine Hochschularbeit verlangt. Als `docs/plan.md`, Entscheide als ADR.
5. **KW43 (19.10.), Variante (b)** nach BPMN v2, Arbeitsmodell `gpt-5.6-luna`:
   - Nodes `offer_engine`, `narrate`, `mandate_guard` + `template_message`, `parse_response`, `assess_response`.
   - ERP-light nach ADR 0005 (in der freigegebenen Fassung). Versionen vorher erneut prüfen.
   - Ablation (a) gegen (b) auf denselben 10 Szenarien; Ziele in `docs/eval-metriken.md`.
6. **Testset:** 10–20 zurückgehaltene Szenarien, entworfen von einer anderen Person als die Dev-Szenarien.
   Danach LLM-Lieferant als Robustheitstest (D7, Mistral Large 3 als andere Modellfamilie).

## 8. Offene Widersprüche und Hinweise

- Briefing nennt «Folie 38» bzw. «Folie 30»: alte Nummern; aktuell Folie 41 (LiteLLM) und 31 (Pareto).
- Das Briefing sagt, v1 sei «ohne Warnungen» geprüft. Das gilt für den bpmn-js-Import; bpmnlint findet
  2 fake-joins. v1 ist abgelöst.
- Briefing plant eine Frontier-Referenz; im LiteLLM gibt es keine. Ersatz: Regel-Referenz (ADR 0004).
- SW4 Artefakt 4 plant rund 30 Szenarien (20 Dev, 10 Test); heute sind es 10 Dev-Szenarien.
- SW4-Modellauswahl nennt GLM-5.3-Flash und DeepSeek V4.1 Flash; beide sind nicht im LiteLLM.
- gpt-oss-120b und Mistral Large 3: Function Calling über den Proxy geprüft am 06.10.2026, liefert leer bzw.
  Fehler 422, obwohl `/model/info` `supports_function_calling` meldet. Für Tool-Use in KW43 nur Luna verlässlich.
- MCP-Versionsfalle: `langchain-mcp-adapters` 0.3.2 verlangt `mcp<2.0`, das SDK steht bei 2.3.0; nicht verwenden
  (ADR 0005). Briefing und SW4 sprechen noch vom «ERP-Mock» mit Preishistorie und Bestellungen.
- Der Simulator bewertet die strukturierten Pakete, nicht den Text. Text-Paket-Widersprüche und Täuschung
  misst erst `mandate_guard` (b) bzw. ein kalibrierter LLM-Judge (KW47).
- Neuer Auftrag auf Folie 43 der aktuellen SW4-Fassung: DeepLearning.AI-Video «AI Agents in LangGraph»
  (Kapitel siehe Moodle).
- BPMN liegt doppelt: `docs/process/einkaufsagent-prozess.bpmn` (Generator) und `einkaufsagent-prozess_v1.bpmn` im
  Root (byte-gleich, beides Prozess v2). Wunsch des Teams: Änderungen als neue Root-Datei `_vN+1`, alte behalten.
  Namensfalle: Datei `_v1` = «Prozess v2» (ADR 0002); `_v2` = schlanke Fassung (ADR 0007, Entwurf). Im Team nur
  Dateinamen verwenden. `_v2` wird bis zur Freigabe direkt angepasst, danach jede Änderung als neue Datei.
- §3 nennt für KW43 noch «ERP-Mock (SQLite)»; ADR 0005 (vorgeschlagen) ersetzt das durch ERP-light.
- Simulator mit Textvorlagen: Die Regel-Referenz ohne LLM löst alle Szenarien; der LLM-Nutzen zeigt sich erst
  gegen freie Texte (KW46, Live-Runden). Limitation für die Präsentation (ADR 0006).

## 9. Arbeitsweise

- Knapp antworten, ohne Einleitung und Zusammenfassung. Ansatz selbst wählen und Annahmen in einer Zeile
  nennen.
- Mehrschrittige Aufgaben als nummerierte Schritte: Titel, Wo, Wie (kopierbar), Checkpoint mit beobachtbarem
  Ergebnis.
- Konzeptentscheide: 2–3 echte Alternativen mit der trennenden Achse, eine Empfehlung, die Bedingung, die sie
  kippt; als `docs/adr/NNNN-slug.md` festhalten. Widerspricht eine Bitte einem früheren Entscheid, das zuerst
  sagen.
- Die Evaluation ist die Spezifikation: keine Prompt- oder Architekturänderung ohne Messung auf demselben
  Szenario-Satz.
- Vor jeder Empfehlung von Bibliothek, Modell oder Muster aktuell recherchieren (Version, Release-Datum,
  Reife [stable]/[current default]/[emerging]/[experimental]). API-Signaturen vor Gebrauch in der Doku
  prüfen (Context7); Unsicheres als «unverified» markieren. Versionen pinnen.
- Doku auf Deutsch mit Schweizer Rechtschreibung («ss»); Code-Bezeichner Englisch.
- Vor jedem Commit: `uv run ruff format && uv run ruff check && uv run pytest`. Nie `.env` oder `kontext/`
  committen.

## 10. Befehle

```bash
uv sync
uv run pytest
uv run ea-run --scenario S04 --policy rule        # offline
uv run ea-check-models                            # braucht .env
uv run ea-run --scenario S04 --model gpt-5.6-luna
uv run ea-eval --model gpt-5.6-luna --repeats 3
uv run ea-benchmark --repeats 3
uv run python scripts/build_scenarios.py          # Szenarien neu erzeugen und prüfen
# BPMN (optional, Node 22 + Playwright-Chromium):
cd docs/process && npm install && python3 gen_bpmn.py einkaufsagent-prozess.bpmn \
  && node validate.mjs einkaufsagent-prozess.bpmn \
  && python3 render.py einkaufsagent-prozess.bpmn einkaufsagent-prozess.png
```
