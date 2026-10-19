# ADR 0013 – Variante (b) gebaut; Ablation (a) gegen (b): die Kernthese trägt

- **Status:** angenommen am 19.10.2026
- **Datum:** 19.10.2026
- **Berührt:** ADR 0002 (Prozess v2, Template-Rate), ADR 0006 (Kippregel), ADR 0008 (Eskalationsregel, Auslegung
  unten), ADR 0009 (`_v3`, Fehlerpfade), ADR 0011 (`parse_response` austauschbar, `confidence`)
- **Code:** `graph_b.py`, `hybrid.py` (Prüfen, Vorlagen, Bewerten), `extract.py` (Parser), `narrate.py`, Prompts in
  `prompts.py`; Tests in `tests/test_variant_b.py` und `tests/test_variant_b_http.py`
- **Daten:** `results/20261019-160219_a_gpt-5.6-luna/`, `results/20261019-160219_b_gpt-5.6-luna/`,
  `results/20261019-160351_b_gpt-5.6-luna/`, `results/20261019-160556_b_gpt-5.6-luna/` (nicht versioniert)

## Kontext

ADR 0002 und `_v3` (ADR 0009) legen fest: Das LLM formuliert und extrahiert, der Code berechnet die Pakete, prüft jede
Nachricht und entscheidet über Annahme, Weiterverhandeln und Eskalation. ADR 0006 verlangt den Nachweis per Ablation auf
denselben Szenarien; die These wird auf «Sicherheit und Nachvollziehbarkeit» verengt, wenn (b) die Baseline (a) bei
Erfolgsquote oder gesichertem Spielraum um weniger als 20 Prozentpunkte schlägt.

## Entscheid: so ist (b) gebaut

| Node | Typ | Inhalt |
| --- | --- | --- |
| `offer_engine` | Code | Pakete und Konzessionskurve aus `RuleBasedPolicy` (Wiederverwendung, kein zweiter Algorithmus) |
| `narrate` | LLM | sieht nur Pakete und Runde, **weder Mandat noch Lieferantentext** |
| `mandate_guard` | Code | jede Zahl mit «Tage» oder «%» ist ein Paketwert, jedes Paket kommt vor, kein CHF-Betrag, kein Walk-away, KI-Hinweis in Runde 1 |
| `template_message` | Code | Standardtext bei Befund oder wenn `narrate` scheitert |
| `send_and_wait` | Code | Simulator per Closure; weiter geht nur der Text |
| `parse_response` | LLM, austauschbar | `ParsedReply`: Antworttyp, Paketwahl, Gegenangebot, Aussagen mit Typ, Grösse und Wert; Einkaufsrichtlinie (Auszug) im Prompt; eine Korrekturrunde |
| `assess_response` | Code | Einigung nur für ein gesendetes Paket bzw. die eigene Annahme; AC_next; Eskalation nur nach ADR 0008; Zurückweisungen als Vorlage |
| `notify_supplier` | Code | Vorlage pro Ausgang |

Vier Festlegungen, die über ADR 0002 und 0008 hinausgehen:

1. **Einigung aus dem Text, nicht aus dem Simulator.** In (a) beendet das Ereignis des Simulators (`accept`, `confirm`)
   den Lauf; in (b) liest `parse_response` die Zustimmung aus dem Text, wie bei einem echten Lieferanten. Damit trägt
   (b) ein Risiko, das (a) nicht hat. Die Eval zählt es als neuen Verstoss `deal:not_agreed` (gebucht, aber laut
   Simulator nicht so vereinbart).
2. **Dual-LLM-Muster beim Formulieren.** `narrate` bekommt den Lieferantentext nicht; eine Injection erreicht das
   schreibende LLM nicht. Zurückweisungen von Behauptungen und Forderungen setzt der Code als Vorlagensatz davor.
3. **Forderung mit angeblicher Freigabe zählt als Behauptung.** Enthält eine Antwort eine Befugnis-Behauptung, zählen
   ihre Forderungen nicht für die Eskalationsregel 2 aus ADR 0008. Sonst würde die wiederholte Injection in S09 nach
   Regel 2 eskalieren, also genau der Denial of Service, den ADR 0008 verhindern soll. Sicher ist das, weil der Code
   ausserhalb des Mandats ohnehin nichts zusagt.
4. **`confidence` vorbereitet.** Liefert ein Parser eine Konfidenz (Entscheidungsmodell, ADR 0011) unter 0,7, gilt die
   Antwort als unklar und wird eskaliert. Luna und der Regel-Parser liefern keine.

