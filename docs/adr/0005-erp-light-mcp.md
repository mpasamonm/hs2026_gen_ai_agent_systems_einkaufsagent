# ADR 0005 – ERP-Adapter als schmaler MCP-Server («ERP-light») statt ERP-Mock

- **Status:** angenommen am 11.10.2026 (Team-Feedback: «ERP als kleiner MCP-Server, bin ich dabei»), mit den
  Prüfpunkten unten
- **Teilweise ersetzt am 19.10.2026 durch ADR 0009:** kein MCP; der ERP-Adapter ist eine schlanke
  Python-Schnittstelle über SQLite. Weiter gültig: drei Funktionen (Kontext, Ergebnis/Protokoll, Historie), SQLite
  `:memory:`, nur `public`-Daten, Metrik «korrekt gebucht». `get_negotiation_history` ruft der Code, nicht das LLM.
- **Datum:** 06.10.2026, angepasst 11.10.2026
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
| `get_negotiation_history(supplier_id)` | LLM (`escalate`, ADR 0007), nur lesend | frühere Verhandlungen; einziges vom LLM gewähltes MCP-Tool, zeigt Function Calling; die Historie ist das Gedächtnis von Variante (c) |

Regeln:
- Eval und Tests sprechen den Server **in-process** an (FastMCP-Client mit In-Memory-Transport, ohne
  Subprozess). Die Demo startet ihn über stdio; damit ist er auch aus anderen MCP-Clients nutzbar.
- Pro Serverinstanz eine **SQLite-Datenbank `:memory:`**, befüllt ausschliesslich aus dem `public`-Teil des
  Szenarios (Prüfpunkt 4).
  Verdeckte Lieferantenparameter kommen nie in die Datenbank; der Canary-Test prüft auch Tool-Ausgaben.
- Deterministische Nodes rufen den FastMCP-Client direkt. Für das LLM-Tool ein schlanker eigener synchroner
  Tool-Wrapper, kein `langchain.mcp` (Prüfpunkt 1).
- Graph und Eval bleiben synchron; die Nodes sprechen den In-Memory-Client über `asyncio.run(...)` an
  (Prüfpunkt 1, in KW43 mit einem kurzen Spike bestätigen, unverified).
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
| Generischer SQLite-MCP-Server, das LLM schreibt SQL selbst | ca. 1 h | das LLM bestimmt Abfragen und damit Zahlen; widerspricht «Code entscheidet» (Prüfpunkt 5) |

## Kippt, wenn

der Dozent LLM-gesteuerten Tool-Use als Kern des Projekts verlangt. Dann mehr Tools für das LLM freigeben
(z.B. Richtlinien-Suche aus KW44 als Tool), aber nicht den Datenumfang erhöhen.

## Konsequenzen

- Aufwand ca. 6–8 h in KW43, weil der Umbau auf async entfällt (Prüfpunkt 1).
- Präsentation: als «ERP-Adapter (Mock)» bezeichnen, nicht als ERP; die Grenze offen benennen.
- Versionen vor der Umsetzung erneut prüfen: fastmcp 4.0.11 [current default], `langchain[mcp]` 1.4.3 mit
  Beta-Namespace `langchain.mcp` [emerging].

## Prüfpunkte vor der Freigabe (Review 06.10.2026, entschieden am 11.10.2026)

Versionen geprüft (PyPI, 06.10.2026): fastmcp 4.0.11, mcp 2.3.0, langchain 1.4.3, langchain-mcp-adapters 0.3.2
mit `mcp<2.0`; die Angaben oben stimmen. Weitere Vereinfachungen, über die das Team vor der Freigabe entscheiden soll:

1. **Async-Umbau vermeiden.** Die Nodes können synchron bleiben und den In-Memory-Client pro Aufruf über
   `asyncio.run(...)` ansprechen (die Eval-Threads haben keine laufende Event-Loop). Für das LLM-Tool ein eigener
   synchroner Wrapper statt `langchain.mcp`; damit entfällt auch die Beta-Abhängigkeit. Schätzung: 3–5 h weniger.
2. **`get_negotiation_history` liefert in der Eval immer eine leere Liste**, weil die Datenbank pro Lauf frisch aus
   `public` entsteht. Das Tool zeigt so nichts, bringt aber ein neues Fehlerbild (unnötige oder erfundene
   Historie). Entweder 2–3 Szenarien mit kurzer öffentlicher Historie ergänzen oder das Tool erst in KW46 einführen.
3. **Ein Gedächtnis statt zwei.** `docs/process/README.md` sieht für `update_memory` den LangGraph Store vor, dieses
   ADR die SQLite-Historie als «Basis für Memory». Vorschlag: Die Historie im ERP-Adapter ist das Gedächtnis; dann
   fällt in der BPMN ein Datenspeicher weg. Sonst den Entscheid ausdrücklich auf KW46 vertagen.
4. **SQLite `:memory:` pro Serverinstanz** statt einer frischen Datei pro Lauf: keine temporären Dateien, parallele
   Läufe kollidieren nicht.
5. **Fehlende Alternative:** generischer SQLite-MCP-Server, bei dem das LLM selbst SQL schreibt. Verworfen, weil das
   LLM damit Zahlen und Abfragen bestimmt (widerspricht «Code entscheidet»); in der Prüfung wahrscheinlich gefragt.
6. **Function Calling über den Proxy** funktioniert nur mit `gpt-5.6-luna` verlässlich (ADR 0004). Das LLM-Tool ist
   damit an das Arbeitsmodell gebunden; gpt-oss und Mistral können es in der Ablation nicht nutzen.

**Entscheid zu den Prüfpunkten (11.10.2026):** 1 angenommen (synchron, eigener Wrapper). 2: Das Tool wird in KW43
im Server gebaut und getestet; das LLM nutzt es erst in `escalate` (KW46), Szenarien mit kurzer öffentlicher
Historie kommen mit Variante (c). 3 angenommen (ADR 0007). 4 angenommen. 5 in die verworfenen Alternativen
aufgenommen. 6 akzeptiert: Das LLM-Tool betrifft nur `escalate`; gpt-oss und Mistral laufen in der Ablation ohne
dieses Tool.
