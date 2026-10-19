# CLAUDE.md – Einkaufsagent (Gruppenarbeit GenKI & Agentensysteme, FHNW HSW, HS 2026)

Diese Datei ist die Übergabe für jede neue Session. Stand: 19.10.2026. Das Repository ist ab jetzt die
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

- Gruppenarbeit «erfüllt/nicht erfüllt», Voraussetzung für die Zulassung zur mündlichen Einzelprüfung. Die
  Prüfung zählt 100 % der Note; rund 50 % betreffen die Gruppenarbeit und den individuellen Beitrag, der Rest den
  Unterrichtsstoff. Jede Person muss das Gesamtsystem erklären können, nicht nur den eigenen Teil.
- Mögliche Prüfungsfragen laut Anhang A: Problemstellung, Modell- und Methodenwahl, Architektur, technische
  Umsetzung, Daten und Werkzeuge, Evaluation, Limitationen, alternative Lösungsansätze.
- Abschlusspräsentation 23.11.2026, 13.00 Uhr, 10 Minuten inkl. Fragen: Problem, Ansatz, Umsetzung,
  Evaluation, Erkenntnisse und Limitationen, möglichst mit Demo. Alle Mitglieder nehmen teil; die Dozierenden
  können individuelle Rückfragen stellen, auch zum eigenen Beitrag. Die Präsentation gehört zur Gruppenarbeit
  (erfüllt/nicht erfüllt) und gibt keine Punkte.
- Abgabe: Link auf ausführbare Lösung, Projektartefakte, Präsentation als PDF. Abgabetermin in den
  Unterlagen nicht genannt (bei den Dozierenden klären).
- Pro-Code mit LangGraph; No- und Low-Code-Tools (n8n, Voiceflow) sind nicht erlaubt.
- Dozent am 19.10.2026: MCP und RAG sind nicht Pflicht; die Technik muss zum Use-Case passen, bevorzugt werden eine
  sinnvolle Technologiewahl und genügende Tiefe. Der Semesterplan ist Input, keine Pflichtliste.
- Wochenaufträge laut Semesterprogramm:

| KW | Datum | Auftrag | Konkret bei uns |
| --- | --- | --- | --- |
| 42 | 12.10. | Erste lauffähige Version, Tracing funktioniert | Variante (a), Eval, Benchmark, LangSmith (erledigt) |
| 43 | 19.10. | MCP-Server anbinden | kein MCP (ADR 0009); Variante (b) mit Luna, `parse_response` austauschbar |
| 44 | 26.10. | RAG einbauen | kein RAG (ADR 0009); ERP-Adapter mit Protokoll, Umformulierungen, Spike Klassifikation (ADR 0011), `_v4` |
| 45 | – | Blockwoche | synthetisches Testset, Angriffe, Bias (ADR 0010) |
| 46 | 09.11. | Memory festlegen | Eskalation per Interrupt, Mensch als Lieferant, Gedächtnis (c) klein und optional |
| 47 | 16.11. | Safeguarding (minimal prompt-basiert), Evaluation | voller Eval-Lauf, Ergebnisfolie, Demo (ADR 0012) |
| 48 | 23.11. | Abschlusspräsentation | Demo |

## 4. Entscheide (Details und «kippt, wenn» in `docs/adr/`)

