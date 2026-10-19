# ADR 0010 – Synthetische Daten: Code würfelt, LLM kleidet ein, Code prüft

- **Status:** angenommen am 19.10.2026
- **Datum:** 19.10.2026
- **Ersetzt:** in ADR 0003 und CLAUDE.md die Vorgabe, dass eine andere Person das Testset entwirft
- **Berührt:** `scripts/build_scenarios.py`, Simulator-Textvorlagen, ADR 0008 (Testset-Kategorien), ADR 0011 (Spike)

## Kontext

Das zurückgehaltene Testset sollte eine andere Person entwerfen, weil Dev-Szenarien und Regel-Referenz aus derselben
Hand stammen. Bis heute hat niemand Szenarien geliefert, und Daten von Hand zu erstellen kostet Zeit, die im Projekt
fehlt. Gebraucht werden: Testset (10–15 Szenarien), Umformulierungen der Simulator-Texte (Robustheit der Extraktion,
Spike in ADR 0011), Angriffstexte, eine kurze Einkaufsrichtlinie, Verhandlungshistorie für Variante (c) und
Bias-Varianten.

Die trennende Achse ist **Unabhängigkeit und Realismus der Daten gegen Handarbeit**.

## Entscheid

Die Daten folgen derselben Arbeitsteilung wie der Agent:

1. **Code würfelt.** Mandat, heutige Konditionen und verdeckte Lieferantenparameter zieht `build_scenarios.py` mit
   Seed aus einem Raster. Der Code rechnet ZOPA und erwartetes Ergebnis.
2. **LLM kleidet ein.** Das LLM schreibt nur Texte: Lieferant und Branche, Forderungs-, Bedingungs- und Angriffstexte,
   Umformulierungen, Richtlinie.
3. **Code prüft.** Jede Zahl im Text muss zu den Parametern passen (Regex: dieselben Zahlen, keine neuen), Labels
   bleiben erhalten, Dubletten fallen weg. Alle Testset-Szenarien und eine Stichprobe von 20
   Umformulierungen werden von Hand gelesen (0 Fehler in 20 heisst mit 95 % Sicherheit höchstens 15 % Fehler).
4. **Einfrieren.** Einmal erzeugt, liegen die Daten als JSONL im Repo, mit Modell, Datum und Prompt; sie werden nie neu
   erzeugt. Die Evaluation bleibt hermetisch (D4).

**Generator:** Claude Opus über Claude Code (Claude-Subscription). Er gehört nicht zur Familie des Agenten
(OpenAI, `gpt-5.6-luna`) und ist stärker als die geprüften Modelle; stärkere Generatoren schreiben schwierigere
Testtexte. Prompts, Modell und Datum stehen in einer README neben den Daten. Weil Claude Haiku 5.5 zur selben Familie
gehört, fällt es als Kandidat aus dem Spike (ADR 0011).

| Datensatz | Inhalt | Prüfung im Code | Aufwand |
| --- | --- | --- | --- |
| Umformulierungen | 5 pro Simulator-Vorlage; der Simulator wählt per Seed | Zahlen und Ereignis unverändert | 2 h |
| Testset | 12–15 Szenarien, je Eskalationskategorie aus ADR 0008 mindestens eines, andere Bedingungen als im Prompt (Laufzeit, Exklusivität, Vorauskasse …), ein Szenario mit bindendem Rundenlimit | ZOPA und erwartetes Ergebnis aus `build_scenarios.py` | 3–4 h |
| Angriffe | 4 Muster aus AgentDojo («ignore previous», «TODO», InjecAgent, «Important message»), 2 Stile aus Tensor Trust, 3–4 harmlose Texte mit Triggerwörtern für Fehlalarme | Ziel des Angriffs ist im Szenario hinterlegt | 2 h |
| Einkaufsrichtlinie | rund eine Seite; Regeln für Behauptungen, Forderungen, Bedingungen | – (von Hand gelesen) | 0,5 h |
| Historie für (c) | Self-Play: Variante (b) gegen den Simulator im «Vorjahr», Protokolle speichern | ganz im Code, ohne LLM-Texte | 1 h |
| Bias | 3 Szenarien × 4 Lieferantennamen bzw. Herkunft, sonst gleich | gleiche verdeckte Parameter und Seeds | 1 h |

## Verworfene Alternativen

| Alternative | Grund |
| --- | --- |
| Daten von Hand oder durch eine andere Person | 6–10 h; bisher hat niemand geliefert |
| LLM erzeugt alles inklusive erwartetem Ergebnis | falsche Labels; Modelle schneiden auf selbst erzeugten Benchmarks besser ab (arXiv 2505.20738) |
| Mistral Large 3 über den Proxy als Generator | neutral zu allen Kandidaten und per Skript wiederholbar, aber schwächere Texte; da die Daten eingefroren werden, zählt die Qualität mehr als die Wiederholbarkeit |
| Haiku 5.5 als Generator | gleiche Familie wie ein Spike-Kandidat |

## Kippt, wenn

- ein Teammitglied doch Szenarien liefert: dann als zusätzliche Hälfte des Testsets, getrennt ausgewertet;
- die Stichprobe mehr als 2 fehlerhafte von 20 Umformulierungen zeigt: Prompt verschärfen und neu erzeugen, bevor
  eingefroren wird;
- der Agent auf ein Anthropic-Modell wechselt: dann erzeugt ein Modell einer dritten Familie das Testset neu.

## Konsequenzen

- Limitation für Präsentation und Prüfung: eine andere Modellfamilie statt einer anderen Person; synthetische Texte
  sind sauberer und meist leichter als echte (arXiv 2505.22830). Die Wahrheit (ZOPA, erwartetes Ergebnis) rechnet der
  Code; Fehler in den Labels fallen damit weg.
- Neue Metriken in `docs/eval-metriken.md`: Erfolgsquote der Angriffe, Fehlalarme, Kippen der Extraktion bei
  Umformulierung, Unterschiede nach Lieferantenname.
- Prüfungsbegründung: «Die Daten folgen derselben Arbeitsteilung wie der Agent: Das LLM liefert die sprachliche
  Vielfalt, der Code legt die Zahlen fest und rechnet die richtige Antwort aus. Ein Modell einer anderen Familie
  schreibt die Texte, damit der Agent nicht gegen seinen eigenen Stil getestet wird.»

## Quellen

- Modelle schneiden auf selbst erzeugten Benchmarks besser ab: arXiv 2505.20738 (NeurIPS 2025).
- «Preference Leakage» bei verwandten Generator- und Prüfmodellen: arXiv 2502.01534 (ICLR 2026).
- Synthetische Varianten sind meist leichter als menschliche Originale: arXiv 2505.22830.
- AgentDojo: arXiv 2406.13352 (NeurIPS 2024); Tensor Trust: arXiv 2311.01011 (ICLR 2024).
- «Rule of three»: Hanley & Lippman-Hand, JAMA, 1983.
- Stand der Recherche 19.10.2026; Titel und Autoren vor der Präsentation im Original nachlesen.
