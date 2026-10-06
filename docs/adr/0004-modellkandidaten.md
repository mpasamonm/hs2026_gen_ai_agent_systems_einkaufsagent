# ADR 0004 – Modellkandidaten für den Benchmark KW42

- **Status:** angenommen, Wahl des Arbeitsmodells nach dem Benchmark
- **Datum:** 05.10.2026
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

## Kippt, wenn

`ea-check-models` zeigt, dass ein Kandidat weder Function Calling noch JSON Schema zuverlässig liefert;
dann `azure_ai/gpt-5.4-mini` nachrücken lassen. Oder das Kostenlimit des Keys reicht nicht für
3 Modelle × 10 Szenarien × 3 Wiederholungen (pro Modell typisch 100–250 LLM-Aufrufe:
30 Läufe × 2–7 Entscheide, plus Korrekturrunden).
