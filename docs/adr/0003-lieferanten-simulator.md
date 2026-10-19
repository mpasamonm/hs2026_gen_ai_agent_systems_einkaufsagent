# ADR 0003 – Regelbasierter Lieferanten-Simulator mit verdeckten Parametern

- **Status:** angenommen für KW42; seit 19.10.2026 Simulator für die ganze Eval. Der LLM-Simulator entfällt
  (ADR 0009: Mensch als Lieferant in Demo und Live-Runden); das Testset entsteht nach ADR 0010 statt durch eine andere
  Person
- **Datum:** 05.10.2026
- **Berührt:** D7 (Agent und Simulator aus unterschiedlichen Modellfamilien), Briefing-Architektur
  «Lieferanten-Simulatoren: LLM plus Parameter»

## Kontext

Variante (a) braucht ein Gegenüber, das reproduzierbar, billig und mit bekannter Wahrheit (ZOPA) antwortet.
Die Achse der Alternativen ist **Reproduzierbarkeit gegen Realismus**.

## Entscheid

Für KW42 ein regelbasierter Simulator (`supplier_sim.py`):

- Nettokosten des Lieferanten pro Jahr aus verdeckten Sätzen (Kapitalkosten, Wert einer Mengenzusage).
- Rundenabhängiges Konzessionsbudget nach Faratin, Sierra und Jennings (1998), Exponent β (Boulware/Conceder),
  Geduld in Runden.
- Gegenangebot = bestes eigenes Paket, Zahlungsziel und Rabatt so weit gekürzt, dass es ins Budget passt.
- Optional: Forderung ausserhalb des Mandats (Runde 1) und Prompt-Injection-Text (ab Runde n).
- Deutsche Textvorlagen, Auswahl über `seed` reproduzierbar.
- Verdeckte Parameter stehen im Szenario unter `hidden`, gehen nur in den Simulator (Closure) und in die
  Auswertung. Ein Canary-Test sichert, dass sie nie im State oder Prompt landen.

Der LLM-Simulator mit vier Charakteren bleibt geplant, als Robustheitstest ab KW46; dann gilt D7.

## Verworfene Alternativen

| Alternative | Grund |
| --- | --- |
| LLM-Persona als Lieferant | Ergebnis streut von Lauf zu Lauf; Modellwahl verschiebt die Aufteilung um 7–18 Prozentpunkte (arXiv 2608.07538); doppelte Kosten |
| Menschen als Lieferant | nicht skalierbar; nur als Validierung (rund 10 Live-Runden) |

## Kippt, wenn

die Agenten die Textvorlagen ausnutzen (z.B. Muster in den Formulierungen erkennen) oder die Dozierenden
realistischere Gegenüber verlangen; dann LLM-Persona mit denselben verdeckten Parametern als Entscheidungslogik.

## Konsequenzen

Der Simulator bewertet die strukturierten Pakete, nicht den Text. Die Regel-Referenz (`RuleBasedPolicy`) löst
alle 10 Szenarien; Szenarien und Referenz stammen aber aus derselben Hand, deshalb muss das zurückgehaltene
Testset von einer anderen Person entworfen werden.
