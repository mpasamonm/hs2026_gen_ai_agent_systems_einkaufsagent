# ADR 0017 – Verhandlungsstrategie lassen, Geschichte schärfen

- **Status:** angenommen am 11.11.2026 (Entscheid des Nutzers: A)
- **Datum:** 11.11.2026
- **Berührt:** ADR 0006 und 0013 (Kernthese, Ablation), ADR 0012 (Red-Teaming, Nachtrag 11.11.), ADR 0014
  (Feature-Freeze)

## Kontext

Frage des Nutzers (11.11.2026): Lieferanten lernen mit der Zeit, wie sie beim Agenten die besten Konditionen bekommen.
Verhandelt der Agent klug, maximiert er, und ist der Use-Case richtig bemessen? Anlass war das Red-Teaming R1 (S04:
Ablehnen bis Runde 6 ergab den Anteil am Spielraum 0.00 statt 0.84).

Die Strategie (`RuleBasedPolicy`, in (b) `offer_engine` und `assess_reply`) ist in der Sprache des BOA-Rahmens
(Baarslag et al.: Bidding, Opponent model, Acceptance) ein «Conceder Linear» (Faratin et al. 1998, e = 1) ohne
Gegnermodell mit AC_next und Fallback auf den Mindestnutzen in der letzten Runde. Jede Antwort ohne Abschluss kostet einen
Schritt.

## Befunde (Analyse 11.11.2026, offline, `scripts/analyse_strategie.py`; Recherche lokal in `kontext/`)

Messung: Effizienz aus den finalen Läufen (`docs/ergebnisse/2026-11-09/`); Ausnutzbarkeit mit dem echten Graphen (b),
Vorlage und Regex-Parser, Dev-Set im ökonomischen Kern (Forderung, Bedingung, Injection entfernt, 9 Szenarien mit ZOPA).

1. **Effizient:** Die Abschlüsse von (b) liegen auf der Pareto-Front (Effizienz 1.00 Dev, 0.98 Test). In allen 26
   Szenarien sind die Kapitalkosten des Lieferanten höher als unsere; ein längeres Zahlungsziel vernichtet gemeinsamen
   Wert, eine Mengenzusage schafft welchen. (b) schliesst deshalb mit heutigem Zahlungsziel, 80 % Mengenzusage und Rabatt
   ab (Dev: Ø 2,5 %, Nutzen 2,1 % des Volumens). Von CHF 4'104 Nutzen pro Lieferant und Jahr stammen 88 % aus diesem
   Tausch. Das leistet MESO ohne Gegnermodell: Der Lieferant wählt das für ihn billigste der gleichwertigen Pakete, und
   das ist das effiziente. (a) mit Luna erreicht 0.42 (Dev) bzw. 0.46 (Test), vor allem wegen 90-Tage-Paketen.
2. **Ausnutzbar:** Ein Lieferant, der bis Runde 6 ablehnt, drückt den Anteil am Spielraum von 0.72 auf 0.05 und unseren
   Nutzen um 58 %; unter den Mindestnutzen kommt er nie. Das ist eine bekannte Eigenschaft zeitabhängiger Taktiken:
   «All the strategies that lie on the line CR = 1 give in fully to Hardliner» (Baarslag et al., Artificial Intelligence
   198, 2013, ANAC 2011).
3. **Was-wäre-wenn** (nur gerechnet, nichts gebaut): Konzession nur auf ein Gegenangebot wird durch Scheinkonzessionen
   umgangen; Boulware bringt gegen den Simulator +3 %, gegen Hinhalten nichts; reziprok (Tit-for-Tat) begrenzt den
   schlechtesten Fall auf −40 % statt −58 %, kostet gegen den Simulator 6 % (S03 ohne Abschluss) und lohnt sich erst ab
   rund 26 % strategischer Lieferanten; ein fester Anspruch ist unangreifbar, aber 27 % schlechter.
4. **Praxis:** Pactum legt seine Konzessionslogik nicht offen; nach eigenen Angaben rechnen Regeln, und Anker und Parameter
   werden über viele Verhandlungen angepasst («every negotiation is an A-B test»), nicht pro Gegner. Dass Lieferanten das
   Muster eines Einkaufsbots über Kampagnen lernen, ist nicht belegt, nur argumentiert («Markets learn players», TWS
   Partners, 10.09.2026). Belegt ist aus Labor und Spielen, dass Menschen Maschinen stärker ausnutzen (Karpus et al. 2021,
   de Melo et al. 2016).
5. **Kennzahl:** Der Anteil am Spielraum misst nur die Verteilung, nicht Effizienz, Einigung über alle Lieferanten,
   Aufwand oder Robustheit.

## Alternativen

Trennende Achse: **wie viel wir bis zum 23.11. am gemessenen System ändern.**

| Alternative | Aufwand | Risiko bis 23.11. | Wirkung in der Prüfung |
| --- | --- | --- | --- |
| **A: Strategie lassen, Geschichte schärfen (gewählt)** | 3–4 h | keines; alle Zahlen bleiben | Limitation mit Zahl, Ursache aus der Forschung, gerechnete Alternativen |
| B: reziproke Konzession einbauen (Ausnahme vom Freeze), Dev neu messen, Testset «nach Anpassung» | 6–10 h | alle Zahlen in Folien, README und Demo ändern sich | gegen unseren Simulator schlechter (−6 %), schwer zu verteidigen ohne strategische Lieferanten in der Eval |
| C: Anspruch und Umfang zurücknehmen, nur Ablation zeigen | 1–2 h | gering | verschenkt Tiefe |

## Entscheid

**A.** Strategie, Graph, Prompts und Regeln bleiben unverändert. Wir sagen nicht «maximiert», sondern: Der Agent schliesst
im Mandat und effizient ab (Tausch Rabatt gegen Mengenzusage); seine zeitabhängige Kurve ist für einen informierten
Lieferanten ausnutzbar, der Schaden endet am Mindestnutzen, weil die Grenze im Code liegt.
- `scripts/analyse_strategie.py` (Effizienz aus `runs.jsonl`, Ausnutzbarkeit offline) macht die Zahlen nachvollziehbar.
- Effizienz ist eine Analyse-Kennzahl, nicht Teil von `eval.py` (`docs/eval-metriken.md`).
- `docs/gesamtsystem.md`: neuer Abschnitt 4.x, Limitationen (§5), Ausbau, verworfene Alternativen (§7), Pactum (§2.5).
- Folien: erst in der Überarbeitung der Geschichte (10 Minuten, eigene Session); höchstens eine Backup-Folie.

**Kippt, wenn** in der Demo-Probe oder in den Live-Runden mindestens eine von vier Personen von sich aus hinhält und den
Anteil unter 0.2 drückt (entspricht dem Bruchpunkt p ≈ 0,26); dann B prüfen, auf dem Dev-Set gemessen und nur nach
ausdrücklichem Ja.

## Folgen

- In der Prüfung: «Ist der Agent klug?» → effizient ja, maximierend nein, ausnutzbar wie jede zeitabhängige Taktik;
  Gegenmittel aus der Forschung (reziprok, Boulware, verdeckte Frist, Gegnermodell) und ihr gerechneter Preis.
- Das Mandatsziel «60 Tage» ist gegen Lieferanten mit höheren Kapitalkosten ein schlechter Tausch; real wäre
  Supply-Chain-Finance die Antwort (nicht modelliert).
- Grenzen der Analyse: Lieferanten-Varianten sind Code mit vollem Wissen über das Muster; der Simulator ist selbst
  zeitabhängig; Menschen zeigen erst die Live-Runden.
