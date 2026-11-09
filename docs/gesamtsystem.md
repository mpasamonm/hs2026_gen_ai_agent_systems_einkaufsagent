# Einkaufsagent – Gesamtsystem und Begründungen

Stand: 09.11.2026. Gemeinsame Grundlage für die Abschlusspräsentation (23.11.2026), die Demo und die mündliche
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
| 6 Demo und Abgabe | Demonstration | – |
| 7 Verworfene Alternativen | Backup-Folie | alternative Lösungsansätze |
| 8 Was wir gewählt haben und warum | Backup-Folie | Modell- und Methodenwahl, alternative Lösungsansätze |
| 9 Abdeckung der Modulthemen | – | Evaluation, Limitationen |
| 10 Beiträge | – | individueller Beitrag |

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
88,88 %. Neuer stützen Liang und Xu (2026, arXiv 2608.07538) dasselbe: Schwächere Modelle nahmen rund 19 % unrentable
Verträge an, und eine automatische Profitprüfung ist die nötige Schranke (Zahl aus der Recherche vom 19.10.2026, vor der
Präsentation im Original nachlesen). Bei uns ist das der Mindestnutzen in `assess_response`; gemessen als Verstoss
`below_walk_away`.

Die Vorlesung sagt dasselbe über Tool-Calls: «Das Modell führt nichts aus. Es schlägt vor, euer Programm entscheidet
und handelt.» (SW5, Folie 23)

Belegt wird die These mit einer **Ablation** auf denselben Szenarien:

| Variante | Inhalt | Stand |
| --- | --- | --- |
| (a) reines LLM | Ein LLM-Node entscheidet alles; Mandat nur im Prompt | läuft seit KW42 |
| (b) Hybrid | Pakete, Prüfung und Bewertung im Code; LLM formuliert und extrahiert | gebaut 19.10.2026, gemessen (ADR 0013) |
| (b) mit kleinem Modell | wie (b), mit dem offenen 3B-Modell `ibm/granite4.1:3b` aus dem FHNW-Proxy (ADR 0011) | KW44 |
| (c) Hybrid mit Gedächtnis | (b), dazu startet «Pakete berechnen» bei der Paketwahl aus früheren Protokollen | KW46, klein und optional (ADR 0009) |

### 2.5 Vorbild: Pactum bei Walmart (2021) und Stand 2026

Walmart lässt einen Verhandlungs-Chatbot der Firma Pactum mit Long-Tail-Lieferanten verhandeln (Pilot 2020
angekündigt, 2021 in Kanada durchgeführt, danach ausgeweitet).

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
| PON Harvard, Pilot Walmart Canada 2021 | 64 % von 89 Lieferanten, im Schnitt in 11 Tagen | 1,5 % | – | 83 % der Lieferanten mit Abschluss äusserten sich positiv |
| Presseberichte 2023 | 68 % | rund 3 % | – | 83 % fanden den Bot einfach zu bedienen |
| Pactum-Website (Okt. 2026) | 72 % | – | im Schnitt +35 Tage | – |

Für Folien: den HBR-Pilot mit 64 % nennen, die späteren Werte als Entwicklung. Frühere Stände unserer Unterlagen
schrieben 68 % und 3 % der HBR-Fallstudie zu; das war falsch und ist am 06.10.2026 korrigiert.

**Der Pilot im Detail:** Anfang 2021, Walmart Canada (Walmart International), 89 Lieferanten von Betriebsmitteln wie
Einkaufswagen; Einigung in im Schnitt 11 Tagen (PON). Die Dauer von rund drei Monaten nennen nur Sekundärquellen.

**Stand 2026** (Recherche vom 19.10.2026; Walmart 2021 ist der Ursprung, nicht mehr der Stand):
- **Walmart:** Die letzte belastbare Ausweitung meldete Bloomberg im April 2023 (USA, Chile, Südafrika, nur Waren für
  den Eigenbedarf). Seither gibt es keine Primärquelle von Walmart; Pactum führt Walmart weiter als Kunden, ob der
  Einsatz noch läuft, ist nicht belegt (unverified). Walmarts eigener Agent «Marty» (Juli 2025) unterstützt Lieferanten
  bei Onboarding und Bestellungen, verhandelt aber nicht.
- **Pactum:** Series C über 54 Mio. USD (Juni 2025); laut Website über 50 Grosskunden und 55 Mrd. USD Einkaufsvolumen.
  Das Produkt «Campaigns» (Konditionen über viele Lieferanten) entspricht unserem Fall. Pactum nennt sich «explainable
  rules-based AI»; laut CEO (Dez. 2024) ist eine Abschlussvollmacht «nur mit einem LLM» unmöglich. Ob Pactum für Texte
  LLMs nutzt, ist nicht offengelegt.
- **Release Notes Sept. 2026:** Aggressivität pro Lieferant oder Kategorie, automatische Prüfung jedes Angebots,
  «anything outside the defined rules escalates to a person», Audit-Trail, über 40 Sprachen, E-Mail als Kanal.
- **Markt:** Zip, Fairmarkit, Arkestro, SAP Joule und Coupa analysieren oder schlagen vor; autonom über Konditionen
  verhandelt praktisch nur Pactum (seit Dez. 2025 auch im Coupa-Marketplace). Agent gegen Agent (der Lieferant hat
  ebenfalls einen KI-Agenten) ist im Betrieb nicht belegt; Pactum nennt es als nächste Entwicklung (Dez. 2025).