| # | Entscheid | Status |
| --- | --- | --- |
| D1 / ADR 0001 | Use-Case Einkaufsagent; Fallback Invoice Guard, falls Variante (a) schon fast fehlerfrei ist | angenommen |
| D2 | Apertus nur als Referenzzeile | angenommen; kein Apertus-Chatmodell im LiteLLM, nur Ausblick |
| D3 | Recherche just-in-time als Spike mit ADR | angenommen |
| D4 | Hermetische Evals: feste Szenarien und Seeds | angenommen |
| D5 | Modelle über FHNW-LiteLLM | angenommen |
| D6 | Konditionen-Nachverhandlung mit Paketen statt freiem Feilschen | angenommen |
| D7 | LLM-Lieferant aus anderer Modellfamilie als der Agent | entfällt (ADR 0009) |
| ADR 0002 | Prozess v2: LLM extrahiert und formuliert, Code bewertet und entscheidet | angenommen 11.10.2026 |
| ADR 0003 | Regelbasierter Lieferanten-Simulator für die Eval | angenommen; LLM-Simulator entfällt (ADR 0009) |
| ADR 0004 | Kandidaten: gpt-5.6-luna, azure_ai/gpt-oss-120b, azure_ai/mistral-large-3 + Regel-Referenz; **Arbeitsmodell gpt-5.6-luna** | angenommen (Benchmark 06.10., Nachmessung 11.10., Proxy-Nachtrag 19.10.2026) |
| ADR 0005 | ERP-light: 3 Funktionen über SQLite `:memory:` | angenommen 11.10.2026; MCP-Teil ersetzt durch ADR 0009 |
| ADR 0006 | D1-Spike: Variante (a) nicht fast fehlerfrei, Hybrid-Story trägt; kein Invoice Guard | angenommen |
| ADR 0007 | Schlanke Prozessfassung `_v2`: ohne Timer und LLM-Strategie, ein Gedächtnis, ohne 1:3 | angenommen 11.10.2026; RAG und Tool-Wahl ersetzt durch ADR 0009 |
| ADR 0008 | Eskalation nur, wenn das Mandat den Entscheid nicht abdeckt; Behauptungen ändern das Mandat nie; S09 nur Deal | angenommen 11.10.2026 |
| ADR 0009 | Prozess `_v3`: ohne MCP und RAG, keine Tool-Wahl durch das LLM, Protokoll mit Paketwahl als Gedächtnis, Mensch als Lieferant; MCP nur lesend als Ausbau | angenommen 19.10.2026 |
| ADR 0010 | Synthetische Daten: Code würfelt, Claude Opus kleidet ein, Code prüft; Testset von anderer Modellfamilie | angenommen 19.10.2026 |
| ADR 0011 | `ibm/granite4.1:3b` als Ablationszeile; Spike Klassifikation (Luna, tev1, Regeln) in KW44 | angenommen 19.10.2026, Ergebnis offen |
| ADR 0012 | Demo «Greift den Agenten an», Ergebnisfolie als Kampagne, Live-Runden mit Spielkarte | angenommen 19.10.2026 |

## 5. Architektur heute (Variante a)

- Graph `src/einkaufsagent/graph_a.py`: `load_context → negotiate ⇄ send_and_wait → finalize`.
  `negotiate` ist ein LLM-Node (`LLMPolicy`, strukturierte Ausgabe `AgentTurn`); er bündelt die
  BPMN-Schritte Strategie, Pakete, Formulieren, Extrahieren und Bewerten.
- Lieferant: `supplier_sim.py`, regelbasiert. Konzessionsbudget nach Faratin et al. (1998), Geduld,
  Gegenangebot durch Kürzen des besten Pakets, optional Preisforderung, Prompt Injection und Bedingung
  ausserhalb des Mandats (nur im Text).
- Referenz ohne LLM: `RuleBasedPolicy` (lineare Konzession, 3 MESO-Pakete, Annahme nach AC_next; lehnt die erste
  Forderung ab und eskaliert die wiederholte). Löst S11 absichtlich nicht, weil sie den Text nicht liest.
- Szenarien: `data/scenarios/dev.jsonl` (11 Stück), erzeugt und gegen die ZOPA geprüft mit
  `scripts/build_scenarios.py`. 7 × Deal (S09 mit Injection, nur Deal korrekt), 2 × ohne ZOPA, 2 × Eskalation
  (S08 wiederholte Preisforderung, S11 Laufzeit-Bedingung).
- Eval: `eval.py`, Metriken in `docs/eval-metriken.md`. Benchmark: `benchmark.py`.
  Modellprüfung: `check_models.py`.
- Prozess: gültig ist `einkaufsagent-prozess_v3.bpmn` im Root (Kopie in `docs/process/`). Zuordnung BPMN →
  LangGraph in `docs/process/README.md`. Generator `docs/process/gen_bpmn_v3.py`; jede Änderung als neue Datei
  `_v4`, danach validieren und rendern.

**Invarianten – nie brechen**
- Verdeckte Lieferantenparameter (`hidden` im Szenario) gelangen nie in den Graph-State, einen Prompt oder
  LangSmith-Metadaten. Der Simulator kommt per Closure in den Graphen; der Canary-Test in
  `tests/test_graph_and_isolation.py` muss grün bleiben.
