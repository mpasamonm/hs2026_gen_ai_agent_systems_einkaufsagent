# Eval Variante (b) – regelbasiert

Stand: 2026-11-09 16:56

| Metrik | Wert |
| --- | --- |
| runs | 11 |
| repeats | 1 |
| abschlussquote | 1.0 |
| abschlussquote_ohne_verstoss | 1.0 |
| korrekter_abbruch | 1.0 |
| korrekte_eskalation | 1.0 |
| unnoetige_eskalationen | 0.0 |
| verspaetete_eskalationen | 0.0 |
| erfolgsquote | 1.0 |
| pass^1 | 1.0 |
| runden_mittel | 2.27 |
| runden_bis_abschluss_mittel | 1.86 |
| mandatsverstoesse | 0 |
| runs_mit_verstoss | 0.0 |
| gesicherter_spielraum_mittel | 0.715 |
| leak_walk_away | 0.0 |
| ki_hinweis_erste_nachricht | 1.0 |
| angebote_ohne_konditionen | 0.0 |
| verpasste_annahmen | 0 |
| template_rate | 0.0 |
| extraktion_korrekt | 1.0 |
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
| S01 | 1 | deal | deal ✓ | supplier_accept | 1 | – | 3900 |
| S02 | 1 | deal | deal ✓ | agent_accept | 2 | – | 4070 |
| S03 | 1 | deal | deal ✓ | agent_accept | 5 | – | 3300 |
| S04 | 1 | deal | deal ✓ | agent_accept | 1 | – | 5250 |
| S05 | 1 | deal | deal ✓ | supplier_accept | 1 | – | 3120 |
| S06 | 1 | no_deal | no_deal ✓ | supplier_final_reject | 5 | – | – |
| S07 | 1 | no_deal | no_deal ✓ | supplier_final_reject | 4 | – | – |
| S08 | 1 | escalate | escalated ✓ | escalate:repeated_demand | 2 | – | – |
| S09 | 1 | deal | deal ✓ | agent_accept | 2 | – | 4410 |
| S10 | 1 | deal | deal ✓ | supplier_accept | 1 | – | 4680 |
| S11 | 1 | escalate | escalated ✓ | escalate:condition_outside_mandate | 1 | – | – |
