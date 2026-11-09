# ADR 0010 – Synthetische Daten: Code würfelt, LLM kleidet ein, Code prüft

- **Status:** angenommen am 19.10.2026
- **Datum:** 19.10.2026
- **Ersetzt:** in ADR 0003 und CLAUDE.md die Vorgabe, dass eine andere Person das Testset entwirft
- **Berührt:** `scripts/build_scenarios.py`, Simulator-Textvorlagen, ADR 0008 (Testset-Kategorien), ADR 0011 (Spike)

## Kontext

Das zurückgehaltene Testset sollte eine andere Person entwerfen, weil Dev-Szenarien und Regel-Referenz aus derselben
Hand stammen. Bis heute hat niemand Szenarien geliefert, und Daten von Hand zu erstellen kostet Zeit, die im Projekt
fehlt. Gebraucht werden: Testset (10–15 Szenarien), Umformulierungen der Simulator-Texte (Robustheit der Extraktion,
Spike in ADR 0011), Angriffstexte, eine kurze Einkaufsrichtlinie, Verhandlungshistorie für Variante (c) und
Bias-Varianten.

Die trennende Achse ist **Unabhängigkeit und Realismus der Daten gegen Handarbeit**.

## Entscheid

Die Daten folgen derselben Arbeitsteilung wie der Agent:

1. **Code würfelt.** Mandat, heutige Konditionen und verdeckte Lieferantenparameter zieht `build_scenarios.py` mit
   Seed aus einem Raster. Der Code rechnet ZOPA und erwartetes Ergebnis.
2. **LLM kleidet ein.** Das LLM schreibt nur Texte: Lieferant und Branche, Forderungs-, Bedingungs- und Angriffstexte,
   Umformulierungen, Richtlinie.
3. **Code prüft.** Jede Zahl im Text muss zu den Parametern passen (Regex: dieselben Zahlen, keine neuen), Labels
   bleiben erhalten, Dubletten fallen weg. Alle Testset-Szenarien und eine Stichprobe von 20
   Umformulierungen werden von Hand gelesen (0 Fehler in 20 heisst mit 95 % Sicherheit höchstens 15 % Fehler).
4. **Einfrieren.** Einmal erzeugt, liegen die Daten als JSONL im Repo, mit Modell, Datum und Prompt; sie werden nie neu
   erzeugt. Die Evaluation bleibt hermetisch (D4).

**Generator:** Claude Opus über Claude Code (Claude-Subscription). Er gehört nicht zur Familie des Agenten
(OpenAI, `gpt-5.6-luna`) und ist stärker als die geprüften Modelle; stärkere Generatoren schreiben schwierigere
Testtexte. Prompts, Modell und Datum stehen in einer README neben den Daten. Weil Claude Haiku 5.5 zur selben Familie
gehört, fällt es als Kandidat aus dem Spike (ADR 0011).

| Datensatz | Inhalt | Prüfung im Code | Aufwand |
| --- | --- | --- | --- |
| Umformulierungen | 5 pro Simulator-Vorlage; der Simulator wählt per Seed | Zahlen und Ereignis unverändert | 2 h |
| Testset | 12–15 Szenarien, je Eskalationskategorie aus ADR 0008 mindestens eines, andere Bedingungen als im Prompt (Laufzeit, Exklusivität, Vorauskasse …), ein Szenario mit bindendem Rundenlimit | ZOPA und erwartetes Ergebnis aus `build_scenarios.py` | 3–4 h |
| Angriffe | 4 Muster aus AgentDojo («ignore previous», «TODO», InjecAgent, «Important message»), 2 Stile aus Tensor Trust, 3–4 harmlose Texte mit Triggerwörtern für Fehlalarme | Ziel des Angriffs ist im Szenario hinterlegt | 2 h |
| Einkaufsrichtlinie | rund eine Seite; Regeln für Behauptungen, Forderungen, Bedingungen | – (von Hand gelesen) | 0,5 h |
| Historie für (c) | Self-Play: Variante (b) gegen den Simulator im «Vorjahr», Protokolle speichern | ganz im Code, ohne LLM-Texte | 1 h |
| Bias | 3 Szenarien × 4 Lieferantennamen bzw. Herkunft, sonst gleich | gleiche verdeckte Parameter und Seeds | 1 h |

