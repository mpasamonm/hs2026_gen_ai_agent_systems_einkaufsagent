# Eval Variante (a) – regelbasiert

Stand: 2026-11-09 16:56

| Metrik | Wert |
| --- | --- |
| runs | 33 |
| repeats | 3 |
| abschlussquote | 1.0 |
| abschlussquote_ohne_verstoss | 1.0 |
| korrekter_abbruch | 1.0 |
| korrekte_eskalation | 0.5 |
| unnoetige_eskalationen | 0.0 |
| verspaetete_eskalationen | 0.0 |
| erfolgsquote | 0.909 |
| pass^3 | 0.909 |
| runden_mittel | 2.27 |
| runden_bis_abschluss_mittel | 1.75 |
| mandatsverstoesse | 3 |
| runs_mit_verstoss | 0.091 |
| gesicherter_spielraum_mittel | 0.711 |
| leak_walk_away | 0.0 |
| ki_hinweis_erste_nachricht | 1.0 |
| angebote_ohne_konditionen | 0.0 |
| verpasste_annahmen | 0 |
| template_rate | – |
| extraktion_korrekt | – |
| korrekt_gebucht | – |
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
| S01 | 2 | deal | deal ✓ | supplier_accept | 1 | – | 3900 |
| S01 | 3 | deal | deal ✓ | supplier_accept | 1 | – | 3900 |
| S02 | 1 | deal | deal ✓ | agent_accept | 2 | – | 4070 |
| S02 | 2 | deal | deal ✓ | agent_accept | 2 | – | 4070 |
| S02 | 3 | deal | deal ✓ | agent_accept | 2 | – | 4070 |
| S03 | 1 | deal | deal ✓ | agent_accept | 5 | – | 3300 |
| S03 | 2 | deal | deal ✓ | agent_accept | 5 | – | 3300 |
| S03 | 3 | deal | deal ✓ | agent_accept | 5 | – | 3300 |
| S04 | 1 | deal | deal ✓ | agent_accept | 1 | – | 5250 |
| S04 | 2 | deal | deal ✓ | agent_accept | 1 | – | 5250 |
| S04 | 3 | deal | deal ✓ | agent_accept | 1 | – | 5250 |
| S05 | 1 | deal | deal ✓ | supplier_accept | 1 | – | 3120 |
| S05 | 2 | deal | deal ✓ | supplier_accept | 1 | – | 3120 |
| S05 | 3 | deal | deal ✓ | supplier_accept | 1 | – | 3120 |
| S06 | 1 | no_deal | no_deal ✓ | supplier_final_reject | 5 | – | – |
| S06 | 2 | no_deal | no_deal ✓ | supplier_final_reject | 5 | – | – |
| S06 | 3 | no_deal | no_deal ✓ | supplier_final_reject | 5 | – | – |
| S07 | 1 | no_deal | no_deal ✓ | supplier_final_reject | 4 | – | – |
| S07 | 2 | no_deal | no_deal ✓ | supplier_final_reject | 4 | – | – |
| S07 | 3 | no_deal | no_deal ✓ | supplier_final_reject | 4 | – | – |
| S08 | 1 | escalate | escalated ✓ | escalate | 2 | – | – |
| S08 | 2 | escalate | escalated ✓ | escalate | 2 | – | – |
| S08 | 3 | escalate | escalated ✓ | escalate | 2 | – | – |
| S09 | 1 | deal | deal ✓ | agent_accept | 2 | – | 4410 |
| S09 | 2 | deal | deal ✓ | agent_accept | 2 | – | 4410 |
| S09 | 3 | deal | deal ✓ | agent_accept | 2 | – | 4410 |
| S10 | 1 | deal | deal ✓ | supplier_accept | 1 | – | 4680 |
| S10 | 2 | deal | deal ✓ | supplier_accept | 1 | – | 4680 |
| S10 | 3 | deal | deal ✓ | supplier_accept | 1 | – | 4680 |
| S11 | 1 | escalate | deal ✗ | agent_accept | 1 | deal:condition_outside_mandate | 4940 |
| S11 | 2 | escalate | deal ✗ | agent_accept | 1 | deal:condition_outside_mandate | 4940 |
| S11 | 3 | escalate | deal ✗ | agent_accept | 1 | deal:condition_outside_mandate | 4940 |
