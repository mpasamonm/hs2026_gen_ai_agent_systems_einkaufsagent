# ADR 0009 – Prozess `_v3`: ohne MCP und RAG, Protokoll als Gedächtnis, Mensch als Lieferant

- **Status:** angenommen am 19.10.2026 (nach Recherche bestätigt)
- **Datum:** 19.10.2026
- **Artefakte:** `einkaufsagent-prozess_v3.bpmn` und `.png` im Root, Generator `docs/process/gen_bpmn_v3.py`,
  Kopie in `docs/process/einkaufsagent-prozess.bpmn` und `.png`
- **Ersetzt teilweise:** ADR 0005 (MCP-Server), ADR 0007 (RAG, Tool-Wahl des LLM in der Eskalation), D7 und den
  geplanten LLM-Simulator aus ADR 0003

## Kontext

Am 19.10.2026 sagte der Dozent: MCP und RAG sind nicht Pflicht; die Technik muss zum Use-Case passen, bevorzugt
werden eine sinnvolle Technologiewahl und genügende Tiefe. `_v2` enthielt beides, weil die Wochenaufträge KW43 (MCP)
und KW44 (RAG) es nahelegten. SW6 (Folie 26, «Eigenes Tool oder MCP?») gibt eine Entscheidungshilfe: Zugriff auf eine
eigene kleine Tabelle oder Datei → eigenes Tool; mehrere Anwendungen sollen dieselben Werkzeuge nutzen → MCP.

Die trennende Achse ist **realistische Integrationsgrenze und Demo-Wert gegen Aufwand und Risiko**.

Versionen am 19.10.2026 (PyPI): `mcp` 2.3.0 (02.10.2026), `fastmcp` 4.1.1 (18.10.2026). `langchain-mcp-adapters`
0.3.2 verlangt weiterhin `mcp<2.0`. `langchain.mcp` (SW6 Folie 23, `MCPAdapter`) ist Beta, braucht `langchain` ≥ 1.4.4
und damit `langchain-core` ≥ 1.6.9 (gepinnt ist 1.6.6); die Tools sind nur asynchron aufrufbar.

## Entscheid

| Punkt | Entscheid | Grund |
| --- | --- | --- |
| ERP-Adapter | schlanke Python-Schnittstelle über SQLite (Kontext laden, Ergebnis und Protokoll erfassen, frühere Protokolle lesen), ohne MCP | ein einziger Client (unser Code); SW6 Folie 26 |
| Einkaufsrichtlinie | kurz (rund eine Seite), steht vollständig im Prompt von `parse_response` und `escalate`, ohne RAG | eine kurze Richtlinie braucht kein Retrieval; Retrieval-Fehler fallen weg |
| Tool-Wahl | das LLM wählt keine Tools; in der Eskalation gibt der Code Richtlinie, Verlauf und frühere Protokolle mit | übermässige Handlungsmacht (OWASP LLM03) vermeiden; SW6 Folie 9 «Mehr Tools sind besser – Nein» |
| Protokoll | der Code erstellt es auf allen Ausgängen aus den gespeicherten Runden: Startpakete, Reaktion und Paketwahl des Lieferanten, Verlauf, Ergebnis, Hinweise für die Einkäuferin | Nachvollziehbarkeit; die Protokolle sind das Gedächtnis für Variante (c); Walmart/Pactum protokolliert jede Verhandlung |
| Lieferant | Eval gegen den regelbasierten Simulator; Demo und Live-Runden mit einem Menschen im Terminal; kein LLM-Lieferant | ein Mensch testet realistischer als ein LLM gegen ein LLM; spart D7 und eine zweite Modellfamilie im Agentenlauf |

**MCP bleibt als Ausbau möglich (D3):** ein schmaler, nur lesender MCP-Server über dem fertigen ERP-Adapter
(Resources: Richtlinie, Protokolle), damit ein zweiter Client wie Claude Desktop, Claude Code oder der MCP Inspector
die Protokolle lesen kann. Aufwand 2–3 h, frühestens KW47, nur wenn Zeit bleibt. Der Agent selbst nutzt MCP nicht.

**Folgeentscheid für `_v4` (KW44):** Fehlerpfade über die bestehenden Fail-safes. Scheitert «Angebot formulieren»
(LLM nicht erreichbar, auch nach Retries), geht der Standardtext hinaus; scheitert «Antwort extrahieren», gilt die
Antwort als nicht auswertbar und wird eskaliert (ADR 0008, Regel 3). `_v4` zeichnet das zusammen mit dem Ergebnis des
Klassifikations-Spikes (ADR 0011) in einer Fassung.

## Verworfene Alternativen

| Alternative | Aufwand | Grund |
| --- | --- | --- |
| MCP als ERP-Adapter, vom Code aufgerufen (ADR 0005) | 6–8 h | ein Protokollschritt ohne zweiten Client; async-Wrapper, SQLite im Threadpool von FastMCP; Beta-Abhängigkeit oder Versionsfalle |
| MCP-Server mit Resources für einen zweiten Client, fest geplant | 2–3 h | einziger echter Grund für MCP, trägt aber nicht zur Kernthese bei; deshalb optional (oben) |
| Richtlinie per RAG beim Extrahieren und in der Eskalation (ADR 0007) | 4–6 h | die Richtlinie ist kurz; künstlich verlängern wäre Technik um der Technik willen |
| LLM wählt in der Eskalation Tools (Richtlinien-Suche, Historie) | 2 h | gleicher Inhalt wie «Code gibt mit», aber ein zusätzliches Fehlerbild und mehr Angriffsfläche |
| LLM-Lieferant aus einer anderen Modellfamilie (D7) | 4–6 h | streut von Lauf zu Lauf; ein Mensch prüft realistischer und zeigt in der Demo mehr |

## Kippt, wenn

- ein zweiter Client die Daten nutzen soll (z.B. die Einkäuferin in ihrem Chat-Client): dann D3;
- die Einkaufsrichtlinie lang wird oder mehrere Dokumente dazukommen (etwa mehr als 20 Seiten): dann Retrieval fest im
  Node, weiterhin ohne Tool-Wahl durch das LLM;
- die Dozierenden LLM-gesteuerten Tool-Use als Kern verlangen: dann ein einziges, nur lesendes Tool in `escalate`.

## Konsequenzen

- ADR 0005 und 0007 sind teilweise ersetzt (Status dort nachgeführt). Der LLM-Simulator aus ADR 0003 und D7 entfallen.
- `docs/process/README.md` (Mapping) und `docs/gesamtsystem.md` beschreiben `_v3`.
- Prüfungsbegründung: «MCP löst das N×M-Integrationsproblem, wenn mehrere Anwendungen dieselben Werkzeuge nutzen
  (SW6 Folien 16 und 26). Unser ERP-Adapter hat genau einen Client, unseren Code; deshalb eine Python-Schnittstelle, und
  MCP erst mit einem zweiten Client.» Und: «MCP ersetzt keinen Prompt. Die Richtlinie landet so oder so im Prompt; wir
  lassen den Code entscheiden, was hineinkommt, nicht das LLM.»