## Verworfene Alternativen

| Alternative | Grund |
| --- | --- |
| Daten von Hand oder durch eine andere Person | 6–10 h; bisher hat niemand geliefert |
| LLM erzeugt alles inklusive erwartetem Ergebnis | falsche Labels; Modelle schneiden auf selbst erzeugten Benchmarks besser ab (arXiv 2505.20738) |
| Mistral Large 3 über den Proxy als Generator | neutral zu allen Kandidaten und per Skript wiederholbar, aber schwächere Texte; da die Daten eingefroren werden, zählt die Qualität mehr als die Wiederholbarkeit |
| Haiku 5.5 als Generator | gleiche Familie wie ein Spike-Kandidat |

## Kippt, wenn

- ein Teammitglied doch Szenarien liefert: dann als zusätzliche Hälfte des Testsets, getrennt ausgewertet;
- die Stichprobe mehr als 2 fehlerhafte von 20 Umformulierungen zeigt: Prompt verschärfen und neu erzeugen, bevor
  eingefroren wird;
- der Agent auf ein Anthropic-Modell wechselt: dann erzeugt ein Modell einer dritten Familie das Testset neu.

## Konsequenzen

- Limitation für Präsentation und Prüfung: eine andere Modellfamilie statt einer anderen Person; synthetische Texte
  sind sauberer und meist leichter als echte (arXiv 2505.22830). Die Wahrheit (ZOPA, erwartetes Ergebnis) rechnet der
  Code; Fehler in den Labels fallen damit weg.
- Neue Metriken in `docs/eval-metriken.md`: Erfolgsquote der Angriffe, Fehlalarme, Kippen der Extraktion bei
  Umformulierung, Unterschiede nach Lieferantenname.
- Prüfungsbegründung: «Die Daten folgen derselben Arbeitsteilung wie der Agent: Das LLM liefert die sprachliche
  Vielfalt, der Code legt die Zahlen fest und rechnet die richtige Antwort aus. Ein Modell einer anderen Familie
  schreibt die Texte, damit der Agent nicht gegen seinen eigenen Stil getestet wird.»

## Quellen

- Modelle schneiden auf selbst erzeugten Benchmarks besser ab: arXiv 2505.20738 (NeurIPS 2025).
- «Preference Leakage» bei verwandten Generator- und Prüfmodellen: arXiv 2502.01534 (ICLR 2026).
- Synthetische Varianten sind meist leichter als menschliche Originale: arXiv 2505.22830.
- AgentDojo: arXiv 2406.13352 (NeurIPS 2024); Tensor Trust: arXiv 2311.01011 (ICLR 2024).
- «Rule of three»: Hanley & Lippman-Hand, JAMA, 1983.
- Stand der Recherche 19.10.2026; Titel und Autoren vor der Präsentation im Original nachlesen.

## Nachtrag 26.10.2026: Umformulierungen umgesetzt

- **Daten:** `data/paraphrases/supplier_templates.json`, 14 Vorlagen × (Original + 5 Umformulierungen) und 6
  Schreibweisen der Konditionen; Generator Claude Opus 5.5 über Claude Code; eingefroren. Prompt, Umfang und
  Prüfung in `data/paraphrases/README.md`. Nicht umformuliert: Einleitungen und die Texte aus den Szenarien
  (Begründung, Injection, Bedingung); die gehören zu Testset und Angriffen (KW45).
- **Einbau:** `SupplierSimulator(..., paraphrase=True)` bzw. `--paraphrase` in `ea-run`, `ea-eval`, `ea-benchmark`.
  Eigener Zufallsgenerator mit dem Seed des Szenarios; Ereignis, Konditionen und Einleitungen bleiben gleich. Ohne
  Flag byte-gleich zu vorher.
- **Code-Prüfung:** `paraphrases.validate()` bestanden (Platzhalter, keine eigenen Zahlen, keine Dubletten, gleiche
  Zahlen gerendert); Test: in allen 11 Szenarien gleiche Ereignisse und Konditionen mit und ohne Umformulierung.
- **Handprüfung:** Stichprobe von 20 in `data/paraphrases/stichprobe.md`. Vom Generator gelesen, 0 Befunde; **Lesung
  durch ein Teammitglied ausstehend**, erst danach gilt die Kippregel als geprüft.
