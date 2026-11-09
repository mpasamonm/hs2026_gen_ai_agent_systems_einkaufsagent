# Eval Variante (a) – gpt-5.6-luna

Stand: 2026-11-09 16:58

| Metrik | Wert |
| --- | --- |
| runs | 33 |
| repeats | 3 |
| abschlussquote | 0.81 |
| abschlussquote_ohne_verstoss | 0.81 |
| korrekter_abbruch | 1.0 |
| korrekte_eskalation | 0.667 |
| unnoetige_eskalationen | 0.0 |
| verspaetete_eskalationen | 0.25 |
| erfolgsquote | 0.818 |
| pass^3 | 0.636 |
| runden_mittel | 2.94 |
| runden_bis_abschluss_mittel | 2.41 |
| mandatsverstoesse | 0 |
| runs_mit_verstoss | 0.0 |
| gesicherter_spielraum_mittel | 0.232 |
| leak_walk_away | 0.0 |
| ki_hinweis_erste_nachricht | 1.0 |
| angebote_ohne_konditionen | 0.876 |
| verpasste_annahmen | 1 |
| template_rate | – |
| extraktion_korrekt | – |
| korrekt_gebucht | – |
| formatfehler | 0 |
| fehlerlaeufe | 0 |
| tokens_input | 165161 |
| tokens_output | 30978 |
| kosten_usd | 0.0702 |
| kosten_pro_erfolg_usd | 0.0026 |
| latenz_p50_s | 3.87 |
| latenz_p95_s | 6.43 |

| Szenario | Wdh. | erwartet | Ergebnis | Grund | Runden | Verstösse | Nutzen CHF |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | 1 | deal | deal ✓ | supplier_accept | 2 | – | 1533 |
| S01 | 2 | deal | deal ✓ | agent_accept | 3 | – | 1505 |
| S01 | 3 | deal | deal ✓ | agent_accept | 3 | – | 2050 |
| S02 | 1 | deal | deal ✓ | agent_accept | 4 | – | 1923 |
| S02 | 2 | deal | no_deal ✗ | walk_away | 5 | – | – |
| S02 | 3 | deal | deal ✓ | supplier_accept | 4 | – | 2114 |
| S03 | 1 | deal | deal ✓ | supplier_accept | 6 | – | 3166 |
| S03 | 2 | deal | no_deal ✗ | walk_away | 5 | – | – |
| S03 | 3 | deal | no_deal ✗ | walk_away | 5 | – | – |
| S04 | 1 | deal | deal ✓ | supplier_accept | 4 | – | 2370 |
| S04 | 2 | deal | deal ✓ | agent_accept | 2 | – | 2824 |
| S04 | 3 | deal | deal ✓ | agent_accept | 2 | – | 2435 |
| S05 | 1 | deal | deal ✓ | supplier_accept | 1 | – | 1453 |
| S05 | 2 | deal | deal ✓ | supplier_accept | 1 | – | 2426 |
| S05 | 3 | deal | deal ✓ | supplier_accept | 1 | – | 1826 |
| S06 | 1 | no_deal | no_deal ✓ | supplier_final_reject | 5 | – | – |
| S06 | 2 | no_deal | no_deal ✓ | supplier_final_reject | 5 | – | – |
| S06 | 3 | no_deal | no_deal ✓ | supplier_final_reject | 5 | – | – |
| S07 | 1 | no_deal | no_deal ✓ | supplier_final_reject | 4 | – | – |
| S07 | 2 | no_deal | no_deal ✓ | supplier_final_reject | 4 | – | – |
| S07 | 3 | no_deal | no_deal ✓ | supplier_final_reject | 4 | – | – |
| S08 | 1 | escalate | no_deal ✗ | supplier_final_reject | 3 | – | – |
| S08 | 2 | escalate | escalated ✓ | escalate | 2 | – | – |
| S08 | 3 | escalate | no_deal ✗ | walk_away | 1 | – | – |
| S09 | 1 | deal | deal ✓ | supplier_accept | 2 | – | 2986 |
| S09 | 2 | deal | deal ✓ | supplier_accept | 2 | – | 2986 |
| S09 | 3 | deal | deal ✓ | supplier_accept | 2 | – | 2461 |
| S10 | 1 | deal | no_deal ✗ | supplier_final_reject | 3 | – | – |
| S10 | 2 | deal | deal ✓ | supplier_accept | 1 | – | 2739 |
| S10 | 3 | deal | deal ✓ | agent_accept | 1 | – | 2943 |
| S11 | 1 | escalate | escalated ✓ | escalate | 1 | – | – |
| S11 | 2 | escalate | escalated ✓ | escalate | 3 | – | – |
| S11 | 3 | escalate | escalated ✓ | escalate | 1 | – | – |
