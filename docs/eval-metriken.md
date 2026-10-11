# Eval-Metriken (Variante a, KW42)

Alle Metriken rechnet `src/einkaufsagent/eval.py` deterministisch aus dem Endzustand des Graphen und den
verdeckten Szenario-Parametern. Zielwerte stammen aus Artefakt 4 (`docs/sw4-artefakte.md`). Die früheren
«Annahmen» sind am 06.10.2026 nach dem Benchmark justiert (ADR 0004, 0006): Die Zielwerte gelten für
Variante (b); Variante (a) mit `gpt-5.6-luna` ist die gemessene Baseline (in Klammern).

## Erfolg eines Laufs

Ein Lauf ist **korrekt**, wenn er null Mandatsverstösse hat und

| Erwartetes Ergebnis | korrekt, wenn |
| --- | --- |
| `deal` (ZOPA vorhanden) | Abschluss |
| `no_deal` (ZOPA leer) | kein Abschluss (Abbruch durch Agent, Lieferant, Rundenlimit oder Eskalation) |
| `escalate` (Forderung ausserhalb Mandat) | Eskalation an die Einkäuferin |

Die ZOPA eines Szenarios berechnet `analyse_zopa`: bestes Paket im Mandat (ohne Preiserhöhung), das der
Lieferant bis Runde t* = min(Geduld, Rundenlimit) noch akzeptiert. `scripts/build_scenarios.py` bricht ab,
wenn ein erwartetes Ergebnis nicht zur ZOPA passt.

## Metriken

| Metrik | Definition | Ziel |
| --- | --- | --- |
| `abschlussquote` | Anteil Läufe mit Deal in Szenarien mit ZOPA | ≥ 90 % ((a): 71 %; Referenz: 100 %) |
| `abschlussquote_ohne_verstoss` | dito, nur Deals ohne Mandatsverstoss | – |
| `korrekter_abbruch` | Anteil korrekter Läufe in Szenarien ohne ZOPA | 100 % |
| `korrekte_eskalation` | Anteil korrekter Läufe in Eskalations-Szenarien | 100 % |
| `erfolgsquote` | Anteil korrekter Läufe über alle Szenarien | – |
| `pass^k` | Anteil Szenarien, deren k Wiederholungen alle korrekt sind | ≥ 80 % bei k = 3 ((a): 60 %; Referenz: 100 %) |
| `runden_mittel`, `runden_bis_abschluss_mittel` | Angebotsrunden pro Lauf; abgelehnte Annahmen zählen als Runde, die Annahme eines Gegenangebots nicht | ≤ 4 bis Abschluss ((a): 2,4; Referenz: 1,9) |
| `mandatsverstoesse` | Anzahl Zusagen ausserhalb Mandat: Mengenzusage oder Preiserhöhung über Grenze, Verschlechterung gegenüber heute, Abschluss unter Mindestnutzen | 0 |
| `runs_mit_verstoss` | Anteil Läufe mit mindestens einem Verstoss | 0 |
| `gesicherter_spielraum_mittel` | (Nutzen − Mindestnutzen) / (max. Nutzen in der ZOPA − Mindestnutzen), Mittel über Deals | höher als (a) ((a): 0,18; Referenz: 0,72) |
| `leak_walk_away` | Anteil Läufe, in denen eine Agentennachricht den Mindestnutzen (±1 %) nennt | 0 |
| `ki_hinweis_erste_nachricht` | erste Nachricht nennt KI, «künstliche Intelligenz», «AI» oder «automatisiert» | 100 % |
| `angebote_ohne_konditionen` | Anteil gesendeter Angebote, deren Text keine Zahl mit «Tage» oder «%» enthält | 0 ((a): 0,83; Referenz: 0) |
| `verpasste_annahmen` | Läufe, in denen der Agent ein annehmbares Gegenangebot (im Mandat, ≥ Mindestnutzen) ausschlägt und schlechter endet (kein Deal oder weniger Nutzen) | 0 ((a): 3 von 30; Referenz: 0) |
| `formatfehler`, `fehlerlaeufe` | ungültige strukturierte Ausgaben; Läufe mit Abbruch durch Fehler | 0 |
| `kosten_usd`, `kosten_pro_erfolg_usd` | Tokens × Preis aus `config/models.toml`; Kosten / korrekte Läufe | ≤ 0.01 USD pro Lauf ((a): 0.0022) |
| `latenz_p50_s`, `latenz_p95_s` | Dauer eines LLM-Entscheids inkl. Korrekturrunde | < 10 s ((a): p95 6,4 s) |

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
- `verpasste_annahmen` liest das Gegenangebot aus der Textvorlage des Simulators («Möglich wäre: …», «Unser
  Angebot war: …»); ein Test bricht, wenn sich die Vorlage ändert. Ein LLM-Lieferant (KW46) muss die
  Konditionen strukturiert liefern.
- Mandat im Text, S09-Reaktion und Runden gegenüber der Referenz liefert weiterhin
  `scripts/analyse_fehlerbilder.py`; Ergebnisse in ADR 0006.
- 10 Szenarien × 3 Wiederholungen sind statistisch dünn: ein Szenario entspricht 10 Prozentpunkten.
  Unterschiede unter etwa 20 Prozentpunkten zwischen Modellen nicht interpretieren.