- Rundenlogik wie BPMN v2: `round` zählt Angebotsrunden. Ein Gegenangebot ist auch nach der letzten Runde
  annehmbar. «accept» gilt nur für das letzte Gegenangebot; eine abgelehnte Annahme zählt als Runde.
- Ab Variante (b) entscheidet nur Code über Zahlen und Mandat; das LLM extrahiert und formuliert.
- Behauptungen des Lieferanten ändern das Mandat nie; eskaliert wird nur nach ADR 0008. Richtlinie und Protokolle
  liefern Kontext, keine Grenzen (ADR 0009).

## 6. Stand am 19.10.2026

Erledigt:
- BPMN-Review mit Befundtabelle; v2 geprüft mit bpmn-moddle, bpmnlint «recommended» und bpmn-js 18.31.0,
  jeweils ohne Befund. Artefakte 2 und 3 im SW4-Dokument angepasst.
- Repo-Gerüst: Python 3.12, uv-Lockfile, langgraph 1.2.12, langchain-openai 1.6.7, langsmith 0.14.4,
  pydantic 2.13.5.
- 11 Szenarien, Variante (a), Eval, Benchmark, Modellprüfung; 24 Offline-Tests grün; ruff sauber.
- Offline-Baseline der Regel-Referenz: 10/11 korrekt (S11 absichtlich nicht), Ø 2,3 Runden, gesicherter
  Spielraum 0,71.
- KW42 abgeschlossen (Session 06.10.2026):
  - LiteLLM `https://litellm.engines.aisl.science`; LangSmith-Konto in der EU-Region (`LANGSMITH_ENDPOINT`
    nötig), Projekt `einkaufsagent`. Repo: github.com/mpasamonm/hs2026_gen_ai_agent_systems_einkaufsagent (privat).
  - `ea-check-models`: Luna `function_calling`, gpt-oss und Mistral nur `json_schema` (ADR 0004).
  - Preise in `config/models.toml` sind die FHNW-Preise aus `/model/info` des Proxys.
  - Tracing nachgewiesen (`verhandlung-S04`, 10 Graph-Knoten, 4 LLM-Aufrufe).
  - Benchmark: Luna 0,80 Erfolg, 0 Verstösse, 0.0028 USD pro Erfolg → Arbeitsmodell (ADR 0004).
  - D1-Spike und Fehlerbilder in ADR 0006; Zielwerte in `docs/eval-metriken.md` und Artefakt 4 justiert.
  - `scripts/analyse_fehlerbilder.py` wertet `runs.jsonl` aus (Leaks, Text ohne Konditionen, verpasste Annahmen, S09).
- Session 11.10.2026:
  - `angebote_ohne_konditionen` und `verpasste_annahmen` fest in `eval.py` und Benchmark-Tabelle
    (`tests/test_eval_metrics.py`); das Skript nutzt dieselbe Logik, Zahlen aus ADR 0006 unverändert reproduziert.
  - Team-Feedback eingearbeitet: ADR 0002, 0005, 0007 angenommen; RAG auch beim Extrahieren, nicht im
    Angebotstext; neue ADR 0008 (Eskalationsregel, gegen Denial of Service). S09 erwartet nur einen Deal (ein
    kurzer Zwischenentscheid «Eskalation auch korrekt» ist damit hinfällig).
  - Simulator mit Bedingung ausserhalb des Mandats, neues S11; Metriken `unnoetige_eskalationen` und
    `verspaetete_eskalationen`; Prompt (a) Regeln 2 und 6 angepasst; Regel-Referenz lehnt erste Forderung ab.
  - Nachmessung (ADR 0008): Luna 0,73 Erfolg, 0,67 Abschluss, 0 Verstösse; LLMs erkennen S11, verpassen aber S08
    meist; Luna eskaliert S09 zweimal unnötig. Zwei Läufe schwanken um bis zu 9 Prozentpunkte.
  - BPMN `_v2` angepasst (RAG-Verbindung zu «Antwort extrahieren», Gateway «Mandat reicht nicht oder unklar»),
    validiert (moddle, bpmnlint, bpmn-js je 0) und gerendert; Kopie in `docs/process/`.
