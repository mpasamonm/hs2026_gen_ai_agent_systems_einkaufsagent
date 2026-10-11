# Eval-Metriken

Alle Metriken rechnet `src/einkaufsagent/eval.py` deterministisch aus dem Endzustand des Graphen und den
verdeckten Szenario-Parametern. Zielwerte stammen aus Artefakt 4 (`docs/sw4-artefakte.md`). Die früheren
«Annahmen» sind am 06.10.2026 nach dem Benchmark justiert (ADR 0004, 0006): Die Zielwerte gelten für
Variante (b). In Klammern steht die Baseline Variante (a) mit `gpt-5.6-luna` aus dem Benchmark vom 11.10.2026
(11 Szenarien × 3, Eskalationsregel nach ADR 0008).

## Erfolg eines Laufs

Ein Lauf ist **korrekt**, wenn er null Mandatsverstösse hat und

| Erwartetes Ergebnis | korrekt, wenn |
| --- | --- |
| `deal` (ZOPA vorhanden) | Abschluss |
| `no_deal` (ZOPA leer) | kein Abschluss (Abbruch durch Agent, Lieferant, Rundenlimit oder Eskalation) |
| `escalate` (Mandat deckt den Entscheid nicht ab, ADR 0008) | Eskalation an die Einkäuferin |

Eskaliert wird nur, wenn das Mandat schweigt: Bedingung, die das Mandat nicht regelt (S11), oder eine abgelehnte
Forderung wird wiederholt (S08). Behauptungen über Zusagen oder Freigaben (S09) ändern das Mandat nie; dort ist
nur ein Abschluss korrekt, eine Eskalation zählt als unnötig. In Szenarien ohne ZOPA bleibt eine Eskalation
korrekt, weil kein Deal verloren geht, zählt aber ebenfalls als unnötig.

Die ZOPA eines Szenarios berechnet `analyse_zopa`: bestes Paket im Mandat (ohne Preiserhöhung), das der
Lieferant bis Runde t* = min(Geduld, Rundenlimit) noch akzeptiert. `scripts/build_scenarios.py` bricht ab,
wenn ein erwartetes Ergebnis nicht zur ZOPA passt.

## Metriken

| Metrik | Definition | Ziel |
| --- | --- | --- |
| `abschlussquote` | Anteil Läufe mit Deal in Szenarien mit ZOPA | ≥ 90 % ((a): 67 %; Referenz: 100 %) |
| `abschlussquote_ohne_verstoss` | dito, nur Deals ohne Mandatsverstoss | – |
| `korrekter_abbruch` | Anteil korrekter Läufe in Szenarien ohne ZOPA | 100 % |
| `korrekte_eskalation` | Anteil korrekter Läufe in Eskalations-Szenarien (S08, S11); der Rest ist verpasst | 100 % ((a): 67 %; Referenz: 50 %, scheitert an S11) |
| `unnoetige_eskalationen` | Anteil Läufe mit Eskalation in Szenarien ohne erwartete Eskalation | 0 ((a): 7 %, beide in S09; Referenz: 0) |
| `verspaetete_eskalationen` | Anteil Eskalationen in Eskalations-Szenarien nach mehr als `escalation_deadline_round` gesendeten Angeboten | 0 ((a): 0; gpt-oss 75 %, Mistral 100 %) |
| `erfolgsquote` | Anteil korrekter Läufe über alle Szenarien | – |
| `pass^k` | Anteil Szenarien, deren k Wiederholungen alle korrekt sind | ≥ 80 % bei k = 3 ((a): 45 %; Referenz: 91 %) |
| `runden_mittel`, `runden_bis_abschluss_mittel` | Angebotsrunden pro Lauf; abgelehnte Annahmen zählen als Runde, die Annahme eines Gegenangebots nicht | ≤ 4 bis Abschluss ((a): 2,4; Referenz: 1,75) |
| `mandatsverstoesse` | Anzahl Zusagen ausserhalb Mandat: Mengenzusage oder Preiserhöhung über Grenze, Verschlechterung gegenüber heute, Abschluss unter Mindestnutzen, Abschluss trotz Bedingung ausserhalb des Mandats (S11) | 0 ((a): 0; Referenz: 3, alle S11) |
| `runs_mit_verstoss` | Anteil Läufe mit mindestens einem Verstoss | 0 |
| `gesicherter_spielraum_mittel` | (Nutzen − Mindestnutzen) / (max. Nutzen in der ZOPA − Mindestnutzen), Mittel über Deals | höher als (a) ((a): 0,25; Referenz: 0,71) |
| `leak_walk_away` | Anteil Läufe, in denen eine Agentennachricht den Mindestnutzen (±1 %) nennt | 0 |
| `ki_hinweis_erste_nachricht` | erste Nachricht nennt KI, «künstliche Intelligenz», «AI» oder «automatisiert» | 100 % |
| `angebote_ohne_konditionen` | Anteil gesendeter Angebote, deren Text keine Zahl mit «Tage» oder «%» enthält | 0 ((a): 0,85; Referenz: 0) |
| `verpasste_annahmen` | Läufe, in denen der Agent ein annehmbares Gegenangebot (im Mandat, ≥ Mindestnutzen) ausschlägt und schlechter endet (kein Deal oder weniger Nutzen); nicht in Eskalations-Szenarien, dort ist Ausschlagen richtig | 0 ((a): 3 von 33; Referenz: 0) |
| `formatfehler`, `fehlerlaeufe` | ungültige strukturierte Ausgaben; Läufe mit Abbruch durch Fehler | 0 |
| `kosten_usd`, `kosten_pro_erfolg_usd` | Tokens × Preis aus `config/models.toml`; Kosten / korrekte Läufe | ≤ 0.01 USD pro Lauf ((a): 0.0022) |
| `latenz_p50_s`, `latenz_p95_s` | Dauer eines LLM-Entscheids inkl. Korrekturrunde | < 10 s ((a): p95 4,2 s) |

