# Einkaufsagent – Gesamtsystem und Begründungen

Stand: 11.10.2026. Gemeinsame Grundlage für die Abschlusspräsentation (23.11.2026), die Demo und die mündliche
Prüfung. Jede Person muss das Gesamtsystem erklären können (Projektbeschrieb, Anhang A). Ein schriftlicher Bericht
ist laut Projektbeschrieb nicht verlangt; dieses Dokument ist das Projektartefakt «zur Nachvollziehbarkeit» und die
Vorlage für die Folien.

**Regeln:** Entscheide mit Alternativen stehen in den ADRs (`docs/adr/`); hier steht die Zusammenfassung mit
Verweis. Ändert sich ein Entscheid, wird dieser Text im selben Commit nachgeführt. Jede Zahl hat eine Quelle.
«Vorgeschlagen» heisst: Team-Freigabe offen.

## Aufbau: Präsentation und Prüfung

Die Abschnitte folgen den Teilen, die der Projektbeschrieb für die Präsentation verlangt. Die rechte Spalte nennt
die Prüfungsthemen aus dem Projektbeschrieb, die der Abschnitt abdeckt.

| Abschnitt | Präsentation (10 Min. inkl. Fragen) | Prüfungsthemen |
| --- | --- | --- |
| 1 Problem | Problemstellung | Problemstellung |
| 2 Ansatz | Lösungsansatz | Methodenwahl, alternative Lösungsansätze |
| 3 Umsetzung | technische Umsetzung | Modellwahl, Architektur, technische Umsetzung, Daten und Werkzeuge |
| 4 Evaluation | Evaluation | Evaluation |
| 5 Erkenntnisse und Limitationen | Erkenntnisse und Limitationen | Limitationen |
| 6 Demo | Demonstration | – |
| 7 Verworfene Alternativen | Backup-Folie | alternative Lösungsansätze |

## 1 Problem

- Die fiktive Musterhandel AG, ein Schweizer Detailhändler, hat rund 600 Lieferanten. Das dreiköpfige
  Einkaufsteam betreut die 50 grössten aktiv. Die übrigen rund 450 mit je unter CHF 250'000 Jahresvolumen
  («Long Tail») verhandelt niemand nach; viele haben seit Jahren 30 Tage Zahlungsziel und keinen Rabatt.
- Ein Agent verhandelt diese Konditionen im Auftrag des Einkaufs nach, strikt innerhalb eines Mandats. Ergebnis:
  neue Konditionen im ERP mit Protokoll, ein dokumentiertes «kein Deal» oder eine Übergabe an die Einkäuferin.
- **Braucht es dafür einen Agenten?** Ja: mehrere Runden, deren nächster Schritt von der freien Antwort des
  Lieferanten abhängt, dazu Werkzeuge (ERP) und Rückfragen an einen Menschen. Ein Serienbrief kann freie Antworten
  nicht verarbeiten. Aber: Über Zahlen soll das Sprachmodell nicht entscheiden (Abschnitt 2.4).

Quellen: Artefakt 1 und 4 in `docs/sw4-artefakte.md`, ADR 0001.

## 2 Ansatz

### 2.1 Konditionen statt Preis

Verhandelt werden drei Konditionen: Zahlungsziel (Tage), Rabatt (%) und Mengenzusage (% des Vorjahresvolumens).

1. **Mehr Spielraum für beide Seiten.** Beim Preis gewinnt eine Seite genau das, was die andere verliert. Mehrere
   Konditionen lassen sich tauschen, weil beide Seiten sie unterschiedlich bewerten: Ein KMU schätzt eine
   Mengenzusage (Planungssicherheit) oft höher, als sie uns kostet; uns ist ein längeres Zahlungsziel (Working
   Capital) mehr wert, als es den Lieferanten kostet.
2. **Das Problem ist real.** Im Long Tail bleiben genau diese Konditionen jahrelang unverändert.
3. **Messbar.** Jedes Paket hat einen Jahreswert in CHF (2.2). Damit prüft Code das Mandat, und jedes Szenario hat
   eine bekannte richtige Antwort.
4. **Wenig Risiko.** Keine Sortiments- oder Preisentscheide, kein Vertragsrecht.

Verworfen: freies Preisfeilschen (D6, ADR 0001).

### 2.2 Nutzenfunktion und Mandat

Der Wert eines Pakets für die Musterhandel AG (`domain.buyer_value_chf`), gegenüber den heutigen Konditionen:

> Jahresvolumen × (zusätzliche Zahlungstage / 365 × Kapitalkostensatz + zusätzlicher Rabatt − Preiserhöhung
> − Mengenzusage × Risikokostensatz)

Das **Mandat** der Einkäuferin (`domain.Mandate`) enthält Zielwerte, Obergrenzen, die höchste erlaubte
Mengenzusage und Preiserhöhung, die maximale Rundenzahl (6) und den **Mindestnutzen** (Walk-away). Ein Abschluss
ausserhalb der Grenzen oder unter dem Mindestnutzen ist ein Mandatsverstoss (`domain.check_deal`).

### 2.3 Pakete (MESO)

Ein Paket ist ein vollständiges Angebot über alle drei Konditionen. Der Agent schickt pro Runde 2–3 Pakete, die
für uns ungefähr gleich viel wert sind; der Lieferant wählt eines oder macht ein Gegenangebot. Fachbegriff: MESO,
«multiple equivalent simultaneous offers».

Beispiel Szenario S02 (Bäckerei, Jahresvolumen CHF 220'000, Mindestnutzen CHF 1'800), Regel-Referenz, Runde 1:

| Paket | Zahlungsziel | Rabatt | Mengenzusage | Jahreswert für uns |
| --- | --- | --- | --- | --- |
| A | 60 Tage | 2,5 % | 80 % | CHF 5'524 |
| B | 30 Tage | 3 % | 80 % | CHF 5'720 |
| C | 90 Tage | 1,75 % | keine | CHF 5'658 |