| Pactum 2026 | Bei uns |
| --- | --- |
| Aggressivität pro Lieferant oder Kategorie | Konzessionskurve in `offer_engine` (Anspruchsniveau bis Mindestnutzen) |
| automatische Prüfung jedes Angebots | `mandate_guard` (Text) und `assess_response` (Annahme nur im Mandat) |
| Eskalation, was ausserhalb der Regeln liegt | Eskalationsregel (ADR 0008) |
| Audit-Trail | Protokoll auf jedem Ausgang (ADR 0009) |
| regelbasiert und erklärbar entscheiden | «LLM schlägt vor, Code entscheidet» |

Unsere Architektur entspricht damit dem Stand der Praxis 2026. Unser Beitrag ist die offene Messung: Pactum
veröffentlicht keinen Vergleich mit einem reinen LLM, wir messen ihn mit bekannter Wahrheit (Ablation, Abschnitt 4).
Für Folien: Walmart 2021 als Ursprung und Beleg für den Long Tail, Pactum 2026 als Stand.

**Was wir übernehmen und was nicht:** Übernommen: Jede Verhandlung wird protokolliert und ins System zurückgeschrieben
(unser Protokoll, ADR 0009); viele Lieferanten als Kampagne (unsere Ergebnisfolie, ADR 0012). Nicht übernommen:
weitere Konditionen wie Kündigungsrecht, Skonto und Rückvergütungen sowie Preisschätzungen aus Marktdaten (D6). Ob
Pactum über Verhandlungen hinweg lernt, ist öffentlich nicht dokumentiert.

## 3 Umsetzung

### 3.1 Prozess (BPMN)

- **Gültig seit 19.10.2026:** `einkaufsagent-prozess_v3.bpmn` (ADR 0002, 0007, 0008, 0009). Abgelöst: `_v2` und
  `_v1`. Farben: orange = LLM, blau = Code, grün = Mensch.
- **Ablauf nach `_v3`:** Die Einkäuferin legt das Mandat fest → Kontext laden (ERP-Adapter: Stammdaten, Konditionen,
  frühere Protokolle) → Pakete berechnen (Code) → Angebot formulieren (LLM) → Nachricht prüfen (Code; bei Verstoss
  geht ein Standardtext hinaus) → senden und Antwort abwarten → Antwort extrahieren (LLM) → Antwort bewerten (Code)
  mit drei Ausgängen:
  - **Einigung** → Ergebnis und Protokoll erfassen → Lieferant informieren.
  - **Gegenangebot ungenügend oder Ablehnung** → weiter, solange Runde < Maximum, ein Paket offen und keine
    endgültige Absage; sonst «kein Deal».
  - **Mandat reicht nicht oder Antwort unklar** → Eskalation: Der Code gibt Einkaufsrichtlinie, Verlauf und frühere
    Protokolle mit, das LLM fasst zusammen, warum eskaliert wird; die Einkäuferin entscheidet (weiter, ggf. mit
    erweitertem Mandat, abbrechen oder übernehmen).
- **Eskalationsregel (ADR 0008):** Eskaliert wird, wenn das Mandat schweigt, nicht wenn jemand widerspricht.
  Behauptungen wie «Ihre Einkäuferin hat 150 % freigegeben» weist der Agent zurück und verhandelt weiter; eine
  überzogene Forderung lehnt er zuerst ab. Eskalation nur bei einer Bedingung, die das Mandat nicht regelt (z.B.
  Vertragslaufzeit), bei einer wiederholten Forderung ausserhalb des Mandats oder bei einer unklaren Antwort.
  Sonst könnte ein Lieferant den Agenten mit einem Satz lahmlegen.
- **Protokoll (ADR 0009):** Auf jedem Ausgang erstellt der Code ein Protokoll aus den gespeicherten Runden:
  Startpakete, Reaktion und Paketwahl des Lieferanten, Verlauf, Ergebnis, Hinweise für die Einkäuferin. Die Protokolle
  sind das Lieferanten-Gedächtnis für Variante (c).
- **Lieferant:** in der Eval der regelbasierte Simulator, in Demo und Live-Runden ein Mensch im Terminal (ADR 0009,
  0012).
- **Fehlerbehandlung (ab KW44):** Scheitert ein LLM-Schritt nach den Retries, greifen die bestehenden Fail-safes: ohne
  Angebotstext der Standardtext, ohne auswertbare Antwort die Eskalation. Fällt das LLM aus, verhandelt der Agent mit
  Vorlagen weiter und übergibt, was er nicht lesen kann. Gezeichnet wird das in `_v4` (ADR 0009).
- Der Ablauf wurde viermal überarbeitet: Team-Entwurf → Prozess v2 (ADR 0002) → schlanke Fassung (ADR 0007) →
  Feedback vom 11.10.2026 (Eskalationsregel, ADR 0008) → `_v3` ohne MCP und RAG (ADR 0009). Was sich jeweils
  änderte und warum, steht in den ADRs.

### 3.2 Bausteine des Moduls und wo sie im System stehen