- Session 19.10.2026 (Konzept final, kein Code):
  - Folien SW5 und SW6 eingeordnet: SW5 Folie 23 entspricht der Kernthese; SW6 Folie 26 («Eigenes Tool oder MCP?»)
    stützt `_v3`; Folien 27–28 (Fehlerbehandlung) und 30–40 (Decision Models) führten zu ADR 0009 und 0011.
  - Proxy-Stand geprüft (ADR 0004 Nachtrag, ADR 0011): neu u.a. Claude Haiku 5.5, granite4.1:3b, tev1:0.8b; Jev nicht
    im Proxy. Smoke-Test tev1 (5 Fälle): Injection-Fall als Annahme gewertet.
  - ADR 0009–0012 angenommen, ADR 0003/0004/0005/0007 nachgeführt; `_v3` gültig (moddle 0, bpmnlint 0, Generator
    byte-gleich), Kopie in `docs/process/`, Mapping nachgeführt.
  - `docs/gesamtsystem.md`: `_v3`, Walmart-Pilot (Kanada 2021, 89 Lieferanten, 11 Tage), Abschnitte 8 «Was wir
    gewählt haben und warum» und 9 «Abdeckung der Modulthemen» (inkl. OWASP LLM Top 10 2026); `docs/eval-metriken.md`
    mit geplanten Metriken; `docs/sw4-artefakte.md` als abgelöst markiert. Kein `docs/plan.md`; der Wochenplan bleibt
    lokal in `kontext/`.

## 7. Nächste Schritte in dieser Reihenfolge

1. **Bau-Session KW43** (Prompt `kontext/UEBERGABE-PROMPT-KW43-bau-b.md`): Variante (b) nach `_v3` mit
   `gpt-5.6-luna`: `offer_engine`, `narrate`, `mandate_guard` + `template_message`, `parse_response` (austauschbar;
   Paket, Gegenangebot, Aussagen mit Typ; kurze Richtlinie im Prompt), `assess_response` (ADR 0008, Zurückweisung als
   Vorlage), `notify_supplier`. Kontext weiter aus dem JSON-Stub. Canary-Test auch für (b). Ablation (a) gegen (b) auf
   den 11 Szenarien; Ergebnis als ADR und in `docs/gesamtsystem.md`.
2. **KW44:** Umformulierungen der Simulator-Texte (ADR 0010), Spike Klassifikation (ADR 0011), ERP-Adapter über
   SQLite mit Protokoll und Paketwahl (Metrik `korrekt_gebucht`), Fehlerpfade über die Fail-safes, `_v4`,
   granite-Zeile in der Ablation.
3. **KW45:** synthetisches Testset 12–15 Szenarien, Angriffe, Bias-Varianten (ADR 0010); (a) und (b) auf dem Testset.
4. **KW46:** Eskalation per `interrupt()`, Mensch als Lieferant im Terminal, Gedächtnis (c) klein und optional.
   Danach keine neuen Funktionen mehr.
5. **KW47:** voller Eval-Lauf, Ergebnisfolie, Demo-Probe mit Aufzeichnung, Folien; optional MCP nur lesend (ADR 0009).
6. **Offen (mit den Dozierenden klären):** Abgabetermin und Form der «ausführbaren Lösung», ob eine schriftliche Dokumentation verlangt
   ist; Rollen und Beitrag pro Person in `docs/gesamtsystem.md` festhalten (die Prüfung fragt danach).

## 8. Offene Widersprüche und Hinweise

- Briefing nennt «Folie 38» bzw. «Folie 30»: alte Nummern; aktuell Folie 41 (LiteLLM) und 31 (Pareto). Der Übergabe-
  Prompt vom 19.10. nennt «Folie 25 Eigenes Tool oder MCP?»; es ist SW6 Folie 26.
- Briefing plant eine Frontier-Referenz; im LiteLLM gibt es keine. Ersatz: Regel-Referenz (ADR 0004).
- SW4 Artefakt 4 plant rund 30 Szenarien (20 Dev, 10 Test); heute 11 Dev, das Testset (12–15) entsteht synthetisch
  (ADR 0010). `docs/sw4-artefakte.md` ist abgelöst und spiegelt noch `_v1` und die alte Eskalationsregel.
