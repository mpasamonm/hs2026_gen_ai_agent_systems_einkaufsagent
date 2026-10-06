# Entscheidungslog

Jeder nicht triviale Entscheid: Entscheid, Datum, verworfene Alternativen, Bedingung, unter der er kippt.
D1–D7 stammen aus dem Kontext-Briefing; ab ADR 0002 aus der Session vom 05.10.2026.

| # | Entscheid | Datum | Verworfen | Kippt, wenn | ADR |
| --- | --- | --- | --- | --- | --- |
| D1 | Use-Case Einkaufsagent | 05.10.2026 | StandortScout, weitere Ideen | reines LLM verhandelt fast fehlerfrei | 0001 |
| D2 | Apertus nur als Referenzzeile | 03.10.2026 | Apertus als Arbeitsmodell | Apertus erreicht den besten offenen Kandidaten | 0004 |
| D3 | Recherche just-in-time als 2-h-Spike mit ADR | 03.10.2026 | Recherchephase vorab | Dozent verlangt Architekturkonzept vor KW42 | – |
| D4 | Hermetische Evals: feste Szenarien und Seeds | 03.10.2026 | Evals gegen Live-Systeme | – | 0003 |
| D5 | Modellzugang über FHNW-LiteLLM | 03.10.2026 | eigenes API-Budget | Kostenlimit reicht nicht | 0004 |
| D6 | Konditionen-Nachverhandlung mit 2–3 Paketen (MESO) | 05.10.2026 | freies Preisfeilschen | Dozent verlangt freie Verhandlung | 0001 |
| D7 | Agent und LLM-Simulator aus verschiedenen Modellfamilien | 05.10.2026 | dasselbe Modell auf beiden Seiten | LiteLLM bietet nur eine Familie | 0003 |
| 0002 | Prozess v2: Code bewertet, LLM extrahiert und formuliert | 05.10.2026 | LLM-Router, Korrekturschleife, Einzelpakete | Template-Rate > 20 % | 0002 |
| 0003 | Regelbasierter Simulator für KW42 | 05.10.2026 | LLM-Persona, Menschen | Agenten nutzen Textvorlagen aus | 0003 |
| 0004 | Kandidaten Luna, gpt-oss-120b, Mistral Large 3 + Regel-Referenz | 05.10.2026 | gpt-5.4-mini, kimi-k2.7-code | Kandidat ohne strukturierte Ausgabe | 0004 |
| 0005 | ERP-light: MCP-Server mit 3 Tools (vorgeschlagen) | 06.10.2026 | voller ERP-Mock, lokale Funktionen, langchain-mcp-adapters | Dozent verlangt LLM-gesteuerten Tool-Use als Kern | 0005 |