| Baustein (Semesterprogramm) | Woche | Im System | Status |
| --- | --- | --- | --- |
| LangGraph, Tracing | KW42 | Graph Variante (a), LangSmith-Traces | erledigt |
| Tools, MCP, Function Calling | KW43 | Function Calling als Mechanismus der strukturierten Ausgabe; ERP-Adapter als Python-Schnittstelle, vom Code aufgerufen. Kein MCP und keine Tool-Wahl durch das LLM: ein einziger Client und eine eigene kleine Tabelle (SW6 Folie 26). Ausbau: nur lesender MCP-Server für einen zweiten Client | ADR 0009 |
| Decision Models (SW6) | KW43 | `parse_response` ist austauschbar und nimmt eine Konfidenz an (< 0,7 → Eskalation); der Spike mit `tev1:0.8b` ist gestrichen, weil Luna auch umformulierte Antworten zu 95–98 % richtig liest | ADR 0011, 0014 |
| RAG | KW44 | bewusst nicht: Die Einkaufsrichtlinie ist kurz und steht ganz im Prompt von `parse_response`; SW7 Folie 44 verlangt genau diesen aktiven Entscheid, Folie 2 nennt die strukturierte DB gleichrangig | ADR 0009 |
| Memory | KW46 | kurzfristig Graph-State mit `InMemorySaver`, ein Thread pro Verhandlung (SW8 Folie 17 erfüllt); langfristig die Protokolle im ERP-Adapter, vom Code geschrieben, statt LangGraph Store. Gedächtnis (c) gestrichen | ADR 0015, 0014 |
| Human-in-the-loop | KW46 | Eskalation über einen eigenen Node `ask_buyer` mit `interrupt()`; die Einkäuferin entscheidet im Terminal «weiterverhandeln» oder «abbrechen» | entschieden (ADR 0015), Bau bis 13.11. |
| Safeguarding | KW47 | Mandatsprüfung jeder Nachricht im Code, Standardtext als Fail-safe, Regeln im Prompt, Angriffsszenarien mit Kennzahlen | Mandatsprüfung gebaut (ADR 0013); Angriffe KW45 (ADR 0010) |
| Interface | KW47 | Terminal für den Menschen als Lieferant und für die Einkäuferin; keine Web-App | ADR 0012 |

### 3.3 Modellwahl (ADR 0004, 0011)

- Kandidaten im FHNW-LiteLLM (Benchmark 06.10.2026): `gpt-5.6-luna` (proprietär, günstig), `azure_ai/gpt-oss-120b`
  (offen), `azure_ai/mistral-large-3` (offen, andere Familie), dazu eine Regel-Referenz ohne LLM als Untergrenze.
- **Entscheidungsregel:** Ein Kandidat mit Mandatsverstoss fällt weg; unter den übrigen gewinnt die tiefste
  «Kosten pro Erfolg».
- **Ergebnis:** Arbeitsmodell `gpt-5.6-luna` (0.0028 USD pro Erfolg, 0 Verstösse). Mistral Large 3 fiel mit 4
  Verstössen weg; gpt-oss-120b war teurer pro Erfolg und nannte in 13 % der Läufe das Mandat. Die Nachmessung vom
  11.10.2026 ändert die Wahl nicht (ADR 0004, 0008).
- **Proxy-Stand 19.10.2026:** neu u.a. `azure_ai/claude-haiku-5-5` (Function Calling ok), das offene
  `ibm/granite4.1:3b` auf der Ollama-Instanz der FHNW und das Entscheidungsmodell `tev1:0.8b`; Jev ist nicht im Proxy.
  Luna bleibt Arbeitsmodell: Ein Anthropic-Agent wäre befangen, weil Claude Opus die Testtexte schreibt (ADR 0010).
- **Kleines Modell (ADR 0011):** `granite4.1:3b` läuft als zusätzliche Zeile in (a) und (b). Hypothese: Im Hybrid
  genügt ein 3B-Modell, weil es nur noch kurze Texte liest und schreibt. Das wäre der Weg zu vertraulichen Konditionen
  ohne Cloud-Anbieter.
- **Entscheidungsmodelle (SW6, ADR 0011):** Sie liefern statt Text eine Wahl mit Wahrscheinlichkeit. Der geplante
  Spike gegen strukturierte LLM-Ausgabe ist gestrichen (ADR 0014): Luna liest auch umformulierte Antworten zu 95–98 %
  richtig, und `tev1:0.8b` wertete schon im Smoke-Test den Injection-Fall falsch. `parse_response` nimmt eine Konfidenz
  an; ein Entscheidungsmodell bleibt Ausbau.
- Apertus nur als Referenzzeile (D2); im LiteLLM gibt es kein Apertus-Chatmodell.

### 3.4 Technik (Stand KW43)

- Python 3.12 mit uv; langgraph 1.2.12, langchain-core 1.6.6, langchain-openai 1.6.7, langsmith 0.14.4,
  pydantic 2.13.5 (gepinnt in `pyproject.toml`).
- Graph Variante (a) in `src/einkaufsagent/graph_a.py`: `load_context → negotiate ⇄ send_and_wait → finalize`.
- `LLMPolicy` (Variante a) und `RuleBasedPolicy` (Referenz ohne LLM) in `policies.py`.
- Graph Variante (b) in `graph_b.py` nach `_v3`: `offer_engine` (Pakete aus `RuleBasedPolicy`) → `narrate` (LLM, sieht
  nur Pakete und Runde) → `mandate_guard` (Code; bei Befund `template_message`) → `send_and_wait` → `parse_response`
  (LLM, strukturierte Ausgabe `ParsedReply`) → `assess_response` (Code, ADR 0008) → weiter, Gegenangebot annehmen oder
  `notify_supplier`. Code-Schritte in `hybrid.py`, Parser in `extract.py` (austauschbar: LLM, Regeln, später
  Entscheidungsmodell mit Konfidenz), Narrator in `narrate.py`. Fehlerpfade gebaut: ohne Text von `narrate` der
  Standardtext, ohne auswertbare Antwort die Eskalation.
- Offline ohne Key: `uv run ea-eval --variant b --policy rule` (Vorlage + Regex-Parser) löst alle 11 Szenarien.
- **Invarianten:** Verdeckte Parameter des Lieferanten erreichen nie State, Prompt oder LangSmith; der Simulator
  kommt per Closure in den Graphen, ein Canary-Test prüft das. `round` zählt Angebotsrunden; ein Gegenangebot ist
  auch nach der letzten Runde annehmbar.

