# ADR 0004 – Modellkandidaten für den Benchmark KW42

- **Status:** angenommen; Arbeitsmodell `gpt-5.6-luna` (Benchmark vom 06.10.2026)
- **Datum:** 05.10.2026, ergänzt 06.10.2026
- **Quelle der Modellliste:** Dropdown im FHNW-LiteLLM (Screenshot vom 05.10.2026)

## Kontext

Im LiteLLM-Proxy verfügbar: `gpt-5.6-luna`, `azure_ai/gpt-oss-120b`, `azure_ai/mistral-large-3`,
`azure_ai/gpt-5.4-mini`, `azure_ai/kimi-k2.7-code`, `leoipulsar/harrier-0.6b:latest`,
`andreasmartin/apertus-v1.1-swiss-embed-0.4b`. Der Agent fällt in die Kategorie «Multi-Turn/Reasoning»:
strukturierte Ausgabe ist Pflicht, Function Calling ab KW43 (MCP).

## Entscheid

| Modell | Rolle | Stand | Reife |
| --- | --- | --- | --- |
| `gpt-5.6-luna` | Arbeitsmodell, proprietär, günstig | OpenAI, 09.07.2026; laut OpenRouter Tool Calling und Structured Outputs, 0.20/1.20 USD pro Mio. Tokens | current default |
| `azure_ai/gpt-oss-120b` | offenes Modell (Apache 2.0) | OpenAI, Aug. 2025 | stable; Tool Calling auf Azure war 2025 defekt (LangChain-Issue #32425) |
| `azure_ai/mistral-large-3` | offenes Modell, andere Familie, EU-Anbieter | Mistral, 02.12.2025, Apache 2.0, 675B MoE / 41B aktiv | stable; Function Calling in der Ankündigung nicht genannt, unverified |

Daneben die **Regel-Referenz ohne LLM** als Untergrenze, die jedes Modell schlagen muss.
Die Methode der strukturierten Ausgabe (`function_calling` oder `json_schema`) setzt `ea-check-models`
pro Modell; Entscheidungsregel im Benchmark: Kandidaten mit Mandatsverstössen fallen für Variante (a) weg,
unter den übrigen gewinnt die niedrigste «Kosten pro Erfolg».

## Verworfene Alternativen

| Alternative | Grund |
| --- | --- |
| `azure_ai/gpt-5.4-mini` (17.03.2026) | ältere, kleinere Schwester von Luna; gleiche Familie, kein Erkenntnisgewinn |
| `azure_ai/kimi-k2.7-code` (Juni 2026) | auf Coding spezialisiert |
| `harrier-0.6b`, `apertus-v1.1-swiss-embed-0.4b` | Embedding-Modelle; Kandidaten für RAG in KW44 |
| Frontier-Referenz (Briefing: «günstig, offen, Frontier») | im LiteLLM nicht verfügbar; Ersatz: Regel-Referenz |
| Apertus als Referenzzeile (D2) | kein Apertus-Chatmodell im LiteLLM; nur über die Swiss AI Research Platform (zweiter Key), nach KW42 |

## Ergebnis `ea-check-models` (06.10.2026)

Alle sieben Modelle sind im Proxy (`https://litellm.engines.aisl.science`). Preise aus `/model/info` des Proxys.

| Modell | Function Calling | JSON Schema | gesetzt | USD/Mtok in / out (FHNW) |
| --- | --- | --- | --- | --- |
| `gpt-5.6-luna` | ok | ok | `function_calling` | 0.20 / 1.20 |
| `azure_ai/gpt-oss-120b` | leere Ausgabe | ok | `json_schema` | 0.15 / 0.60 (OpenRouter-Schätzung war 0.03 / 0.17) |
| `azure_ai/mistral-large-3` | Fehler 422 (Azure) | ok | `json_schema` | 0.50 / 1.50 |

Jeder Kandidat liefert strukturierte Ausgabe; die Kipp-Bedingung «weder Function Calling noch JSON Schema» tritt
nicht ein, `azure_ai/gpt-5.4-mini` rückt nicht nach. Die Proxy-Metadaten melden `supports_function_calling` auch für
gpt-oss und Mistral; der Test widerlegt das. Für KW43 (MCP, Tool-Use) heisst das: Function Calling geht über den
Proxy derzeit nur mit Luna verlässlich.

## Ergebnis Benchmark (06.10.2026)

`uv run ea-benchmark --repeats 3`, Variante (a), 10 Szenarien × 3 Wiederholungen; Kosten mit FHNW-Preisen.
«Ohne Konditionen» (Anteil Angebote ohne Zahl im Text) und «Verpasste Annahmen» (Läufe) am 11.10.2026 aus denselben
`runs.jsonl` nachgerechnet; seither Teil von `eval.py` und der Benchmark-Tabelle.

| Policy | Erfolg | pass^3 | Abschluss | Verstösse | Ø Runden | Spielraum | Leak | Ohne Konditionen | Verpasste Annahmen | Kosten USD | USD/Erfolg | Latenz p50 / p95 s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Regel-Referenz | 1.00 | 1.0 | 1.00 | 0 | 2.30 | 0.715 | 0 | 0 | 0 | 0 | 0 | – |
| `gpt-5.6-luna` | 0.80 | 0.6 | 0.71 | 0 | 3.13 | 0.178 | 0 | 0.83 | 3 | 0.067 | 0.0028 | 3.2 / 6.4 |
| `azure_ai/gpt-oss-120b` | 0.67 | 0.6 | 0.52 | 0 | 2.80 | 0.369 | 0.13 | 0.19 | 3 | 0.084 | 0.0042 | 6.1 / 8.7 |
| `azure_ai/mistral-large-3` | 0.83 | 0.7 | 0.95 | 4 | 2.17 | 0.170 | 0 | 0.17 | 1 | 0.077 | 0.0031 | 54.0 / 100.6 |

**Entscheid nach der Regel oben:** Mistral Large 3 fällt wegen 4 Mandatsverstössen weg (Abschlüsse unter dem
Mindestnutzen in 4 von 30 Läufen); zudem verfehlt es das Latenzziel < 10 s deutlich. Unter Luna und gpt-oss hat
Luna die niedrigsten Kosten pro Erfolg (0.0028 gegen 0.0042 USD) und ist auch bei Leak (0 gegen 13 %),
KI-Hinweis (100 gegen 80 %) und Latenz besser. **Arbeitsmodell ist `gpt-5.6-luna`.** gpt-oss bleibt als offenes
Vergleichsmodell in der Ablation, Mistral als Vertreter einer anderen Modellfamilie (D7, LLM-Lieferant ab KW46).

Einschränkungen: `benchmark.py` verlangt im Docstring zusätzlich pass^k ≥ Zielwert (70 %, Annahme). Diesen Wert
erreicht nur Mistral, das wegen der Verstösse ausscheidet; angewendet wurde deshalb die Regel dieses ADR.
Ein Szenario entspricht 10 Prozentpunkten; die Erfolgsquoten liegen innerhalb der Unschärfe von etwa
20 Prozentpunkten. Die Wahl hängt deshalb nicht an der Kostendifferenz allein: Luna ist zusätzlich in jeder
Sicherheitsmetrik (Leak, KI-Hinweis) besser. Der volle Benchmark kostete 0.23 USD.

## Kippt, wenn

`ea-check-models` zeigt, dass ein Kandidat weder Function Calling noch JSON Schema zuverlässig liefert;
dann `azure_ai/gpt-5.4-mini` nachrücken lassen. Oder das Kostenlimit des Keys reicht nicht für
3 Modelle × 10 Szenarien × 3 Wiederholungen (pro Modell typisch 100–250 LLM-Aufrufe:
30 Läufe × 2–7 Entscheide, plus Korrekturrunden).
