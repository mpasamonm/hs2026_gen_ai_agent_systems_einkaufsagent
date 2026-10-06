# ADR 0005 – ERP-Adapter als schmaler MCP-Server («ERP-light») statt ERP-Mock

- **Status:** vorgeschlagen (Team-Freigabe offen)
- **Datum:** 06.10.2026
- **Ersetzt:** im Briefing die Zeile «ERP-Mock: eigener MCP-Server über SQLite – Lieferantenstamm,
  Preishistorie, Bestellung anlegen»

## Kontext

Das Semesterprogramm verlangt für KW43 «MCP Server anbinden». Der Projektbeschrieb (Anhang A) nennt MCP
dagegen nur als möglichen Baustein («je nach Projekt»). MCP ist also ein Wochenauftrag, kein
Erfüllungskriterium, kommt aber in der Prüfung vor. Unsere Architektur ruft Daten deterministisch ab
(`load_context`, `book_deal`); das LLM soll über Zahlen nicht entscheiden. Ein vollwertiger ERP-Mock bringt
Aufwand ohne Beitrag zur Kernthese.

Die trennende Achse ist **Integrationstiefe gegen Aufwand und Reproduzierbarkeit der Evaluation**.

## Entscheid

Ein eigener MCP-Server mit FastMCP 4.0.11 über SQLite, genau drei Tools:

| Tool | Aufrufer | Zweck |
| --- | --- | --- |
| `get_supplier_context(supplier_id)` | Code (`load_context`) | Lieferant, Kategorie, Volumen, heutige Konditionen; ersetzt den JSON-Stub |
| `record_outcome(supplier_id, outcome, terms, summary)` | Code (`book_deal`, `update_memory`) | Ergebnis und Protokoll schreiben (Deal, kein Deal, Übergabe) |
| `get_negotiation_history(supplier_id)` | LLM (`plan`), nur lesend | frühere Verhandlungen; einziges vom LLM gewähltes Tool, zeigt Function Calling; Basis für Memory in KW46 |

Regeln:
- Eval und Tests sprechen den Server **in-process** an (FastMCP-Client mit In-Memory-Transport, ohne
  Subprozess). Die Demo startet ihn über stdio; damit ist er auch aus anderen MCP-Clients nutzbar.
- Pro Lauf eine **frische SQLite-Datei**, befüllt ausschliesslich aus dem `public`-Teil des Szenarios.
  Verdeckte Lieferantenparameter kommen nie in die Datenbank; der Canary-Test prüft auch Tool-Ausgaben.
- Deterministische Nodes rufen den FastMCP-Client direkt. Für das LLM-Tool `langchain.mcp.MCPAdapter`
  (Beta seit langchain 1.4) oder ein schlanker eigener Tool-Wrapper.
- Graph und Eval werden asynchron (`graph.ainvoke`), weil der MCP-Client asynchron ist.
- Server loggt nur auf stderr; Ausgaben auf stdout zerstören das stdio-Protokoll.
- Neue Metrik «korrekt gebucht»: Der Datenbankzustand am Ende entspricht den vereinbarten Konditionen
  (zustandsbasierte Evaluation wie bei τ-Bench).

Nicht im Scope: Bestellungen, Preishistorie über Jahre, ein Stamm mit 600 Lieferanten, Authentifizierung,
HTTP-Deployment, MCP über den LiteLLM-Proxy.

## Verworfene Alternativen

| Alternative | Aufwand (Schätzung) | Grund |
| --- | --- | --- |
| Vollwertiger ERP-Mock (Stamm, Preishistorie, Bestellungen, 6–8 Tools) | 20–25 h | Aufwand ohne Beitrag zur Kernthese; mehr Tools für das LLM heisst mehr Fehlerbilder ausserhalb der Fragestellung |
| Lokale Python-Funktionen ohne MCP | ca. 2 h | verfehlt den KW43-Auftrag; MCP in der Prüfung nicht aus eigener Arbeit erklärbar |
| `langchain-mcp-adapters` 0.3.2 (06.08.2026) als Client | – | verlangt `mcp<2.0`, das offizielle SDK steht bei 2.3.0 (02.10.2026); LangChain migriert auf `langchain.mcp` |

## Kippt, wenn

der Dozent LLM-gesteuerten Tool-Use als Kern des Projekts verlangt. Dann mehr Tools für das LLM freigeben
(z.B. Richtlinien-Suche aus KW44 als Tool), aber nicht den Datenumfang erhöhen.

## Konsequenzen

- Aufwand ca. 9–13 h (rund 1,5 Personentage) in KW43; grösster Einzelposten ist der Umbau auf async.
- Präsentation: als «ERP-Adapter (Mock)» bezeichnen, nicht als ERP; die Grenze offen benennen.
- Versionen vor der Umsetzung erneut prüfen: fastmcp 4.0.11 [current default], `langchain[mcp]` 1.4.3 mit
  Beta-Namespace `langchain.mcp` [emerging].