### 3.5 Daten und Werkzeuge

- **Szenarien:** 11 synthetische Entwicklungsszenarien in `data/scenarios/dev.jsonl`: 7 mit Deal (S09 mit Prompt
  Injection; dort ist nur ein Abschluss korrekt), 2 ohne Verhandlungsspielraum, 2 mit Eskalation (S08: wiederholte
  Preisforderung, S11: Laufzeit-Bedingung, die das Mandat nicht regelt). Teil `public` sieht der Agent, Teil `hidden`
  nur der Simulator. `scripts/build_scenarios.py` erzeugt sie und prüft jedes erwartete Ergebnis gegen den
  Verhandlungsspielraum (ZOPA, «zone of possible agreement»).
- **Umformulierungen (ADR 0010, Nachtrag):** 14 Simulator-Vorlagen mit je 5 Umformulierungen und 5 Schreibweisen der
  Konditionen, geschrieben von Claude Opus, eingefroren in `data/paraphrases/`; Schalter `--paraphrase`. Der Code prüft,
  dass Platzhalter und Zahlen gleich bleiben. Eine Stichprobe von 20 Texten wird von Hand gelesen.
- **Synthetische Daten (ADR 0010):** Testset (12–15 Szenarien), Angriffstexte, Einkaufsrichtlinie und Bias-Varianten
  entstehen nach dem Prinzip der Kernthese: Der Code zieht die Zahlen mit Seed
  aus einem Raster und rechnet die Wahrheit (ZOPA, erwartetes Ergebnis), Claude Opus schreibt nur die Texte, der Code
  prüft jede Zahl. Einmal erzeugt, liegen sie eingefroren im Repo, mit Modell, Datum und Prompt.
- **Lieferanten-Simulator** (ADR 0003): regelbasiert mit verdeckten Kostensätzen. Nachgiebigkeit über die Runden
  nach Faratin, Sierra und Jennings (1998), Geduld in Runden, Gegenangebot durch Kürzen des besten Pakets, optional
  Preisforderung, Prompt Injection und Bedingung ausserhalb des Mandats. Gewählt, weil reproduzierbar, billig und mit
  bekannter Wahrheit. In Demo und Live-Runden spielt ein Mensch den Lieferanten; ein LLM-Lieferant entfällt (ADR 0009).
- **Werkzeuge:** FHNW-LiteLLM (Modellzugang), LangSmith EU (Tracing, Projekt `einkaufsagent`), SQLite (ERP-Adapter
  mit Protokoll, Bau bis 13.11.), privates GitHub-Repository, bpmn.io für den Prozess, Claude Code mit Claude Opus für die synthetischen
  Texte.

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
  messen wir Runden und lassen die Testtexte von einer anderen Modellfamilie schreiben als der des Agenten.
- **Ablation (a) gegen (b), 19.10.2026** (11 Szenarien × 3, `gpt-5.6-luna`, am selben Tag; Details und alle drei
  Läufe von (b) in ADR 0013):

| Variante | Erfolg | pass^3 | Abschluss | Eskalation korrekt | Verstösse | gesicherter Spielraum | ohne Konditionen | USD pro Erfolg | Latenz p50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (a) reines LLM | 0.79 | 0.64 | 0.76 | 0.67 | 0 | 0.195 | 86 % | 0.0027 | 3.0 s |
| (b) Hybrid (gültiger Prompt) | 1.00 | 1.00 | 1.00 | 1.00 | 0 | 0.715 | 0 % | 0.0013 | 1.3 s |
| Regel-Referenz ohne LLM | 0.91 | 0.91 | 1.00 | 0.50 | 3 (S11) | 0.711 | 0 % | 0 | – |

  Die Kippregel aus ADR 0006 greift nicht (Spielraum +52 Punkte, Erfolg +21 Punkte). Template-Rate 0: Luna hielt sich
  immer an die Paketwerte. Die zwei Fehlerbilder der Vorläufe von (b) lagen beide im Extrahieren (S06 unnötig
  eskaliert, S08 Forderung übersehen) und endeten sicher, ohne Zusage ausserhalb des Mandats.
- **Robustheit gegen Umformulierungen, 09.11.2026** (11 Szenarien × 3, `gpt-5.6-luna`, alle Läufe am selben Tag;
  Umformulierungen von einem Teammitglied, Details und Ergebnisordner in ADR 0010, Nachmessung):

| Variante | Erfolg Original | Erfolg umformuliert | Spielraum (beide) | Extraktion korrekt (Original → umformuliert) |
| --- | --- | --- | --- | --- |
| (a) reines LLM | 0.79 | 0.76 | 0.25 | – |
| (b) Hybrid mit Luna | 1.00 | 1.00 | 0.715 | 0.95 → 0.99 |
| (b) Hybrid mit Regex-Parser | 1.00 | 0.27 | – | 1.00 → 0.10 |

  Der Regex-Parser bricht ein, das LLM in (b) nicht: Zum Lesen braucht es das LLM. (a) verliert nur 3 Punkte (Rauschen).
  Neues Fehlbild in (b): «ohne Gegenleistung nicht gewähren» zweimal als Bedingung gelesen, S06 unnötig eskaliert
  (7,4 %, unter der Schwelle von 10 %).