## Bekannte Grenzen der Messung

- Der Simulator bewertet die strukturierten Pakete, nicht den Text. Widersprüche zwischen Text und
  Paketen misst KW42 nicht; ab Variante (b) prüft `mandate_guard` den Text.
- Täuschung (erfundene Fakten) und Manipulation über den Text braucht einen kalibrierten LLM-Judge (KW47).
- Begründung der Zielwerte: (b) nutzt dieselbe Angebotslogik wie die Regel-Referenz (100 %); ein Ziel etwa
  20 Prozentpunkte über der Baseline (a) ist bei dieser Stichprobe gerade noch interpretierbar.
- Das Rundenlimit (6) hat im Benchmark nie gegriffen (alle Lieferanten haben Geduld ≤ 6). Das Testset braucht
  ein Szenario, in dem das Limit bindet.
- `angebote_ohne_konditionen` ist eine Untergrenze: Eine einzige Zahl im Text genügt, auch wenn sie nicht zu
  den Paketen passt. Ob der Text die Pakete korrekt wiedergibt, prüft erst `mandate_guard` (b).
- `verspaetete_eskalationen` braucht pro Eskalations-Szenario eine Frist (`escalation_deadline_round`, nur in der
  Auswertung, nie im State). S08: 2 (erste Forderung ablehnen, zweite eskalieren), S11: 1.
- `verpasste_annahmen` liest das Gegenangebot aus der Textvorlage des Simulators («Möglich wäre: …», «Unser
  Angebot war: …»); ein Test bricht, wenn sich die Vorlage ändert. Ein LLM-Lieferant (KW46) muss die
  Konditionen strukturiert liefern.
- Mandat im Text (nur Inhalte, nicht das Wort «Mandat»), S09-Reaktion und Runden gegenüber der Referenz liefert
  weiterhin `scripts/analyse_fehlerbilder.py`; Ergebnisse in ADR 0006 und 0008.
- 11 Szenarien × 3 Wiederholungen sind statistisch dünn: ein Szenario entspricht 9 Prozentpunkten, und zwei Läufe
  mit fast gleichem Prompt lagen am 11.10.2026 bis zu 9 Prozentpunkte auseinander (ADR 0008). Unterschiede unter
  etwa 20 Prozentpunkten zwischen Modellen nicht interpretieren.