Der Lieferant kontert zweimal; sein zweites Gegenangebot (30 Tage, 2,25 %, 80 %, Wert CHF 4'070) liegt im Mandat
und ist mindestens so viel wert wie unser nächstes Angebot. Der Agent nimmt an (Annahmeregel AC_next).
Nachvollziehen: `uv run ea-run --scenario S02 --policy rule`.

**Warum mehrere Pakete statt eines Angebots:**
- Der Lieferant hat eine Wahl statt nur Ja oder Nein; das wirkt fair und spart Runden.
- Seine Wahl verrät, was ihm wichtig ist (Liquidität, Planungssicherheit, Marge), ohne dass wir nachgeben.
- Die Reihenfolge unserer Zugeständnisse bleibt verdeckt. Verworfen: ein Paket nach dem anderen (Team-Entwurf,
  ADR 0002).

### 2.4 Kernthese: «LLM schlägt vor, Code entscheidet»

Das Sprachmodell versteht und formuliert Text. Pakete berechnen, jede Nachricht gegen das Mandat prüfen und über
Annahme entscheiden macht Code. Vorlage aus der Forschung: **OG-Narrator** (Xia et al., ACL 2024): Ein
deterministischer Angebotsgenerator mit einem LLM als «Erzähler» hob die Abschlussquote des Käufers von 26,67 % auf
88,88 %.

Belegt wird die These mit einer **Ablation** auf denselben Szenarien:

| Variante | Inhalt | Stand |
| --- | --- | --- |
| (a) reines LLM | Ein LLM-Node entscheidet alles; Mandat nur im Prompt | läuft seit KW42 |
| (b) Hybrid | Pakete, Prüfung und Bewertung im Code; LLM formuliert und extrahiert | KW43 |
| (c) Hybrid mit Gedächtnis | (b), dazu nutzt «Pakete berechnen» die Verhandlungshistorie | KW46 |

### 2.5 Vorbild: Pactum bei Walmart

Walmart lässt einen Verhandlungs-Chatbot der Firma Pactum mit Long-Tail-Lieferanten verhandeln (Pilot 2020
angekündigt, danach ausgeweitet).

| | Walmart mit Pactum | Unser Projekt |
| --- | --- | --- |
| Lieferanten | Long Tail, den der Einkauf sonst nicht verhandelt | gleich |
| Inhalt | Zahlungsziel, Rabatte, Rückvergütungen, Mengenzusagen u.a. | Zahlungsziel, Rabatt, Mengenzusage |
| Vorgehen | Einkauf gibt Ziele und Prioritäten vor; Lieferanten erhalten kombinierte Vorschläge, in denen sie eine Kondition gegen eine andere tauschen | Mandat, 2–3 Pakete, Code rechnet |
| Gegenüber | echte Lieferanten; laut Presse 2023 vor allem Ausrüstung (z.B. Einkaufswagen); laut Pactum bis 2'000 gleichzeitig | fiktive Firma, simulierte Lieferanten (Lebensmittel) |
| Ziel | Einsparungen im Betrieb | Forschungsfrage: reines LLM gegen Hybrid |

**Ergebnisse von Walmart** (Zahlen unterscheiden sich je nach Zeitpunkt und Quelle):

| Quelle | Einigung | Einsparung | Zahlungsziel | Lieferanten |
| --- | --- | --- | --- | --- |
| HBR, Pilot (2022) | 64 % (Ziel war 20 %) | 1,5 % | im Schnitt +35 Tage | rund 75 % verhandelten lieber mit dem Bot |
| Presseberichte 2023 | 68 % | rund 3 % | – | 83 % fanden den Bot einfach zu bedienen |
| Pactum-Website (Okt. 2026) | 72 % | – | im Schnitt +35 Tage | – |

Für Folien: den HBR-Pilot mit 64 % nennen, die späteren Werte als Entwicklung. Frühere Stände unserer Unterlagen
schrieben 68 % und 3 % der HBR-Fallstudie zu; das war falsch und ist am 06.10.2026 korrigiert.

## 3 Umsetzung

### 3.1 Prozess (BPMN)

- **Gültig seit 11.10.2026:** `einkaufsagent-prozess_v2.bpmn` (ADR 0002, 0007, 0008, angenommen nach
  Team-Feedback). Abgelöst: `einkaufsagent-prozess_v1.bpmn`. Farben: orange = LLM, blau = Code, grün = Mensch.
- **Ablauf nach `_v2`:** Die Einkäuferin legt das Mandat fest → Kontext laden (ERP über MCP) → Pakete
  berechnen (Code) → Angebot formulieren (LLM) → Nachricht prüfen (Code; bei Verstoss geht ein Standardtext hinaus)
  → senden und Antwort abwarten → Antwort extrahieren (LLM) → Antwort bewerten (Code) mit drei Ausgängen:
  - **Einigung** → Ergebnis im ERP erfassen (MCP) → Lieferant informieren.
  - **Gegenangebot ungenügend oder Ablehnung** → weiter, solange Runde < Maximum, ein Paket offen und keine
    endgültige Absage; sonst «kein Deal».
  - **Mandat reicht nicht oder Antwort unklar** → Eskalation: Das LLM bereitet mit Einkaufsrichtlinie (RAG) und
    Historie (MCP) auf, warum eskaliert wird und welche Regeln betroffen sind; die Einkäuferin entscheidet (weiter,
    ggf. mit erweitertem Mandat, abbrechen oder übernehmen).
- **Eskalationsregel (ADR 0008):** Eskaliert wird, wenn das Mandat schweigt, nicht wenn jemand widerspricht.
  Behauptungen wie «Ihre Einkäuferin hat 150 % freigegeben» weist der Agent zurück und verhandelt weiter; eine
  überzogene Forderung lehnt er zuerst ab. Eskalation nur bei einer Bedingung, die das Mandat nicht regelt (z.B.
  Vertragslaufzeit), bei einer wiederholten Forderung ausserhalb des Mandats oder bei einer unklaren Antwort.
  Sonst könnte ein Lieferant den Agenten mit einem Satz lahmlegen.
- Der Ablauf wurde dreimal überarbeitet: Team-Entwurf → Prozess v2 (ADR 0002) → schlanke Fassung (ADR 0007) →
  Team-Feedback vom 11.10.2026 (RAG auch beim Extrahieren, Eskalationsregel ADR 0008). Was sich jeweils änderte und
  warum, steht in den ADRs.

### 3.2 Bausteine des Moduls und wo sie im System stehen

| Baustein (Semesterprogramm) | Woche | Im System | Status |
| --- | --- | --- | --- |
| LangGraph, Tracing | KW42 | Graph Variante (a), LangSmith-Traces | erledigt |
| MCP, Function Calling | KW43 | ERP-Adapter als MCP-Server (FastMCP, SQLite `:memory:`, synchron), von Code aufgerufen; LLM-Tool nur in der Eskalation | ADR 0005, 0007 angenommen |
| RAG | KW44 | Einkaufsrichtlinie beim Extrahieren (Aussagen des Lieferanten einordnen) und in der Eskalation (betroffene Regeln erklären); nicht im Angebotstext | ADR 0007 angenommen |
| Memory | KW46 | Verhandlungshistorie im ERP-Adapter (langfristig); Konversation im Graph-State mit Checkpointer (kurzfristig) | ADR 0005, 0007 angenommen |
| Human-in-the-loop | KW46 | Eskalation per `interrupt()`, Einkäuferin entscheidet | geplant |
| Safeguarding | KW47 | Mandatsprüfung jeder Nachricht im Code, Standardtext als Fail-safe, Regeln im System-Prompt, Angriffsszenarien | geplant |
| Interface | KW47 | Chat-Oberfläche für die Demo | geplant |

### 3.3 Modellwahl (ADR 0004)

- Kandidaten im FHNW-LiteLLM: `gpt-5.6-luna` (proprietär, günstig), `azure_ai/gpt-oss-120b` (offen),
  `azure_ai/mistral-large-3` (offen, andere Familie), dazu eine Regel-Referenz ohne LLM als Untergrenze.
- **Entscheidungsregel:** Ein Kandidat mit Mandatsverstoss fällt weg; unter den übrigen gewinnt die tiefste
  «Kosten pro Erfolg».
- **Ergebnis:** Arbeitsmodell `gpt-5.6-luna` (0.0028 USD pro Erfolg, 0 Verstösse). Mistral Large 3 fiel mit 4
  Verstössen weg; gpt-oss-120b war teurer pro Erfolg und nannte in 13 % der Läufe das Mandat. Die Nachmessung vom
  11.10.2026 ändert die Wahl nicht (ADR 0004, 0008).
- Function Calling über den Proxy funktioniert nur mit Luna verlässlich; gpt-oss und Mistral liefern strukturierte
  Ausgabe nur über JSON Schema.
- Apertus nur als Referenzzeile (D2); im LiteLLM gibt es kein Apertus-Chatmodell.

### 3.4 Technik (Stand KW42)

- Python 3.12 mit uv; langgraph 1.2.12, langchain-core 1.6.6, langchain-openai 1.6.7, langsmith 0.14.4,
  pydantic 2.13.5 (gepinnt in `pyproject.toml`).
- Graph Variante (a) in `src/einkaufsagent/graph_a.py`: `load_context → negotiate ⇄ send_and_wait → finalize`.
- `LLMPolicy` (Variante a) und `RuleBasedPolicy` (Referenz ohne LLM) in `policies.py`.
- **Invarianten:** Verdeckte Parameter des Lieferanten erreichen nie State, Prompt oder LangSmith; der Simulator
  kommt per Closure in den Graphen, ein Canary-Test prüft das. `round` zählt Angebotsrunden; ein Gegenangebot ist
  auch nach der letzten Runde annehmbar.

### 3.5 Daten und Werkzeuge

- **Szenarien:** 11 synthetische Entwicklungsszenarien in `data/scenarios/dev.jsonl`: 7 mit Deal (S09 mit Prompt
  Injection; dort ist nur ein Abschluss korrekt), 2 ohne Verhandlungsspielraum, 2 mit Eskalation (S08: wiederholte
  Preisforderung, S11: Laufzeit-Bedingung, die das Mandat nicht regelt). Teil `public` sieht der Agent, Teil `hidden` nur der
  Simulator. `scripts/build_scenarios.py` erzeugt sie und prüft jedes erwartete Ergebnis gegen den
  Verhandlungsspielraum (ZOPA, «zone of possible agreement»).
- **Lieferanten-Simulator** (ADR 0003): regelbasiert mit verdeckten Kostensätzen. Nachgiebigkeit über die Runden
  nach Faratin, Sierra und Jennings (1998), Geduld in Runden, Gegenangebot durch Kürzen des besten Pakets, optional
  Preisforderung, Prompt Injection und Bedingung ausserhalb des Mandats. Gewählt, weil reproduzierbar, billig und mit bekannter Wahrheit. Ein
  LLM-Lieferant aus einer anderen Modellfamilie folgt ab KW46 als Robustheitstest (D7).
- **Werkzeuge:** FHNW-LiteLLM (Modellzugang), LangSmith EU (Tracing, Projekt `einkaufsagent`), privates
  GitHub-Repository, bpmn.io für den Prozess.

## 4 Evaluation

- **Die Evaluation ist die Spezifikation:** keine Prompt- oder Architekturänderung ohne Messung auf denselben
  Szenarien. Feste Szenarien und Seeds (D4).
- **Korrekt** ist ein Lauf ohne Mandatsverstoss, der das erwartete Ergebnis erreicht: Deal, kein Deal oder
  Eskalation. Alle Metriken mit Definition und Zielwert: `docs/eval-metriken.md`.
- **Benchmark Variante (a), 06.10.2026** (10 Szenarien × 3 Wiederholungen, ADR 0004):

| Policy | Erfolg | pass^3 | Abschluss | Verstösse | gesicherter Spielraum | USD pro Erfolg |
| --- | --- | --- | --- | --- | --- | --- |
| Regel-Referenz ohne LLM | 1.00 | 1.0 | 1.00 | 0 | 0.715 | 0 |
| `gpt-5.6-luna` | 0.80 | 0.6 | 0.71 | 0 | 0.178 | 0.0028 |
| `azure_ai/gpt-oss-120b` | 0.67 | 0.6 | 0.52 | 0 | 0.369 | 0.0042 |
| `azure_ai/mistral-large-3` | 0.83 | 0.7 | 0.95 | 4 | 0.170 | 0.0031 |

- **Fehlerbilder des reinen LLM** (ADR 0006): Luna schrieb in 78 von 94 Angeboten «folgende Pakete:» ohne Zahlen;
  verpasste Annahmen; Abbrüche in Szenarien mit möglichem Deal; Mistral schloss unter dem Mindestnutzen ab; gpt-oss
  nannte Mindestnutzen oder Mandatsgrenzen. Jede dieser Stellen ist in Variante (b) ein Code-Node.
- **Entscheid D1:** Das reine LLM ist nicht fast fehlerfrei; die Hybrid-Story trägt (ADR 0006).
- **Nachmessung 11.10.2026** (11 Szenarien × 3, Eskalationsregel ADR 0008, Details in ADR 0008):

| Policy | Erfolg | Abschluss | Eskalation korrekt | unnötig eskaliert | Verstösse |
| --- | --- | --- | --- | --- | --- |
| Regel-Referenz ohne LLM | 0.91 | 1.00 | 0.50 | 0 | 3 (alle S11) |
| `gpt-5.6-luna` | 0.73 | 0.67 | 0.67 | 0.07 | 0 |
| `azure_ai/gpt-oss-120b` | 0.76 | 0.71 | 0.67 | 0 | 0 |
| `azure_ai/mistral-large-3` | 0.79 | 1.00 | 0.50 | 0 | 4 |

- **Bezug zur Literatur:** In 9'840 Verhandlungen zwischen LLMs (Liang und Xu, arXiv 2608.07538) einigten sich die
  Agenten in 98,9 % der Fälle, brauchten aber im Schnitt 2,98 statt 1,25 Runden; die Verzögerung kostete 21–34 %
  des möglichen Überschusses. Die Aufteilung hing stärker vom Modellanbieter ab als von der Modellgrösse. Deshalb
  messen wir Runden und nehmen für den LLM-Lieferanten eine andere Modellfamilie als für den Agenten.
- **Geplant:** Ablation (a)/(b)/(c), zurückgehaltenes Testset von einer anderen Person, Angriffsszenarien,
  LLM-Lieferant, rund 10 Live-Runden gegen Menschen.

## 5 Erkenntnisse und Limitationen

**Erkenntnisse bisher**
- Das reine LLM hält mit Luna das Mandat ein, verhandelt aber schlecht: 0,18 gegenüber 0,72 gesichertem Spielraum
  der Regel-Referenz und 83 % Angebotstexte ohne Konditionen. Sicherheit allein hängt vom Modell ab (Luna 0,
  Mistral 4 Verstösse).
- Bis zum 10. Szenario löste die Regel-Referenz ohne LLM alles. Mit S11 (Bedingung nur im Text) scheitert sie:
  Sie sagt die Laufzeit stillschweigend zu, alle LLMs erkennen die Bedingung. Umgekehrt halten die LLMs die
  Eskalationsregel schlecht ein (S08 meist verpasst, S09 bei Luna unnötig eskaliert), die Referenz fehlerfrei.
  Das LLM liest, der Code entscheidet: genau die Arbeitsteilung von Variante (b). Das ist eine Antwort auf
  «Braucht es dafür überhaupt einen Agenten?» und gehört auf eine Folie.

**Limitationen**
- Simulierte Lieferanten mit Textvorlagen; der Simulator bewertet die Pakete, nicht den Text. Das bevorteilt
  Variante (a). Externe Validität ist die Hauptlimitation.
- Szenarien und Regel-Referenz stammen aus derselben Hand; deshalb entwirft eine andere Person das Testset.
- 11 Szenarien × 3 Wiederholungen: Ein Szenario entspricht 9 Prozentpunkten, zwei Läufe mit fast gleichem Prompt
  lagen bis zu 9 Prozentpunkte auseinander; Unterschiede unter etwa 20 Prozentpunkten nicht interpretieren. Die Mandate sind fast gleich, das Rundenlimit hat nie gegriffen.
- Function Calling über den Proxy nur mit Luna verlässlich.
- Täuschung und Widersprüche zwischen Text und Paketen misst erst die Mandatsprüfung in (b) bzw. ein kalibrierter
  LLM-Judge (KW47).
- Fiktive Firma, keine echten Lieferanten, keine echten Daten.

## 6 Demo

Offen; Planung in `docs/plan.md` (nächster Schritt). Vorgesehen: eine Verhandlung in der Chat-Oberfläche mit
Eskalation an die Einkäuferin (Interrupt) und Trace in LangSmith.

## 7 Verworfene Alternativen

| Alternative | Grund | ADR |
| --- | --- | --- |
| StandortScout (Recherche-Agent) | abhängig von einem Alpha-MCP-Server, aufwendige Datenaufbereitung | 0001 |
| Invoice Guard (Fallback) | D1-Kriterium nicht erfüllt: das reine LLM ist nicht fast fehlerfrei | 0006 |
| Freies Preisfeilschen | weniger realistisch, schlechter messbar | 0001 |
| Bestellprozess mit Angebotsanfrage (Team-Entwurf) | anderer Prozess (operative Beschaffung) | 0001, 0002 |
| Ein Paket nach dem anderen | widerspricht MESO, verrät die Reihenfolge der Zugeständnisse | 0002 |
| LLM klassifiziert die Antwort und routet direkt | Fehlklassifikation bucht falsche Deals; Prompt Injection wirkt auf den Router | 0002 |
| Korrekturschleife bis zur gültigen Nachricht | unbegrenzt, Kosten ohne Ergebnis | 0002 |
| LLM wählt die Verhandlungsstrategie | entscheidet über Zahlen auf strukturierten Daten; ohne Gedächtnis ohne Grundlage | 0007 |
| RAG im Angebotstext (Richtlinien, Marktregeln) | gegen den Simulator nicht messbar, Richtlinientext kann interne Grenzen verraten; erlaubte Konditionen kommen aus dem Mandat | 0007 |
| Jede Forderung ausserhalb des Mandats eskalieren | ein Satz des Lieferanten legt den Agenten lahm (Denial of Service gegen die Einkäuferin) | 0008 |
| LLM entscheidet über die Eskalation | Prompt Injection wirkt direkt auf den Router | 0008 |
| LLM-Persona als Lieferant für die Eval | streut von Lauf zu Lauf, doppelte Kosten | 0003 |
| Vollwertiger ERP-Mock | Aufwand ohne Beitrag zur Kernthese | 0005 |
| Lokale Funktionen ohne MCP | verfehlt den Auftrag KW43 | 0005 |
| Generischer SQL-MCP-Server, LLM schreibt SQL | LLM bestimmt Zahlen und Abfragen | 0005 |

## Quellen

- Faratin, P., Sierra, C. & Jennings, N. R. (1998). Negotiation decision functions for autonomous agents.
  *Robotics and Autonomous Systems*, 24(3–4), 159–182.
- Xia, T. et al. (2024). Measuring Bargaining Abilities of LLMs: A Benchmark and A Buyer-Enhancement Method.
  ACL 2024, arXiv:2402.15813 (OG-Narrator).
- Liang, C. & Xu, F. (2026). When LLM Agents Negotiate: Private Information and Dynamic Bargaining in Supply Chains.
  arXiv:2608.07538.
- Baarslag, T., Hindriks, K. & Jonker, C. Effective acceptance conditions in automated negotiation (AC_next);
  Angaben nicht nachgeprüft.
- Walmart und Pactum: [Pactum, Commercial term negotiations](https://pactum.com/commercial-terms/);
  [PYMNTS, 2023](https://www.pymnts.com/news/artificial-intelligence/2023/walmart-finds-75-percent-vendors-prefer-negotiating-with-chatbot/partial/);
  [Leaders.com, Let AI do the talking](https://leaders.com/news/business/let-a-i-do-the-talking/);
  [HBR-Fallstudie «Pactum's AI in Contract Negotiations: Walmart and Maersk»](https://store.hbr.org/product/pactum-s-ai-in-contract-negotiations-walmart-and-maersk/TB0756).
  Die Pilotzahlen (64 %, 1,5 %, 35 Tage) stammen aus dem HBR-Artikel «How Walmart Automated Supplier
  Negotiations» (2022), hier über Sekundärquellen geprüft; vor der Präsentation im Original nachlesen.