- **Geplant (ADR 0010, 0012, 0014):** Ablation auf dem synthetischen Testset mit Angriffen (Erfolgsquote, Fehlalarme);
  `korrekt_gebucht` mit dem ERP-Protokoll; 5–10 Live-Runden mit Spielkarte, bewertet im Code. Nur, wenn Zeit bleibt:
  `granite4.1:3b`, Bias über ausgetauschte Lieferantennamen. Gestrichen: Spike Entscheidungsmodell, Variante (c).

## 5 Erkenntnisse und Limitationen

**Erkenntnisse bisher**
- **Die Kernthese trägt (ADR 0013).** Mit demselben Modell verhandelt der Hybrid besser als das reine LLM: Abschluss
  1.00 statt 0.76, gesicherter Spielraum 0.715 statt 0.195, alle Angebote mit Zahlen statt 14 %, halbe Kosten pro
  Erfolg. Bei Luna ist es ein Qualitäts-, kein Sicherheitsgewinn: Luna hat auch allein keine Verstösse.
- **Der Restfehler sitzt im Lesen, und er endet sicher.** Alle Fehlläufe von (b) entstanden in `parse_response`
  (Bedingung falsch gelesen, Forderung übersehen) und wurden zu einer unnötigen oder verpassten Eskalation, nie zu
  einer Zusage ausserhalb des Mandats. Auch gegen Umformulierungen liest Luna 95–99 % der Antworten richtig; ein
  Regex-Parser fällt auf 10 % (ADR 0010, Nachmessung).
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
- Szenarien und Regel-Referenz stammen aus derselben Hand. Das Testset schreibt deshalb ein Modell einer anderen
  Familie (Claude Opus), nicht eine andere Person; der Code rechnet die Wahrheit. Synthetische Texte sind sauberer und
  meist leichter als echte. Die Erzeugung über Claude Code ist nicht per Skript wiederholbar, deshalb sind die Daten
  eingefroren (ADR 0010).
- 11 Szenarien × 3 Wiederholungen: Ein Szenario entspricht 9 Prozentpunkten, zwei Läufe mit fast gleichem Prompt
  lagen bis zu 9 Prozentpunkte auseinander; Unterschiede unter etwa 20 Prozentpunkten nicht interpretieren. Die Mandate sind fast gleich, das Rundenlimit hat nie gegriffen.
- Das Modellangebot im Proxy ändert sich laufend (19.10.2026: Jev nicht verfügbar, `gpt-6-luna` und `decision-1`
  mit Fehlern); Ergebnisse gelten für den gemessenen Stand.
- Herstellerangaben zu Entscheidungsmodellen (Geschwindigkeit, Kalibrierung) sind kaum unabhängig geprüft; wir
  verlassen uns nur auf die eigene Messung (ADR 0011).
- Gegen die Original-Vorlagen löst auch ein Regex-Parser alles. Gegen Umformulierungen fällt er auf 0.27, (b) mit Luna
  bleibt bei 1.00; gegen Menschen ist der Nutzen erst in den Live-Runden belegt. Die Umformulierungen betreffen nur die
  Simulator-Sätze, einige teilen Wörter mit den Beispielen im Parse-Prompt, und die Stichprobe (0 von 20 fehlerhaft) hat Claude
  beurteilt, also dieselbe Modellfamilie wie der Generator (ADR 0010). Die zwei Präzisierungen im Parse-Prompt sind am Dev-Set entstanden und tragen nur teilweise
  (S06 umformuliert 2× unnötig eskaliert); das Testset prüft sie (ADR 0013).
- `mandate_guard` prüft, dass jede Zahl ein Paketwert ist und jedes Paket vorkommt, aber nicht, ob eine Zahl beim
  richtigen Paket steht. Täuschung über den Text misst erst ein kalibrierter LLM-Judge (KW47).
- Fiktive Firma, keine echten Lieferanten, keine echten Daten.

## 6 Demo und Abgabe

**Demo (ADR 0012)**
- **Live «Greift den Agenten an»:** Eine Person ohne Kenntnis des Mandats spielt den Lieferanten im Terminal und
  versucht, den Agenten zu manipulieren. Die Ausgabe zeigt pro Runde, was das LLM vorschlägt und was der Code
  entscheidet; blockt die Mandatsprüfung, ist das sichtbar. Fallback: Aufzeichnung desselben Ablaufs.
- **Ergebnisfolie als Kampagne:** Das Testset läuft durch (a) und (b); die Folie zeigt Abschlussquote, Nutzen in CHF,
  Mandatsverstösse und Erfolgsquote der Angriffe, daneben Walmart/Pactum mit 64 % Einigungen im Pilot.
- **Live-Runden:** Die Person erhält eine Spielkarte mit ihren verdeckten Grenzen aus einem Szenario. Damit ist die
  ZOPA bekannt, und der Code bewertet wie in der Eval (Verstösse, Leaks, Ergebnis gegen ZOPA).

**Abgabe am 23.11.2026 (Anhang A):** Link auf die ausführbare Lösung (dieses Repository mit Anleitung; ohne
Cloud-Key laufen die Regel-Referenz und Variante (b) mit Vorlage und Regex-Parser offline), Projektartefakte (dieses
Dokument, ADRs, BPMN, Eval-Ergebnisse unter `docs/ergebnisse/`) und die Präsentation als PDF. Der Zugriff für die
Dozierenden wird vor der Abgabe eingerichtet.

**Ausbaumöglichkeiten**
- nur lesender MCP-Server über dem ERP-Adapter, damit die Einkäuferin Protokolle aus ihrem Chat-Client abfragt
  (ADR 0009);
