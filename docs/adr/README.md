# Entscheidungslog

Jeder nicht triviale Entscheid: Entscheid, Datum, verworfene Alternativen, Bedingung, unter der er kippt.
D1–D7 stammen aus dem Kontext-Briefing; ab ADR 0002 aus den Sessions ab dem 05.10.2026.

| # | Entscheid | Datum | Verworfen | Kippt, wenn | ADR |
| --- | --- | --- | --- | --- | --- |
| D1 | Use-Case Einkaufsagent | 05.10.2026 | StandortScout, weitere Ideen | reines LLM verhandelt fast fehlerfrei | 0001 |
| D2 | Apertus nur als Referenzzeile | 03.10.2026 | Apertus als Arbeitsmodell | Apertus erreicht den besten offenen Kandidaten | 0004 |
| D3 | Recherche just-in-time als 2-h-Spike mit ADR | 03.10.2026 | Recherchephase vorab | Dozent verlangt Architekturkonzept vor KW42 | – |
| D4 | Hermetische Evals: feste Szenarien und Seeds | 03.10.2026 | Evals gegen Live-Systeme | – | 0003 |
| D5 | Modellzugang über FHNW-LiteLLM | 03.10.2026 | eigenes API-Budget | Kostenlimit reicht nicht | 0004 |
| D6 | Konditionen-Nachverhandlung mit 2–3 Paketen (MESO) | 05.10.2026 | freies Preisfeilschen | Dozent verlangt freie Verhandlung | 0001 |
| D7 | Agent und LLM-Simulator aus verschiedenen Modellfamilien; **entfällt** mit ADR 0009 (kein LLM-Lieferant) | 05.10.2026 | dasselbe Modell auf beiden Seiten | LiteLLM bietet nur eine Familie | 0003, 0009 |
| 0002 | Prozess v2: Code bewertet, LLM extrahiert und formuliert (angenommen 11.10.2026) | 05.10.2026 | LLM-Router, Korrekturschleife, Einzelpakete | Template-Rate > 20 % | 0002 |
| 0003 | Regelbasierter Simulator für die Eval; LLM-Simulator entfällt (ADR 0009), Testset nach ADR 0010 | 05.10.2026 | LLM-Persona, Menschen | Agenten nutzen Textvorlagen aus | 0003 |
| 0004 | Kandidaten Luna, gpt-oss-120b, Mistral Large 3 + Regel-Referenz | 05.10.2026 | gpt-5.4-mini, kimi-k2.7-code | Kandidat ohne strukturierte Ausgabe | 0004 |
| 0005 | ERP-light: MCP-Server mit 3 Tools, synchron, `:memory:` (angenommen 11.10.2026; **teilweise ersetzt** durch ADR 0009: ohne MCP) | 06.10.2026 | voller ERP-Mock, lokale Funktionen, langchain-mcp-adapters | Dozent verlangt LLM-gesteuerten Tool-Use als Kern | 0005 |
| 0006 | D1-Spike: Variante (a) nicht fast fehlerfrei, Hybrid-Story trägt; Arbeitsmodell Luna (ADR 0004) | 06.10.2026 | Wechsel auf Invoice Guard | (b) schlägt (a) um < 20 Prozentpunkte | 0006 |
| 0007 | Schlanke Prozessfassung `_v2`: ohne Timer und LLM-Strategie, RAG beim Extrahieren und in der Eskalation, ein Gedächtnis (angenommen 11.10.2026; **teilweise ersetzt** durch ADR 0009: ohne RAG, ohne Tool-Wahl) | 06.10.2026 | `_v1` unverändert, RAG im Formulieren, Rückfrage-Pfad | Live-Demo mit Mensch als Lieferant; LLM-Lieferant liest Text | 0007 |
| 0008 | Eskalation nur, wenn das Mandat den Entscheid nicht abdeckt; Behauptungen ändern das Mandat nie | 11.10.2026 | jede Forderung eskalieren, LLM entscheidet über Eskalation, nie eskalieren | > 10 % übersehene Bedingungen oder unnötige Eskalationen im Testset | 0008 |
| 0009 | Prozess `_v3`: ohne MCP und RAG, keine Tool-Wahl durch das LLM, Protokoll mit Paketwahl als Gedächtnis, Mensch statt LLM-Lieferant | 19.10.2026 | MCP als ERP-Adapter, RAG, LLM wählt Tools, LLM-Lieferant | zweiter Client soll die Daten nutzen (dann MCP nur lesend); Richtlinie wird lang | 0009 |
| 0010 | Synthetische Daten: Code würfelt, LLM (Claude Opus) kleidet ein, Code prüft; Testset von anderer Modellfamilie statt anderer Person | 19.10.2026 | Handarbeit, LLM erzeugt auch die Wahrheit, Mistral als Generator | Teammitglied liefert Szenarien; > 2 von 20 Umformulierungen fehlerhaft | 0010 |
| 0011 | `granite4.1:3b` (FHNW-Proxy) als Ablationszeile; Entscheidungsmodelle (tev1) gegen Luna per Spike in KW44 | 19.10.2026 | eigenes Ollama, nur Cloud, Entscheidungsmodell ungeprüft einsetzen, Jev | Jev oder Microsoft-Decision-1 im Proxy mit Deutsch | 0011 |
| 0012 | Demo «Greift den Agenten an» mit Mensch als Lieferant, Ergebnisfolie als Kampagne; Live-Runden mit Spielkarte, Bewertung im Code | 19.10.2026 | Trace als Hauptdemo, Pareto-Grafik, MCP-Client, LLM-Lieferant | Proxy unzuverlässig (dann Aufzeichnung) | 0012 |
