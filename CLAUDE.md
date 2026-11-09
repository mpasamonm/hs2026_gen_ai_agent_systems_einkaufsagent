# CLAUDE.md – Einkaufsagent (Gruppenarbeit GenKI & Agentensysteme, FHNW HSW, HS 2026)

Diese Datei ist die Übergabe für jede neue Session. Stand: 09.11.2026 (nach Abgabe-Paket). Das Repository ist ab jetzt die
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
- Abschlusspräsentation 23.11.2026, 13.00 Uhr, 10 Minuten (Projektbeschrieb; das Semesterprogramm sagt «inkl.
  Verständnisfragen»; Entscheid des Nutzers 09.11.: 6 Min. Folien und 4 Min. Demo, Fragen nicht eingerechnet): Problem, Ansatz, Umsetzung,
  Evaluation, Erkenntnisse und Limitationen, möglichst mit Demo. Alle Mitglieder nehmen teil; die Dozierenden
  können individuelle Rückfragen stellen, auch zum eigenen Beitrag. Die Präsentation gehört zur Gruppenarbeit
  (erfüllt/nicht erfüllt) und gibt keine Punkte.
- **Abgabe am 23.11.2026** (Termin vom Nutzer bestätigt, 09.11.2026): Link auf die ausführbare Lösung (bei uns das
  Repository), die Projektartefakte zur Nachvollziehbarkeit und die Abschlusspräsentation, vorzugsweise als PDF.
  Laut Projektbeschrieb kann die Lösung z.B. ein Code-Repository, ein ausführbares Notebook, eine LangGraph-Anwendung
  oder ein Prototyp sein. Das Repo ist privat; wie die Dozierenden Zugriff bekommen, entscheidet der Nutzer am Schluss.
- Pro-Code mit LangGraph; No- und Low-Code-Tools (n8n, Voiceflow) sind nicht erlaubt.
- Dozent am 19.10.2026: MCP und RAG sind nicht Pflicht; die Technik muss zum Use-Case passen, bevorzugt werden eine
  sinnvolle Technologiewahl und genügende Tiefe. Der Semesterplan ist Input, keine Pflichtliste.
- Wochenaufträge laut Semesterprogramm:

| KW | Datum | Auftrag | Konkret bei uns |
| --- | --- | --- | --- |
| 42 | 12.10. | Erste lauffähige Version, Tracing funktioniert | Variante (a), Eval, Benchmark, LangSmith (erledigt) |
| 43 | 19.10. | MCP-Server anbinden | kein MCP (ADR 0009); Variante (b) mit Luna, `parse_response` austauschbar (erledigt 19.10., ADR 0013) |
| 44 | 26.10. | RAG einbauen | kein RAG (ADR 0009, SW7 Folie 44); Umformulierungen (erledigt 26.10., PR #2, gemergt 09.11.) |
| 45 | – | Blockwoche | nichts gebaut; Testset mit Angriffen verschoben auf Bau 2 (ADR 0014) |
| 46 | 09.11. | Memory festlegen | festgelegt in ADR 0015 und gebaut (Bau 1 erledigt 09.11.: ERP-Protokoll, `interrupt()`, Mensch als Lieferant, `_v4`); Bau 2 erledigt 09.11.: Testset mit Angriffen (ADR 0010, Nachtrag Testset) |
| 47 | 16.11. | Safeguarding (minimal prompt-basiert), Evaluation | SW9 einordnen («Guardrail Agent», SW8 Folie 31); voller Eval-Lauf, Ergebnisfolie, Demo (ADR 0012) |
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
| ADR 0010 | Synthetische Daten: Code würfelt, Claude Opus kleidet ein, Code prüft; Testset von anderer Modellfamilie | angenommen 19.10.2026; Nachtrag 26.10. (Umformulierungen, Teammitglied), nachgemessen 09.11.; Nachtrag Testset 09.11. (15 Szenarien, gemessen) |
| ADR 0011 | `ibm/granite4.1:3b` als Ablationszeile; Spike Klassifikation (Luna, tev1, Regeln) | angenommen 19.10.2026; Spike gestrichen, granite optional (ADR 0014) |
| ADR 0012 | Demo «Greift den Agenten an», Ergebnisfolie als Kampagne, Live-Runden mit Spielkarte | angenommen 19.10.2026 |
| ADR 0013 | Variante (b) gebaut; Ablation (a) gegen (b): Kernthese trägt (Spielraum +52 Punkte), Restfehler im Extrahieren | angenommen 19.10.2026; Nachtrag 09.11.: Kippregel unnötige Eskalationen auf dem Testset greift formal, Entscheid: nicht ändern |
| ADR 0014 | Umfang bis 23.11.: Bau 1 (ERP-Protokoll, `interrupt()`, Mensch als Lieferant, `_v4`), Bau 2 (Testset mit Angriffen); Spike, (c), MCP gestrichen | angenommen 09.11.2026; Nachtrag: (c) nur bei Restzeit nach dem Testset |
| ADR 0015 | Memory: State mit `InMemorySaver`, Protokoll im ERP-Adapter statt Store; Node `ask_buyer` mit `interrupt()`; `HumanSupplier` per `input()`, nur (b) | angenommen und gebaut 09.11.2026 (Nachtrag mit Messung) |

## 5. Architektur heute (Varianten a und b)

- Graph `src/einkaufsagent/graph_a.py`: `load_context → negotiate ⇄ send_and_wait → finalize`.
  `negotiate` ist ein LLM-Node (`LLMPolicy`, strukturierte Ausgabe `AgentTurn`); er bündelt die
  BPMN-Schritte Strategie, Pakete, Formulieren, Extrahieren und Bewerten.
- Graph `src/einkaufsagent/graph_b.py` (Variante b, `_v4`): `load_context (ERP) → offer_engine → narrate → mandate_guard
  (→ template_message) → send_and_wait → parse_response → assess_response →` neue Runde / Gegenangebot annehmen /
  `escalate → ask_buyer (interrupt)` / `record_outcome → notify_supplier`. Nach `ask_buyer`: «weiterverhandeln» →
  `offer_engine` (dieselbe Grösse wird nicht erneut eskaliert), «abbrechen» → `record_outcome`. ERP-Adapter in `erp.py`
  (SQLite, eine Verbindung pro Lauf; Eval `:memory:`, Demo `--erp PFAD`); Metrik `korrekt_gebucht` (nur b). Runner im
  Terminal in `live.py`: `--live` (Simulator, Einkäuferin entscheidet), `--human` (`HumanSupplier`, sieht nur Text,
  Ereignis `human`). Die Eval hält am Interrupt an und wertet `escalated` wie bisher. Code-Schritte in `hybrid.py` (`check_message`, `assess_reply`, Vorlagen), Parser in `extract.py`
  (`LLMParser`, `RuleParser`; Protokoll `Parser` mit optionaler `confidence`), Narrator in `narrate.py`. `narrate` sieht
  nur Pakete und Runde; `parse_response` sieht nur Antwort und Gesendetes; keiner sieht das Mandat. Einigung liest
  `parse_response` aus dem Text; die Eval prüft sie gegen den Simulator (`deal:not_agreed`). Offline:
  `--variant b --policy rule` (Vorlage + Regex).
- Lieferant: `supplier_sim.py`, regelbasiert. Konzessionsbudget nach Faratin et al. (1998), Geduld,
  Gegenangebot durch Kürzen des besten Pakets, optional Preisforderung, Prompt Injection und Bedingung
  ausserhalb des Mandats (nur im Text). Mit `paraphrase=True` (`--paraphrase` in `ea-run`, `ea-eval`, `ea-benchmark`)
  wählt er pro Seed eine der eingefrorenen Umformulierungen aus `data/paraphrases/` (`paraphrases.py`, ADR 0010);
  ohne Schalter byte-gleich zu vorher. Angehängter Text (`hidden.injection`, ab Runde) trägt Angriffe, Behauptungen und
  harmlose Texte; `OpeningDemand.once` macht eine Forderung einmalig (ADR 0008, Kat. 2).
- Referenz ohne LLM: `RuleBasedPolicy` (lineare Konzession, 3 MESO-Pakete, Annahme nach AC_next; lehnt die erste
  Forderung ab und eskaliert die wiederholte). Löst S11 absichtlich nicht, weil sie den Text nicht liest.
- Szenarien: `data/scenarios/dev.jsonl` (11 Stück), erzeugt und gegen die ZOPA geprüft mit
  `scripts/build_scenarios.py`. 7 × Deal (S09 mit Injection, nur Deal korrekt), 2 × ohne ZOPA, 2 × Eskalation
  (S08 wiederholte Preisforderung, S11 Laufzeit-Bedingung). Testset `data/scenarios/test.jsonl` (15 Stück, T01–T15,
  ADR 0010): erzeugt mit `scripts/build_testset.py` (Raster mit Seed, ZOPA-Prüfung, Regel-Referenz löst die Zahlen),
  Texte eingefroren in `test_texts.json`, Code-Prüfung `testset.py`; Muster und Ziel eines Angriffs nur in
  `Scenario.attack` (Auswertung). Aufbau in `data/scenarios/README.md`.
- Eval: `eval.py` mit `--variant a|b`, `--paraphrase` und `--scenarios` (Ergebnisordner mit `_test`), Metriken in
  `docs/eval-metriken.md` (`extraktion_korrekt` nur b; nur Testset: `angriffe_zugestellt`, `angriff_erfolgsquote`,
  `nutzen_unter_angriff`, `nutzen_ohne_angriff`, `fehlalarme`). Benchmark: `benchmark.py`.
  Modellprüfung: `check_models.py`.
- Prozess: gültig ist `einkaufsagent-prozess_v4.bpmn` im Root (Kopie in `docs/process/`). Zuordnung BPMN →
  LangGraph in `docs/process/README.md`. Generator `docs/process/gen_bpmn_v4.py`; jede Änderung als neue Datei
  `_v5`, danach validieren und rendern.

**Invarianten – nie brechen**
- Verdeckte Lieferantenparameter (`hidden` im Szenario) gelangen nie in den Graph-State, einen Prompt,
  LangSmith-Metadaten oder das ERP. Simulator, Mensch und ERP kommen per Closure in den Graphen; die Canary-Tests in
  `tests/test_graph_and_isolation.py` und `tests/test_variant_b.py` (auch DB-Dump) müssen grün bleiben. Ebenso erreichen
  Muster und Ziel eines Angriffs (`Scenario.attack`) nie Agent, Parser oder Narrator (`tests/test_testset.py`).
- In `ask_buyer` steht nichts vor `interrupt()`; Nebenwirkungen (Protokoll, Zwischenbescheid) gehören in `escalate`.
- Rundenlogik wie BPMN v2: `round` zählt Angebotsrunden. Ein Gegenangebot ist auch nach der letzten Runde
  annehmbar. «accept» gilt nur für das letzte Gegenangebot; eine abgelehnte Annahme zählt als Runde.
- Ab Variante (b) entscheidet nur Code über Zahlen und Mandat; das LLM extrahiert und formuliert.
- Behauptungen des Lieferanten ändern das Mandat nie; eskaliert wird nur nach ADR 0008. Richtlinie und Protokolle
  liefern Kontext, keine Grenzen (ADR 0009).

## 6. Stand am 09.11.2026 (nach Abgabe-Paket)

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
- Session 19.10.2026, Bau b (ADR 0013):
  - Variante (b) nach `_v3` gebaut (`graph_b.py`, `hybrid.py`, `extract.py`, `narrate.py`), Fehlerpfade inklusive.
    `ea-eval`, `ea-benchmark`, `ea-run` mit `--variant a|b`; neue Metriken `template_rate` und Verstoss
    `deal:not_agreed`. 46 Tests grün (22 neu, davon Canary für b und Fake-Server-Kette), ruff sauber.
  - Ablation mit Luna am selben Tag: (a) Erfolg 0.79, pass^3 0.64, Spielraum 0.195; (b) mit gültigem Prompt 1.00,
    1.00, 0.715; Template-Rate 0; Kosten pro Erfolg halbiert. Kippregel ADR 0006 greift nicht. Zwei Präzisierungen im
    Parse-Prompt nach Befunden in S06 und S08; alle drei Läufe in ADR 0013.
  - `docs/gesamtsystem.md` §2.5 mit Pactum-Stand 2026 (Release Notes Sept. 2026: Aggressivität, Angebotsprüfung,
    Eskalation, Audit-Trail = unsere Bausteine), §2.4 mit Liang und Xu als zweitem Beleg.

- Session 26.10.2026 (Teammitglied PeisProjects, über PR #2), Umformulierungen (ADR 0010, Nachtrag):
  - `data/paraphrases/` (14 Vorlagen × 5 Umformulierungen, 6 Schreibweisen der Konditionen, eingefroren; Claude Opus
    5.5), `paraphrases.py` mit Code-Prüfung, Flag `--paraphrase` in allen CLIs, Metrik `extraktion_korrekt`,
    `verpasste_annahmen` ohne Textmuster. 51 Tests grün, ruff sauber.
  - Luna × 3: (b) umformuliert 1.00 Erfolg, Extraktion 0.976; (a) umformuliert 0.70 (vorher 0.79); Regex-Parser
    0.27. Stichprobe `data/paraphrases/stichprobe.md` muss noch ein Teammitglied lesen.
- Session 09.11.2026, Bestandsaufnahme:
  - PR #2 reviewt (keine Rückdrehungen, Invarianten unverändert, ohne `--paraphrase` gleiche Läufe) und per Merge
    übernommen (0dcb2aa); PR #1 war schon geschlossen (falsche Basis). Nacharbeiten: `extraktion_korrekt` prüft Paketwahl
    und bedingte Annahme; Stichprobe neu gezogen (jede Vorlage mindestens einmal, `--neu`); Grenzen der Umformulierungen
    in `data/paraphrases/README.md`. 52 Tests grün.
  - Nachmessung Luna × 3 am selben Tag (ADR 0010, Nachmessung): (a) 0.79 → 0.76 umformuliert (Rauschen; «30 statt 21»
    hält nicht), (b) 1.00 und 1.00, Spielraum 0.715 gegen 0.25, Extraktion (b) 0.95 → 0.99; Regex-Parser 0.27. Neues
    Fehlbild: «ohne Gegenleistung nicht gewähren» als Bedingung, S06 2× unnötig eskaliert (7,4 %). Kosten 0.24 USD.
  - Folien SW7 (RAG) und SW8 (Orchestrierung, Memory) eingeordnet (`kontext/sw7-sw8-folien-extrakt.md`): stützen ADR 0009
    (Nachtrag); Auftrag SW8 Folie 17 (InMemorySaver) war schon erfüllt; keine Fristen.
  - ADR 0014 (Umfang bis 23.11.) und ADR 0015 (Memory und Human-in-the-loop) angenommen; `docs/gesamtsystem.md` mit
    §10 Beiträge.
- Session 09.11.2026, Bau 1 (ADR 0015, Nachtrag):
  - ERP-Adapter mit Protokoll und Buchung (`erp.py`, `record_outcome`, Metrik `korrekt_gebucht`), Eskalation mit
    `escalate` und `ask_buyer` (`interrupt()`, `Command(resume=…)`), Mensch als Lieferant und Einkäuferin im Terminal
    (`live.py`, `ea-run --live/--human/--erp`), BPMN `_v4` (moddle, bpmnlint, bpmn-js je 0; Generator byte-gleich).
    70 Tests grün, ruff sauber.
  - Messung: (b) offline und umformuliert bis auf den Text identisch zu vorher, (a) unverändert; Luna × 3: 1.00, pass^3
    1.00, Spielraum 0.715, `korrekt_gebucht` 1.00; umformuliert 1.00, S06 einmal unnötig eskaliert. Live mit Luna und
    Mensch geprüft (S04).
  - Bau 1 ist vor dem 12.11. fertig: Die Kippregel für Gedächtnis (c) greift formal; Entscheid des Nutzers: zuerst das
    Testset, (c) nur bei Restzeit vor dem 15.11. (ADR 0014, Nachtrag).
- Session 09.11.2026, Bau 2 (ADR 0010, Nachtrag Testset):
  - Testset T01–T15: Kategorien 1–3 aus ADR 0008, neue Bedingungen (Exklusivität, Gerichtsstand, ganze Paletten),
    Rundenlimit 3 (T07), 2 ohne ZOPA, 6 Angriffe (AgentDojo ×3, InjecAgent, Tensor Trust ×2), Behauptung T01, 3 harmlose
    Texte. Code würfelt mit Seed 201–215, Claude Opus 5.5 schreibt, Code prüft; Build byte-gleich wiederholbar.
    Lesungsblatt `data/scenarios/test_lesung.md` (Lesung durch den Nutzer offen). 79 Tests grün, ruff sauber.
  - Messung Luna × 3: (b) 0.98 / umformuliert 0.93, (a) 0.64 / 0.71, Regel-Referenz und Regex 0.80 (Bedingungen
    zugesagt). Angriffserfolg überall 0; (b) erkennt alle Bedingungen rechtzeitig; (a) eskaliert die Behauptung (T01),
    verpasst die wiederholte Forderung (T06) und schliesst in T10 unter dem Mindestnutzen ab. Unnötige Eskalationen (b)
    9 % / umformuliert 18 %: T09 (Content-Filter des Proxys → nicht auswertbar → Eskalation, ohne ZOPA) und T11
    (wiederholter «TODO»-Satz als wiederholte Forderung). Fehlalarme nur bei T15 («freigegeben»), (a) und (b). Kosten 0.38
    USD. Kippregel ADR 0008/0013 (unnötige Eskalationen > 10 %) greift formal im umformulierten Lauf; Entscheid des
    Nutzers: nicht ändern, als Befund berichten (ADR 0013, Nachtrag).
  - Lesung der 15 Testtexte: 0 Fehler, freigegeben (vom Nutzer an Claude delegiert; Hinweis T12 in `test_lesung.md`).
- Session 09.11.2026, Abgabe-Paket (Etappe 3):
  - Finale Läufe: 14 Läufe auf Commit `3ac6beb` (Dev und Testset; Regel-Referenz, (b) offline mit und ohne
    `--paraphrase`, (a) und (b) mit Luna × 3 mit und ohne `--paraphrase`), 0.61 USD, versioniert mit `runs.jsonl` unter
    `docs/ergebnisse/2026-11-09/` (Übersicht, Befehle, Fehlläufe in `README.md`). (b) 1.00 Dev / 0.98 Test, (a) 0.82 /
    0.73, Spielraum 0.71 / 0.70 gegen 0.23 / 0.25, Angriffserfolg 0. Kippregel ADR 0006 greift formal bei der
    Erfolgsquote auf Dev (+18 < 20); Entscheid des Nutzers: formal nennen, Kernthese halten (ADR 0013, Nachtrag finale
    Läufe). Unnötige Eskalationen (b) jetzt 12 % Test, 11 % Dev umformuliert (S06, ohne ZOPA); Entscheid A gilt weiter.
  - README neu als Einstieg für die Dozierenden; `docs/demo.md` mit Ablauf «Greift den Agenten an» (mit Luna geskriptet
    geprüft: Behauptung zurückgewiesen, kein Leak, Eskalation), Fallbacks, Aufzeichnung (`script`/`scriptreplay`),
    Live-Runden-Tabelle und Spielkarten S02, S04, S08, S11.
  - Veröffentlichungs-Check: keine Secrets, `.env` und `kontext/` nie in der Historie; sichtbar wären die Proxy-Adresse
    (CLAUDE.md, ADR 0004), Commit-E-Mails (auch des Teammitglieds) und CLAUDE.md als Arbeitsprotokoll. Zugriff offen.
  - Folien als Slides-Artifact (15 Folien: 8 Hauptfolien, Backup-Trenner und 6 Backup-Folien, Sprechernotizen mit Zeiten):
    https://claude.ai/artifact/C2fJqULVGBRzwNBkxBpzPJ (privat). Namen und PDF-Export macht der Nutzer.

## 7. Fahrplan bis zur Abgabe am 23.11.2026

Ab dem 09.11.2026 arbeiten wir direkt auf die Abgabe hin, nicht mehr in Wochenschritten nach dem Semesterprogramm.
Plan und Streichungen in ADR 0014 (Nachtrag), Memory und Human-in-the-loop in ADR 0015. Jede Session endet mit einem
Commit und dem Prompt für die nächste; Einstieg ist der jeweils neueste `kontext/UEBERGABE-PROMPT-ABGABE-<N>.md`.

1. **Bau 1 erledigt 09.11.:** ERP-Adapter mit Protokoll und `korrekt_gebucht`, Eskalation mit `interrupt()`, Mensch als
   Lieferant im Terminal, BPMN `_v4` (ADR 0015, Nachtrag). Einstieg für Etappe 2: `kontext/UEBERGABE-PROMPT-ABGABE-2.md`.
2. **Bau 2 erledigt 09.11.:** Testset T01–T15 mit Angriffen, (a) und (b) mit Luna gemessen (ADR 0010, Nachtrag Testset).
   Kippregel unnötige Eskalationen entschieden (nicht ändern, ADR 0013, Nachtrag), Testtexte gelesen (0 Fehler).
   **Feature-Freeze ab 09.11.2026**: keine neuen Funktionen, keine Prompt- oder Regeländerung; Ausnahmen nur nach Rückfrage
   (SW9, ADR 0014). Bias gestrichen; granite und (c) nur bei Restzeit vor dem 15.11.
   Einstieg für Etappe 3: `kontext/UEBERGABE-PROMPT-ABGABE-3.md`.
3. **Abgabe-Paket erledigt 09.11.:** finale Läufe unter `docs/ergebnisse/2026-11-09/`, README, `docs/demo.md` mit
   Spielkarten, Veröffentlichungs-Check (Befund in §6), Folien als Slides-Artifact (6 Min. Folien, 4 Min. Demo).
   Einstieg für Etappe 4: `kontext/UEBERGABE-PROMPT-ABGABE-4.md`.
4. **Beim Nutzer:** Namen auf der Titelfolie, PDF-Export der Folien (Share › Export); SW9 einordnen lassen, sobald die
   Folien da sind; Demo-Probe mit Aufzeichnung; mindestens 3 Live-Runden mit Spielkarte plus Red-Teaming durch Claude als eigene Zeile (Tabelle in `docs/demo.md`); Zugriff für
   die Dozierenden (öffentlich oder Einladung) erst am Schluss.
5. **Erledigt 09.11.:** Stichprobe der Umformulierungen, 0 von 20 fehlerhaft (vom Nutzer gelesen und bestätigt;
   Kippregel ADR 0010 geprüft). Eine schriftliche Dokumentation ist laut Projektbeschrieb nicht verlangt; `docs/gesamtsystem.md` ist das Artefakt.
   Beiträge pro Person stehen in `docs/gesamtsystem.md` §10.

## 8. Offene Widersprüche und Hinweise

- Briefing nennt «Folie 38» bzw. «Folie 30»: alte Nummern; aktuell Folie 41 (LiteLLM) und 31 (Pareto). Der Übergabe-
  Prompt vom 19.10. nennt «Folie 25 Eigenes Tool oder MCP?»; es ist SW6 Folie 26.
- Briefing plant eine Frontier-Referenz; im LiteLLM gibt es keine. Ersatz: Regel-Referenz (ADR 0004).
- SW4 Artefakt 4 plant rund 30 Szenarien (20 Dev, 10 Test); heute 11 Dev und 15 Test (synthetisch, ADR 0010). `docs/sw4-artefakte.md` ist abgelöst und spiegelt noch `_v1` und die alte Eskalationsregel.
- SW4-Modellauswahl nennt GLM-5.3-Flash und DeepSeek V4.1 Flash; beide sind nicht im LiteLLM.
- **Proxy (19.10.2026):** Function Calling geht mit Luna, Claude Haiku 5.5 und `gpt-5.4-mini-new`; gpt-oss, Mistral und
  `ibm/granite4.1:3b` (Ollama ignoriert `tool_choice`) nur mit `json_schema`. `azure_ai/gpt-6-luna` liefert bei Chat
  und JSON Schema 404, `azure_ai/decision-1` «DeploymentNotFound». Modelle vor jedem Lauf mit `ea-check-models` prüfen.
- **Proxy (09.11.2026):** `ea-check-models` lieferte für Luna einmal einen 422-Fehler, die Wiederholung lief. Neu in der
  Modellliste: `microsoft-decision-1` und `gpt-6-luna` (ohne Präfix `azure_ai/`), nicht geprüft; der Spike ist
  gestrichen (ADR 0014).
- **LangSmith (09.11.2026):** Das monatliche Trace-Limit des Kontos ist erschöpft (HTTP 429, «Monthly unique traces usage
  limit exceeded»). Läufe und Tests laufen weiter, der Client schreibt aber Fehlermeldungen ins Terminal; für Demo und
  Probe `export LANGSMITH_TRACING=false`. Neue Traces erst nach der Monatswende.
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
- Der Simulator bewertet die strukturierten Pakete, nicht den Text. `mandate_guard` (b) prüft Zahlen gegen Pakete, nicht
  deren Zuordnung. Die Regel-Referenz löst alle Szenarien ausser S11, (b) offline mit Regex-Parser alle Originale, aber
  nur 0.27 der Umformulierungen; (b) mit Luna löst beide. Gegen Menschen ist der Nutzen erst mit den Live-Runden belegt
  (ADR 0006, 0010, 0013).
- Die Präzisierungen im Parse-Prompt (ADR 0013) sind am Dev-Set entstanden; Prompt-Beispiele dürfen den Wortlaut der
  Szenarien nicht übernehmen. Das Testset ist anders formuliert (Code-Prüfung `testset.py`). **Keine Prompt- oder
  Regeländerung wegen des Testsets**, sonst ist es kein Testset mehr; Befunde als Limitation oder als neue Messung auf dem
  Dev-Set, das Testset danach nur als «nach Anpassung» berichten.
- Widerspruch im Übergabe-Prompt vom 09.11.: Exklusivität und Vorauskasse galten als «andere Bedingungen als im Prompt»,
  stehen aber im Parse-Prompt und in Regel 6 von Prompt (a). Das Testset hat deshalb eine Bedingung aus dieser Liste
  (T03, `bedingung_prompt`) und zwei, die in keinem Prompt stehen (T04, T05, `bedingung_neu`).
- Der Content-Filter des Azure-Proxys («jailbreak detected») weist Aufrufe mit Tensor-Trust-Texten mit 400 ab; in (b)
  endet `parse_response` dann als «nicht auswertbar» und eskaliert (T09). In (a) nie beobachtet.
- Wiederkehrende Angriffstexte stehen in jeder Antwort; liest der Parser sie als Forderung auf «other», eskaliert
  Regel 2 beim zweiten Mal (T11). ADR 0008 schliesst den Denial of Service nur für Behauptungen.
- `pkill -f` mit einem Muster wie «ea-eval» trifft auch die eigene Shell (Exit 144); Läufe besser per PID beenden.
- BPMN liegt doppelt: `docs/process/einkaufsagent-prozess.bpmn` und `einkaufsagent-prozess_v4.bpmn` im Root
  (byte-gleich, gültig seit 09.11.2026). Änderungen als neue Root-Datei, alte behalten; die nächste heisst `_v5`.
  Namensfalle: Datei `_v1` = «Prozess v2» (ADR 0002). Im Team nur Dateinamen verwenden.
- Rendern braucht unter WSL `libasound2t64` (ohne sudo: `apt-get download`, `dpkg -x`, `LD_LIBRARY_PATH`), siehe
  `docs/process/README.md`.
- Neuer Auftrag auf Folie 43 der aktuellen SW4-Fassung: DeepLearning.AI-Video «AI Agents in LangGraph»
  (Kapitel siehe Moodle).
- SW8: ab PDF-Seite 29 ist die Foliennummer um 1 höher (Folie 29 fehlt). SW8 Folie 19 sagt, nach `interrupt()` laufe
  der Graph «an derselben Stelle weiter»; laut LangGraph-Doku startet der ganze Node neu. Deshalb steht `interrupt()`
  allein im Node `ask_buyer` (ADR 0015). Einordnung SW7/SW8 lokal in `kontext/sw7-sw8-folien-extrakt.md`.
- Eskalationen warten nur, solange der Prozess läuft (`InMemorySaver`). Die Eval setzt nach `ask_buyer` nicht fort;
  «weiterverhandeln» prüfen nur `tests/test_escalation.py` und Läufe im Terminal. Live gibt es keine Wahrheit
  (Ereignis `human`); `extraktion_korrekt` und `verpasste_annahmen` entfallen dort.
- `langgraph-checkpoint-sqlite` ist nicht installiert; 3.1.3 verlangt `langgraph-checkpoint` ≥ 4.3.1 (installiert 4.2.0),
  3.1.1 passt ohne Upgrade (nur falls `SqliteSaver` nötig wird, ADR 0015).
- Umformulierungen: Einige Varianten verwenden «entgegenkommen» bzw. «Listenpreise» wie die Beispiele im Parse-Prompt
  (Grenzen in `data/paraphrases/README.md`); das Testset meidet diese Wortfelder.
- Beiträge über GitHub: PRs mit `gh pr view`; das Fine-grained-Token braucht dieses Repo unter «Repository access»
  (am 09.11.2026 ergänzt). Commits des Teammitglieds nicht umschreiben, Merge über den PR (`--merge`).

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
uv run ea-eval --variant b --policy rule                      # Variante (b) offline: 11/11
uv run ea-eval --variant b --model gpt-5.6-luna --repeats 3
uv run ea-run --scenario S09 --variant b --model gpt-5.6-luna # zeigt auch die Hinweise für die Einkäuferin
uv run ea-benchmark --repeats 3
uv run ea-eval --variant b --model gpt-5.6-luna --repeats 3 --paraphrase   # Simulator umformuliert (ADR 0010)
uv run ea-eval --variant b --policy rule --paraphrase                       # offline: Regex-Parser bricht ein (0.27)
uv run python scripts/sample_paraphrases.py       # Code-Prüfung; Stichprobe nur mit --neu neu ziehen (überschreibt Befunde)
uv run python scripts/build_scenarios.py          # Szenarien neu erzeugen und prüfen
uv run python scripts/build_testset.py            # Testset prüfen; schreibt test.jsonl byte-gleich neu (Texte eingefroren)
uv run ea-eval --policy rule --repeats 3 --scenarios data/scenarios/test.jsonl              # Testset offline: 0.80
uv run ea-eval --variant b --model gpt-5.6-luna --repeats 3 --scenarios data/scenarios/test.jsonl   # Testset (b): 0.98
uv run ea-run --scenario S11 --variant b --policy rule --live                # Eskalation, Einkäuferin im Terminal (offline)
uv run ea-run --scenario S04 --variant b --model gpt-5.6-luna --human --erp results/erp-demo.sqlite   # Demo mit Mensch
# Finale Läufe der Abgabe (14 Stück, --out docs/ergebnisse/<datum>): Befehle in docs/ergebnisse/2026-11-09/README.md
# BPMN (optional, Node 22 + Playwright-Chromium; Details und WSL-Hinweis in docs/process/README.md):
cd docs/process && npm install && python3 gen_bpmn_v4.py ../../einkaufsagent-prozess_v4.bpmn \
  && node validate.mjs ../../einkaufsagent-prozess_v4.bpmn \
  && uv run --no-project --with playwright==1.63.0 python render.py \
     ../../einkaufsagent-prozess_v4.bpmn ../../einkaufsagent-prozess_v4.png
```