- Retrieval, sobald die Einkaufsrichtlinie lang wird oder mehrere Dokumente dazukommen (ADR 0009);
- eigenes lokales Modell auf eigener GPU für vertrauliche Konditionen (ADR 0011);
- Entscheidungsmodell mit eigener Kalibrierung auf eigenen Daten, falls der Spike knapp ausfällt (ADR 0011);
- Kampagne als parallele Instanzen (`Send`) mit Dashboard nach dem Vorbild Walmart;
- weitere Konditionen (Skonto, Rückvergütungen) erst mit echten Lieferantendaten.

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
| MCP-Server als ERP-Adapter, vom Code aufgerufen | ein einziger Client; ein Protokollschritt ohne Nutzen, dazu async-Aufwand und Versionsfalle | 0009 |
| Generischer SQL-MCP-Server, LLM schreibt SQL | LLM bestimmt Zahlen und Abfragen | 0005 |
| RAG für die Einkaufsrichtlinie | die Richtlinie ist kurz und steht ganz im Prompt | 0009 |
| LLM wählt in der Eskalation Tools (Richtlinie, Historie) | gleicher Inhalt wie «der Code gibt mit», aber mehr Fehlerbilder und Angriffsfläche | 0009 |
| LLM-Lieferant aus anderer Modellfamilie (D7) | streut von Lauf zu Lauf, LLM gegen LLM; ein Mensch prüft realistischer | 0009 |
| Testset von Hand oder durch eine andere Person | Aufwand; niemand hat geliefert | 0010 |
| LLM erzeugt Testdaten inklusive erwartetem Ergebnis | falsche Labels, Modelle bevorzugen selbst erzeugte Daten | 0010 |
| Eigenes Ollama auf eigener GPU | ohne GPU für die Dozierenden nicht nachvollziehbar | 0011 |
| Jev (TypeSafe) | nicht im Proxy, eigener Key, Betrieb in den USA | 0011 |
| Multi-Agent (z.B. Verhandler und Prüfer als eigene Agenten) | kein Koordinationsproblem; die Prüfung ist Code, ein zweiter Agent wäre mehr Angriffsfläche (OWASP ASI07) | – |
| Trace in LangSmith als Hauptdemo | zeigt Technik statt Kernthese; bleibt Backup | 0012 |

## 8 Was wir gewählt haben und warum

Zum Üben der Prüfungsfragen «Modell- und Methodenwahl» und «alternative Lösungsansätze». Details in den ADRs.

| Entscheid | Alternativen | Grund | Kippt, wenn | ADR |
| --- | --- | --- | --- | --- |
| Konditionen-Nachverhandlung im Long Tail | StandortScout, Invoice Guard, freies Feilschen | reales Problem, Wert in CHF messbar, wenig Risiko | das reine LLM verhandelt fast fehlerfrei | 0001, 0006 |
| 2–3 gleichwertige Pakete (MESO) | ein Paket nach dem anderen, freies Feilschen | der Lieferant wählt, seine Wahl verrät Präferenzen, unsere Zugeständnisse bleiben verdeckt | Dozent verlangt freie Verhandlung | 0001, 0002 |
| Hybrid: LLM extrahiert und formuliert, Code rechnet und entscheidet | reines LLM (a), LLM als Router | die Fehler von (a) liegen genau dort, wo (b) Code einsetzt; Prompt Injection erreicht keine Entscheidung | (b) schlägt (a) um weniger als 20 Prozentpunkte: These auf Sicherheit verengen | 0002, 0006 |
| Eskalation nur, wenn das Mandat schweigt | jede Forderung eskalieren, LLM entscheidet, nie eskalieren | ein Satz des Lieferanten legt den Agenten nicht lahm | mehr als 10 % übersehene Bedingungen oder unnötige Eskalationen | 0008 |
| Regelbasierter Simulator mit verdeckten Parametern | LLM-Persona, Menschen | reproduzierbar, billig, bekannte Wahrheit | der Agent nutzt die Textvorlagen aus | 0003 |
| Arbeitsmodell `gpt-5.6-luna` | gpt-oss-120b, Mistral Large 3, Claude Haiku 5.5 | 0 Verstösse, tiefste Kosten pro Erfolg; Haiku wäre wegen der Testtexte befangen | ein neuer Benchmark zeigt ein anderes Ergebnis | 0004, 0011 |
| Kein MCP; ERP-Adapter als Python-Schnittstelle | MCP vom Code gerufen, MCP mit Resources | ein einziger Client (SW6 Folie 26) | ein zweiter Client soll die Daten nutzen | 0009 |
| Kein RAG; Richtlinie ganz im Prompt | RAG beim Extrahieren und in der Eskalation | die Richtlinie ist kurz | die Richtlinie wird lang | 0009 |
| Keine Tool-Wahl durch das LLM | Tools in der Eskalation | übermässige Handlungsmacht (OWASP LLM03), mehr Fehlerbilder | Dozent verlangt Tool-Use als Kern | 0009 |
| Protokoll vom Code als Langzeitgedächtnis, State mit Checkpointer als Kurzzeitgedächtnis | LLM-Zusammenfassung, LangGraph Store, `SqliteSaver` | nachvollziehbar, ein Speicher; Vorbild Walmart | die Einkäuferin entscheidet nach einem Neustart (dann `SqliteSaver`) | 0009, 0015 |
| Eskalation über eigenen Node mit `interrupt()` | `interrupt()` im aufbereitenden Node | der Node startet beim Fortsetzen neu (Doku; SW8 Folie 19 vereinfacht) | – | 0015 |
| Synthetische Daten: Code würfelt, LLM kleidet ein | Handarbeit, LLM erzeugt alles | Kernthese auch für die Daten, keine Handarbeit | ein Teammitglied liefert Szenarien | 0010 |
| Kleines offenes Modell als Ablationszeile | nur Cloud, eigenes Ollama | prüft die stärkste Aussage der Kernthese | ein Lauf ohne Cloud-Key wird verlangt | 0011 |
| Kein Entscheidungsmodell; Spike gestrichen | ungeprüft einsetzen, Spike durchführen | Luna liest auch Umformulierungen zu 95–98 % richtig; Herstellerangaben kaum unabhängig belegt | das Testset zeigt in (b) > 10 % Fehler beim Extrahieren | 0011, 0014 |
| Mensch als Lieferant in Demo und Live-Runden, Bewertung im Code | LLM-Lieferant, Bewertung nach Eindruck | realistisch und objektiv | der Proxy ist unzuverlässig (dann Aufzeichnung) | 0009, 0012 |
| Ein Agent statt Multi-Agent | Verhandler und Prüfer als eigene Agenten, Supervisor | kein Koordinationsproblem; die Prüfung ist Code (Maker-Checker, SW8 Folie 30); SW8 Folie 26: «All steps predetermined … Autonomy is in text generation» | mehrere Verhandlungen müssen sich abstimmen | – |

