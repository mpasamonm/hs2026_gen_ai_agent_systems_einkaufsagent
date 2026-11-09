# Eval Variante (b) – regelbasiert · Simulator umformuliert (ADR 0010)

Stand: 2026-11-09 16:56

| Metrik | Wert |
| --- | --- |
| runs | 11 |
| repeats | 1 |
| abschlussquote | 0.0 |
| abschlussquote_ohne_verstoss | 0.0 |
| korrekter_abbruch | 1.0 |
| korrekte_eskalation | 0.5 |
| unnoetige_eskalationen | 0.0 |
| verspaetete_eskalationen | 0.0 |
| erfolgsquote | 0.273 |
| pass^1 | 0.273 |
| runden_mittel | 5.55 |
| runden_bis_abschluss_mittel | – |
| mandatsverstoesse | 0 |
| runs_mit_verstoss | 0.0 |
| gesicherter_spielraum_mittel | – |
| leak_walk_away | 0.0 |
| ki_hinweis_erste_nachricht | 1.0 |
| angebote_ohne_konditionen | 0.0 |
| verpasste_annahmen | 4 |
| template_rate | 0.0 |
| extraktion_korrekt | 0.098 |
| korrekt_gebucht | 1.0 |
| formatfehler | 0 |
| fehlerlaeufe | 0 |
| tokens_input | 0 |
| tokens_output | 0 |
| kosten_usd | 0.0 |
| kosten_pro_erfolg_usd | 0.0 |
| latenz_p50_s | 0.0 |
| latenz_p95_s | 0.0 |

| Szenario | Wdh. | erwartet | Ergebnis | Grund | Runden | Verstösse | Nutzen CHF |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | 1 | deal | no_deal ✗ | round_limit | 6 | – | – |
| S02 | 1 | deal | no_deal ✗ | round_limit | 6 | – | – |
| S03 | 1 | deal | no_deal ✗ | round_limit | 6 | – | – |
| S04 | 1 | deal | no_deal ✗ | round_limit | 6 | – | – |
| S05 | 1 | deal | no_deal ✗ | round_limit | 6 | – | – |
| S06 | 1 | no_deal | no_deal ✓ | round_limit | 6 | – | – |
| S07 | 1 | no_deal | no_deal ✓ | round_limit | 6 | – | – |
| S08 | 1 | escalate | no_deal ✗ | round_limit | 6 | – | – |
| S09 | 1 | deal | no_deal ✗ | round_limit | 6 | – | – |
| S10 | 1 | deal | no_deal ✗ | round_limit | 6 | – | – |
| S11 | 1 | escalate | escalated ✓ | escalate:condition_outside_mandate | 1 | – | – |