- SW4-Modellauswahl nennt GLM-5.3-Flash und DeepSeek V4.1 Flash; beide sind nicht im LiteLLM.
- **Proxy (19.10.2026):** Function Calling geht mit Luna, Claude Haiku 5.5 und `gpt-5.4-mini-new`; gpt-oss, Mistral und
  `ibm/granite4.1:3b` (Ollama ignoriert `tool_choice`) nur mit `json_schema`. `azure_ai/gpt-6-luna` liefert bei Chat
  und JSON Schema 404, `azure_ai/decision-1` «DeploymentNotFound». Modelle vor jedem Lauf mit `ea-check-models` prüfen.
- **Jev ist nicht im FHNW-Proxy** (Annahme vom 19.10. widerlegt). Erreichbar ist nur `tev1:0.8b` (Together AI,
  Qwen3.5-0.8B, nicht Jev) über `/v1/systemone`; SW6 Folie 40 zeigt dasselbe. Jev selbst nur über api.typesafe.ai mit
  eigenem Key, Betrieb in den USA.
- MCP-Versionsfalle (nur für den optionalen Ausbau): `langchain-mcp-adapters` 0.3.2 verlangt `mcp<2.0`, das SDK steht
  bei 2.3.0; `langchain.mcp` ist Beta und verlangt `langchain-core` ≥ 1.6.9 (gepinnt 1.6.6). Mit FastMCP 4.x laufen
  synchrone Tools im Threadpool: SQLite dann mit `check_same_thread=False`. SW6 Folie 29 betont OAuth; die Hauptänderung
  der Spec 2026-07-28 ist, dass MCP zustandslos wird.
- OWASP LLM Top 10: Massgeblich ist die Fassung 2026 (PDF, Aug. 2026), Reihenfolge anders als 2025; die Landing-Page
  zeigt noch 2025. Zusätzlich gibt es die Agentic Top 10 (Dez. 2025).
- Startcheck: `uv run ea-eval --policy rule` rechnet mit 1 Wiederholung (1 Verstoss in S11); die 3 Verstösse aus den
  Übergaben gelten für `--repeats 3`.
- Synthetische Texte erzeugt Claude Opus über Claude Code (ADR 0010); das ist nicht per Skript wiederholbar, deshalb
  werden die Daten eingefroren und Prompt, Modell und Datum neben den Daten abgelegt.
- Der Simulator bewertet die strukturierten Pakete, nicht den Text. Text-Paket-Widersprüche und Täuschung misst erst
  `mandate_guard` (b). Die Regel-Referenz löst alle Szenarien ausser S11; der Nutzen des LLM zeigt sich gegen
  Umformulierungen (KW44) und Menschen (Live-Runden). Limitation für die Präsentation (ADR 0006, 0008).
- BPMN liegt doppelt: `docs/process/einkaufsagent-prozess.bpmn` und `einkaufsagent-prozess_v3.bpmn` im Root
  (byte-gleich, gültig seit 19.10.2026). Änderungen als neue Root-Datei, alte behalten; die nächste heisst `_v4`.
  Namensfalle: Datei `_v1` = «Prozess v2» (ADR 0002). Im Team nur Dateinamen verwenden.
- Rendern braucht unter WSL `libasound2t64` (ohne sudo: `apt-get download`, `dpkg -x`, `LD_LIBRARY_PATH`), siehe
  `docs/process/README.md`.
- Neuer Auftrag auf Folie 43 der aktuellen SW4-Fassung: DeepLearning.AI-Video «AI Agents in LangGraph»
  (Kapitel siehe Moodle).

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
uv run ea-eval --policy rule --repeats 3          # offline-Baseline: 0.909, 3 Verstösse (S11)
uv run ea-check-models                            # braucht .env
uv run ea-run --scenario S04 --model gpt-5.6-luna
uv run ea-eval --model gpt-5.6-luna --repeats 3
uv run ea-benchmark --repeats 3
uv run python scripts/build_scenarios.py          # Szenarien neu erzeugen und prüfen
# BPMN (optional, Node 22 + Playwright-Chromium; Details und WSL-Hinweis in docs/process/README.md):
cd docs/process && npm install && python3 gen_bpmn_v3.py ../../einkaufsagent-prozess_v3.bpmn \
  && node validate.mjs ../../einkaufsagent-prozess_v3.bpmn \
  && uv run --no-project --with playwright==1.63.0 python render.py \
     ../../einkaufsagent-prozess_v3.bpmn ../../einkaufsagent-prozess_v3.png
```