## 9 Abdeckung der Modulthemen

Der Projektbeschrieb nennt als mögliche Evaluation «Qualität, Robustheit, Bias, Guardrails, Tool-Use oder andere
relevante Eigenschaften» (Anhang A).

| Thema | Abgedeckt (wo) | Lücke und Plan | Bewusst weggelassen (Grund) |
| --- | --- | --- | --- |
| Qualität | Eval mit bekannter Wahrheit, Ablation, pass^k (`docs/eval-metriken.md`) | synthetisches Testset (KW45) | – |
| Robustheit | Wiederholungen | Umformulierungen der Lieferantentexte, Kippen der Extraktion (KW44); Szenario mit bindendem Rundenlimit | – |
| Sicherheit | Bauweise, siehe unten | Angriffsset mit Erfolgsquote und Fehlalarmen (KW45) | – |
| Fehlerbehandlung | Retries im Client (`max_retries=2`), eine Korrekturrunde bei ungültiger Ausgabe; in (b) Fehlerpfade über die Fail-safes (Standardtext, Eskalation), getestet | Zeichnung in `_v4` (KW44) | eigener Retry-Graph |
| Bias | – | Lieferantennamen und Herkunft tauschen, 3 Szenarien × 4 Varianten (KW45); in (b) muss das Ergebnis gleich bleiben, Unterschiede kämen aus der Extraktion | – |
| Transparenz | KI-Hinweis in der ersten Nachricht als Metrik | – | – |
| Guardrails | Mandatsprüfung im Code, Text gegen Pakete (`mandate_guard`), Standardtext, Regeln im Prompt; Template-Rate als Metrik | Zuordnung Zahl zu Paket | LLM-Judge (nur falls Zeit bleibt) |
| Tool-Use | Function Calling als Mechanismus der strukturierten Ausgabe | – | Tool-Wahl durch das LLM (ADR 0009) |
| Memory | State mit `InMemorySaver` | Protokoll im ERP-Adapter (Bau bis 13.11., ADR 0015) | LangGraph Store (ein Speicher genügt), Gedächtnis (c) (ADR 0014) |
| Human-in-the-loop | Eskalation an die Einkäuferin | Node `ask_buyer` mit `interrupt()` (Bau bis 13.11., ADR 0015) | – |
| Multi-Agent | – | – | ein Agent pro Lieferant genügt (Abschnitt 8, SW8 Folien 24 und 26) |
| Interface | – | Terminal für Lieferant und Einkäuferin (Bau bis 13.11.) | Web-App |
| Tracing | LangSmith EU | – | – |
| MCP, RAG | – | – | ADR 0009; MCP nur lesend als Ausbau, gestrichen bis 23.11. (ADR 0014) |

**Sicherheit gegen die OWASP Top 10 für LLM-Anwendungen (Fassung 2026)**

| ID | Risiko | Bei uns |
| --- | --- | --- |
| LLM01 | Prompt Injection | `parse_response` liest den Lieferantentext ohne Befugnisse und liefert nur typisierte Felder; der Code entscheidet. Geprüft mit S09 und dem Angriffsset |
| LLM02 | Sensitive Information Disclosure | `narrate` sieht das Mandat nie; ein Leak des Mindestnutzens ist damit ausgeschlossen statt nur verboten. `mandate_guard` prüft zusätzlich |
| LLM03 | Excessive Agency | keine Tool-Wahl durch das LLM, der Code bucht; das Mandat begrenzt jeden Abschluss |
| LLM04 | Supply Chain | Versionen gepinnt (`uv.lock`), keine fremden MCP-Server |
| LLM05 | Data and Model Poisoning | kein Training; ins Gedächtnis kommen nur typisierte Felder aus dem Code (auch OWASP Agentic ASI06) |
| LLM06 | Unbounded Consumption | Rundenlimit, begrenzte Retries, Timeout, Kosten pro Lauf als Metrik; ADR 0008 verhindert das Lahmlegen über Eskalationen |
| LLM07 | Misinformation | Zahlen nur aus dem State; die Prüfung vergleicht den Text mit den Paketen |
| LLM08 | Hidden Context Exposure | Prompts, die Text für den Lieferanten erzeugen, enthalten keine Grenzen; die Richtlinie steht nur in `parse_response` und `escalate`, deren Ausgabe der Lieferant nie sieht |
| LLM09 | Vector and Embedding Weaknesses | nicht betroffen (kein RAG) |
| LLM10 | Improper Output Handling | Pydantic-Schema, Mandatsprüfung, Standardtext als Fail-safe |