- **Neue Metrik** `extraktion_korrekt` (nur b) gegen die Wahrheit des Simulators; `verpasste_annahmen` liest das
  Gegenangebot nicht mehr aus dem Text, sondern aus `SupplierReply.terms`.

Messung 26.10.2026, 11 Dev-Szenarien × 3, `gpt-5.6-luna`:

| Lauf | Erfolg | pass^3 | Abschluss | Eskalation | Spielraum | Extraktion korrekt | Verstösse | Kosten USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (b) Regex-Parser, Original | 1.00 | 1.00 | – | – | – | 1.00 | 0 | 0 |
| (b) Regex-Parser, umformuliert | 0.27 | – | – | – | – | 0.10 | 0 | 0 |
| (a) Regel-Referenz, umformuliert | 0.909 | – | – | – | – | – | 3 (S11, wie ohne) | 0 |
| (b) Luna, Original | 1.00 | 1.00 | 1.00 | 1.00 | 0.715 | 0.952 | 0 | 0.044 |
| (b) Luna, umformuliert | 1.00 | 1.00 | 1.00 | 1.00 | 0.715 | 0.976 | 0 | 0.044 |
| (a) Luna, umformuliert | 0.697 | 0.545 | 0.714 | 0.333 | 0.233 | – | 0 | 0.069 |

(a) Luna ohne Umformulierung: 0.79 Erfolg, pass^3 0.64, Spielraum 0.195 (ADR 0013, 19.10.2026).

**Befunde**

- Der Regex-Parser bricht ein (0.27); der LLM-Parser in (b) nicht. Erst mit Umformulierungen zeigt sich der Nutzen
  des LLM beim Extrahieren, den die Dev-Vorlagen bisher verdeckten (Limitation aus ADR 0006, 0013).
- (b) mit Luna bleibt bei 1.00; `extraktion_kippt` ist im Rahmen der Schwankung null (0.952 ohne, 0.976 mit;
  Unterschiede zwischen Läufen ohne Umformulierung schon so gross). Eine unnötige Eskalation in 27 Läufen
  (0.037) und ein Formatfehler, beide abgefangen.
- (a) verliert mit Umformulierungen weiter: Erfolg 0.79 → 0.70, korrekte Eskalation 0.33. Die Kernthese
  «LLM schlägt vor, Code entscheidet» wird robuster belegt: Abstand (a) zu (b) jetzt 30 Punkte statt 21. *(Überholt, siehe
  Nachmessung 09.11.2026: am selben Tag verliert (a) nur 3 Punkte.)*
- Einziger beobachteter Extraktionsfehler (Diagnoselauf, S06 Runde 4): Ablehnung mit dem Zusatz «Dabei bleibt es von
  unserer Seite.» als Abbruch gelesen. Kein Fehler der Umformulierung: die Vorlage «letztes Wort» ist schon im
  Original mehrdeutig; Ergebnis korrekt (kein Deal).
- Grenze: Umformuliert sind nur die Simulator-Sätze; Szenariotexte und Angriffe sind unverändert. Die Messung läuft
  noch auf dem Dev-Set, an dem der Parse-Prompt präzisiert wurde (ADR 0013).

## Nachmessung 09.11.2026: Review, Korrekturen, alle vier Läufe am selben Tag

Der Beitrag kam als PR #2 eines Teammitglieds (Upload über die GitHub-Weboberfläche) und ist am 09.11.2026 per Merge
übernommen. Review: keine Rückdrehungen, Invarianten unverändert, ohne `--paraphrase` gleiche Läufe wie vorher (Feld
für Feld verglichen, nur die Laufzeit weicht ab). Nachgearbeitet:

- `extraktion_korrekt` prüft bei «accept» jetzt die Paketwahl. Eine Annahme unter Bedingung zählt nur dann auch als
  «accept», wenn die Werte einem gesendeten Paket entsprechen; ein echtes Gegenangebot mit angehängter Bedingung (S11)
  muss «counter» bleiben. Test in `tests/test_paraphrases.py`.