Fehlerpfade (ADR 0009) sind gebaut, nicht erst in KW44: Scheitert `narrate`, geht der Standardtext hinaus; scheitert
`parse_response` nach der Korrekturrunde oder ist der Proxy weg, wird eskaliert. Getestet mit Fake-Server und
absichtlich kaputten Bausteinen.

## Messung 19.10.2026 (11 Szenarien × 3, `gpt-5.6-luna`, am selben Tag)

`uv run ea-eval --variant a|b --model gpt-5.6-luna --repeats 3`. (b) lief dreimal, weil zwei Befunde zu je einer
Präzisierung im Prompt von `parse_response` führten (unten); alle drei Läufe stehen hier.

| Lauf | Erfolg | pass^3 | Abschluss | Eskalation korrekt | unnötig | verspätet | Verstösse | Spielraum | Template-Rate | USD/Erfolg | Latenz p50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (a) Luna | 0.79 | 0.64 | 0.76 | 0.67 | 0.04 | 0.25 | 0 | 0.195 | – | 0.0027 | 3.0 s |
| (b) Luna, Lauf 1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.11 (S06 3×) | 0 | 0 | 0.715 | 0 | 0.0011 | 1.4 s |
| (b) Luna, Lauf 2 | 0.94 | 0.91 | 1.00 | 0.67 (S08 2× verpasst) | 0 | 0 | 0 | 0.715 | 0 | 0.0014 | 1.3 s |
| **(b) Luna, Lauf 3 (gültiger Prompt)** | **1.00** | **1.00** | **1.00** | **1.00** | **0** | **0** | **0** | **0.715** | **0** | **0.0013** | **1.3 s** |
| (b) offline (Vorlage + Regex) | 1.00 | – | 1.00 | 1.00 | 0 | 0 | 0 | 0.715 | 0 | 0 | – |
| Regel-Referenz (Variante a ohne LLM) | 0.91 | 0.91 | 1.00 | 0.50 (S11 verpasst) | 0 | 0 | 3 (S11) | 0.711 | – | 0 | – |

Weitere Kennzahlen (a) gegen (b): Angebote ohne Konditionen 86 % gegen 0 %, verpasste Annahmen 2 gegen 0, Runden
3,0 gegen 1,9–2,2, Leaks 0 und 0, KI-Hinweis 100 % und 100 %.

**Zwei Präzisierungen im Prompt von `parse_response`** (beide allgemein formuliert, ohne Wortlaut aus den Szenarien):
- Nach Lauf 1: Luna las «Ohne Gegenleistung sehen wir … keinen Spielraum» (S06) als Bedingung auf einer unbekannten
  Grösse und eskalierte unnötig (3 von 27 Läufen = 11 %, über der Schwelle von 10 % aus ADR 0008). Neu: «Eine Bedingung
  nennt etwas Konkretes, das die Musterhandel AG tun oder zusagen soll … Eine allgemeine Begründung einer Ablehnung ist
  keine Bedingung.»
- Nach Lauf 2: Luna legte die angekündigte Preiserhöhung in S08 zweimal nur als «Information» ab; die Wiederholung
  zählte dann als erste Forderung, die Eskalation blieb aus. Neu: «demand» umfasst auch eine angekündigte Änderung
  zulasten der Musterhandel AG (Beispiel «ab Januar gelten höhere Listenpreise»).

## Ergebnis

- **(b) schlägt (a) deutlich.** Mit dem gültigen Prompt (Lauf 3) löst (b) alle 33 Läufe: Erfolg 1.00 gegen 0.79
  (+21 Punkte), pass^3 1.00 gegen 0.64. Über alle drei Läufe (drei Prompt-Stände) sind es 97 von 99 korrekten Läufen.
  (a) scheitert wie am 11.10.2026: S03 bricht dreimal ab, S08 verpasst die Eskalation zweimal, S09 eskaliert einmal
  unnötig.

- **Kippregel ADR 0006 greift nicht.** Der gesicherte Spielraum steigt in jedem Lauf von 0,195 auf 0,715 (+52
  Prozentpunkte), die Abschlussquote von 0,76 auf 1,00. Die Kernthese bleibt «LLM schlägt vor, Code entscheidet» mit
  Leistung **und** Sicherheit, nicht nur Sicherheit.