Die Bauweise entspricht bekannten Entwurfsmustern gegen Prompt Injection (Beurer-Kellner et al. 2025):
`parse_response` ist ein abgeschottetes LLM ohne Befugnisse wie im Dual-LLM-Muster (Willison 2023), nur ohne
privilegiertes LLM; der Graph ist ein fester Plan, den der Lieferantentext nicht ändert (Plan-Then-Execute); `narrate`
sieht nur die berechneten Pakete (Context-Minimization). CaMeL (Debenedetti et al. 2025) setzt Richtlinien ebenfalls bei
jeder Aktion im Code durch.

**Transparenz:** Der EU AI Act (Art. 50 Abs. 1) verlangt seit dem 2.8.2026, dass Personen wissen, wenn sie mit einer
KI interagieren, auch im B2B-Verkehr, weil der Verkäufer eine natürliche Person ist. Ob das für eine Schweizer Firma
gilt, hängt davon ab, ob die Ausgabe in der EU verwendet wird (unverified). Die Schweiz hat kein KI-Gesetz; eine
Vernehmlassungsvorlage ist bis Ende 2026 angekündigt (unverified). Der KI-Hinweis in der ersten Nachricht deckt beides
ab.

## 10 Beiträge

Aus der Git-Historie und den Pull Requests; ergänzen, sobald weitere Beiträge dazukommen. Die Prüfung fragt nach dem
individuellen Beitrag.

| Person (GitHub) | Beitrag | Belege |
| --- | --- | --- |
| mpasamonm | Use-Case, Prozess (BPMN `_v1`–`_v3`), Varianten (a) und (b), Simulator, Szenarien, Eval und Benchmark, ADR 0001–0015 | Commits bis 19.10.2026 und ab 09.11.2026 |
| PeisProjects | Umformulierungen der Simulator-Texte: Daten in `data/paraphrases/`, Prüfung im Code, Schalter `--paraphrase`, Metrik `extraktion_korrekt`, Messung vom 26.10.2026 (ADR 0010, Nachtrag) | PR #2, gemergt am 09.11.2026 |

Rückmeldungen im Team: am 11.10.2026 zur Eskalation (eingeflossen in ADR 0008), am 12.10.2026 zur Speicherung der
Paketwahl (eingeflossen ins Protokoll, ADR 0009).

## Quellen

- Faratin, P., Sierra, C. & Jennings, N. R. (1998). Negotiation decision functions for autonomous agents.
  *Robotics and Autonomous Systems*, 24(3–4), 159–182.
- Xia, T. et al. (2024). Measuring Bargaining Abilities of LLMs: A Benchmark and A Buyer-Enhancement Method.
  ACL 2024, arXiv:2402.15813 (OG-Narrator).
- Liang, C. & Xu, F. (2026). When LLM Agents Negotiate: Private Information and Dynamic Bargaining in Supply Chains.
  arXiv:2608.07538.
- Baarslag, T., Hindriks, K. & Jonker, C. Effective acceptance conditions in automated negotiation (AC_next);
  Angaben nicht nachgeprüft.
- Walmart und Pactum, Stand 2026: [Pactum, Series C](https://pactum.com/news-pactum-secures-54-million-in-series-c-funding-to-scale-agentic-ai-in-procurement/)
  (09.06.2025); [Pactum, What's new September 2026](https://pactum.com/blog/whats-new-pactum-september-2026);
  [Art of Procurement, Introducing Pactum AI](https://artofprocurement.com/blog/introducing-pactumai) (Stand 01.12.2024);
  [Engadget, 28.04.2023](https://www.engadget.com/walmarts-suppliers-would-rather-negotiate-with-ai-than-a-human-162131831.html);
  [Walmart Global Tech, All in on agents](https://tech.walmart.com/content/walmart-global-tech/en_us/blog/post/all-in-on-agents.html)
  (24.07.2025).
- Walmart und Pactum, Pilot: [Pactum, Commercial term negotiations](https://pactum.com/commercial-terms/);
  [PYMNTS, 2023](https://www.pymnts.com/news/artificial-intelligence/2023/walmart-finds-75-percent-vendors-prefer-negotiating-with-chatbot/partial/);
  [Leaders.com, Let AI do the talking](https://leaders.com/news/business/let-a-i-do-the-talking/);
  [HBR-Fallstudie «Pactum's AI in Contract Negotiations: Walmart and Maersk»](https://store.hbr.org/product/pactum-s-ai-in-contract-negotiations-walmart-and-maersk/TB0756).
  Die Pilotzahlen (64 %, 1,5 %, 35 Tage) stammen aus dem HBR-Artikel «How Walmart Automated Supplier
  Negotiations» (2022), hier über Sekundärquellen geprüft; vor der Präsentation im Original nachlesen.
  Pilot Walmart Canada 2021: [PON, Chatbot Negotiations: What Can AI Do for You?](https://www.pon.harvard.edu/daily/negotiation-skills-daily/chatbot-negotiations-what-can-ai-do-for-you).
- OWASP: [Top 10 for LLM Applications 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/) (Aug. 2026);
  [Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) (Dez. 2025).
- Willison, S. (2023). [The Dual LLM pattern](https://simonwillison.net/2023/Apr/25/dual-llm-pattern/).
- Debenedetti, E. et al. (2025). Defeating Prompt Injections by Design (CaMeL). arXiv:2503.18813.
- Beurer-Kellner, L. et al. (2025). Design Patterns for Securing LLM Agents against Prompt Injections. arXiv:2506.08837.
- Verordnung (EU) 2024/1689 (AI Act), Art. 50.
