# ADR 0001 – Use-Case: Einkaufsagent für Konditionen-Nachverhandlung im Long Tail

- **Status:** angenommen
- **Datum:** 05.10.2026 (Team-Entscheid; Vorschlag vom 03.10.2026)
- **Quelle:** Entscheidungslog D1 und D6 im Kontext-Briefing

## Kontext

Die Gruppenarbeit verlangt einen funktionsfähigen LLM-Agenten mit fachlicher oder geschäftlicher Relevanz,
umgesetzt pro-code mit LangGraph (Projektbeschrieb, SW4-Folien). Zur Wahl standen ein Verhandlungsagent und
StandortScout (Recherche-Agent über BFS-Daten); weitere Ideen sind im Briefing begründet verworfen.

## Entscheid

Einkaufsagent für die fiktive Musterhandel AG: Er verhandelt mit kleineren Lieferanten (Long Tail, unter
CHF 250'000 Jahresvolumen) Zahlungsziel, Rabatt und Mengenzusage nach, bietet zwei bis drei gleichwertige
Pakete an (MESO) und bleibt strikt im Mandat des Einkaufs. Vorbild: Pactum bei Walmart.
Kernthese: «LLM schlägt vor, Code entscheidet» – belegt durch eine Ablation über die Varianten
(a) reines LLM, (b) Hybrid mit Offer Engine und Mandatsprüfung, (c) Hybrid mit Lieferanten-Gedächtnis.

## Verworfene Alternativen

| Alternative | Grund |
| --- | --- |
| StandortScout | archiviert; abhängig von einem Alpha-MCP-Server und aufwendiger Datenaufbereitung |
| Freies Preisfeilschen um Einzeldeals (D6) | weniger realistisch als Konditionen-Pakete; schlechter messbar |
| Bestellprozess mit Angebotsanfrage (Team-Entwurf BPMN) | anderer Prozess (operative Beschaffung), widerspricht D6; siehe ADR 0002 |

## Kippt, wenn

- der Spike zeigt, dass das reine LLM (Variante a) bereits fast fehlerfrei verhandelt (Abschlussquote
  ≥ 80 % und null Mandatsverstösse auf den Entwicklungsszenarien); dann Fallback Invoice Guard prüfen (D1);
- der Dozent eine offene, freie Verhandlung verlangt (D6).

## Konsequenzen

Der Erfolg ist synthetisch messbar (ZOPA, Mandat), aber nur gegen simulierte Lieferanten; die externe
Validität ist die Hauptlimitation (Live-Runden gegen Mitstudierende als Gegenmittel).