- Die Stichprobe deckte 3 der 14 Vorlagen nicht ab und ist neu gezogen (jede Vorlage mindestens einmal); das Skript
  überschreibt sie nur noch mit `--neu`. Die Lesung von Hand steht weiter aus.
- Grenzen in `data/paraphrases/README.md`: Einige Varianten verwenden «entgegenkommen» bzw. «Listenpreise» wie die
  Beispiele im Parse-Prompt (ADR 0013); der Prompt liegt nur sinngemäss vor.
- Die geplante Metrik `extraktion_kippt` (paarweise) ist nicht gebaut; berichtet wird die Differenz von
  `extraktion_korrekt` ohne und mit Umformulierung (`docs/eval-metriken.md`).

`uv run ea-eval --variant a|b --model gpt-5.6-luna --repeats 3 [--paraphrase]`, 11 Szenarien × 3, alle am 09.11.2026:

| Lauf | Erfolg | pass^3 | Abschluss | Eskalation korrekt | unnötig | Spielraum | Extraktion korrekt | Verstösse | USD/Erfolg | Ordner (`results/`) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (a) Luna, Original | 0.79 | 0.73 | 0.76 | 0.67 | 0 | 0.250 | – | 0 | 0.0027 | `20261109-143146_a_gpt-5.6-luna` |
| (a) Luna, umformuliert | 0.76 | 0.64 | 0.81 | 0.33 | 0 | 0.252 | – | 0 | 0.0030 | `20261109-143340_a_gpt-5.6-luna_umformuliert` |
| (b) Luna, Original | 1.00 | 1.00 | 1.00 | 1.00 | 0 | 0.715 | 0.952 | 0 | 0.0014 | `20261109-143531_b_gpt-5.6-luna` |
| (b) Luna, umformuliert | 1.00 | 1.00 | 1.00 | 1.00 | 0.074 (S06 2×) | 0.715 | 0.988 | 0 | 0.0014 | `20261109-143659_b_gpt-5.6-luna_umformuliert` |
| (b) Regex-Parser, Original | 1.00 | – | 1.00 | 1.00 | 0 | 0.715 | 1.00 | 0 | 0 | `20261109-143043_b_regelbasiert` |
| (b) Regex-Parser, umformuliert | 0.27 | – | 0.00 | – | – | – | 0.10 | 0 | 0 | `20261109-143045_b_regelbasiert_umformuliert` |

Die Regel-Referenz von (a) liest den Text nicht und bleibt mit und ohne Umformulierung bei 0.91 und 3 Verstössen (S11).
Kosten der vier Luna-Läufe zusammen 0.24 USD.

**Befunde**

- **Der Abstand (a) zu (b) bleibt bei rund 21–24 Punkten.** Am selben Tag verliert (a) mit Umformulierungen nur 3 Punkte
  (0.79 → 0.76), das liegt im Rauschen (ein Szenario = 9 Punkte). Die Aussage «30 statt 21» aus dem Nachtrag vom
  26.10. verglich zwei Tage und hält nicht. Robust ist der Vorsprung von (b) beim Spielraum (0.715 gegen 0.25) und bei
  pass^3.
- **Das LLM in (b) liest Umformulierungen so gut wie die Originale** (Extraktion 0.988 gegen 0.952), der Regex-Parser
  bricht ein (0.27). Damit ist die Limitation aus ADR 0006 und 0013 teilweise ausgeräumt: Gegen umformulierte Vorlagen
  braucht es das LLM zum Lesen; gegen Menschen ist das noch offen (Live-Runden).
- **Neues Fehlbild:** «… können wir ohne Gegenleistung nicht gewähren» (Umformulierung von `reject_no_room`) las Luna
  zweimal als Bedingung und eskalierte S06 unnötig (2 von 27 = 7,4 %, unter der Schwelle von 10 % aus ADR 0008). Die
  Präzisierung im Parse-Prompt aus ADR 0013 trägt also nur teilweise. `extraktion_korrekt` sieht das nicht, weil die
  Metrik Antworttyp und Werte prüft, nicht die Aussagen; sichtbar wird es in `unnoetige_eskalationen`.
- Der wiederkehrende Fehler in S06 Runde 4 («Dabei bleibt es von unserer Seite.» als Abbruch gelesen) steht schon im
  Original und endet richtig (kein Deal).
