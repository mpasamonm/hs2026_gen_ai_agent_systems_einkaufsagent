# Einkaufsagent – Verhandlungsagent «Einkauf»

Gruppenarbeit «Generative KI und Agentensysteme», FHNW Hochschule für Wirtschaft, HS 2026.
Ein LangGraph-Agent verhandelt für die fiktive Musterhandel AG Zahlungsziel, Rabatt und Mengenzusage
mit kleineren Lieferanten nach, strikt innerhalb eines Mandats des Einkaufs (ADR 0001).

**Stand KW43 (19.10.2026):** Variante (a) (reines LLM) und Variante (b) (Hybrid: LLM formuliert und extrahiert,
Code rechnet und entscheidet) laufen gegen einen regelbasierten, simulierten Lieferanten; 11 Entwicklungsszenarien,
Eval, Benchmark, LangSmith-Tracing. Ablation mit `gpt-5.6-luna`: (a) 0.79 Erfolg, (b) 1.00 (ADR 0013).

## Schnellstart

```bash
uv sync                                   # Python ≥ 3.12, Abhängigkeiten aus uv.lock
cp .env.example .env                      # LiteLLM- und LangSmith-Keys eintragen
uv run pytest                             # Offline-Tests, ohne API-Key
uv run ea-run --scenario S04 --policy rule          # eine Verhandlung, Regel-Referenz (offline)
uv run ea-check-models                    # Function Calling / JSON Schema pro Modell prüfen
uv run ea-run --scenario S04 --model gpt-5.6-luna   # dieselbe Verhandlung mit LLM, erscheint in LangSmith
uv run ea-eval --model gpt-5.6-luna --repeats 3     # alle Szenarien, Metriken nach Artefakt 4
uv run ea-eval --variant b --policy rule            # Variante (b) offline (Vorlage + Regex-Parser)
uv run ea-eval --variant b --model gpt-5.6-luna --repeats 3   # Variante (b) mit LLM
uv run ea-benchmark --repeats 3           # drei Modelle + Regel-Referenz, Vergleichstabelle
uv run ea-eval --variant b --model gpt-5.6-luna --repeats 3 --paraphrase   # Simulator mit Umformulierungen (ADR 0010)
```

Ergebnisse landen in `results/` (nicht versioniert): `runs.jsonl` mit vollem Verlauf pro Lauf,
`summary.md` und `summary.json`, beim Benchmark zusätzlich `benchmark.md`.

## Aufbau

| Pfad | Inhalt |
| --- | --- |
| `CLAUDE.md` | Übergabe für neue Sessions: Kontext, Entscheide, Stand, nächste Schritte, Arbeitsweise |
| `kontext/` | lokale Kursunterlagen und Exporte, **nicht im Git** (siehe `kontext/README.md`) |
| `docs/gesamtsystem.md` | Gesamtsystem und Begründungen: Grundlage für Präsentation, Demo und Prüfung |
| `docs/sw4-artefakte.md` | SW4-Artefakte 1–4 (Use-Case, Prozess, Anforderungen, Erfolgskriterien) |
| `docs/adr/` | Architekturentscheide (ADR), Index in `docs/adr/README.md` |
| `docs/process/` | BPMN 2.0 des Soll-Prozesses (`_v3`), Render, Validierungsskripte, Mapping BPMN → LangGraph |
| `docs/eval-metriken.md` | Definition jeder Metrik und des Erfolgskriteriums |
| `data/scenarios/dev.jsonl` | 11 Entwicklungsszenarien; `public` für den Agenten, `hidden` nur für den Simulator |
| `data/paraphrases/` | eingefrorene Umformulierungen der Simulator-Vorlagen, Prompt und Stichprobe (ADR 0010) |
| `scripts/build_scenarios.py` | erzeugt `dev.jsonl` und prüft jedes erwartete Ergebnis gegen die ZOPA |
| `config/models.toml` | Modellkandidaten im FHNW-LiteLLM (ADR 0004) |
| `src/einkaufsagent/domain.py` | Konditionen, Mandat, Käufernutzen, Mandatsprüfung (deterministisch) |
| `src/einkaufsagent/supplier_sim.py` | Lieferanten-Simulator mit verdeckten Parametern, ZOPA-Analyse |
| `src/einkaufsagent/graph_a.py` | LangGraph-Graph Variante (a) |
| `src/einkaufsagent/policies.py` | `LLMPolicy` (Variante a) und `RuleBasedPolicy` (Referenz ohne LLM) |
| `src/einkaufsagent/graph_b.py` | LangGraph-Graph Variante (b) nach `_v3` |
| `src/einkaufsagent/hybrid.py` | Code-Schritte von (b): Nachricht prüfen, Vorlagen, Antwort bewerten (ADR 0008) |
| `src/einkaufsagent/extract.py`, `narrate.py` | austauschbare LLM-Schritte von (b): Antwort extrahieren, Angebot formulieren |
| `src/einkaufsagent/prompts.py` | System-Prompt Variante (a), Prompts für `narrate` und `parse_response` |
| `src/einkaufsagent/eval.py`, `benchmark.py`, `check_models.py`, `run.py` | CLIs |

## Grundsätze

- **Die Evaluation ist die Spezifikation.** Keine Prompt- oder Architekturänderung ohne Messung auf
  denselben Szenarien; das erwartete Ergebnis jedes Szenarios ist aus seinen Parametern hergeleitet.
- **Verdeckte Lieferantenparameter erreichen den Agenten nie.** Der Simulator kommt per Closure in den
  Graphen; ein Canary-Test prüft State und Prompts (`tests/test_graph_and_isolation.py`).
- **LLM schlägt vor, Code entscheidet** – ab Variante (b). Variante (a) ist bewusst die Baseline ohne
  diese Trennung (ADR 0002, 0013).
