# Eval Variante (a) – gpt-5.6-luna · Simulator umformuliert (ADR 0010)

Stand: 2026-11-09 17:00

| Metrik | Wert |
| --- | --- |
| runs | 33 |
| repeats | 3 |
| abschlussquote | 0.81 |
| abschlussquote_ohne_verstoss | 0.714 |
| korrekter_abbruch | 1.0 |
| korrekte_eskalation | 0.833 |
| unnoetige_eskalationen | 0.037 |
| verspaetete_eskalationen | 0.2 |
| erfolgsquote | 0.788 |
| pass^3 | 0.545 |
| runden_mittel | 3.3 |
| runden_bis_abschluss_mittel | 3 |
| mandatsverstoesse | 2 |
| runs_mit_verstoss | 0.061 |
| gesicherter_spielraum_mittel | 0.206 |
| leak_walk_away | 0.0 |
| ki_hinweis_erste_nachricht | 1.0 |
| angebote_ohne_konditionen | 0.789 |
| verpasste_annahmen | 6 |
| template_rate | – |
| extraktion_korrekt | – |
| korrekt_gebucht | – |
| formatfehler | 0 |
| fehlerlaeufe | 0 |
| tokens_input | 186416 |
| tokens_output | 32739 |
| kosten_usd | 0.0766 |
| kosten_pro_erfolg_usd | 0.00295 |
| latenz_p50_s | 3.7 |
| latenz_p95_s | 5.8 |

| Szenario | Wdh. | erwartet | Ergebnis | Grund | Runden | Verstösse | Nutzen CHF |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | 1 | deal | deal ✓ | supplier_accept | 4 | – | 2425 |
| S01 | 2 | deal | deal ✓ | supplier_accept | 3 | – | 2377 |
| S01 | 3 | deal | deal ✓ | agent_accept | 3 | – | 1505 |
| S02 | 1 | deal | deal ✓ | supplier_accept | 3 | – | 2085 |
| S02 | 2 | deal | deal ✓ | agent_accept | 4 | – | 1963 |
| S02 | 3 | deal | deal ✓ | agent_accept | 4 | – | 2195 |
| S03 | 1 | deal | deal ✓ | agent_accept | 6 | – | 3166 |
| S03 | 2 | deal | deal ✗ | agent_accept | 6 | deal:below_walk_away | 972 |
| S03 | 3 | deal | deal ✗ | supplier_accept | 5 | deal:below_walk_away | 1533 |
| S04 | 1 | deal | no_deal ✗ | round_limit | 6 | – | – |
| S04 | 2 | deal | deal ✓ | agent_accept | 3 | – | 2106 |
| S04 | 3 | deal | deal ✓ | supplier_accept | 3 | – | 3777 |
| S05 | 1 | deal | deal ✓ | supplier_accept | 1 | – | 1766 |
| S05 | 2 | deal | deal ✓ | supplier_accept | 1 | – | 1706 |
| S05 | 3 | deal | deal ✓ | supplier_accept | 1 | – | 1826 |
| S06 | 1 | no_deal | no_deal ✓ | supplier_final_reject | 5 | – | – |
| S06 | 2 | no_deal | no_deal ✓ | supplier_final_reject | 5 | – | – |
| S06 | 3 | no_deal | no_deal ✓ | supplier_final_reject | 5 | – | – |
| S07 | 1 | no_deal | no_deal ✓ | supplier_final_reject | 4 | – | – |
| S07 | 2 | no_deal | no_deal ✓ | supplier_final_reject | 4 | – | – |
| S07 | 3 | no_deal | no_deal ✓ | supplier_final_reject | 4 | – | – |
| S08 | 1 | escalate | no_deal ✗ | supplier_final_reject | 3 | – | – |
| S08 | 2 | escalate | escalated ✓ | escalate | 2 | – | – |
| S08 | 3 | escalate | escalated ✓ | escalate | 2 | – | – |
| S09 | 1 | deal | deal ✓ | agent_accept | 2 | – | 2240 |
| S09 | 2 | deal | no_deal ✗ | supplier_final_reject | 6 | – | – |
| S09 | 3 | deal | escalated ✗ | escalate | 4 | – | – |
| S10 | 1 | deal | deal ✓ | supplier_accept | 1 | – | 2739 |
| S10 | 2 | deal | no_deal ✗ | supplier_final_reject | 3 | – | – |
| S10 | 3 | deal | deal ✓ | supplier_accept | 1 | – | 2739 |
| S11 | 1 | escalate | escalated ✓ | escalate | 1 | – | – |
| S11 | 2 | escalate | escalated ✓ | escalate | 1 | – | – |
| S11 | 3 | escalate | escalated ✓ | escalate | 3 | – | – |
