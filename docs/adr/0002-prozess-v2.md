# ADR 0002 – Soll-Prozess v2: Code bewertet, LLM extrahiert und formuliert

- **Status:** angenommen am 11.10.2026 nach Team-Feedback; als Zeichnung gilt die schlanke Fassung
  `einkaufsagent-prozess_v2.bpmn` (ADR 0007), Punkt 5 ist durch ADR 0008 präzisiert
- **Datum:** 05.10.2026, angepasst 11.10.2026
- **Artefakte:** `einkaufsagent-prozess_v1.bpmn` (diese Fassung), `einkaufsagent-prozess_v2.bpmn` (gültig),
  Mapping in `docs/process/README.md`

## Kontext

Zwei Entwürfe lagen vor: der Team-Entwurf (PNG) und `einkaufsagent-prozess.bpmn` aus der Vorsession (v1).
Der Team-Entwurf modelliert einen Bestellprozess ohne Pools, Nachrichtenflüsse und Rundenlimit; v1 hat zwei
bpmnlint-Befunde (fake-join), eine unbegrenzte Korrekturschleife und bucht eine «Annahme» allein auf Basis der
LLM-Klassifikation.

## Entscheid

v2 übernimmt die Struktur von v1 und drei Ideen des Team-Entwurfs. Die Kernpunkte:

1. **Antwort: LLM extrahiert, Code bewertet.** `parse_response` liefert strukturierte Daten; `assess_response`
   entscheidet deterministisch. Annahme nur, wenn das gewählte Paket zu einem gesendeten passt.
2. **Gegenangebot annehmen nach AC_next** (aus dem Team-Entwurf): im Mandat und mindestens so viel wert wie
   das eigene nächste Angebot. Spart Runden; Muster aus Baarslag et al., «Acceptance Conditions in Automated
   Negotiation».
3. **Weitere Abbruchkriterien** neben dem Rundenlimit: «kein Paket mehr offen» (aus dem Team-Entwurf) und
   «Lieferant lehnt endgültig ab». Ein annehmbares Gegenangebot ist auch in der letzten Runde eine Einigung.
4. **Fail-safe statt Korrekturschleife:** Verletzt eine formulierte Nachricht das Mandat, geht ein
   deterministischer Standardtext hinaus. Die Template-Rate wird zur Metrik.
5. **Eskalation** auch bei unklarer Antwort und nach 48 h ohne Antwort; LLM bereitet auf, Mensch entscheidet
   per Interrupt (weiter, ggf. mit erweitertem Mandat, abbrechen oder übernehmen). Seit 11.10.2026: Eskaliert wird
   nur, wenn das Mandat den Entscheid nicht abdeckt; Behauptungen über Zusagen ändern das Mandat nie (ADR 0008).
   Den Timer hat ADR 0007 gestrichen.
6. **Jeder Ausgang** teilt dem Lieferanten das Ergebnis mit und schreibt Protokoll und Gedächtnis.
7. **Datenspeicher sichtbar** (aus dem Team-Entwurf): ERP-Mock und Lieferanten-Gedächtnis. In `_v2` ein Speicher:
   ERP-Adapter mit Historie als Gedächtnis (ADR 0005, 0007), dazu die Einkaufsrichtlinie (RAG).

## Verworfene Alternativen

| Alternative | Grund |
| --- | --- |
| LLM klassifiziert die Antwort und routet direkt (v1) | eine Fehlklassifikation bucht einen falschen Deal; Prompt Injection wirkt direkt auf den Router |
| Korrekturschleife bis zur gültigen Nachricht (v1) | unbegrenzt, Kosten ohne Ergebnis; nicht deterministisch |
| Ein Paket nach dem anderen (Team-Entwurf) | widerspricht MESO (D6, US3); verrät die Konzessionsreihenfolge |

## Kippt, wenn

die Template-Rate in Variante (b) über 20 % liegt (dann eine begrenzte Korrekturrunde mit Rückmeldung des
Guards testen) oder die Einkäuferin Eskalationen nicht innerhalb einer Minute entscheiden kann (US4).

## Konsequenzen

Mehr Nodes (13 statt 10 im SW4-Graphen), dafür ist jeder Entscheid über Zahlen und Mandat im Code und testbar. Variante (a)
fasst die Schritte 3–9 bewusst in einem LLM-Node zusammen; sie ist die Baseline der Ablation.