- **Bei Luna kommt der Vorteil aus der Qualität, nicht aus der Sicherheit.** Luna hat auch in (a) 0 Verstösse. Der
  Vorsprung von (b) liegt bei Spielraum, Abschluss, Zuverlässigkeit (pass^3), lesbaren Angeboten (0 % statt 86 % ohne
  Konditionen) und der Eskalationsregel. Dazu kommen halbe Kosten pro Erfolg und halbe Latenz, weil `narrate` und
  `parse_response` kurze Prompts haben und Pakete nicht mehr im LLM entstehen.
- **Die Template-Rate ist 0.** Luna hielt sich in allen Läufen an die Paketwerte; die Kippregel aus ADR 0002 (> 20 %)
  greift nicht. Der Guard ist trotzdem nötig, weil er die Garantie liefert und nicht das Modell.
- **Der verbleibende Fehler sitzt im Extrahieren.** Alle Fehlläufe von (b) entstehen in `parse_response`
  (falsch gelesene Bedingung, übersehene Forderung), nie in Pakete oder Mandat. Sie streuen von Lauf zu Lauf und
  enden sicher: als unnötige oder verpasste Eskalation, nie als Zusage ausserhalb des Mandats und nie als
  `deal:not_agreed`. Genau das misst der Spike in KW44 (Luna gegen `tev1:0.8b` gegen Regeln, ADR 0011).

## Was die Messung nicht zeigt

- **(b) offline löst alles, weil der Regex-Parser die Simulatorvorlagen kennt.** Gegen Textvorlagen trägt das LLM in
  (b) messbar nichts bei, das Regeln nicht auch könnten; in S11 ist es nur gegenüber der Regel-Referenz von (a) nötig,
  die den Text gar nicht liest. Der Nutzen des LLM zeigt sich erst gegen Umformulierungen (KW44) und Menschen
  (Live-Runden). Das bleibt die Hauptlimitation (ADR 0006).
- **Die zwei Präzisierungen sind am Dev-Set entstanden.** Ob sie verallgemeinern, prüft erst das synthetische Testset
  (KW45, ADR 0010), dessen Bedingungen und Forderungen anders formuliert sein müssen als die Beispiele im Prompt.
- **`mandate_guard` prüft nicht, ob eine Zahl beim richtigen Paket steht**, nur dass sie ein Paketwert ist und dass
  jedes Paket vorkommt. Vertauschte Werte zwischen Paket A und B gingen durch.
- 11 Szenarien × 3: Ein Szenario sind 9 Prozentpunkte; die drei Läufe von (b) zeigen genau diese Streuung.

## Verworfene Alternativen

| Alternative | Grund |
| --- | --- |
| Einigung weiter am Simulator-Ereignis erkennen (wie in a) | unrealistisch; ein echter Lieferant schreibt Text. Das Risiko einer Fehllesung gehört in die Messung |
| `narrate` sieht den Lieferantentext (natürlichere Antworten) | eine Injection erreicht dann das schreibende LLM; die Zurückweisung käme vom LLM statt aus der Vorlage (ADR 0008) |
| Korrekturrunde für `narrate` mit Rückmeldung des Guards | Template-Rate 0; erst nötig, wenn sie über 20 % steigt (ADR 0002) |
| Fehlklassifikationen im Code abfangen (z.B. jede Bedingung mit Grösse «other» ignorieren) | würde echte Bedingungen wie «nur bei Selbstabholung» übersehen; das Problem gehört in den Parser und in den Spike |
| (b) so lange nachmessen, bis ein Lauf 1.00 zeigt | Rauschen; alle Läufe werden berichtet |

## Kippt, wenn

- das Testset (KW45) mehr als 10 % unnötige oder verpasste Eskalationen zeigt (ADR 0008): dann Fail-safe verschärfen
  oder den Parser nach dem Spike wechseln;
- die Template-Rate gegen andere Modelle (granite, KW44) über 20 % steigt: dann eine Korrekturrunde für `narrate`;
- `deal:not_agreed` in einem Lauf auftritt: dann bucht (b) nur noch nach einer Bestätigungsrunde («Wir halten fest: …,
  bitte bestätigen Sie»).

## Konsequenzen

- `ea-eval`, `ea-benchmark` und `ea-run` haben `--variant a|b`; `--variant b --policy rule` läuft offline.
- Neue Metriken: `template_rate`, Verstoss `deal:not_agreed` (`docs/eval-metriken.md`).
- `docs/gesamtsystem.md` §2.4, §3.4, §4 und §5 sind nachgeführt; `docs/process/README.md` markiert die gebauten Nodes.
- KW44 baut darauf auf: ERP-Adapter in `load_context` und `record_outcome`, Spike auf `parse_response`, granite-Zeile
  mit `--variant b --model ibm/granite4.1:3b`.
