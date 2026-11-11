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

## Nachtrag 11.11.2026: Gegenstand sind Jahreskonditionen, nicht einzelne Bestellungen

**Anlass.** Frage des Nutzers vom 10.11.2026: Verhandeln wir Rahmenkonditionen für ein Jahr oder einzelne Lieferungen,
und steht das samt Begründung irgendwo? Die Nutzenformel rechnet pro Jahr, und S11 setzt einen Rahmenvertrag über
12 Monate voraus; ausdrücklich beschrieben war es nicht. Das ist eine Präzisierung, kein neuer Entscheid: Domäne, Graph
und Eval bleiben unverändert.

**Gegenstand.** Die Jahreskonditionen im bestehenden Rahmenvertrag (Laufzeit 12 Monate). Sie gelten im ERP für jede
Bestellung der nächsten 12 Monate:
- Zahlungsziel: Tage ab Rechnung, für jede Rechnung;
- Rabatt: % auf jeden Rechnungsbetrag;
- Mengenzusage: verbindliche Mindestabnahme der Musterhandel AG über die 12 Monate, in % des Vorjahresvolumens; für uns
  ein Abnahmerisiko (Risikokostensatz im Mandat), für den Lieferanten Planungssicherheit.

Der Nutzen eines Pakets ist deshalb ein Jahreswert in CHF (`domain.buyer_value_chf`). Die Laufzeit selbst verhandelt der
Agent nicht; eine Bedingung dazu geht an die Einkäuferin (S11, ADR 0008).

**Warum nicht pro Bestellung**
1. Hebel: Einmal verhandelt, gilt es für jede Bestellung des Jahres. Pro Bestellung brächte ein Gespräch im Long Tail
   wenig, und der Lieferant müsste bei jeder Bestellung verhandeln.
2. Mengenzusage und Zahlungsziel (Working Capital) ergeben nur über einen Zeitraum Sinn; bei einer einzelnen Bestellung
   ist die Menge die Bestellung.
3. Messbar: ein Jahreswert pro Szenario und eine bekannte richtige Antwort.
4. Anderer Prozess: Verhandeln pro Bestellung gehört in die operative Beschaffung mit Angebotsanfrage (Team-Entwurf,
   schon verworfen; ADR 0002).
5. Praxis: Pactum trennt die beiden Fälle in eigene Agenten. «Campaigns» verhandeln «supplier-level terms» und sind
   «especially valuable at annual contract renewals»; als Beispiel nennt Pactum «a tail spend campaign across 1,240
   suppliers under $250k a year». Der Agent «Single-Source Negotiation» verhandelt einzelne Bedarfsanforderungen vor der
   Bestellung (Herstellerangaben, pactum.com, ohne Datum, nachgelesen am 11.11.2026; `docs/gesamtsystem.md` §2.5).

| Alternative | Grund |
| --- | --- |
| Pro Bestellung bzw. Bedarfsanforderung verhandeln (wie Pactum «Single-Source») | anderer Prozess (operative Beschaffung), wenig Wert pro Gespräch, Mengenzusage ohne Sinn; passt zu einmaligen Beschaffungen, nicht zu wiederkehrenden Warenlieferungen |

**Wo es steht:** `docs/gesamtsystem.md` §1, §2.1, §2.5 und §7; Spielkarten (`docs/demo.md` §4); in der Web-UI die
Einladung vor dem Chat (ADR 0016, Nachtrag 11.11.2026); Folien 2 und 3.

**Kippt, wenn** die Musterhandel AG einmalige Beschaffungen ohne Rahmenvertrag nachverhandeln will: dann ein eigener
Prozess pro Bedarfsanforderung (Gegenstand Preis und Lieferzeit), nicht dieser Agent.
